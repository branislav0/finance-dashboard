// Transactions feed — recent activity list

const txStyles = {
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
  dateHead: {
    padding: '8px 18px',
    fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: 'var(--ink-3)', fontWeight: 600,
    background: 'var(--bg-2)',
    borderBottom: '1px solid var(--line-2)',
    borderTop: '1px solid var(--line-2)',
    display: 'flex', justifyContent: 'space-between',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '28px 1fr auto auto',
    alignItems: 'center', gap: 12,
    padding: '10px 18px',
    fontSize: 13,
    borderBottom: '1px solid var(--line-2)',
  },
  ico: {
    width: 28, height: 28, borderRadius: 8, background: 'var(--bg-2)',
    display: 'grid', placeItems: 'center', color: 'var(--ink-2)',
  },
  merchant: { fontWeight: 500, color: 'var(--ink)' },
  meta: { fontSize: 11, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 },
  dot: (color) => ({ width: 6, height: 6, borderRadius: '50%', background: color }),
  amt: (pos) => ({
    fontVariantNumeric: 'tabular-nums', fontFamily: 'Geist',
    color: pos ? 'var(--pos)' : 'var(--ink)',
    fontWeight: 500,
  }),
};

function groupByDate(txs) {
  const out = {};
  for (const t of txs) {
    (out[t.date] ||= []).push(t);
  }
  return Object.entries(out).sort((a, b) => a[0] < b[0] ? 1 : -1);
}

function formatDate(s) {
  const d = new Date(s);
  const today = new Date('2026-02-17');
  const diff = Math.round((today - d) / (1000 * 60 * 60 * 24));
  if (diff === 0) return 'Dnes';
  if (diff === 1) return 'Včera';
  const names = ['nedeľa','pondelok','utorok','streda','štvrtok','piatok','sobota'];
  return `${d.getDate()}. ${['jan','feb','mar','apr','máj','jún','júl','aug','sep','okt','nov','dec'][d.getMonth()]}`;
}

function TransactionList({ account, currency, limit = 10 }) {
  const filtered = TRANSACTIONS.filter(t => account === 'all' || t.acc === account).slice(0, limit);
  const groups = groupByDate(filtered);
  const fmt = (n) => fmtMoney(toCcy(n, currency), currency, { decimals: 2, alwaysSign: n > 0 });

  return (
    <div style={txStyles.section}>
      <div style={txStyles.head}>
        <div>
          <div style={txStyles.title}>Posledné transakcie</div>
          <div style={txStyles.sub}>synchronizované automaticky z bánk · {filtered.length} položiek</div>
        </div>
        <a href="#" style={{ fontSize: 12, color: 'var(--ink-2)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          Všetky transakcie <Icon name="chevRight" size={12} />
        </a>
      </div>
      <div style={txStyles.wrap}>
        {groups.map(([date, rows], gi) => {
          const dayTotal = rows.reduce((a, r) => a + r.amt, 0);
          return (
            <React.Fragment key={date}>
              <div style={{ ...txStyles.dateHead, ...(gi === 0 ? { borderTop: 0 } : {}) }}>
                <span>{formatDate(date)}</span>
                <span className="mono tnum">{fmt(dayTotal)}</span>
              </div>
              {rows.map((t, i) => {
                const cat = CAT_BY_ID[t.cat];
                const acc = ACCOUNTS.find(a => a.id === t.acc);
                return (
                  <div key={t.id} style={{ ...txStyles.row, ...(i === rows.length - 1 && gi === groups.length - 1 ? { borderBottom: 0 } : {}) }}>
                    <div style={txStyles.ico}><Icon name={cat.icon} size={14} /></div>
                    <div style={{ minWidth: 0 }}>
                      <div style={txStyles.merchant}>{t.merchant}</div>
                      <div style={txStyles.meta}>
                        <span>{cat.name}</span>
                        <span style={{ opacity: 0.4 }}>·</span>
                        <span style={txStyles.dot(acc.color)} />
                        <span>{acc.name}</span>
                      </div>
                    </div>
                    <div />
                    <div className="mono" style={txStyles.amt(t.amt > 0)}>{fmt(t.amt)}</div>
                  </div>
                );
              })}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

window.TransactionList = TransactionList;
