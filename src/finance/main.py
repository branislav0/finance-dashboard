from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from html import escape

from finance import db
from finance.providers.enablebanking import from_env as enablebanking_from_env

load_dotenv()

_pending_states: dict[str, dict[str, str]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="finance-dashboard", lifespan=lifespan)


def _redirect_url(request: Request) -> str:
    override = os.environ.get("ENABLEBANKING_REDIRECT_URL")
    if override:
        return override
    return str(request.url_for("callback"))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    accounts = db.list_accounts()
    rows = ["<h1>Finance dashboard</h1>"]
    rows.append('<p><a href="/connect/Revolut/LT">+ Connect Revolut</a></p>')
    rows.append('<p><a href="/categories">Kategórie</a> · <a href="/rules">Rules</a> · <a href="/summary">Summary</a></p>')
    rows.append('<p><small><a href="/connect/mock/SK">(sandbox: Mock ASPSP SK)</a></small></p>')
    if not accounts:
        rows.append("<p><em>No accounts yet.</em></p>")
        return "\n".join(rows)
    rows.append("<h2>Accounts</h2><ul>")
    for a in accounts:
        rows.append(
            f'<li>{a["iban"]} ({a["currency"]}) — '
            f'<a href="/accounts/{a["id"]}/tx">transactions</a> · '
            f'<a href="/accounts/{a["id"]}/sync">sync now</a></li>'
        )
    rows.append("</ul>")
    return "\n".join(rows)


@app.get("/categories", response_class=HTMLResponse)
def categories_view() -> str:
    cats = db.list_categories()
    by_parent: dict[int | None, list] = {}
    for c in cats:
        by_parent.setdefault(c["parent_id"], []).append(c)

    def render_list(kind: str) -> str:
        roots = [c for c in by_parent.get(None, []) if c["kind"] == kind]
        items = []
        for r in roots:
            children = by_parent.get(r["id"], [])
            if children:
                subs = "".join(f"<li>{c['name']}</li>" for c in children)
                items.append(f"<li><strong>{r['name']}</strong><ul>{subs}</ul></li>")
            else:
                items.append(f"<li>{r['name']}</li>")
        return f"<ul>{''.join(items)}</ul>"

    return (
        '<p><a href="/">← back</a></p>'
        "<h1>Kategórie</h1>"
        "<h2>Príjmy</h2>" + render_list("income") +
        "<h2>Výdavky</h2>" + render_list("expense") +
        "<h2>Presuny</h2>" + render_list("transfer") +
        "<p><em>CRUD príde v kroku 2.4 — zatiaľ len read-only view zo seed dát.</em></p>"
    )


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
    account_id: int, synced: str | None = None, uncat: int = 0
) -> str:
    txs = db.list_transactions(account_id, only_uncategorized=bool(uncat))
    cats = db.list_categories()
    banner = f'<p><strong>Sync:</strong> {synced.replace("_", " ")}</p>' if synced else ""
    toggle_label = "Zobraz všetky" if uncat else "Zobraz len nezaradené"
    toggle_target = 0 if uncat else 1
    rows = [
        '<p><a href="/">← back</a></p>',
        "<h1>Transactions</h1>",
        banner,
        f'<p>{len(txs)} shown · '
        f'<a href="/accounts/{account_id}/tx?uncat={toggle_target}">{toggle_label}</a></p>',
        '<table border=1 cellpadding=4><tr>'
        "<th>Date</th><th>Amount</th><th>Currency</th><th>Dir</th>"
        "<th>Counterparty</th><th>Info</th><th>Category</th></tr>",
    ]
    for t in txs:
        ref = escape(t["entry_reference"])
        manual_mark = " *" if t["manual_override"] else ""
        select = _category_select(cats, t["category_id"])
        form = (
            f'<form method="post" action="/accounts/{account_id}/tx/{ref}/category" '
            f'style="margin:0;display:flex;gap:4px">'
            f'<input type="hidden" name="uncat" value="{uncat}">'
            f'{select}<button type="submit">✓</button>{manual_mark}</form>'
        )
        rows.append(
            f"<tr><td>{t['booking_date'] or ''}</td>"
            f"<td align=right>{t['amount']}</td>"
            f"<td>{t['currency']}</td>"
            f"<td>{t['credit_debit'] or ''}</td>"
            f"<td>{escape(t['counterparty_name'] or '')}</td>"
            f"<td>{escape(t['remittance_info'] or '')}</td>"
            f"<td>{form}</td></tr>"
        )
    rows.append("</table>")
    rows.append('<p><small>* = manuálne nastavené (auto-rules to neprepíšu)</small></p>')
    return "\n".join(rows)


