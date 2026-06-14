from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from html import escape
from starlette.middleware.base import BaseHTTPMiddleware

from finance import db
from finance import auth
from finance.csv_import import parse_csob_csv
from finance.providers import claude as claude_provider
from finance.providers.enablebanking import from_env as enablebanking_from_env

load_dotenv()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _fmt(amount: float, currency: str = "", decimals: int = 0) -> str:
    sign = "-" if amount < 0 else ""
    s = f"{abs(amount):,.{decimals}f}".replace(",", " ")
    return f"{sign}{s}{(' ' + currency) if currency else ''}"


_BUFFER_TARGET_CZK = float(os.getenv("BUFFER_TARGET_CZK", "50000"))
_BUFFER_CATEGORY_NAME = os.getenv("BUFFER_CATEGORY_NAME", "Sporenie")
_BUFFER_PER_PAYCHECK_CZK = float(os.getenv("BUFFER_PER_PAYCHECK_CZK", "5000"))
_MASTER_PLAN_START = os.getenv("MASTER_PLAN_START", "2026-05-13")


_CASHFLOW_CURRENCIES = {"CZK"}


def _daily_cashflow(today: date, currency: str = "CZK") -> dict:
    """Daily expense bars for the current month (all currencies → CZK)."""
    month_key = today.strftime("%Y-%m")
    days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    n_days = days_in_month.day
    daily = [0.0] * n_days
    income_total = expense_total = 0.0
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.booking_date, t.credit_debit, t.amount, t.currency, c.kind "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE substr(t.booking_date, 1, 7) = ? "
            "AND COALESCE(t.hidden, 0) = 0",
            (month_key,),
        ):
            if r["kind"] == "transfer":
                continue
            try:
                amt = float(r["amount"])
            except (TypeError, ValueError):
                continue
            if r["currency"] != "CZK":
                converted = db.to_czk(amt, r["currency"], r["booking_date"])
                if converted is None:
                    continue
                amt = converted
            try:
                day = int(r["booking_date"][8:10])
            except (TypeError, ValueError, IndexError):
                continue
            if r["credit_debit"] == "CRDT":
                income_total += amt
            else:
                expense_total += amt
                if 1 <= day <= n_days:
                    daily[day - 1] += amt
    peak = max(daily) if daily else 0.0
    bars = []
    for i, v in enumerate(daily, start=1):
        bars.append({
            "day": i,
            "amount": v,
            "amount_label": _fmt(v),
            "pct": int(round((v / peak) * 100)) if peak else 0,
            "is_today": i == today.day,
            "is_future": i > today.day,
        })
    net = income_total - expense_total
    return {
        "month": month_key,
        "currency": currency,
        "bars": bars,
        "income": _fmt(income_total),
        "expense": _fmt(expense_total),
        "net": ("+" if net >= 0 else "") + _fmt(net),
        "net_pos": net >= 0,
        "n_days": n_days,
        "today_day": today.day,
    }


def _cashflow_history(today: date, months: int = 6) -> dict:
    keys: list[str] = []
    cursor = today.replace(day=1)
    for _ in range(months):
        keys.append(cursor.strftime("%Y-%m"))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    keys.reverse()
    by_ccy: dict[str, dict[str, dict[str, float]]] = {"CZK": {k: {"in": 0.0, "out": 0.0} for k in keys}}
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT substr(t.booking_date, 1, 7) AS m, t.booking_date, t.currency, "
            "t.credit_debit, t.amount, c.kind "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE substr(t.booking_date, 1, 7) IN (" + ",".join("?" * len(keys)) + ") "
            "AND COALESCE(t.hidden, 0) = 0",
            keys,
        ):
            if r["kind"] == "transfer":
                continue
            try:
                amt = float(r["amount"])
            except (TypeError, ValueError):
                continue
            if r["currency"] != "CZK":
                converted = db.to_czk(amt, r["currency"], r["booking_date"])
                if converted is None:
                    continue
                amt = converted
            slot = by_ccy["CZK"][r["m"]]
            if r["credit_debit"] == "CRDT":
                slot["in"] += amt
            else:
                slot["out"] += amt
    series = {}
    for ccy, monthly in by_ccy.items():
        rows = []
        peak = 0.0
        for k in keys:
            d = monthly[k]
            peak = max(peak, d["in"], d["out"])
            rows.append({
                "month": k[5:],
                "income": d["in"],
                "expense": d["out"],
                "net": d["in"] - d["out"],
            })
        for r in rows:
            r["in_pct"] = int(round((r["income"] / peak) * 100)) if peak else 0
            r["out_pct"] = int(round((r["expense"] / peak) * 100)) if peak else 0
            r["income_label"] = _fmt(r["income"])
            r["expense_label"] = _fmt(r["expense"])
            r["net_label"] = ("+" if r["net"] >= 0 else "") + _fmt(r["net"])
            r["net_pos"] = r["net"] >= 0
        series[ccy] = rows
    return {"currencies": [{"currency": c, "rows": series[c]} for c in sorted(series.keys())]}


