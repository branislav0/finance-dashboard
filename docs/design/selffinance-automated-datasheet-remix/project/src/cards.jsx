// KPI cards + summary blocks

const cardStyles = {
  grid: {
    display: 'grid', gap: 16,
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    padding: '16px 28px 0',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--line)',
    borderRadius: 'var(--radius-lg)',
    padding: '16px 18px',
  },
  accentCard: {
    background: 'var(--ink)',
    color: 'var(--bg)',
    border: '1px solid var(--ink)',
    borderRadius: 'var(--radius-lg)',
    padding: '16px 18px',
  },
  label: { fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-3)', fontWeight: 600 },
  labelOnDark: { fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'oklch(0.75 0.01 240)', fontWeight: 600 },
  value: { fontSize: 28, fontWeight: 500, letterSpacing: '-0.02em', marginTop: 6, fontFamily: 'Geist', fontVariantNumeric: 'tabular-nums' },
  delta: (pos) => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    marginTop: 8, fontSize: 12,
    color: pos ? 'var(--pos)' : 'var(--neg)',
    fontVariantNumeric: 'tabular-nums',
  }),
  row: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  barTrack: { height: 4, borderRadius: 2, background: 'var(--line)', overflow: 'hidden', marginTop: 14 },
  barFill: (pct, color) => ({ height: '100%', width: pct + '%', background: color, borderRadius: 2 }),
  sub: { fontSize: 11, color: 'var(--ink-3)', marginTop: 6, display: 'flex', justifyContent: 'space-between' },
};

function KpiCards({ month, account, currency }) {
  const t = monthTotals(month, account);
  const prevKey = month === 'mar' ? 'feb' : (month === 'feb' ? 'jan' : 'jan');
  const prev = monthTotals(prevKey, account);
  const fmt = (n, d) => fmtMoney(toCcy(n, currency), currency, { decimals: d ?? 0 });

  const incDelta = prev.income ? ((t.income - prev.income) / prev.income) * 100 : 0;
  const expDelta = prev.expense ? ((t.expense - prev.expense) / prev.expense) * 100 : 0;

  const savingsRate = t.income > 0 ? (t.net / t.income) * 100 : 0;

  // Budget sample
  const budgetCap = account === 'all' ? 42000 : 20000;
  const spent = t.expense;
  const pct = Math.min(100, (spent / budgetCap) * 100);

  return (
    <div style={cardStyles.grid}>
      <div style={cardStyles.accentCard}>
        <div style={cardStyles.row}>
          <div style={cardStyles.labelOnDark}>Zostatok na konci mesiaca</div>
          <Icon name="wallet" size={14} style={{ color: 'oklch(0.75 0.01 240)' }} />
        </div>
        <div style={cardStyles.value}>{fmt(t.net, 0)}</div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'oklch(0.80 0.01 240)' }}>
          Príjmy <span className="mono tnum" style={{ color: 'var(--pos)' }}>{fmt(t.income, 0)}</span>
          <span style={{ margin: '0 8px', opacity: 0.3 }}>·</span>
          Výdaje <span className="mono tnum" style={{ color: 'oklch(0.80 0.12 28)' }}>{fmt(t.expense, 0)}</span>
        </div>
      </div>

      <div style={cardStyles.card}>
        <div style={cardStyles.row}>
          <div style={cardStyles.label}>Príjmy</div>
          <Icon name="arrowDown" size={14} style={{ color: 'var(--pos)', transform: 'rotate(180deg)' }} />
        </div>
        <div style={cardStyles.value}>{fmt(t.income, 0)}</div>
        <div style={cardStyles.delta(incDelta >= 0)}>
          <Icon name={incDelta >= 0 ? 'arrowUp' : 'arrowDown'} size={12} />
          <span className="mono">{Math.abs(incDelta).toFixed(1)}%</span>
          <span style={{ color: 'var(--ink-3)' }}>vs. {MONTHS[prevKey].short}</span>
        </div>
      </div>

      <div style={cardStyles.card}>
        <div style={cardStyles.row}>
          <div style={cardStyles.label}>Výdaje</div>
          <Icon name="arrowUp" size={14} style={{ color: 'var(--neg)', transform: 'rotate(180deg)' }} />
        </div>
        <div style={cardStyles.value}>{fmt(t.expense, 0)}</div>
        <div style={cardStyles.delta(expDelta <= 0)}>
          <Icon name={expDelta >= 0 ? 'arrowUp' : 'arrowDown'} size={12} />
          <span className="mono">{Math.abs(expDelta).toFixed(1)}%</span>
          <span style={{ color: 'var(--ink-3)' }}>vs. {MONTHS[prevKey].short}</span>
        </div>
      </div>

      <div style={cardStyles.card}>
        <div style={cardStyles.row}>
          <div style={cardStyles.label}>Miera sporenia</div>
          <Icon name="target" size={14} style={{ color: 'var(--ink-3)' }} />
        </div>
        <div style={cardStyles.value}>{savingsRate.toFixed(1)}%</div>
        <div style={cardStyles.barTrack}>
          <div style={cardStyles.barFill(Math.max(0, Math.min(100, savingsRate)), 'var(--accent)')} />
        </div>
        <div style={cardStyles.sub}>
          <span>cieľ 25%</span>
          <span className="mono tnum">{fmt(t.net, 0)} usporené</span>
        </div>
      </div>
    </div>
  );
}

window.KpiCards = KpiCards;
