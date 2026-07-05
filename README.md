# Groš

Self-hosted personal finance dashboard. Aggregates bank transactions from SK/LT/CZ accounts, categorizes them, and tracks cashflow and savings goals. Runs on a Raspberry Pi 5, reachable only over Tailscale.

**Status:** v0.5 · single-user · fully usable.

## Features

- **3 banks via PSD2** (Enable Banking) — Revolut LT, ČSOB SK, Tatra banka — plus CSV import for ČSOB CZ
- **Multi-currency dashboard** — per-currency KPIs, cashflow chart, savings tracker with ETA
- **Auto-categorization** — prioritized regex rules; manual overrides survive re-sync
- **Auth** — Argon2 + signed session cookie, bound to `127.0.0.1` (exposed via Tailscale)

## Stack

Python 3.13 · FastAPI · Jinja2 · SQLite (WAL) · `uv`. No JS framework, no build step.

## Architecture

```
┌─────────────┐    PSD2 OAuth    ┌─────────────────────┐
│   Browser   │ ───────────────> │  Enable Banking API │
│ (Tailscale) │                  └─────────────────────┘
└─────┬───────┘                            │
      │ HTTPS                              │ tx data
      ▼                                    ▼
┌──────────────────────────────────────────────────┐
│  FastAPI app (RPi 5)                             │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │ routes/ │─▶│ db.py    │─▶│ SQLite (WAL)    │  │
│  │ main.py │  │ auth.py  │  │ data/finance.db │  │
│  └─────────┘  │csv_import│  └─────────────────┘  │
│               └──────────┘                       │
└──────────────────────────────────────────────────┘
```

## Run

```bash
git clone https://github.com/branislav0/finance-dashboard
cd finance-dashboard
cp .env.example .env       # APP_SECRET_KEY, EB credentials
uv sync
uv run python -m finance.set_password   # set a password
uv run python -m finance.main           # http://127.0.0.1:8000
```

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