def _buffer_progress(today: date) -> dict:
    year = today.year
    saved = 0.0
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(CAST(t.amount AS REAL)), 0) AS s "
            "FROM transactions t JOIN categories c ON c.id = t.category_id "
            "WHERE c.name = ? AND t.currency = 'CZK' "
            "AND substr(t.booking_date, 1, 4) = ? "
            "AND t.credit_debit = 'DBIT' "
            "AND COALESCE(t.hidden, 0) = 0",
            (_BUFFER_CATEGORY_NAME, str(year)),
        ).fetchone()
        if row:
            saved = float(row["s"] or 0.0)
    target = _BUFFER_TARGET_CZK
    remaining = max(0.0, target - saved)
    pct = min(100, int(round((saved / target) * 100))) if target else 0
    import math
    paychecks_left = math.ceil(remaining / _BUFFER_PER_PAYCHECK_CZK) if remaining > 0 else 0
    months_done = today.month - 1 + (today.day / 30.0)
    pace = saved / months_done if months_done > 0 else 0.0
    eta_months = int(round(remaining / pace)) if pace > 0 else None
    eta_label = None
    if eta_months is not None and eta_months > 0:
        eta_dt = today.replace(day=1)
        for _ in range(eta_months):
            eta_dt = (eta_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
        eta_label = eta_dt.strftime("%Y-%m")
    return {
        "year": year,
        "saved": _fmt(saved),
        "target": _fmt(target),
        "remaining": _fmt(remaining),
        "pct": pct,
        "paychecks_left": paychecks_left,
        "per_paycheck": _fmt(_BUFFER_PER_PAYCHECK_CZK),
        "pace": _fmt(pace) if pace > 0 else None,
        "eta": eta_label,
        "on_track": pace * 12 >= target if pace > 0 else False,
    }


def _master_plan_period(today: date) -> tuple[str, str]:
    """Return (period_start_iso, period_end_iso) for budget tracking.

    Logic: master plan started on MASTER_PLAN_START (e.g. 2026-05-13).
    - If today is in the same month as start → period = start..today
    - If today is in a later month → period = 1st-of-month..today
    """
    try:
        start = date.fromisoformat(_MASTER_PLAN_START)
    except ValueError:
        start = today.replace(day=1)
    if today.year == start.year and today.month == start.month:
        period_start = start
    else:
        period_start = today.replace(day=1)
    return period_start.isoformat(), today.isoformat()


def _master_plan_progress(today: date) -> dict:
    """Compute per-category budget vs. spent for the current master-plan period."""
    period_start, period_end = _master_plan_period(today)
    cats = db.list_categories()
    budgeted = [dict(c) for c in cats if c["monthly_budget_czk"] and c["kind"] == "expense"]
    if not budgeted:
        return {"period_start": period_start, "period_end": period_end, "rows": [],
                "total_budget": 0, "total_spent": 0, "total_remaining": 0,
                "total_pct": 0}

    spent: dict[int, float] = {c["id"]: 0.0 for c in budgeted}
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.category_id, t.booking_date, t.currency, t.amount "
            "FROM transactions t "
            "WHERE t.credit_debit = 'DBIT' "
            "AND t.booking_date >= ? AND t.booking_date <= ? "
            "AND COALESCE(t.hidden, 0) = 0 "
            "AND t.category_id IS NOT NULL",
            (period_start, period_end),
        ):
            cid = r["category_id"]
            if cid not in spent:
                continue
            try:
                amt = float(r["amount"])
            except (TypeError, ValueError):
                continue
            if r["currency"] != "CZK":
                converted = db.to_czk(amt, r["currency"], r["booking_date"])
                if converted is None:
                    continue
                amt = converted
            spent[cid] += amt

    items = []
    total_budget = total_spent = 0.0
    for c in budgeted:
        budget = float(c["monthly_budget_czk"])
        sp = spent[c["id"]]
        remaining = budget - sp
        pct = min(100, int(round((sp / budget) * 100))) if budget else 0
        items.append({
            "id": c["id"],
            "name": c["name"],
            "budget": budget,
            "budget_label": _fmt(budget),
            "spent": sp,
            "spent_label": _fmt(sp),
            "remaining": remaining,
            "remaining_label": _fmt(abs(remaining)),
            "remaining_pos": remaining >= 0,
            "pct": pct,
            "over": sp > budget,
        })
        total_budget += budget
        total_spent += sp
    items.sort(key=lambda x: x["pct"], reverse=True)
    total_remaining = total_budget - total_spent
    total_pct = min(100, int(round((total_spent / total_budget) * 100))) if total_budget else 0
    return {
        "period_start": period_start,
        "period_end": period_end,
        "rows": items,
        "total_budget_label": _fmt(total_budget),
        "total_spent_label": _fmt(total_spent),
        "total_remaining_label": _fmt(abs(total_remaining)),
        "total_remaining_pos": total_remaining >= 0,
        "total_pct": total_pct,
    }


