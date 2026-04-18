// Categories breakdown — with trend, bar, amount
// Two variants: 'cons' (clean table) / 'exp' (richer w/ horizontal bars + compare)

const catStyles = {
  section: { padding: '0 28px', marginTop: 24 },
  head: {
    display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
    marginBottom: 12,
  },
  title: { fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' },
  sub: { fontSize: 12, color: 'var(--ink-3)' },
  wrap: {
    background: 'var(--surface)',
    border: '1px solid var(--line)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  },
  thead: {
    display: 'grid',
    gridTemplateColumns: '24px 1.5fr 1fr 0.8fr 70px 110px',
    alignItems: 'center', gap: 12,
    padding: '10px 18px',
    borderBottom: '1px solid var(--line)',
    fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: 'var(--ink-3)', fontWeight: 600,
    background: 'var(--bg-2)',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '24px 1.5fr 1fr 0.8fr 70px 110px',
    alignItems: 'center', gap: 12,
    padding: '11px 18px',
    borderBottom: '1px solid var(--line-2)',
    fontSize: 13,
  },
  rowLast: { borderBottom: 0 },
  ico: { width: 24, height: 24, borderRadius: 6, background: 'var(--bg-2)', display: 'grid', placeItems: 'center', color: 'var(--ink-2)' },
  name: { color: 'var(--ink)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  nameSub: { color: 'var(--ink-3)', fontSize: 11 },
  barCell: { display: 'flex', alignItems: 'center', gap: 8 },
  barTrack: { flex: 1, height: 4, background: 'var(--line)', borderRadius: 2, overflow: 'hidden', minWidth: 40 },
  barFill: (pct, color) => ({ height: '100%', width: pct + '%', background: color, borderRadius: 2 }),
  pct: { width: 36, textAlign: 'right', fontSize: 11, color: 'var(--ink-3)' },
  accDots: { display: 'flex', gap: 3, alignItems: 'center' },
  amt: { textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontFamily: 'Geist' },
};

function CategoryRow({ cat, data, total, month, account, currency, kind, variant }) {
  const amt = account === 'all' ? data.total : (data.by[account] || 0);
  const pct = total ? (amt / total) * 100 : 0;
  const series = seriesFor(cat.id, kind, account);
  const tone = kind === 'income' ? 'var(--pos)' : 'var(--accent)';
  const fmt = (n) => fmtMoney(toCcy(n, currency), currency, { decimals: 0 });

  // Account distribution dots
  const dots = ACCOUNTS.filter(a => (data.by[a.id] || 0) > 0).slice(0, 3);

  return (
    <div style={catStyles.row}>
      <div style={catStyles.ico}><Icon name={cat.icon} size={14} /></div>
      <div style={{ minWidth: 0 }}>
        <div style={catStyles.name}>{cat.name}</div>
        <div style={catStyles.nameSub}>{series[series.length - 2] > 0
          ? `${((amt - series[series.length - 2]) / series[series.length - 2] * 100).toFixed(0)}% vs. min. mesiac`
          : (amt > 0 ? 'nové v tomto mesiaci' : '—')}
        </div>
      </div>
      <div style={catStyles.barCell}>
        <div style={catStyles.barTrack}>
          <div style={catStyles.barFill(Math.min(100, pct), tone)} />
        </div>
        <span className="mono" style={catStyles.pct}>{pct.toFixed(0)}%</span>
      </div>
      <div style={catStyles.accDots}>
        {dots.map(a => <span key={a.id} title={a.name} style={{ width: 8, height: 8, borderRadius: '50%', background: a.color }} />)}
        {dots.length === 0 && <span style={{ color: 'var(--ink-4)', fontSize: 11 }}>—</span>}
      </div>
      <div style={{ color: 'var(--ink-3)' }}>
        <Sparkline values={series} stroke={tone} width={60} height={16} />
      </div>
      <div className="mono tnum" style={catStyles.amt}>{amt > 0 ? fmt(amt) : <span style={{ color: 'var(--ink-4)' }}>0</span>}</div>
    </div>
  );
}

function CategoryTable({ title, sub, cats, source, total, month, account, currency, kind, variant }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={catStyles.head}>
        <div>
          <div style={catStyles.title}>{title}</div>
          <div style={catStyles.sub}>{sub}</div>
        </div>
        <button style={{ background: 'transparent', border: '1px solid var(--line)', borderRadius: 8, padding: '4px 10px', fontSize: 12, color: 'var(--ink-2)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Icon name="filter" size={12} /> Filter
        </button>
      </div>
      <div style={catStyles.wrap}>
        <div style={catStyles.thead}>
          <span></span><span>Kategória</span><span>Podiel</span><span>Účty</span><span>Trend</span><span style={{ textAlign: 'right' }}>Suma</span>
        </div>
        {cats.map((c, i) => (
          <div key={c.id} style={i === cats.length - 1 ? { ...catStyles.rowLast } : null}>
            <CategoryRow
              cat={c} data={source[c.id]} total={total}
              month={month} account={account} currency={currency}
              kind={kind} variant={variant}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function CategoriesBlock({ month, account, currency, variant }) {
  const m = DATA[month];
  const t = monthTotals(month, account);

  return (
    <div style={catStyles.section}>
      <CategoryTable
        title="Výdaje podľa kategórií"
        sub="16 kategórií · zoradené podľa objemu"
        cats={[...EXPENSE_CATS].sort((a, b) => {
          const av = account === 'all' ? m.expense[a.id].total : (m.expense[a.id].by[account] || 0);
          const bv = account === 'all' ? m.expense[b.id].total : (m.expense[b.id].by[account] || 0);
          return bv - av;
        })}
        source={m.expense}
        total={t.expense}
        month={month} account={account} currency={currency}
        kind="expense" variant={variant}
      />
      <CategoryTable
        title="Príjmy podľa kategórií"
        sub="4 kategórie"
        cats={[...INCOME_CATS].sort((a, b) => {
          const av = account === 'all' ? m.income[a.id].total : (m.income[a.id].by[account] || 0);
          const bv = account === 'all' ? m.income[b.id].total : (m.income[b.id].by[account] || 0);
          return bv - av;
        })}
        source={m.income}
        total={t.income}
        month={month} account={account} currency={currency}
        kind="income" variant={variant}
      />
    </div>
  );
}

window.CategoriesBlock = CategoriesBlock;
