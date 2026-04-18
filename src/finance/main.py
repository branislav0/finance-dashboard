from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

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
    rows.append('<p><a href="/connect/mock/SK">+ Connect Mock ASPSP (SK)</a></p>')
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


@app.get("/accounts/{account_id}/tx", response_class=HTMLResponse)
def show_transactions(account_id: int, synced: str | None = None) -> str:
    txs = db.list_transactions(account_id)
    banner = f'<p><strong>Sync:</strong> {synced.replace("_", " ")}</p>' if synced else ""
    rows = [
        '<p><a href="/">← back</a></p>',
        "<h1>Transactions</h1>",
        banner,
        f"<p>{len(txs)} stored</p>",
        '<table border=1 cellpadding=4><tr>'
        "<th>Date</th><th>Amount</th><th>Currency</th><th>Dir</th>"
        "<th>Counterparty</th><th>Info</th></tr>",
    ]
    for t in txs:
        rows.append(
            f"<tr><td>{t['booking_date'] or ''}</td>"
            f"<td align=right>{t['amount']}</td>"
            f"<td>{t['currency']}</td>"
            f"<td>{t['credit_debit'] or ''}</td>"
            f"<td>{t['counterparty_name'] or ''}</td>"
            f"<td>{t['remittance_info'] or ''}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)