def _sidebar_months(count: int = 12) -> list[str]:
    """Return last N months as YYYY-MM strings, most recent first."""
    out = []
    cursor = date.today().replace(day=1)
    for _ in range(count):
        out.append(cursor.strftime("%Y-%m"))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    return out


def _sb_period(sb_month: str) -> tuple[str | None, str | None]:
    """Map sb_month cookie value to (date_from, date_to) inclusive.

    Special values:
      - "all"          → (None, None)
      - "master-plan"  → (MASTER_PLAN_START, today)
      - "YYYY-MM"      → (1st, last) of that month, BUT if MASTER_PLAN_START
                         falls in that month, the month is capped at the
                         day BEFORE master plan starts (e.g. May → 01.05..12.05)
    """
    if sb_month == "all":
        return None, None
    today = date.today()
    if sb_month == "master-plan":
        return _MASTER_PLAN_START, today.isoformat()
    if len(sb_month) == 7 and sb_month[4] == "-":
        try:
            y, m = int(sb_month[:4]), int(sb_month[5:7])
        except ValueError:
            return None, None
        start = date(y, m, 1)
        nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        end = nxt - timedelta(days=1)
        try:
            mp = date.fromisoformat(_MASTER_PLAN_START)
            if mp.year == y and mp.month == m:
                end = mp - timedelta(days=1)
                if end < start:
                    return None, None  # empty period
        except ValueError:
            pass
        return start.isoformat(), end.isoformat()
    return None, None


def _sidebar_context(request: Request | None = None) -> dict:
    """Build the sidebar category-totals + sync-status block, primary currency CZK.

    Reads cookie `sb_month`: "YYYY-MM" / "master-plan" / "all" / missing.
    """
    today = date.today()
    default_month = today.strftime("%Y-%m")
    sb_month = (request.cookies.get("sb_month") if request else None) or default_month
    df, dt = _sb_period(sb_month)
    rows = db.transactions_for_summary(date_from=df, date_to=dt)
    income: dict[str, float] = {}
    expense: dict[str, float] = {}
    income_total = 0.0
    expense_total = 0.0
    for r in rows:
        try:
            amt = float(r["amount"])
        except (TypeError, ValueError):
            continue
        if r["currency"] != "CZK":
            converted = db.to_czk(amt, r["currency"], r["booking_date"])
            if converted is None:
                continue
            amt = converted
        if r["kind"] == "income" and r["credit_debit"] == "CRDT":
            income[r["category_name"]] = income.get(r["category_name"], 0.0) + amt
            income_total += amt
        elif r["kind"] == "expense" and r["credit_debit"] == "DBIT":
            expense[r["category_name"]] = expense.get(r["category_name"], 0.0) + amt
            expense_total += amt

    cats = db.list_categories()
    income_cats = [
        {"id": c["id"], "name": c["name"], "amt": _fmt(income.get(c["name"], 0.0), "CZK") if income.get(c["name"]) else None}
        for c in cats if c["kind"] == "income" and c["parent_id"] is None
    ]
    expense_cats = [
        {
            "id": c["id"],
            "name": c["name"],
            "amt": _fmt(expense.get(c["name"], 0.0), "CZK") if expense.get(c["name"]) else None,
            "budget": _fmt(c["monthly_budget_czk"]) if c["monthly_budget_czk"] else None,
        }
        for c in cats if c["kind"] == "expense" and c["parent_id"] is None
    ]
    accounts = db.list_accounts()
    return {
        "consent_warnings": db.consent_status(warn_days=14),
        "sidebar_income": income_cats,
        "sidebar_expense": expense_cats,
        "sidebar_income_total": _fmt(income_total, "CZK") if income_total else None,
        "sidebar_expense_total": _fmt(expense_total, "CZK") if expense_total else None,
        "accounts_count": len(accounts),
        "sync_status": "sync: pri requeste",
        "sb_month": sb_month,
        "sb_months_available": _sidebar_months(12),
    }

