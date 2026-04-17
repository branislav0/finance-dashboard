---
tags:
  - project/finance
  - decisions
---

# Decisions Log

[[00 - Overview|← Späť na Overview]]

Zafixované rozhodnutia v ADR (Architecture Decision Record) štýle. Každý záznam: **Rozhodnutie + Prečo + Dopad**.

---

## ADR-001: Stack = FastAPI + SQLite + HTMX
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** Python FastAPI pre backend, SQLite pre storage, HTMX + Tailwind pre frontend.

**Prečo:**
- FastAPI = async, typing, rýchly vývoj, dobré docs
- SQLite = žiadny server, súborové, <100MB aj po rokoch
- HTMX = žiadny build step, server-rendered, stačí mobile-friendly

**Alternatívy zvažené:**
- Flask + Jinja — menej moderné, bez async
- Node.js / Next.js — user preferuje Python
- PostgreSQL — overkill pre single-user
- React / Vue — zbytočná komplexnosť

**Dopad:** Lightweight RPi footprint (~50–100MB RAM), rýchly vývoj, ľahká údržba.

---

## ADR-002: GoCardless Bank Account Data (nie CSV import)
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** Primárny zdroj bankových dát = GoCardless API, nie manuálny CSV export.

**Prečo:**
- Cieľ projektu = **automatizácia**, CSV by znova znamenalo manuálnu prácu
- GoCardless free tier bohato stačí (100 calls/deň/účet)
- Read-only tokeny = bezpečné
- Podporuje všetky 3 banky usera (Revolut, ČSOB SK, Tatra banka)

**Trade-off:** Re-autorizácia každých 90 dní (PSD2). Akceptované — ~10 minút za štvrťrok.

**Dopad:** Appka je plne automatická mimo 90-dňovej re-auth. Detaily v [[02 - GoCardless Setup]].

---

## ADR-003: Lokálne na RPi + Tailscale only (žiadny verejný tunnel)
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** Appka beží na RPi, prístupná **len cez Tailscale**. Žiadny Cloudflare tunnel ani verejná IP.

**Prečo:**
- User už má Tailscale nasadený na telefóne
- Zero exposure voči internetu = podstatne menšia attack surface
- Žiadna potreba SSL certifikátu, žiadny public DNS

**Dopad:** App dostupná len cez `100.x.x.x` (Tailscale IP). Z verejnej siete neprístupná.

---

## ADR-004: Sync = automatický cron každých 6h
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** systemd timer spúšťa sync každých 6 hodín. NIE manuálne tlačidlo ako hlavný flow.

**Prečo:**
- Cieľ projektu = **zbaviť sa manuálnej práce**. Manuálny sync by spôsobil zabúdanie.
- 4 volania/deň = hlboko pod GoCardless free limitom (100/deň)

**Poznámka:** Počas MVP **DOČASNE** bude manuálne tlačidlo (jednoduchšie debugovať). Cron sa pridá vo fáze 3.

**Dopad:** User zabudne na existenciu sync-u — funguje samo.

---

## ADR-005: Provider interface od MVP (nie neskôr)
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** Aj MVP s jedinou bankou (Revolut) bude mať abstract `Provider` triedu.

**Prečo:**
- Plánované rozšírenia ([[05 - Future Extensions]]): Trading212, Coinbase, ďalšie banky
- Refactor neskôr by bol bolestivejší než malá extra vrstva teraz
- Cost = ~30 min navyše v MVP, benefit = žiadny refactor pri pridávaní providerov

**Dopad:** Pridanie nového zdroja dát = **napísať jednu triedu**, zvyšok appky sa nemení.

---

## ADR-006: DB schema dopredu podporuje investment + crypto
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** `transactions.type` enum (`bank | investment | crypto`) a extra fields pre ticker, quantity, coin_symbol, atď. už v MVP schema.

**Prečo:**
- User plánuje Trading212 a Coinbase ako budúcu nadstavbu
- Migrácia existujúcej DB je komplikovanejšia než mať to dopredu

**Dopad:** MVP tabuľka má pár nevyužitých stĺpcov (NULL pre bankové transakcie). Akceptované.

---

## ADR-007: Projekt publikovaný na GitHub (postupne)
**Dátum:** 2026-04-17
**Status:** Accepted

**Rozhodnutie:** Stavať ako verejný open-source GitHub projekt s proper repo štruktúrou od dňa 1. Publikovať repo **až keď MVP reálne funguje**.

**Prečo:**
- User chce mať osobný projekt popri práci (portfolio piece)
- Zároveň chce appku reálne používať — **funkčnosť má prednosť pred parádou**
- Postupné publikovanie = žiadne rozbité WIP na verejnosti

**Dopad:** +2–4h práce navyše (README, Docker, docs, CI). Detaily v [[06 - GitHub & OSS Plan]].

---

## ADR-008: Priorita funkčnosť > paráda
**Dátum:** 2026-04-17
**Status:** Accepted (meta-ADR)

**Rozhodnutie:** Počas celého vývoja platí pravidlo — *čo ti pomôže skôr používať appku* > *čo vyzerá dobre na GitHube*.

**Konkrétne:**
- MVP funguje na RPi **pred** prvým commitom
- Docs píšeme **až keď feature funguje**, nie dopredu
- Žiadne abstrakcie "lebo to vyzerá pro" (okrem Provider interface — má reálnu hodnotu)
- Polish + screenshoty + publish repa **až po ~2 týždňoch reálneho používania**

**Dopad:** Appka bude reálne použiteľná skôr. Repo bude vyzerať menej "plánovane", zato funkčne.

---

## Ešte neurobené rozhodnutia

Pozri [[08 - Open Questions]]:
- Repo meno
- GitHub username
- Licencia (odporúčané AGPLv3)
- Kategórie z Excelu (čakám na user)
