---
tags:
  - project/finance
  - tech/architecture
---

# Stack & Architektúra

[[00 - Overview|← Späť na Overview]]

## Tech stack

| Vrstva | Technológia | Prečo |
|--------|-------------|-------|
| Backend | **Python 3.11+ / FastAPI** | async, jednoduchý, typing, dobré docs |
| DB | **SQLite** | žiadny server, file-based, <100MB aj po rokoch |
| Frontend | **HTMX + Tailwind** | žiadny build step, server-rendered, mobile-friendly |
| Auth | **Argon2 + sessions** (voliteľne TOTP 2FA) | modern, resistente voči GPU attacks |
| Deploy | **systemd service** na RPi | auto-restart, journal logs |
| Sync | **systemd timer** (cron alternative) | každých 6h |
| Network | **Tailscale only binding** | nikdy nie verejne dostupné |

## Priečinková štruktúra

```
finance-dashboard/
├── src/finance/
│   ├── providers/          # GoCardless, Trading212, Coinbase, …
│   │   ├── base.py         # abstract Provider interface
│   │   └── gocardless.py
│   ├── models/             # SQLite schema (SQLAlchemy alebo plain)
│   ├── api/                # FastAPI routes
│   ├── web/                # HTMX templates (Jinja2)
│   └── main.py
├── tests/
├── docs/
├── .env.example
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Provider interface (kľúčové rozhodnutie)

Od MVP bude appka mať abstract `Provider` triedu:

```python
class Provider(ABC):
    @abstractmethod
    def sync(self) -> list[Transaction]: ...

    @abstractmethod
    def get_accounts(self) -> list[Account]: ...
```

Každá banka / broker / crypto = vlastná implementácia. Pridanie ďalšieho zdroja = **nová trieda, žiadny refactor**. Detaily v [[05 - Future Extensions]].

## DB schema (v skratke)

```
accounts
  id, provider, provider_account_id, name, currency, last_synced_at

transactions
  id, account_id, external_id (unique), date, amount, currency,
  merchant, description, category_id, type (bank|investment|crypto),
  -- investment fields: ticker, quantity, unit_price
  -- crypto fields: coin_symbol, amount_coin, fiat_price

categories
  id, name, parent_id, color, icon

rules
  id, pattern (regex), category_id, priority
```

## Resources na RPi

- **RAM:** ~50–100MB (FastAPI + uvicorn)
- **Disk:** <100MB SQLite aj po rokoch
- **Network:** len outbound HTTPS na `bankaccountdata.gocardless.com`
- **Porty:** žiadne verejne otvorené (Tailscale binding `100.x.x.x`)

## Bezpečnosť v skratke

Detaily v [[03 - Security]]. Kľúčové:
- GoCardless tokeny = **read-only** (nemôžu poslať peniaze)
- `.env` s `chmod 600`
- Login do UI + voliteľne TOTP 2FA
- Tailscale-only binding → **nikdy verejne dostupné**
