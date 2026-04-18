// Finance data — mock realistic dataset driven by user's spreadsheet categories
// 3 accounts: main (bežný), save (sporiaci), revo (Revolut)

const ACCOUNTS = [
  { id: 'main', name: 'Bežný účet', bank: 'Tatra banka',   iban: 'SK12 1100 ••• 0042', ccy: 'EUR', balance: 2840.15, color: 'oklch(0.72 0.11 145)' },
  { id: 'save', name: 'Sporiaci',   bank: '365.bank',       iban: 'SK22 8330 ••• 9911', ccy: 'EUR', balance: 12450.00, color: 'oklch(0.70 0.10 245)' },
  { id: 'revo', name: 'Revolut',    bank: 'Revolut',        iban: 'LT45 3250 ••• 7788', ccy: 'CZK', balance: 18420.00, color: 'oklch(0.72 0.09 310)' },
];

// Category hierarchy directly from user's spreadsheet
const INCOME_CATS = [
  { id: 'salary',    name: 'Príjem z práce',      icon: 'briefcase' },
  { id: 'side',      name: 'Vedľajší príjem',     icon: 'sparkle'   },
  { id: 'family',    name: 'Rodina',              icon: 'heart'     },
  { id: 'other_in',  name: 'Iné',                 icon: 'dot'       },
];

const EXPENSE_CATS = [
  { id: 'housing',   name: 'Bývanie',             icon: 'home'      },
  { id: 'fuel',      name: 'Nafta / doprava',     icon: 'fuel'      },
  { id: 'grocery',   name: 'Supermarkety',        icon: 'cart'      },
  { id: 'clothing',  name: 'Oblečenie, topánky',  icon: 'shirt'     },
  { id: 'tobacco',   name: 'Tabak',               icon: 'flame'     },
  { id: 'restaurant',name: 'Reštaurácie / fastfood', icon: 'fork' },
  { id: 'subs',      name: 'Subscriptions',       icon: 'repeat'    },
  { id: 'brno',      name: 'Brno (MHD, mesto)',   icon: 'tram'      },
  { id: 'extra',     name: 'Mimoriadne výdaje',   icon: 'bolt'      },
  { id: 'gifts',     name: 'Darčeky',             icon: 'gift'      },
  { id: 'fun',       name: 'Zábava (hry, kultúra)', icon: 'joystick' },
  { id: 'fitness',   name: 'Fitness a zdravie',   icon: 'pulse'     },
  { id: 'hygiene',   name: 'Hygiena',             icon: 'drop'      },
  { id: 'atm',       name: 'Výber z bankomatu',   icon: 'banknote'  },
  { id: 'stocks',    name: 'Investície — Akcie',  icon: 'trend'     },
  { id: 'crypto',    name: 'Investície — Crypto', icon: 'coin'      },
];

const CAT_BY_ID = Object.fromEntries([...INCOME_CATS, ...EXPENSE_CATS].map(c => [c.id, c]));

// Mock monthly aggregates (CZK). Account split is in "by" fields.
// Shape: { [monthKey]: { income: {catId: {total, by:{acc:amt}}}, expense: {...}, tx: [...] } }
const MONTHS = {
  jan: { label: 'Január 2026',   short: 'Jan' },
  feb: { label: 'Február 2026',  short: 'Feb' },
  mar: { label: 'Marec 2026',    short: 'Mar' },
};

