// Top bar: month picker, account filter chips, search, sync status

const topbarStyles = {
  root: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '16px 28px',
    borderBottom: '1px solid var(--line)',
    background: 'var(--bg)',
    position: 'sticky', top: 0, zIndex: 10,
  },
  title: { fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em', marginRight: 2 },
  sub: { fontSize: 12, color: 'var(--ink-3)' },
  monthGroup: {
    display: 'inline-flex', alignItems: 'center', gap: 2,
    padding: 3, borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--surface)',
  },
  monthBtn: (active) => ({
    padding: '4px 10px', borderRadius: 6, border: 0,
    background: active ? 'var(--ink)' : 'transparent',
    color: active ? 'var(--bg)' : 'var(--ink-2)',
    fontSize: 12, fontWeight: 500,
  }),
  chip: (active, tone) => ({
    display: 'inline-flex', alignItems: 'center', gap: 7,
    padding: '5px 10px 5px 8px', borderRadius: 999,
    border: '1px solid ' + (active ? 'var(--ink)' : 'var(--line)'),
    background: active ? 'var(--ink)' : 'var(--surface)',
    color: active ? 'var(--bg)' : 'var(--ink-2)',
    fontSize: 12, cursor: 'pointer',
  }),
  dot: (color) => ({ width: 7, height: 7, borderRadius: '50%', background: color }),
  search: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '6px 10px', borderRadius: 8,
    border: '1px solid var(--line)', background: 'var(--surface)',
    color: 'var(--ink-3)', fontSize: 13, minWidth: 200,
  },
  searchInput: {
    border: 0, outline: 'none', background: 'transparent',
    color: 'var(--ink)', fontSize: 13, width: '100%',
    fontFamily: 'inherit',
  },
  iconBtn: {
    width: 32, height: 32, display: 'grid', placeItems: 'center',
    border: '1px solid var(--line)', borderRadius: 8,
    background: 'var(--surface)', color: 'var(--ink-2)',
  },
  kbd: { fontSize: 10, padding: '1px 5px', border: '1px solid var(--line)', borderRadius: 4, color: 'var(--ink-3)', fontFamily: 'Geist Mono, monospace' },
};

function Topbar({ month, setMonth, account, setAccount, currency, setCurrency, onMenu }) {
  const chips = [
    { id: 'all',  name: 'Všetky',    color: 'var(--ink-3)' },
    ...ACCOUNTS.map(a => ({ id: a.id, name: a.name, color: a.color })),
  ];
  return (
    <div style={topbarStyles.root}>
      <button onClick={onMenu} style={{ ...topbarStyles.iconBtn, display: 'none' }} className="mobile-only">
        <Icon name="menu" size={16} />
      </button>
      <div>
        <div style={topbarStyles.title}>Dashboard</div>
        <div style={topbarStyles.sub}>{MONTHS[month].label} · {account === 'all' ? 'Všetky účty' : ACCOUNTS.find(a => a.id === account).name}</div>
      </div>

      <div style={{ flex: 1 }} />

      <div className="hide-sm" style={topbarStyles.search}>
        <Icon name="search" size={14} />
        <input placeholder="Hľadať transakciu, merchant…" style={topbarStyles.searchInput} />
        <span style={topbarStyles.kbd}>⌘K</span>
      </div>

      <div style={topbarStyles.monthGroup}>
        {Object.entries(MONTHS).map(([k, m]) => (
          <button key={k} style={topbarStyles.monthBtn(month === k)} onClick={() => setMonth(k)}>{m.short}</button>
        ))}
      </div>

      <div style={topbarStyles.monthGroup}>
        <button style={topbarStyles.monthBtn(currency === 'CZK')} onClick={() => setCurrency('CZK')}>Kč</button>
        <button style={topbarStyles.monthBtn(currency === 'EUR')} onClick={() => setCurrency('EUR')}>€</button>
      </div>

      <button style={topbarStyles.iconBtn}><Icon name="bell" size={15} /></button>
      <button style={topbarStyles.iconBtn}><Icon name="download" size={15} /></button>
    </div>
  );
}

// Secondary row of account chips (used under topbar)
function AccountChips({ account, setAccount, currency }) {
  const chips = [
    { id: 'all',  name: 'Všetky účty', color: 'var(--ink-3)', sub: 'agregované' },
    ...ACCOUNTS.map(a => {
      const bal = a.ccy === currency ? a.balance : (a.ccy === 'CZK' ? a.balance / FX.CZK_per_EUR : a.balance * FX.CZK_per_EUR);
      return { id: a.id, name: a.name, color: a.color, sub: fmtMoney(bal, currency, { decimals: 0 }) };
    }),
  ];
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '12px 28px 4px' }}>
      {chips.map(c => {
        const active = account === c.id;
        return (
          <button key={c.id} style={topbarStyles.chip(active)} onClick={() => setAccount(c.id)}>
            <span style={topbarStyles.dot(c.color)} />
            <span>{c.name}</span>
            <span className="mono tnum" style={{ opacity: active ? 0.8 : 0.55, fontSize: 11 }}>{c.sub}</span>
          </button>
        );
      })}
    </div>
  );
}

window.Topbar = Topbar;
window.AccountChips = AccountChips;