_pending_states: dict[str, dict[str, str]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Groš", lifespan=lifespan)


PUBLIC_PATHS = {"/login", "/healthz", "/logout"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS:
            return await call_next(request)
        if not auth.password_hash_from_env():
            return await call_next(request)
        token = request.cookies.get(auth.SESSION_COOKIE_NAME, "")
        if not auth.verify_session_token(token):
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", response_model=None)
def login_submit(request: Request, password: str = Form(...)):
    stored = auth.password_hash_from_env()
    if not stored or not auth.verify_password(password, stored):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Nesprávne heslo."}, status_code=401
        )
    token = auth.create_session_token()
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=token,
        max_age=auth.SESSION_LIFETIME_DAYS * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return resp


@app.get("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE_NAME, path="/")
    return resp


def _redirect_url(request: Request) -> str:
    override = os.environ.get("ENABLEBANKING_REDIRECT_URL")
    if override:
        return override
    return str(request.url_for("callback"))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, month: str | None = None, synced: str | None = None):
    accounts = db.list_accounts()
    today = date.today()
    if not month:
        month = today.strftime("%Y-%m")
    per_ccy: dict[str, dict] = {}
    tx_count = uncat_count = 0
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.credit_debit, t.amount, t.currency, t.category_id, c.kind "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE substr(t.booking_date, 1, 7) = ? AND COALESCE(t.hidden, 0) = 0",
            (month,),
        ):
            tx_count += 1
            if r["category_id"] is None:
                uncat_count += 1
            if r["kind"] == "transfer":
                continue
            try:
                amt = float(r["amount"])
            except (TypeError, ValueError):
                continue
            ccy = r["currency"] or "?"
            bucket = per_ccy.setdefault(ccy, {"income": 0.0, "expense": 0.0})
            if r["credit_debit"] == "CRDT":
                bucket["income"] += amt
            else:
                bucket["expense"] += amt

    kpi_currencies = []
    for ccy in sorted(per_ccy.keys()):
        b = per_ccy[ccy]
        net = b["income"] - b["expense"]
        kpi_currencies.append({
            "currency": ccy,
            "income": _fmt(b["income"]),
            "expense": _fmt(b["expense"]),
            "net": ("+" if net >= 0 else "") + _fmt(net),
            "net_pos": net >= 0,
        })
    kpi = {
        "currencies": kpi_currencies,
        "count": str(tx_count),
        "uncategorized": str(uncat_count),
    }

    recent = []
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.booking_date, t.counterparty_name, t.remittance_info, t.amount, "
            "t.currency, t.credit_debit, c.name AS category_name "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE COALESCE(t.hidden, 0) = 0 "
            "ORDER BY t.booking_date DESC, t.entry_reference DESC LIMIT 10"
        ):
            recent.append(dict(r))

    accounts_view = []
    with db.connect() as conn:
        for a in accounts:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE account_id = ?", (a["id"],)
            ).fetchone()[0]
            accounts_view.append({**dict(a), "tx_count": cnt})

    months = []
    for i in range(6):
        m = (today.replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m")
        if m not in months:
            months.append(m)

    buffer = _buffer_progress(today)
    cashflow = _daily_cashflow(today, currency="CZK")

    ctx = {
        "nav": "dashboard",
        "kpi": kpi,
        "recent_tx": recent,
        "accounts": accounts_view,
        "month": month,
        "months": months,
        "synced": synced,
        "buffer": buffer,
        "cashflow": cashflow,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@app.post("/categorize-ai")
def categorize_ai() -> RedirectResponse:
    txs = db.list_uncategorized_transactions(limit=200)
    if not txs:
        return RedirectResponse(url="/transactions?ai_msg=Žiadne+nezaradené+transakcie", status_code=303)
    cats = db.categories_with_parent_name()
    examples = db.list_manual_examples(limit=40)
    try:
        results = claude_provider.categorize_transactions(txs, cats, examples)
    except claude_provider.CategorizationError as e:
        return RedirectResponse(url=f"/transactions?ai_err={escape(str(e))}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/transactions?ai_err=AI+failed:+{escape(str(e)[:80])}", status_code=303)
    applied = 0
    for r in results:
        try:
            db.set_transaction_category(
                _account_id_for_ref(r["entry_reference"]),
                r["entry_reference"],
                r["category_id"],
                manual=False,
            )
            applied += 1
        except Exception:
            continue
    skipped = len(txs) - applied
    msg = f"AI+zaradila+{applied}+tx,+{skipped}+nechala+nezaradených"
    return RedirectResponse(url=f"/transactions?uncat=1&ai_msg={msg}", status_code=303)


def _account_id_for_ref(entry_ref: str) -> int:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT account_id FROM transactions WHERE entry_reference = ? LIMIT 1",
            (entry_ref,),
        ).fetchone()
        if not row:
            raise ValueError(f"tx not found: {entry_ref}")
        return row["account_id"]


@app.post("/fx-refresh")
def fx_refresh():
    """Backfill ČNB rates for all distinct non-CZK transaction dates."""
    fetched, skipped = db.backfill_fx_rates()
    return RedirectResponse(url=f"/?fx_msg=fetched+{fetched}+dates,+cached+{skipped}", status_code=303)


@app.post("/sb-month")
def set_sidebar_month(request: Request, month: str = Form(...), next: str = Form("/")):
    """Set the sidebar month filter cookie and redirect back."""
    safe_next = next if next.startswith("/") else "/"
    resp = RedirectResponse(url=safe_next, status_code=303)
    if month in ("all", "master-plan") or (len(month) == 7 and month[4] == "-"):
        resp.set_cookie("sb_month", month, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


@app.get("/graf", response_class=HTMLResponse)
def graf_view(request: Request):
    today = date.today()
    yearly = _cashflow_history(today, months=12)
    ctx = {
        "nav": "graf",
        "yearly": yearly,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "graf.html", ctx)


@app.get("/master-plan", response_class=HTMLResponse)
def master_plan_view(request: Request):
    today = date.today()
    plan = _master_plan_progress(today)
    ctx = {
        "nav": "master-plan",
        "plan": plan,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "master_plan.html", ctx)


@app.get("/categories", response_class=HTMLResponse)
def categories_view(request: Request):
    cats = [dict(c) for c in db.list_categories()]
    by_parent: dict[int | None, list] = {}
    for c in cats:
        by_parent.setdefault(c["parent_id"], []).append(c)
    roots = by_parent.get(None, [])
    ctx = {
        "nav": "categories",
        "by_parent": by_parent,
        "income_roots": [c for c in roots if c["kind"] == "income"],
        "expense_roots": [c for c in roots if c["kind"] == "expense"],
        "transfer_roots": [c for c in roots if c["kind"] == "transfer"],
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "categories.html", ctx)


@app.post("/categories/add")
def categories_add(
    name: str = Form(""),
    kind: str = Form(""),
    parent_id: str = Form(""),
) -> RedirectResponse:
    name = (name or "").strip()
    if not name or not kind:
        return RedirectResponse(url="/categories", status_code=303)
    pid = int(parent_id) if parent_id else None
    try:
        db.add_category(name, kind, pid)
    except (ValueError, sqlite3.IntegrityError):
        return RedirectResponse(url="/categories?err=add", status_code=303)
    return RedirectResponse(url="/categories", status_code=303)


@app.post("/categories/{category_id}/rename")
def categories_rename(category_id: int, name: str = Form(...)) -> RedirectResponse:
    try:
        db.rename_category(category_id, name)
    except (ValueError, sqlite3.IntegrityError):
        return RedirectResponse(url="/categories?err=rename", status_code=303)
    return RedirectResponse(url="/categories", status_code=303)


@app.post("/categories/{category_id}/delete")
def categories_delete(category_id: int) -> RedirectResponse:
    db.delete_category(category_id)
    return RedirectResponse(url="/categories", status_code=303)


@app.post("/categories/{category_id}/budget")
def categories_set_budget(category_id: int, budget: str = Form("")) -> RedirectResponse:
    """Set or clear monthly budget for a category. Empty string = unset."""
    val: float | None
    s = (budget or "").strip().replace(" ", "").replace(",", ".")
    if not s or s == "0":
        val = None
    else:
        try:
            val = float(s)
        except ValueError:
            return RedirectResponse(url="/categories?err=budget", status_code=303)
    db.set_category_budget(category_id, val)
    return RedirectResponse(url="/categories", status_code=303)


@app.get("/import", response_class=HTMLResponse)
def import_form(request: Request, ok: str | None = None, err: str | None = None):
    return templates.TemplateResponse(
        request,
        "import.html",
        {"nav": "import", "ok": ok, "err": err, **_sidebar_context(request)},
    )


@app.post("/import")
async def import_submit(file: UploadFile = File(...)) -> RedirectResponse:
    try:
        content = await file.read()
        info, txs = parse_csob_csv(content)
    except (ValueError, UnicodeDecodeError) as e:
        return RedirectResponse(url=f"/import?err={escape(str(e))}", status_code=303)
    if not txs:
        return RedirectResponse(url="/import?err=Žiadne+transakcie+v+súbore", status_code=303)

    account_no = info["account_no"] or "manual"
    currency = info["currency"]
    iban = f"CSOB-CZ-{account_no}"
    session_id = "manual-csob-cz"
    payload = {
        "session_id": session_id,
        "aspsp": {"name": "ČSOB CZ (manual)", "country": "CZ"},
        "access": {"valid_until": None},
        "accounts": [{
            "uid": iban,
            "account_id": {"iban": iban},
            "currency": currency,
            "name": f"ČSOB CZ {account_no}",
        }],
    }
    ids = db.save_session_and_accounts(payload)
    account_id = ids[0]
    inserted, updated = db.upsert_transactions(account_id, txs)
    fx_fetched, _ = db.backfill_fx_rates()
    fx_note = f"+(FX:+{fx_fetched})" if fx_fetched else ""
    msg = f"Importovaných+{inserted}+nových,+{updated}+aktualizovaných{fx_note}"
    return RedirectResponse(url=f"/import?ok={msg}", status_code=303)


@app.get("/connect/mock/{country}")
def connect_mock(country: str, request: Request) -> RedirectResponse:
    client = enablebanking_from_env()
    state = secrets.token_urlsafe(24)
    result = client.start_auth(
        aspsp_name="Mock ASPSP",
        aspsp_country=country.upper(),
        redirect_url=_redirect_url(request),
        state=state,
    )
    _pending_states[state] = {"aspsp": "Mock ASPSP", "country": country.upper()}
    return RedirectResponse(url=result["url"], status_code=302)


@app.get("/connect/{aspsp_name}/{country}")
def connect_aspsp(aspsp_name: str, country: str, request: Request) -> RedirectResponse:
    client = enablebanking_from_env()
    state = secrets.token_urlsafe(24)
    result = client.start_auth(
        aspsp_name=aspsp_name,
        aspsp_country=country.upper(),
        redirect_url=_redirect_url(request),
        state=state,
    )
    _pending_states[state] = {"aspsp": aspsp_name, "country": country.upper()}
    return RedirectResponse(url=result["url"], status_code=302)


@app.get("/callback", name="callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(400, f"Auth error: {error}")
    if not code or not state:
        raise HTTPException(400, "Missing code/state")
    if state not in _pending_states:
        raise HTTPException(400, "Unknown state")
    _pending_states.pop(state)

    client = enablebanking_from_env()
    session = client.create_session(code)
    db.save_session_and_accounts(session)
    return RedirectResponse(url="/", status_code=302)


@app.get("/accounts", response_class=HTMLResponse)
def accounts_view(request: Request):
    accounts = []
    with db.connect() as conn:
        for a in db.list_accounts():
            cnt = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE account_id = ?", (a["id"],)
            ).fetchone()[0]
            uncat = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE account_id = ? AND category_id IS NULL",
                (a["id"],),
            ).fetchone()[0]
            accounts.append({**dict(a), "tx_count": cnt, "uncat": uncat})
    ctx = {"nav": "accounts", "accounts": accounts, **_sidebar_context(request)}
    return templates.TemplateResponse(request, "accounts.html", ctx)


@app.get("/transactions", response_class=HTMLResponse)
def transactions_all(
    request: Request,
    uncat: int = 0,
    category: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    q: str | None = None,
    ai_msg: str | None = None,
    ai_err: str | None = None,
    limit: int = 500,
):
    where = ["COALESCE(t.hidden, 0) = 0"]
    args: list = []
    if uncat:
        where.append("t.category_id IS NULL")
    if category:
        where.append("t.category_id = ?")
        args.append(category)
    # Apply sidebar month filter when user hasn't set explicit dates
    sb_month_cookie = request.cookies.get("sb_month") or date.today().strftime("%Y-%m")
    if not date_from and not date_to:
        sb_from, sb_to = _sb_period(sb_month_cookie)
        if sb_from:
            where.append("t.booking_date >= ?")
            args.append(sb_from)
        if sb_to:
            where.append("t.booking_date <= ?")
            args.append(sb_to)
    if date_from:
        where.append("t.booking_date >= ?")
        args.append(date_from)
    if date_to:
        where.append("t.booking_date <= ?")
        args.append(date_to)
    if amount_min:
        where.append("CAST(t.amount AS REAL) >= ?")
        args.append(float(amount_min))
    if amount_max:
        where.append("CAST(t.amount AS REAL) <= ?")
        args.append(float(amount_max))
    if q:
        where.append("(t.counterparty_name LIKE ? OR t.remittance_info LIKE ? OR t.note LIKE ?)")
        like = f"%{q}%"
        args.extend([like, like, like])
    args.append(limit)
    sql = (
        "SELECT t.account_id, t.booking_date, t.counterparty_name, t.remittance_info, "
        "t.amount, t.currency, t.credit_debit, t.category_id, t.manual_override, "
        "t.tx_type, t.note, "
        "c.name AS category_name, a.currency AS account_currency "
        "FROM transactions t "
        "LEFT JOIN categories c ON c.id = t.category_id "
        "LEFT JOIN accounts a ON a.id = t.account_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY t.booking_date DESC, t.entry_reference DESC LIMIT ?"
    )
    with db.connect() as conn:
        txs = [dict(r) for r in conn.execute(sql, args).fetchall()]
        filter_name = None
        if category:
            row = conn.execute("SELECT name FROM categories WHERE id = ?", (category,)).fetchone()
            if row:
                filter_name = row["name"]
    ctx = {
        "nav": "tx",
        "txs": txs,
        "uncat": uncat,
        "category": category,
        "filter_category_name": filter_name,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "amount_min": amount_min or "",
        "amount_max": amount_max or "",
        "q": q or "",
        "ai_msg": ai_msg,
        "ai_err": ai_err,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "transactions_all.html", ctx)


@app.get("/sync")
def sync_all() -> RedirectResponse:
    accounts = db.list_accounts()
    if not accounts:
        return RedirectResponse(url="/accounts", status_code=302)
    client = enablebanking_from_env()
    date_from = (date.today() - timedelta(days=90)).isoformat()
    total_new = total_upd = errors = 0
    for a in accounts:
        try:
            data = client.list_transactions(a["eb_uid"], date_from=date_from)
            ins, upd = db.upsert_transactions(a["id"], data.get("transactions", []))
            total_new += ins
            total_upd += upd
        except Exception:
            errors += 1
    msg = f"synced_{len(accounts)}_accounts_{total_new}_new_{total_upd}_updated"
    if errors:
        msg += f"_{errors}_errors"
    return RedirectResponse(url=f"/?synced={msg}", status_code=302)


@app.get("/accounts/{account_id}/sync")
def sync_account(account_id: int) -> RedirectResponse:
    acc = db.get_account(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    client = enablebanking_from_env()
    date_from = (date.today() - timedelta(days=90)).isoformat()
    data = client.list_transactions(acc["eb_uid"], date_from=date_from)
    inserted, updated = db.upsert_transactions(account_id, data.get("transactions", []))
    return RedirectResponse(
        url=f"/accounts/{account_id}/tx?synced={inserted}_new_{updated}_updated",
        status_code=302,
    )


def _category_select(cats, selected: int | None, name: str = "category_id") -> str:
    opts = ['<option value="">—</option>']
    for c in cats:
        label = ("↳ " if c["parent_id"] else "") + c["name"]
        sel = " selected" if selected == c["id"] else ""
        opts.append(f'<option value="{c["id"]}"{sel}>{escape(label)}</option>')
    return f'<select name="{name}">{"".join(opts)}</select>'


@app.get("/accounts/{account_id}/tx", response_class=HTMLResponse)
def show_transactions(
    request: Request,
    account_id: int,
    synced: str | None = None,
    uncat: int = 0,
    show_hidden: int = 0,
):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    txs = db.list_transactions(
        account_id,
        only_uncategorized=bool(uncat),
        include_hidden=bool(show_hidden),
    )
    cats = db.list_categories()
    ctx = {
        "nav": "tx",
        "account": dict(account),
        "txs": [dict(t) for t in txs],
        "cats": [dict(c) for c in cats],
        "uncat": uncat,
        "show_hidden": show_hidden,
        "synced": synced,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "transactions.html", ctx)


@app.get("/rules", response_class=HTMLResponse)
def rules_view(request: Request, msg: str | None = None):
    ctx = {
        "nav": "rules",
        "rules": [dict(r) for r in db.list_rules()],
        "cats": [dict(c) for c in db.list_categories()],
        "msg": msg,
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "rules.html", ctx)


@app.post("/rules")
def add_rule(
    category_id: str = Form(...),
    pattern: str = Form(...),
    field: str = Form("any"),
    priority: int = Form(100),
) -> RedirectResponse:
    if not category_id:
        raise HTTPException(400, "category_id required")
    db.add_rule(int(category_id), pattern, field, priority)
    return RedirectResponse(url="/rules?msg=Rule+added", status_code=303)


@app.post("/rules/{rule_id}/delete")
def delete_rule_route(rule_id: int) -> RedirectResponse:
    db.delete_rule(rule_id)
    return RedirectResponse(url="/rules?msg=Rule+deleted", status_code=303)


@app.post("/rules/generate")
def generate_rules_route() -> RedirectResponse:
    n = db.generate_rules_from_manual()
    return RedirectResponse(url=f"/rules?msg=Generated+{n}+rules", status_code=303)


@app.post("/rules/apply")
def apply_rules_route() -> RedirectResponse:
    changed, skipped = db.recategorize_all()
    return RedirectResponse(
        url=f"/rules?msg=Changed+{changed}+skipped+{skipped}+manual", status_code=303
    )


@app.get("/summary", response_class=HTMLResponse)
def summary_view(request: Request):
    rows = db.summary_by_category()
    agg: dict[tuple[str, str, str], dict[str, float]] = {}
    for r in rows:
        key = (r["kind"], r["category_name"], r["currency"])
        bucket = agg.setdefault(key, {"in": 0.0, "out": 0.0, "cnt": 0})
        amt = float(r["total"])
        if r["credit_debit"] == "CRDT":
            bucket["in"] += amt
        else:
            bucket["out"] += amt
        bucket["cnt"] += r["cnt"]

    def to_items(want_transfer: bool):
        out = []
        for (kind, cat, cur), v in agg.items():
            is_transfer = kind == "transfer"
            if want_transfer != is_transfer:
                continue
            out.append({
                "cat": cat, "cur": cur,
                "in_": v["in"], "out": v["out"],
                "net": v["in"] - v["out"], "cnt": v["cnt"],
            })
        return sorted(out, key=lambda x: (x["cat"], x["cur"]))

    ctx = {
        "nav": "summary",
        "main_items": to_items(False),
        "transfer_items": to_items(True),
        **_sidebar_context(request),
    }
    return templates.TemplateResponse(request, "summary.html", ctx)


@app.post("/accounts/{account_id}/tx/{entry_ref:path}/category")
def set_tx_category(
    request: Request,
    account_id: int,
    entry_ref: str,
    category_id: str = Form(""),
    uncat: int = Form(0),
):
    cat_id = int(category_id) if category_id else None
    db.set_transaction_category(account_id, entry_ref, cat_id, manual=True)
    rules_added = 0
    auto_applied = 0
    if cat_id is not None:
        rules_added = db.generate_rules_from_manual()
        if rules_added:
            auto_applied, _ = db.recategorize_all()
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            {"rules_added": rules_added, "auto_applied": auto_applied}
        )
    anchor = f"#tx-{entry_ref}"
    return RedirectResponse(
        url=f"/accounts/{account_id}/tx?uncat={uncat}{anchor}", status_code=303
    )


@app.post("/accounts/{account_id}/tx/{entry_ref:path}/hide")
def hide_tx(account_id: int, entry_ref: str, uncat: int = Form(0)) -> RedirectResponse:
    db.set_transaction_hidden(account_id, entry_ref, True)
    return RedirectResponse(url=f"/accounts/{account_id}/tx?uncat={uncat}", status_code=303)


@app.post("/accounts/{account_id}/tx/{entry_ref:path}/unhide")
def unhide_tx(account_id: int, entry_ref: str) -> RedirectResponse:
    db.set_transaction_hidden(account_id, entry_ref, False)
    return RedirectResponse(url=f"/accounts/{account_id}/tx?show_hidden=1", status_code=303)


@app.post("/accounts/{account_id}/tx/{entry_ref:path}/note")
def set_tx_note(
    account_id: int,
    entry_ref: str,
    note: str = Form(""),
    uncat: int = Form(0),
) -> RedirectResponse:
    db.set_transaction_note(account_id, entry_ref, note.strip() or None)
    return RedirectResponse(
        url=f"/accounts/{account_id}/tx?uncat={uncat}", status_code=303
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("FINANCE_HOST", "127.0.0.1")
    port = int(os.getenv("FINANCE_PORT", "8000"))
    uvicorn.run("finance.main:app", host=host, port=port, reload=False)