const DATA = {
  jan: {
    income: {
      salary:   { total: 58200,  by: { main: 58200 } },
      side:     { total: 4500,   by: { revo: 4500 } },
      family:   { total: 0,      by: {} },
      other_in: { total: 320,    by: { main: 320 } },
    },
    expense: {
      housing:    { total: 15200, by: { main: 15200 } },
      fuel:       { total: 3120,  by: { main: 2200, revo: 920 } },
      grocery:    { total: 6840,  by: { main: 4200, revo: 2640 } },
      clothing:   { total: 1490,  by: { revo: 1490 } },
      tobacco:    { total: 1200,  by: { main: 1200 } },
      restaurant: { total: 2780,  by: { main: 1200, revo: 1580 } },
      subs:       { total: 489,   by: { revo: 489 } },
      brno:       { total: 670,   by: { main: 670 } },
      extra:      { total: 0,     by: {} },
      gifts:      { total: 850,   by: { main: 850 } },
      fun:        { total: 1240,  by: { revo: 1240 } },
      fitness:    { total: 599,   by: { main: 599 } },
      hygiene:    { total: 420,   by: { main: 420 } },
      atm:        { total: 1500,  by: { main: 1500 } },
      stocks:     { total: 3000,  by: { save: 3000 } },
      crypto:     { total: 1500,  by: { revo: 1500 } },
    },
  },
  feb: {
    income: {
      salary:   { total: 62100, by: { main: 62100 } },
      side:     { total: 8200,  by: { revo: 8200 } },
      family:   { total: 1500,  by: { main: 1500 } },
      other_in: { total: 0,     by: {} },
    },
    expense: {
      housing:    { total: 15200, by: { main: 15200 } },
      fuel:       { total: 2890,  by: { main: 1870, revo: 1020 } },
      grocery:    { total: 7240,  by: { main: 4580, revo: 2660 } },
      clothing:   { total: 3290,  by: { revo: 3290 } },
      tobacco:    { total: 980,   by: { main: 980 } },
      restaurant: { total: 3450,  by: { main: 1650, revo: 1800 } },
      subs:       { total: 489,   by: { revo: 489 } },
      brno:       { total: 670,   by: { main: 670 } },
      extra:      { total: 2400,  by: { main: 2400 } },
      gifts:      { total: 320,   by: { main: 320 } },
      fun:        { total: 1890,  by: { revo: 1890 } },
      fitness:    { total: 599,   by: { main: 599 } },
      hygiene:    { total: 510,   by: { main: 510 } },
      atm:        { total: 2000,  by: { main: 2000 } },
      stocks:     { total: 4000,  by: { save: 4000 } },
      crypto:     { total: 2500,  by: { revo: 2500 } },
    },
  },
  mar: {
    income: {
      salary:   { total: 62100, by: { main: 62100 } },
      side:     { total: 3200,  by: { revo: 3200 } },
      family:   { total: 0,     by: {} },
      other_in: { total: 180,   by: { main: 180 } },
    },
    expense: {
      housing:    { total: 15200, by: { main: 15200 } },
      fuel:       { total: 3340,  by: { main: 2240, revo: 1100 } },
      grocery:    { total: 6120,  by: { main: 3980, revo: 2140 } },
      clothing:   { total: 780,   by: { revo: 780 } },
      tobacco:    { total: 1100,  by: { main: 1100 } },
      restaurant: { total: 2190,  by: { main: 940, revo: 1250 } },
      subs:       { total: 489,   by: { revo: 489 } },
      brno:       { total: 670,   by: { main: 670 } },
      extra:      { total: 0,     by: {} },
      gifts:      { total: 0,     by: {} },
      fun:        { total: 890,   by: { revo: 890 } },
      fitness:    { total: 599,   by: { main: 599 } },
      hygiene:    { total: 380,   by: { main: 380 } },
      atm:        { total: 1000,  by: { main: 1000 } },
      stocks:     { total: 3000,  by: { save: 3000 } },
      crypto:     { total: 1800,  by: { revo: 1800 } },
    },
  },
};

