# Groš — Architecture

Personal finance dashboard: pulls bank transactions, categorizes them, and shows
cashflow, budgets, and savings progress. Single-user, self-hosted on a Raspberry
Pi 5, reachable only over Tailscale (or `127.0.0.1` locally).

## What it does

- **Imports transactions** over PSD2 / open banking (Enable Banking) — Revolut LT,
  ČSOB SK, Tatra banka — plus **CSV import** for ČSOB CZ.
- **Categorizes** two ways: prioritized **regex rules** and optional **AI
  categorization**; manual overrides always win and survive re-sync.
- **Multi-currency dashboard** — per-currency KPIs, cashflow chart, monthly view,
  category budgets (master plan), and a savings tracker with ETA.
- Converts EUR ↔ CZK using **CNB** (Czech National Bank) daily rates.

## How it works

Server-rendered **FastAPI** app (Jinja2 templates, no JS framework, no build step),
**SQLite** (WAL) for storage, run with `uv`.

```
Browser ──HTTPS (Tailscale)──▶ FastAPI (RPi 5)
                                  │
        ┌─────────────────────────┼──────────────────────────┐
        ▼                         ▼                           ▼
 providers/enablebanking    providers/ai               providers/cnb
   (PSD2 bank data)      (AI categorization)         (EUR/CZK FX rates)
        │                         │                           │
        └──────────────▶ db.py / SQLite (WAL) ◀───────────────┘
              accounts · transactions · categories
              category_rules · fx_rates · sessions
```

- **Bank connect** — OAuth-style flow: `/connect/{bank}/{country}` → bank login →
  `/callback` stores the consent, then accounts and transactions are fetched.
- **Sync** — `GET /sync` (or per-account) pulls fresh transactions and upserts them
  by unique reference. **Manual — there is no background scheduler.**
- **Categorization** — on sync/import, regex rules (`category_rules`, by priority)
  run first; `/categorize-ai` sends still-uncategorized transactions to the AI model,
  which only assigns a category above a confidence threshold. A category set manually
  in the UI is never overwritten.
- **Auth** — single password (Argon2) + signed session cookie; the app binds to
  `127.0.0.1` and is exposed only through Tailscale.

## Known limitations / rough edges

- **Manual sync** — no background scheduler; you trigger `/sync` yourself.
- **PSD2 re-authorization every 90 days** — bank consent expires by EU law; you
  re-approve via bank login (~2–3 min per bank). Stored data is untouched.
- **Bank-specific quirks** — ČSOB SK auth flow can be finicky; historical lookback
  varies per bank (often < 90 days); Revolut multi-currency pockets need care in how
  they map to accounts.
- **AI categorization needs `ANTHROPIC_API_KEY`** and leaves low-confidence
  transactions for you to assign manually.
- **Single-user by design** — one password, one owner.
- Empty `api/`, `models/`, `web/` packages remain from the original scaffold and are
  currently unused.
