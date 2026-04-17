---
tags:
  - project/finance
  - planning
---

# Roadmap & fázy

[[00 - Overview|← Späť na Overview]]

## Prístup

> [!tip] MVP-first
> Najprv fungujúci prototyp (len zobraziť transakcie), potom postupne features. Žiadny "big bang release".

## Fáza 0 — Prípravka (pred prvou session)

- [ ] User vytvorí **GoCardless účet** na gocardless.com/bank-account-data
- [ ] Vygeneruje **Secret ID + Secret Key** v ich dashboarde
- [ ] Dodá **kategórie z Excelu** (jedlo, hovadiny, investície, doprava, …)
- [ ] Rozhodne **repo meno** a **GitHub username**
- [ ] Rozhodne **licenciu** (odporúčané: AGPLv3 — detaily v [[06 - GitHub & OSS Plan]])

## Fáza 1 — MVP (~4–6h)

**Cieľ:** vidieť svoje reálne transakcie z Revolutu vo webovom UI.

- [ ] Python projekt setup (`pyproject.toml`, `src/`, venv)
- [ ] GoCardless integrácia — **len Revolut** (najjednoduchší)
- [ ] Auth flow (requisition → redirect → callback)
- [ ] SQLite schema (`accounts`, `transactions`)
- [ ] Sync tlačidlo v UI (nie cron zatiaľ — jednoduchšie debugovať)
- [ ] **Jedna HTML stránka** = tabuľka transakcií (žiadny CSS)
- [ ] Beží lokálne `python -m finance` na `localhost:8000`

**Milestone:** vidíš svoje reálne transakcie v DB. 🎉

## Fáza 2 — Core features (~3–4h)

- [ ] Pridať ČSOB a Tatra banka cez Provider interface
- [ ] Filter: podľa účtu, dátumu, sumy, kategórie
- [ ] **Auto kategorizácia** cez regex rules (`pattern → category`)
- [ ] Manuálny override kategórie v UI (klik → dropdown)
- [ ] Categories CRUD (pridať/premenovať/zmazať)

## Fáza 3 — Automatizácia & security (~2h)

- [ ] **systemd timer** — sync každých 6h
- [ ] **Login** (Argon2 + sessions)
- [ ] Tailscale-only binding (app listen na `100.x.x.x`)
- [ ] systemd service (auto restart, logs do journalu)
- [ ] Notifikácia pri expirácii consentu (email alebo ntfy push)

## Fáza 4 — Reporty & UX (~2–3h)

- [ ] Mesačný prehľad: súčet príjmov/výdavkov, breakdown podľa kategórií
- [ ] Chart: výdavky v čase (Chart.js)
- [ ] Chart: pie chart kategórií
- [ ] Mobile-friendly layout (Tailwind responsive)
- [ ] Export do CSV / Excel

## Fáza 5 — Polish & GitHub publish (~2–3h)

- [ ] README so screenshotmi a quickstartom
- [ ] `Dockerfile` + `docker-compose.yml` pre one-command setup
- [ ] `docs/installation.md`, `docs/gocardless-setup.md`
- [ ] GitHub Actions CI (lint + basic tests)
- [ ] Issue templates
- [ ] CHANGELOG
- [ ] **Switch repo private → public**

## Fáza 6 — Historical import (voliteľné, ~1h)

- [ ] Import starých transakcií z Excelu (cez upload formulár)
- [ ] Deduplication s GoCardless dátami

## Fáza 7 — Future extensions (ďaleko neskôr)

Detaily v [[05 - Future Extensions]]:
- [ ] **Trading212** provider (~2–3h)
- [ ] **Coinbase** provider (~2–3h)
- [ ] Portfolio view oddelený od cash flow

## Spolu

| Fáza | Odhad | Kumulatívne |
|------|-------|-------------|
| 0 — Prípravka | ~30 min (user) | — |
| 1 — MVP | 4–6h | 4–6h |
| 2 — Core features | 3–4h | 7–10h |
| 3 — Automatizácia & security | 2h | 9–12h |
| 4 — Reporty & UX | 2–3h | 11–15h |
| 5 — Polish & publish | 2–3h | 13–18h |
| 6 — Historical import | 1h | 14–19h |
| 7 — Future extensions | 4–6h | 18–25h |

**Realisticky:** MVP za 1–2 session, všetko po fázu 5 za ~2–4 týždne popri práci.
