// Root app — assembles dashboard with variants

const { useState, useEffect } = React;

function useTweaks() {
  const [tw, setTw] = useState(window.__TWEAKS);
  useEffect(() => {
    const onChange = (e) => setTw({ ...e.detail });
    window.addEventListener('tweaks:change', onChange);
    return () => window.removeEventListener('tweaks:change', onChange);
  }, []);
  return [tw, (k, v) => { window.__TWEAKS[k] = v; window.dispatchEvent(new CustomEvent('tweaks:change', { detail: { ...window.__TWEAKS } })); }];
}

const appStyles = {
  root: { display: 'flex', minHeight: '100vh', background: 'var(--bg)' },
  main: { flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' },
  content: { flex: 1, paddingBottom: 48 },
  experimentalBanner: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '3px 8px', borderRadius: 999,
    background: 'var(--accent)', color: 'var(--accent-ink)',
    fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
    fontFamily: 'Geist Mono',
  },
};

function Dashboard({ tw }) {
  const [activeCat, setActiveCat] = useState(null);
  return (
    <>
      <Topbar
        month={tw.month} setMonth={(m) => window.__TWEAKS.month = m || setT()}
        account={tw.account}
        currency={tw.currency} setCurrency={() => {}}
      />
      <AccountChips account={tw.account} setAccount={() => {}} currency={tw.currency} />
      <KpiCards month={tw.month} account={tw.account} currency={tw.currency} />
      <CashflowChart account={tw.account} currency={tw.currency} variant={tw.variant} />
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 0, alignItems: 'start' }} className="split">
        <div>
          <CategoriesBlock month={tw.month} account={tw.account} currency={tw.currency} variant={tw.variant} />
        </div>
        <div>
          <TransactionList account={tw.account} currency={tw.currency} limit={12} />
          <AccountsBlock month={tw.month} currency={tw.currency} />
        </div>
      </div>
    </>
  );
}

// The topbar above wraps its own state handlers — we re-wire via a small controller
function App() {
  const [tw, set] = useTweaks();
  const [activeCat, setActiveCat] = useState(null);
  const [nav, setNav] = useState('dashboard');

  const setMonth = (m) => set('month', m);
  const setAccount = (a) => set('account', a);
  const setCurrency = (c) => set('currency', c);

  return (
    <div style={appStyles.root}>
      <Sidebar
        nav={nav} setNav={setNav}
        month={tw.month} account={tw.account} currency={tw.currency}
        activeCat={activeCat} setActiveCat={setActiveCat}
      />
      <main style={appStyles.main}>
        <Topbar
          month={tw.month} setMonth={setMonth}
          account={tw.account} setAccount={setAccount}
          currency={tw.currency} setCurrency={setCurrency}
        />
        <AccountChips account={tw.account} setAccount={setAccount} currency={tw.currency} />
        <div style={{ padding: '8px 28px 0', display: 'flex', gap: 10, alignItems: 'center' }}>
          {tw.variant === 'exp' && <span style={appStyles.experimentalBanner}>Experimental</span>}
          <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
            {tw.variant === 'exp'
              ? 'Tmavý režim, vyšší kontrast, akcentová farba cobalt'
              : 'Čistý svetlý režim, jemné zelenkavé akcenty'}
          </span>
        </div>
        <div style={appStyles.content}>
          <KpiCards month={tw.month} account={tw.account} currency={tw.currency} />
          <CashflowChart account={tw.account} currency={tw.currency} variant={tw.variant} />
          <div className="split-grid">
            <CategoriesBlock month={tw.month} account={tw.account} currency={tw.currency} variant={tw.variant} />
            <div>
              <TransactionList account={tw.account} currency={tw.currency} limit={10} />
              <AccountsBlock month={tw.month} currency={tw.currency} />
            </div>
          </div>
        </div>
      </main>

      <style>{`
        .split-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
          gap: 0;
          align-items: start;
        }
        @media (max-width: 1100px) {
          .split-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 820px) {
          aside { display: none; }
        }
        .hide-sm { display: flex; }
        @media (max-width: 900px) { .hide-sm { display: none; } }
      `}</style>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
