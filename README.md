# finance-dashboard

Self-hosted osobný finančný dashboard. Agreguje bankové transakcie zo SK/LT/CZ účtov, kategorizuje ich pravidlami, sleduje cashflow a sporiace ciele. Beží na Raspberry Pi 5, prístupný len cez Tailscale (alebo `127.0.0.1` lokálne).

**Status:** v0.5 — plne použiteľné pre vlastné nasadenie. Single-user.

## Funkcie

- **3 banky cez PSD2** (Enable Banking API) — Revolut LT, ČSOB SK, Tatra banka. Auth flow, consent obnova, automatický sync.
- **CSV import pre ČSOB CZ** — Enable Banking nemá CZ pasportovanú licenciu, takže tam manuálny upload výpisu (idempotentne, deduplikuje cez `ID transakce`).
- **Multi-currency dashboard** — KPI per mena (príjem / výdaj / net), žiadne FX prepočty.
- **Cashflow mini-graf** — 6 mesiacov dozadu, zelené stĺpce príjem, červené výdaj.
- **Sporiaci tracker** — progress bar 0 → cieľ, počet zostávajúcich výplat, ETA dátum.
- **Kategórie + pravidlá** — auto-categorize cez regex pravidlá s prioritami; manual override sa neprepisuje pri sync; "generuj pravidlá z manuálnych" extrahuje vzory.
- **Hidden flag** — skryť test/duplikátne tx z KPI bez fyzického delete (sync ich nevráti späť).
- **Demo blur mód** — toggle v topbare, blurne všetky čísla pre screenshoty/portfolio.
- **Mobile-friendly** — sidebar collapse, horizontal scroll nav, touch-size tlačidlá.
- **Auth** — Argon2 hash + signed session token (itsdangerous), brute-force-resistant.

## Stack

- Python 3.13 / FastAPI / Jinja2 / SQLite (WAL, FK ON)
- `uv` pre dependency management
- Argon2 + itsdangerous URLSafeTimedSerializer
- Žiadny JS framework, žiadny build step — server-rendered HTML s pár inline `<script>` blokmi
- Deploy: nohup + Tailscale Serve HTTPS proxy

## Architektúra

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

## Spustenie

```bash
git clone https://github.com/branislav0/finance-dashboard
cd finance-dashboard
cp .env.example .env       # nastav APP_SECRET_KEY, EB credentials
uv sync
uv run python -m finance.set_password   # vyber heslo
uv run python -m finance.main           # http://127.0.0.1:8000
```

## Testy

```bash
uv run pytest               # 25 testov
```

Pokrýva: auth (hash, session token expiry, tampering), upsert idempotency, rules engine priority/regex, consent expiry warning, kategórie CRUD.

## Bezpečnosť

- Heslo: Argon2id, default cost
- Sessions: HMAC-podpísaný token v cookie, expiry default 7 dní (configurable)
- DB: SQLite súbor v `.gitignore`, žiadne dáta v git history
- Network: bind len na 127.0.0.1, vystavený cez Tailscale Serve (žiadny verejný internet)
- Žiadne secrets v repe — `.env` je gitignored

## Limitácie / future work

- Single-user (multi-user variant by potreboval SQLCipher per-user DB)
- Žiadny CSRF token (mitigácia: SameSite cookies)
- Žiadny rate-limit na /login (Argon2 to spomalí brute-force, ale nie zastaví)
- Žiadny CI (GitHub Actions na pytest by sa hodili)
- Schema migrácie ručné (`ALTER TABLE` v `init_db`)

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
