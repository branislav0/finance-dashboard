// Cashflow chart — 3-month income/expense bars with net line (experimental variant adds stacked category breakdown)

const chartStyles = {
  section: { padding: '0 28px', marginTop: 24 },
  head: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 },
  title: { fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' },
  sub: { fontSize: 12, color: 'var(--ink-3)' },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--line)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px 22px',
  },
  legend: { display: 'flex', gap: 16, fontSize: 12, color: 'var(--ink-2)' },
  legendItem: { display: 'inline-flex', alignItems: 'center', gap: 6 },
  swatch: (c) => ({ width: 10, height: 10, borderRadius: 2, background: c }),
};

function CashflowChart({ account, currency, variant }) {
  const months = Object.keys(MONTHS);
  const totals = months.map(m => monthTotals(m, account));
  const maxVal = Math.max(...totals.flatMap(t => [t.income, t.expense])) || 1;

  const W = 600, H = 200, pad = { t: 10, r: 20, b: 28, l: 40 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const gw = plotW / months.length;
  const bw = variant === 'exp' ? 18 : 22;
  const gap = 4;

  const fmt = (n) => fmtMoney(toCcy(n, currency), currency, { decimals: 0 });

  const ticks = 4;
  const tickVals = Array.from({ length: ticks + 1 }, (_, i) => (maxVal / ticks) * i);

  // Net polyline
  const netPts = totals.map((t, i) => {
    const x = pad.l + gw * i + gw / 2;
    const y = pad.t + plotH - (t.net / maxVal) * plotH;
    return [x, y];
  });
  const netPath = netPts.map((p, i) => (i ? 'L' : 'M') + p[0] + ' ' + p[1]).join(' ');

  return (
    <div style={chartStyles.section}>
      <div style={chartStyles.head}>
        <div>
          <div style={chartStyles.title}>Cashflow · 3 mesiace</div>
          <div style={chartStyles.sub}>príjmy vs. výdaje, zostatok na konci mesiaca</div>
        </div>
        <div style={chartStyles.legend}>
          <span style={chartStyles.legendItem}><span style={chartStyles.swatch('var(--pos)')} /> Príjmy</span>
          <span style={chartStyles.legendItem}><span style={chartStyles.swatch('var(--accent)')} /> Výdaje</span>
          <span style={chartStyles.legendItem}><span style={{ ...chartStyles.swatch('var(--ink)'), borderRadius: 999 }} /> Zostatok</span>
        </div>
      </div>

      <div style={chartStyles.card}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
          {/* gridlines */}
          {tickVals.map((v, i) => {
            const y = pad.t + plotH - (v / maxVal) * plotH;
            return (
              <g key={i}>
                <line x1={pad.l} x2={W - pad.r} y1={y} y2={y} stroke="var(--line)" strokeDasharray={i === 0 ? '' : '2 3'} strokeWidth="1" />
                <text x={pad.l - 8} y={y + 3} textAnchor="end" fontSize="9" fill="var(--ink-3)" fontFamily="Geist Mono">
                  {v >= 1000 ? (toCcy(v, currency) / 1000).toFixed(0) + 'k' : toCcy(v, currency).toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* bars */}
          {totals.map((t, i) => {
            const cx = pad.l + gw * i + gw / 2;
            const incH = (t.income / maxVal) * plotH;
            const expH = (t.expense / maxVal) * plotH;
            const incX = cx - bw - gap / 2;
            const expX = cx + gap / 2;
            const baseY = pad.t + plotH;
            return (
              <g key={i}>
                <rect x={incX} y={baseY - incH} width={bw} height={incH} rx="2" fill="var(--pos)" opacity="0.9" />
                <rect x={expX} y={baseY - expH} width={bw} height={expH} rx="2" fill="var(--accent)" opacity={variant === 'exp' ? 0.9 : 0.8} />
                <text x={cx} y={H - 10} textAnchor="middle" fontSize="11" fill="var(--ink-2)" fontFamily="Geist">
                  {MONTHS[months[i]].short}
                </text>
              </g>
            );
          })}

          {/* net line */}
          <path d={netPath} stroke="var(--ink)" strokeWidth="1.5" fill="none" />
          {netPts.map((p, i) => (
            <g key={i}>
              <circle cx={p[0]} cy={p[1]} r="3.5" fill="var(--bg)" stroke="var(--ink)" strokeWidth="1.5" />
              <text x={p[0]} y={p[1] - 10} textAnchor="middle" fontSize="10" fill="var(--ink)" fontFamily="Geist Mono" fontWeight="500">
                {fmt(totals[i].net)}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}

window.CashflowChart = CashflowChart;
