from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, timedelta

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from html import escape
from starlette.middleware.base import BaseHTTPMiddleware

from finance import db
from finance import auth
from finance.providers.enablebanking import from_env as enablebanking_from_env

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _fmt(amount: float, currency: str = "", decimals: int = 0) -> str:
    sign = "-" if amount < 0 else ""
    s = f"{abs(amount):,.{decimals}f}".replace(",", " ")
    return f"{sign}{s}{(' ' + currency) if currency else ''}"


def _sidebar_context() -> dict:
    """Build the sidebar category-totals + sync-status block, primary currency CZK."""
    rows = db.summary_by_category()
    income = {}
    expense = {}
    income_total = 0.0
    expense_total = 0.0
    for r in rows:
        if r["currency"] != "CZK":
            continue
        if r["kind"] == "income":
            bucket = income.setdefault(r["category_name"], 0.0)
            income[r["category_name"]] = bucket + (float(r["total"]) if r["credit_debit"] == "CRDT" else 0.0)
            income_total += float(r["total"]) if r["credit_debit"] == "CRDT" else 0.0
        elif r["kind"] == "expense":
            bucket = expense.setdefault(r["category_name"], 0.0)
            expense[r["category_name"]] = bucket + (float(r["total"]) if r["credit_debit"] == "DBIT" else 0.0)
            expense_total += float(r["total"]) if r["credit_debit"] == "DBIT" else 0.0

    cats = db.list_categories()
    income_cats = [
        {"id": c["id"], "name": c["name"], "amt": _fmt(income.get(c["name"], 0.0), "CZK") if income.get(c["name"]) else None}
        for c in cats if c["kind"] == "income" and c["parent_id"] is None
    ]
    expense_cats = [
        {"id": c["id"], "name": c["name"], "amt": _fmt(expense.get(c["name"], 0.0), "CZK") if expense.get(c["name"]) else None}
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
    }

load_dotenv()

_pending_states: dict[str, dict[str, str]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="finance-dashboard", lifespan=lifespan)


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
    income_total = expense_total = 0.0
    tx_count = uncat_count = 0
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.credit_debit, t.amount, t.category_id, c.kind "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE t.currency = 'CZK' AND substr(t.booking_date, 1, 7) = ?",
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
            if r["credit_debit"] == "CRDT":
                income_total += amt
            else:
                expense_total += amt

    net = income_total - expense_total
    kpi = {
        "income": _fmt(income_total),
        "income_currency": "CZK",
        "expense": _fmt(expense_total),
        "expense_currency": "CZK",
        "net": ("+" if net >= 0 else "") + _fmt(net),
        "net_currency": "CZK",
        "count": str(tx_count),
        "uncategorized": str(uncat_count),
    }

    recent = []
    with db.connect() as conn:
        for r in conn.execute(
            "SELECT t.booking_date, t.counterparty_name, t.remittance_info, t.amount, "
            "t.currency, t.credit_debit, c.name AS category_name "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
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
    ctx = {
        "nav": "dashboard",
        "kpi": kpi,
        "recent_tx": recent,
        "accounts": accounts_view,
        "month": month,
        "months": months,
        "synced": synced,
        **_sidebar_context(),
    }
    return templates.TemplateResponse(request, "dashboard.html", ctx)


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
        **_sidebar_context(),
    }
    return templates.TemplateResponse(request, "categories.html", ctx)


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
    ctx = {"nav": "accounts", "accounts": accounts, **_sidebar_context()}
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
    limit: int = 500,
):
    where = ["1=1"]
    args: list = []
    if uncat:
        where.append("t.category_id IS NULL")
    if category:
        where.append("t.category_id = ?")
        args.append(category)
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
        **_sidebar_context(),
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
    request: Request, account_id: int, synced: str | None = None, uncat: int = 0
):
    account = db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    txs = db.list_transactions(account_id, only_uncategorized=bool(uncat))
    cats = db.list_categories()
    ctx = {
        "nav": "tx",
        "account": dict(account),
        "txs": [dict(t) for t in txs],
        "cats": [dict(c) for c in cats],
        "uncat": uncat,
        "synced": synced,
        **_sidebar_context(),
    }
    return templates.TemplateResponse(request, "transactions.html", ctx)


@app.get("/rules", response_class=HTMLResponse)
def rules_view(request: Request, msg: str | None = None):
    ctx = {
        "nav": "rules",
        "rules": [dict(r) for r in db.list_rules()],
        "cats": [dict(c) for c in db.list_categories()],
        "msg": msg,
        **_sidebar_context(),
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
        **_sidebar_context(),
    }
    return templates.TemplateResponse(request, "summary.html", ctx)


@app.post("/accounts/{account_id}/tx/{entry_ref:path}/category")
def set_tx_category(
    account_id: int,
    entry_ref: str,
    category_id: str = Form(""),
    uncat: int = Form(0),
) -> RedirectResponse:
    cat_id = int(category_id) if category_id else None
    db.set_transaction_category(account_id, entry_ref, cat_id, manual=True)
    return RedirectResponse(
        url=f"/accounts/{account_id}/tx?uncat={uncat}", status_code=303
    )


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