@app.get("/rules", response_class=HTMLResponse)
def rules_view(msg: str | None = None) -> str:
    rules = db.list_rules()
    cats = db.list_categories()
    head = [
        '<p><a href="/">← back</a></p>',
        "<h1>Auto-categorization rules</h1>",
    ]
    if msg:
        head.append(f"<p><strong>{escape(msg)}</strong></p>")
    head.append(
        '<form method="post" action="/rules/generate" style="display:inline">'
        '<button type="submit">Generate rules from manual assignments</button></form> '
        '<form method="post" action="/rules/apply" style="display:inline">'
        '<button type="submit">Re-categorize all (respect manual)</button></form>'
    )
    head.append("<h2>Add rule</h2>")
    head.append(
        '<form method="post" action="/rules">'
        f'{_category_select(cats, None)} '
        '<select name="field">'
        '<option value="counterparty">counterparty</option>'
        '<option value="remittance">remittance</option>'
        '<option value="any" selected>any</option>'
        '</select> '
        '<input name="pattern" placeholder="regex pattern" style="width:300px" required> '
        '<input name="priority" type="number" value="100" style="width:60px"> '
        '<button>Add</button></form>'
    )
    head.append("<h2>Existing rules</h2>")
    if not rules:
        head.append("<p><em>No rules yet.</em></p>")
    else:
        head.append(
            "<table border=1 cellpadding=4><tr>"
            "<th>Priority</th><th>Field</th><th>Pattern</th><th>Category</th><th></th></tr>"
        )
        for r in rules:
            head.append(
                f"<tr><td>{r['priority']}</td>"
                f"<td>{r['field']}</td>"
                f"<td><code>{escape(r['pattern'])}</code></td>"
                f"<td>{escape(r['category_name'] or '?')}</td>"
                f'<td><form method="post" action="/rules/{r["id"]}/delete" style="margin:0">'
                f'<button type="submit">✕</button></form></td></tr>'
            )
        head.append("</table>")
    return "\n".join(head)


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
def summary_view() -> str:
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

    def render_section(title: str, items) -> str:
        if not items:
            return ""
        out = [
            f"<h2>{title}</h2>",
            "<table border=1 cellpadding=4><tr>"
            "<th>Category</th><th>Currency</th><th>In</th><th>Out</th><th>Net</th><th>Count</th></tr>",
        ]
        for (cat, cur), v in sorted(items):
            net = v["in"] - v["out"]
            out.append(
                f"<tr><td>{escape(cat)}</td><td>{escape(cur)}</td>"
                f"<td align=right>{v['in']:.2f}</td>"
                f"<td align=right>{v['out']:.2f}</td>"
                f"<td align=right><strong>{net:+.2f}</strong></td>"
                f"<td align=right>{v['cnt']}</td></tr>"
            )
        out.append("</table>")
        return "\n".join(out)

    main_items = [((cat, cur), v) for (kind, cat, cur), v in agg.items() if kind != "transfer"]
    transfer_items = [((cat, cur), v) for (kind, cat, cur), v in agg.items() if kind == "transfer"]

    html = [
        '<p><a href="/">← back</a></p>',
        "<h1>Summary by category</h1>",
        render_section("Príjmy / Výdavky", main_items),
        render_section("Interné presuny (nerátajú sa do In/Out)", transfer_items),
    ]
    return "\n".join(html)


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
