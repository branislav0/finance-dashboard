---
tags:
  - project/finance
  - oss
---

# GitHub & OSS Plan

[[00 - Overview|← Späť na Overview]]

## Princíp

> [!important] Funkčnosť > paráda
> Repo publikujeme **až keď MVP funguje a reálne sa používa**. Žiadne stavanie do prázdna len pre "portfolio".

## Cieľ

1. **Osobný projekt popri práci** — reálne sa používa na manažment peňazí
2. **Portfolio piece** na GitHub — ukazuje schopnosti
3. **Neskôr prípadne** — open-source komunita ak to niekoho zaujme (v štýle Firefly III / Actual Budget)

## Repo štruktúra

```
finance-dashboard/
├── README.md                   # screenshoty, features, quickstart
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── .env.example
├── .gitignore                  # *.db, .env, __pycache__, .venv
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── src/finance/
│   ├── providers/
│   │   ├── base.py
│   │   └── gocardless.py
│   ├── models/
│   ├── api/
│   ├── web/
│   └── main.py
├── tests/
│   └── test_smoke.py           # aspoň jeden basic test
├── docs/
│   ├── installation.md
│   ├── gocardless-setup.md     # walkthrough so screenshotmi
│   ├── architecture.md
│   └── adding-a-provider.md
└── .github/
    ├── workflows/ci.yml        # lint + test on push
    └── ISSUE_TEMPLATE/
        ├── bug_report.md
        └── feature_request.md
```

## Licencia — rozhodnutie

| Licencia | Plus | Minus | Použitie |
|----------|------|-------|----------|
| **MIT** | Maximum šírenia, ktokoľvek použije komerčne | Niekto môže postaviť SaaS klon a nepridať nič naspäť | Chceš max adopciu |
| **AGPLv3** | Kto hostuje ako SaaS, musí zverejniť zmeny | Časť firiem sa AGPL bojí, nepoužije | Firefly III, Plausible, Bitwarden |

> [!tip] Odporúčanie: **AGPLv3**
> Chráni pred SaaS konkurenciou ak by si sám chcel hosted verziu neskôr. Pre osobné self-host userov nemení nič.

## Commit hygiene

**Conventional Commits:**
```
feat: add GoCardless provider for Revolut
fix: handle expired consent gracefully
docs: add gocardless setup walkthrough
refactor: extract Provider base class
chore: pin dependencies in pyproject.toml
test: add smoke test for sync endpoint
```

- **Žiadne giant commits** — radšej 10 malých s jasnou správou
- **1 commit = 1 logická zmena**
- Správy píšeme po slovensky? Alebo anglicky? → **Anglicky** (public repo)

## Verejnosť repa

**Plán:**
1. **Private** počas fázy 1–4 (MVP + core features + automatizácia + reporty)
2. **Reálne používanie ~2 týždne**
3. **Switch na public** spolu s polished README a screenshotmi (fáza 5)

Dôvod: nechceme verejne WIP rozbité veci — GitHub history je **trvalá**.

## README — štruktúra

1. **Header + screenshoty** (~3 screenshoty hneď hore)
2. **What it does** — 3 vety
3. **Features** — bullet list
4. **Quick start** — docker-compose up v ideálnom prípade
5. **Supported banks** — zoznam s ikonkami
6. **Security** — krátky odstavec + link na [[03 - Security]]
7. **Development** — ako kontribuovať / setup env
8. **License** — AGPLv3 badge
9. **Acknowledgements** — GoCardless, FastAPI, HTMX, …

## Badges v README

- ![Build](ci.yml badge)
- ![License](AGPLv3 badge)
- ![Python](3.11+ badge)
- ![Last commit]

## Otvorené rozhodnutia

Pozri [[08 - Open Questions]]:
- Repo meno (`finance-dashboard`, `monyz`, `peniazomat`, `kasa`, ...)
- GitHub username (treba dodať)
- Licencia (AGPLv3 odporúčané, neschválené)
- Kedy switch public

## Post-launch nápady

- **GitHub Discussions** zapnuté pre feature requests
- **Demo screenshot / video** v READMU
- **Pridanie do awesome-self-hosted** listu (ak sa hodí)
- **Reddit r/selfhosted** post keď má ≥5 hviezd? (risky — chce to solid README)
