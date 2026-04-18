from __future__ import annotations

import os
import secrets
from datetime import date, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from finance.providers.enablebanking import from_env as enablebanking_from_env

load_dotenv()

app = FastAPI(title="finance-dashboard")

# In-memory session store — replaced by DB in next step.
_pending_states: dict[str, dict[str, str]] = {}
_sessions: dict[str, dict] = {}


def _redirect_url(request: Request) -> str:
    override = os.environ.get("ENABLEBANKING_REDIRECT_URL")
    if override:
        return override
    return str(request.url_for("callback"))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


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


@app.get("/callback", name="callback", response_class=HTMLResponse)
def callback(code: str | None = None, state: str | None = None, error: str | None = None) -> str:
    if error:
        raise HTTPException(400, f"Auth error: {error}")
    if not code or not state:
        raise HTTPException(400, "Missing code/state")
    if state not in _pending_states:
        raise HTTPException(400, "Unknown state")
    _pending_states.pop(state)

    client = enablebanking_from_env()
    session = client.create_session(code)
    session_id = session["session_id"]
    _sessions[session_id] = session

    accounts = session.get("accounts", [])
    html = [
        "<h1>Connected ✅</h1>",
        f"<p>Session: <code>{session_id}</code></p>",
        "<h2>Accounts</h2>",
        "<ul>",
    ]
    for a in accounts:
        iban = a.get("account_id", {}).get("iban", "?")
        html.append(
            f"<li><code>{a['uid']}</code> — {iban} ({a.get('currency', '?')}) "
            f"<a href='/accounts/{a['uid']}/tx'>show transactions</a></li>"
        )
    html.append("</ul>")
    return "\n".join(html)


@app.get("/accounts/{account_uid}/tx", response_class=HTMLResponse)
def show_transactions(account_uid: str) -> str:
    client = enablebanking_from_env()
    date_from = (date.today() - timedelta(days=90)).isoformat()
    data = client.list_transactions(account_uid, date_from=date_from)
    txs = data.get("transactions", [])
    rows = [
        "<h1>Transactions</h1>",
        f"<p>{len(txs)} since {date_from}</p>",
        "<table border=1 cellpadding=4><tr>"
        "<th>Date</th><th>Amount</th><th>Currency</th><th>Counterparty</th><th>Info</th></tr>",
    ]
    for t in txs[:50]:
        amt = t.get("transaction_amount", {})
        cp = (t.get("creditor") or {}).get("name") or (t.get("debtor") or {}).get("name") or ""
        info = (t.get("remittance_information") or [""])[0]
        rows.append(
            f"<tr><td>{t.get('booking_date', '')}</td>"
            f"<td align=right>{amt.get('amount', '')}</td>"
            f"<td>{amt.get('currency', '')}</td>"
            f"<td>{cp}</td><td>{info}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)
