---
tags:
  - project/finance
  - tech/security
---

# Bezpečnosť & Threat Model

[[00 - Overview|← Späť na Overview]]

## TL;DR

> [!success] Nikto nemôže ukradnúť peniaze cez túto appku
> GoCardless tokeny sú **read-only** a PSD2 architektúra **nevyžaduje bankové heslo**. Najhorší scenár = leak transakcií (privacy), nie krádež peňazí.

## Čo chráni appku

### Sieťová vrstva

- **Tailscale-only binding** — appka počúva len na `100.x.x.x` interface, **nikdy nie na verejnej IP**
- Nikto z internetu sa k nej nedostane ani keby chcel
- Tailscale = WireGuard (end-to-end encrypted)

### Aplikačná vrstva

- **Login s Argon2 hash** — aj keby niekto bol na tvojej Tailscale sieti, ešte stále potrebuje heslo
- Voliteľne **TOTP 2FA** (Google Authenticator)
- Session cookies s `HttpOnly + Secure + SameSite=Strict`

### Credentials / secrets

- **API tokeny v `.env`** s `chmod 600` (číta len user `rpios`)
- **GoCardless tokeny sú read-only** — aj keby unikli, nikto peniaze neposlal
- Žiadne hardcoded secrets v repo (`.env.example` ako template)

### Dáta at rest

- SQLite na RPi disku — neposiela sa nikam
- Voliteľne **SQLCipher** (šifrovaná SQLite) — ale realisticky ak má niekto root na RPi, je to aj tak koniec
- **Šifrované zálohy** (`age` alebo `gpg`) — rsync cez Tailscale na iné zariadenie

## Threat model — realistické hrozby

Zoradené od najpravdepodobnejšieho:

### 1. Strata odomknutého telefónu s Tailscale + app heslom
**Mitigation:** App login + TOTP 2FA. Bez TOTP útočník stále potrebuje heslo do appky.

### 2. Kompromitácia RPi (SSH brute force, zranteľný balíček)
**Mitigation:** Tailscale-only prístup aj k SSH, fail2ban, pravidelné `apt update`, kľúč-only auth.

### 3. GoCardless data breach
**Impact:** Privacy leak (transakcie, IBAN). **Peniaze v bezpečí.**
**Mitigation:** Nič sami neurobíme, dôvera v ich SOC 2 / ISO 27001.

### 4. Leak `.env` súboru z RPi
**Impact:** Útočník môže čítať tvoje transakcie cez GoCardless API (90 dní, potom expire).
**Peniaze v bezpečí** — read-only tokeny.
**Mitigation:** `chmod 600`, `.env` v `.gitignore`, žiadny commit secretov.

### 5. Supply chain attack (kompromitovaný Python balíček)
**Mitigation:** Pin verzie v `pyproject.toml`, `pip-audit` v CI, obmedziť deps na minimum.

## Čo NECHRÁNI (buďme úprimní)

- ❌ Fyzický prístup k RPi + vedomosť hesla = vidí všetko (rovnaké ako tvoj Excel teraz)
- ❌ Kompromitované tvoje vlastné zariadenie s Tailscale (RPi, notebook, telefón)
- ❌ Ak by si sám dal `.env` do verejného GitHub repa 😬

## Porovnanie s alternativami

| Scenár | Táto appka | Excel v OneDrive/GDrive | Papierový zošit |
|--------|-----------|-------------------------|-----------------|
| Útočník z internetu | **Nevidí** (Tailscale) | Vidí ak ti prelomí MS/Google účet | Nevidí |
| Tvoj cloud provider | **Nemá dáta** | **Má dáta** (aj keď šifrované) | Nevidí |
| Stratený telefón | Potrebuje app heslo | Potrebuje heslo do OneDrive | N/A |
| Krádež peňazí cez únik dát | **Nemožná** | Nemožná | Nemožná |

**Záver:** Výrazne lepšie ako Excel v cloude, porovnateľné s bankovou appkou pokiaľ ide o prístup k dátam, a úplne mimo dosahu verejného internetu.

## Checklist pri nasadení

- [ ] `.env` v `.gitignore` (pre istotu aj `*.db`)
- [ ] `chmod 600 .env`
- [ ] App binding na Tailscale IP, nie `0.0.0.0`
- [ ] Login endpoint s rate limiting
- [ ] Argon2 pre hashing hesiel (nie bcrypt, nie MD5, NIKDY plaintext)
- [ ] Session cookies `HttpOnly + Secure + SameSite`
- [ ] Test: appka NIE je dostupná z bežného WiFi bez Tailscale
- [ ] CI kontroluje že `.env` nie je v repo
