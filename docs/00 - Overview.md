---
tags:
  - project/finance
  - status/planning
created: 2026-04-17
---

# Finance Dashboard — Overview

Lokálna web appka na **RPi 5** na sledovanie transakcií z viacerých bánk + neskôr investície a krypto. Automatizácia namiesto manuálneho prepisovania Excelu.

## Stav

> [!info] Status: **Planning**
> Sketch dohodnutý, implementácia ešte nezačala. Ďalší krok = registrácia GoCardless účtu.

## Čo sa buduje

- **3 banky:** Revolut, ČSOB SK, Tatra banka (cez [[02 - GoCardless Setup|GoCardless Bank Account Data API]])
- **Lokálne na RPi**, prístup cez **Tailscale VPN** (aj z mobilu)
- **Auto sync** každých 6h cez cron
- **Auto kategorizácia** transakcií (jedlo, hovadiny, investície, doprava, …)
- **Neskôr:** [[05 - Future Extensions|Trading212 + Coinbase]]

## Mapa poznámok

- [[01 - Stack & Architecture]] — čo stavieme a z čoho
- [[02 - GoCardless Setup]] — ako funguje API, PSD2, re-autorizácia
- [[03 - Security]] — bezpečnosť, threat model
- [[04 - Roadmap & Phases]] — MVP → plná verzia, časové odhady
- [[05 - Future Extensions]] — Trading212, Coinbase nadstavba
- [[06 - GitHub & OSS Plan]] — repo, licencia, distribúcia
- [[07 - Decisions Log]] — zafixované rozhodnutia (ADR-style)
- [[08 - Open Questions]] — čo treba ešte vyriešiť

## Základné princípy

1. **Funkčnosť > paráda.** Appka sa musí reálne používať, nie len vyzerať dobre na GitHube.
2. **MVP funguje pred prvým commitom.** Žiadne stavanie do prázdna.
3. **Žiadne abstrakcie bez reálnej hodnoty.** Provider interface áno (kvôli budúcim providerom), zbytočné vrstvy nie.
4. **Polish a screenshoty až po ~2 týždňoch reálneho používania.**

## Rýchle fakty

| Parameter | Hodnota |
|-----------|---------|
| Stack | Python FastAPI + SQLite + HTMX |
| Hosting | RPi 5 (lokálne) |
| Prístup | Tailscale VPN only |
| Náklady | 0 € (GoCardless free tier, Tailscale free tier) |
| Odhad času | **8–12h** rozložene do 2–4 session |
| Sync frekvencia | Každých 6h (cron/systemd timer) |
| Re-autorizácia | Každých 90 dní (PSD2 zákon) |
