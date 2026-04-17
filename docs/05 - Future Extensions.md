---
tags:
  - project/finance
  - future
---

# Future Extensions

[[00 - Overview|← Späť na Overview]]

Plánované rozšírenia **po MVP** a po pár týždňoch reálneho používania.

## Trading212

> [!info] Má oficiálne public REST API od 2024
> Informácia že "Trading212 nemá API" je zastaraná.

### Čo vieme vytiahnuť
- Portfolio (equity positions)
- Cash balance
- Order history
- Dividendy
- Account metadata

### Setup
- API key si vygeneruješ v **Trading212 appke → Settings → API**
- Read-only scope dostupný
- Rate limity rozumné (stačí sync raz za pár hodín)

### Odhad implementácie
- **~2–3h** — nová trieda `Trading212Provider` implementujúca base interface

### Rozdiel oproti bankám
- **Žiadna 90-dňová re-autorizácia** (nie je PSD2)
- API key platí kým ho nezrušíš
- Transakcie nie sú "cash flow" — treba ich mapovať ako `type='investment'`

## Coinbase

### API
- **Advanced Trade API** (plnohodnotné REST)
- Read-only API keys dostupné
- Výborná dokumentácia

### Čo vieme vytiahnuť
- Účty s balance per coin
- History: buy, sell, send, receive, convert
- Portfolio value v EUR (automatická konverzia)
- Staking rewards (ak používaš)

### Odhad implementácie
- **~2–3h** — nová trieda `CoinbaseProvider`

### Rozdiel oproti bankám
- Žiadne PSD2 obmedzenie
- Potrebuje mapovanie `type='crypto'` s coin symbol + fiat cenou v čase

## DB schema musí dopredu podporovať

```
transactions.type: 'bank' | 'investment' | 'crypto'

-- investment extras
ticker, quantity, unit_price, fee

-- crypto extras
coin_symbol, amount_coin, fiat_price_at_time, network_fee
```

> [!warning] Schema decision od MVP
> Aj keď MVP bude len banky, schema a Provider interface **musia byť navrhnuté tak aby pridanie investment/crypto nevyžadovalo refactor**.

## Dashboard views (oddelené)

- **Cash Flow** (z bánk) — príjmy/výdavky, kategórie
- **Portfolio Value** (investície + krypto) — hodnota v čase, allocation

## Ďalšie možné providery (zatiaľ len brainstorm)

- **Binance** — crypto, má public API, read-only keys
- **XTB / Degiro** — bez public API, museli by sa CSV importy
- **Revolut Crypto** — mohlo by ísť cez GoCardless ak to zaradí medzi účty, inak CSV
- **PayPal** — má API, ale komplikované
- **Apple Card / Google Pay** — zapojené do bankových účtov, takže by sa to už mohlo vidieť cez GoCardless

## Nie-provider features do budúcna

- **Budgeting** — stanoviť mesačný limit na kategóriu, warning keď sa blíži
- **Receipts upload** — pripojiť foto bločku k transakcii
- **Tags** — ľubovoľné tagy popri kategóriách
- **Forecasting** — predpoveď konca mesiaca na základe trendu
- **Multi-currency** — ak budeš mať USD účty, konverzia do primárnej meny (EUR)
- **Rules engine** nad regexom — napr. "ak merchant = Lidl AND amount > 50 THEN category = 'Veľký nákup'"