// Recent transactions (mock, CZK) — used for "Posledné transakcie" block
const TRANSACTIONS = [
  { id: 't1',  date: '2026-02-17', merchant: 'Lidl Brno-Slatina',    cat: 'grocery',    acc: 'main', amt: -1284.20 },
  { id: 't2',  date: '2026-02-17', merchant: 'Shell Svitavská',       cat: 'fuel',       acc: 'main', amt: -1450.00 },
  { id: 't3',  date: '2026-02-16', merchant: 'Spotify Premium',       cat: 'subs',       acc: 'revo', amt: -169.00  },
  { id: 't4',  date: '2026-02-16', merchant: 'Zásilkovna — ZARA',     cat: 'clothing',   acc: 'revo', amt: -1890.00 },
  { id: 't5',  date: '2026-02-15', merchant: 'Wolt — Ramen Shifu',    cat: 'restaurant', acc: 'revo', amt: -349.00  },
  { id: 't6',  date: '2026-02-15', merchant: 'DPMB jízdenka 150',     cat: 'brno',       acc: 'main', amt: -150.00  },
  { id: 't7',  date: '2026-02-14', merchant: 'Mzda — Acme s.r.o.',    cat: 'salary',     acc: 'main', amt: 62100.00 },
  { id: 't8',  date: '2026-02-13', merchant: 'Binance — BTC',         cat: 'crypto',     acc: 'revo', amt: -2500.00 },
  { id: 't9',  date: '2026-02-12', merchant: 'Tabák U Nádraží',       cat: 'tobacco',    acc: 'main', amt: -135.00  },
  { id: 't10', date: '2026-02-11', merchant: 'Albert Vaňkovka',       cat: 'grocery',    acc: 'main', amt: -682.40  },
  { id: 't11', date: '2026-02-11', merchant: 'FitnessCentrum MultiSport', cat: 'fitness', acc: 'main', amt: -599.00 },
  { id: 't12', date: '2026-02-10', merchant: 'Nájom — Veveří 42',     cat: 'housing',    acc: 'main', amt: -15200.00},
  { id: 't13', date: '2026-02-09', merchant: 'Upwork výplata',        cat: 'side',       acc: 'revo', amt: 8200.00  },
  { id: 't14', date: '2026-02-08', merchant: 'Kino Scala — Anora',    cat: 'fun',        acc: 'revo', amt: -260.00  },
  { id: 't15', date: '2026-02-07', merchant: 'ATM MONETA',            cat: 'atm',        acc: 'main', amt: -2000.00 },
];

// FX rate (mock)
const FX = { CZK_per_EUR: 25.2 };
function toCcy(amountCZK, ccy) {
  if (ccy === 'EUR') return amountCZK / FX.CZK_per_EUR;
  return amountCZK;
}
function fmtMoney(amount, ccy, opts = {}) {
  const sign = amount < 0 ? '−' : (opts.alwaysSign && amount > 0 ? '+' : '');
  const abs = Math.abs(amount);
  const locale = ccy === 'EUR' ? 'sk-SK' : 'cs-CZ';
  const str = new Intl.NumberFormat(locale, { minimumFractionDigits: opts.decimals ?? (abs < 100 ? 2 : 0), maximumFractionDigits: opts.decimals ?? (abs < 100 ? 2 : 0) }).format(abs);
  const sym = ccy === 'EUR' ? '€' : 'Kč';
  return `${sign}${str}\u00A0${sym}`;
}

// Aggregate totals helper
function monthTotals(monthKey, accountFilter = 'all') {
  const m = DATA[monthKey];
  const inc = Object.entries(m.income).reduce((a, [k, v]) => a + (accountFilter === 'all' ? v.total : (v.by[accountFilter] || 0)), 0);
  const exp = Object.entries(m.expense).reduce((a, [k, v]) => a + (accountFilter === 'all' ? v.total : (v.by[accountFilter] || 0)), 0);
  return { income: inc, expense: exp, net: inc - exp };
}

// Trend series (3 months)
function seriesFor(catId, kind, accountFilter = 'all') {
  return Object.keys(MONTHS).map(m => {
    const v = DATA[m][kind][catId];
    if (!v) return 0;
    return accountFilter === 'all' ? v.total : (v.by[accountFilter] || 0);
  });
}

Object.assign(window, {
  ACCOUNTS, INCOME_CATS, EXPENSE_CATS, CAT_BY_ID,
  MONTHS, DATA, TRANSACTIONS, FX,
  toCcy, fmtMoney, monthTotals, seriesFor,
});
