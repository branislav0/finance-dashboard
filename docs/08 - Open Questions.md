---
tags:
  - project/finance
  - todo
---

# Open Questions

[[00 - Overview|← Späť na Overview]]

Veci ktoré treba rozhodnúť / dodať pred začatím implementácie alebo počas nej.

## Pred prvou session (blokujúce)

- [ ] **Vytvoriť GoCardless účet** na https://gocardless.com/bank-account-data
- [ ] Vygenerovať **Secret ID + Secret Key** v dashboarde a uložiť (bezpečne!)
- [ ] **Kategórie z Excelu** — dodať zoznam (jedlo, hovadiny, investície, doprava, …)
- [ ] **Repo meno** — návrhy:
  - `finance-dashboard` (generic, bezpečná voľba)
  - `monyz` / `peniazomat` / `kasa` (SK, catchy)
  - `personal-ledger` (pro-sounding, anglické)
  - vlastný návrh?
- [ ] **GitHub username** — treba dodať pre správne URL v dokumentácii

## Licencia a publishing

- [ ] **MIT vs AGPLv3** — odporúčané AGPLv3 (detaily v [[06 - GitHub & OSS Plan]])
- [ ] **Public alebo private repo na začiatku** — odporúčané private počas MVP, public po ~2 týždňoch používania

## Počas implementácie (nedôležité teraz)

- [ ] **Notifikácie pri expirácii consentu** — email (Resend/SMTP) alebo push (ntfy)?
- [ ] **Backup stratégia** — `age` encrypted + rsync kam? (iný RPi? notebook? cloud?)
- [ ] **TOTP 2FA** — hneď v MVP, alebo neskôr?
- [ ] **Multi-currency** — user má len EUR účty? Alebo aj USD/iné?
- [ ] **Historical Excel import** — urobiť hneď (fáza 6) alebo až keď bude potreba?

## Bank-specific

- [ ] **ČSOB SK auth flow** — občas má zvláštnosti, prípadne treba doladiť
- [ ] **Tatra banka historical range** — koľko dní dozadu reálne vráti (môže byť menej než 90)
- [ ] **Revolut EUR vs multi-currency pockets** — treba ich modelovať ako samostatné účty alebo jeden?

## UX rozhodnutia (riešime pri fáze 4)

- [ ] **Kategórie: flat alebo hierarchické** (Jedlo > Reštaurácia, Jedlo > Potraviny)?
- [ ] **Farby kategórií** — default paletu alebo custom per kategória?
- [ ] **Mesačný vs custom date range** reporty ako default?
- [ ] **Default pohľad po otvorení** — tabuľka všetkých transakcií, alebo mesačný dashboard?

## Dlhodobé úvahy (ďaleko neskôr)

- [ ] **Trading212 integrácia** — kedy aktuálne? Keď bude MVP + banky stabilné.
- [ ] **Coinbase integrácia** — dtto.
- [ ] **Multi-user**? — NIE (single-user designe, ak SaaS tak nový repo).
- [ ] **Mobile appka**? — pravdepodobne nie, responsive web stačí cez Tailscale.

## Poznámky pre mňa (Claude)

- Pri ďalšej session začať sekciou "Pred prvou session" — bez toho sa nehne.
- Memory pointer: `/home/rpios/.claude/projects/-home-rpios/memory/project_finance_dashboard.md`
