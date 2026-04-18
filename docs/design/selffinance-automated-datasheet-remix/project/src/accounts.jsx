// Accounts summary block — 3 account cards with balance + this-month flow

const accStyles = {
  section: { padding: '0 28px', marginTop: 24 },
  head: { marginBottom: 12 },
  title: { fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' },
  sub: { fontSize: 12, color: 'var(--ink-3)' },
  grid: { display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' },
  card: (color) => ({
    background: 'var(--surface)',
    border: '1px solid var(--line)',
    borderLeft: `3px solid ${color}`,
    borderRadius: 'var(--radius-lg)',
    padding: '16px 18px',
    display: 'flex', flexDirection: 'column', gap: 4,
  }),
  bankRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  bank: { fontSize: 12, color: 'var(--ink-3)' },
  name: { fontSize: 14, fontWeight: 600, color: 'var(--ink)' },
  bal: { fontSize: 22, fontWeight: 500, letterSpacing: '-0.02em', marginTop: 10, fontFamily: 'Geist', fontVariantNumeric: 'tabular-nums' },
  iban: { fontSize: 11, color: 'var(--ink-3)', marginTop: 2 },
  flow: { display: 'flex', gap: 14, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line-2)', fontSize: 11 },
  flowLabel: { color: 'var(--ink-3)', display: 'block' },
  flowAmt: (tone) => ({ fontFamily: 'Geist', fontVariantNumeric: 'tabular-nums', fontSize: 13, color: tone, fontWeight: 500 }),
};

function AccountsBlock({ month, currency }) {
  const m = DATA[month];
  return (
    <div style={accStyles.section}>
      <div style={accStyles.head}>
        <div style={accStyles.title}>Účty</div>
        <div style={accStyles.sub}>3 pripojené účty · posledná sync 14:32</div>
      </div>
      <div style={accStyles.grid}>
        {ACCOUNTS.map(a => {
          const balDisplay = a.ccy === currency ? a.balance : (a.ccy === 'CZK' ? a.balance / FX.CZK_per_EUR : a.balance * FX.CZK_per_EUR);
          const accIn = Object.values(m.income).reduce((s, v) => s + (v.by[a.id] || 0), 0);
          const accOut = Object.values(m.expense).reduce((s, v) => s + (v.by[a.id] || 0), 0);
          return (
            <div key={a.id} style={accStyles.card(a.color)}>
              <div style={accStyles.bankRow}>
                <div style={accStyles.bank}>{a.bank}</div>
                <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>{a.ccy}</span>
              </div>
              <div style={accStyles.name}>{a.name}</div>
              <div className="mono tnum" style={accStyles.bal}>{fmtMoney(balDisplay, currency, { decimals: 2 })}</div>
              <div style={accStyles.iban}>{a.iban}</div>
              <div style={accStyles.flow}>
                <div style={{ flex: 1 }}>
                  <span style={accStyles.flowLabel}>Príjmy {MONTHS[month].short}</span>
                  <span className="mono" style={accStyles.flowAmt('var(--pos)')}>
                    {fmtMoney(toCcy(accIn, currency), currency, { decimals: 0 })}
                  </span>
                </div>
                <div style={{ flex: 1 }}>
                  <span style={accStyles.flowLabel}>Výdaje {MONTHS[month].short}</span>
                  <span className="mono" style={accStyles.flowAmt('var(--neg)')}>
                    {fmtMoney(toCcy(accOut, currency), currency, { decimals: 0 })}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

window.AccountsBlock = AccountsBlock;
