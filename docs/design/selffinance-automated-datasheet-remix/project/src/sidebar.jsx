// Left sidebar with categories (income + expense) — mirrors the user's spreadsheet.

const sidebarStyles = {
  root: {
    width: 268, flex: '0 0 268px',
    background: 'var(--bg-2)',
    borderRight: '1px solid var(--line)',
    display: 'flex', flexDirection: 'column',
    height: '100vh', position: 'sticky', top: 0,
    overflow: 'hidden',
  },
  brand: {
    padding: '18px 20px 16px',
    display: 'flex', alignItems: 'center', gap: 10,
    borderBottom: '1px solid var(--line)',
  },
  logo: {
    width: 24, height: 24, borderRadius: 6,
    background: 'var(--ink)',
    color: 'var(--bg)',
    display: 'grid', placeItems: 'center',
    fontSize: 12, fontWeight: 700,
  },
  brandName: { fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em' },
  section: { padding: '14px 10px 6px' },
  nav: { padding: '4px 10px 14px', borderBottom: '1px solid var(--line)' },
  navItem: (active) => ({
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '7px 10px', borderRadius: 8, cursor: 'pointer',
    color: active ? 'var(--ink)' : 'var(--ink-2)',
    background: active ? 'var(--surface)' : 'transparent',
    boxShadow: active ? '0 0 0 1px var(--line), 0 1px 0 var(--line)' : 'none',
    fontSize: 13, fontWeight: active ? 500 : 400,
  }),
  sectionTitle: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 12px 8px',
    fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase',
    color: 'var(--ink-3)', fontWeight: 600,
  },
  sectionTitleRight: { color: 'var(--ink-4)', fontWeight: 500, letterSpacing: 0, textTransform: 'none', fontSize: 11 },
  cat: (active) => ({
    display: 'grid', gridTemplateColumns: '18px 1fr auto', alignItems: 'center', gap: 10,
    padding: '6px 12px', borderRadius: 8, cursor: 'pointer',
    color: active ? 'var(--ink)' : 'var(--ink-2)',
    background: active ? 'var(--surface)' : 'transparent',
    boxShadow: active ? 'inset 0 0 0 1px var(--line)' : 'none',
    fontSize: 13,
  }),
  catName: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  catAmt: { fontSize: 11, color: 'var(--ink-3)' },
  scroll: { overflowY: 'auto', flex: 1, paddingBottom: 12 },
  footer: {
    padding: '12px 14px',
    borderTop: '1px solid var(--line)',
    display: 'flex', alignItems: 'center', gap: 10,
  },
  avatar: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'linear-gradient(135deg, var(--accent) 0%, oklch(0.55 0.12 280) 100%)',
    color: 'white', display: 'grid', placeItems: 'center',
    fontSize: 11, fontWeight: 600,
  },
  addBtn: {
    display: 'flex', alignItems: 'center', gap: 8,
    margin: '4px 12px', padding: '6px 10px',
    border: '1px dashed var(--line)', borderRadius: 8,
    background: 'transparent', color: 'var(--ink-3)',
    fontSize: 12, width: 'calc(100% - 24px)',
  },
};

function Sidebar({ nav, setNav, month, account, currency, activeCat, setActiveCat, onCloseMobile }) {
  const monthData = DATA[month];
  const fmt = (n) => fmtMoney(toCcy(n, currency), currency, { decimals: 0 });

  const totalIncome = INCOME_CATS.reduce((a, c) => {
    const v = monthData.income[c.id];
    return a + (account === 'all' ? v.total : (v.by[account] || 0));
  }, 0);
  const totalExpense = EXPENSE_CATS.reduce((a, c) => {
    const v = monthData.expense[c.id];
    return a + (account === 'all' ? v.total : (v.by[account] || 0));
  }, 0);

  const navItems = [
    { id: 'dashboard', icon: 'dashboard', label: 'Dashboard' },
    { id: 'tx',        icon: 'list',      label: 'Transakcie' },
    { id: 'accounts',  icon: 'wallet',    label: 'Účty', badge: '3' },
    { id: 'budgets',   icon: 'target',    label: 'Rozpočty' },
    { id: 'reports',   icon: 'chart',     label: 'Reporty' },
  ];

  return (
    <aside style={sidebarStyles.root}>
      <div style={sidebarStyles.brand}>
        <div style={sidebarStyles.logo}>M</div>
        <div>
          <div style={sidebarStyles.brandName}>Moneyyy</div>
          <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>self-hosted · v0.4</div>
        </div>
      </div>

      <nav style={sidebarStyles.nav}>
        {navItems.map(it => (
          <div key={it.id} style={sidebarStyles.navItem(nav === it.id)} onClick={() => { setNav(it.id); onCloseMobile?.(); }}>
            <Icon name={it.icon} size={15} />
            <span style={{ flex: 1 }}>{it.label}</span>
            {it.badge && <span className="mono" style={{ fontSize: 10, color: 'var(--ink-3)' }}>{it.badge}</span>}
          </div>
        ))}
      </nav>

      <div style={sidebarStyles.scroll}>
        <div style={sidebarStyles.section}>
          <div style={sidebarStyles.sectionTitle}>
            <span>Príjmy</span>
            <span className="mono tnum" style={{ ...sidebarStyles.sectionTitleRight, color: 'var(--pos)' }}>{fmt(totalIncome)}</span>
          </div>
          {INCOME_CATS.map(c => {
            const v = monthData.income[c.id];
            const amt = account === 'all' ? v.total : (v.by[account] || 0);
            const active = activeCat === c.id;
            return (
              <div key={c.id} style={sidebarStyles.cat(active)} onClick={() => setActiveCat(active ? null : c.id)}>
                <Icon name={c.icon} size={14} style={{ color: 'var(--ink-3)' }} />
                <span style={sidebarStyles.catName}>{c.name}</span>
                <span className="mono tnum" style={sidebarStyles.catAmt}>{amt ? fmt(amt) : '—'}</span>
              </div>
            );
          })}
          <button style={sidebarStyles.addBtn}>
            <Icon name="plus" size={12} /> Pridať kategóriu
          </button>
        </div>

        <div style={sidebarStyles.section}>
          <div style={sidebarStyles.sectionTitle}>
            <span>Výdaje</span>
            <span className="mono tnum" style={{ ...sidebarStyles.sectionTitleRight, color: 'var(--neg)' }}>{fmt(totalExpense)}</span>
          </div>
          {EXPENSE_CATS.map(c => {
            const v = monthData.expense[c.id];
            const amt = account === 'all' ? v.total : (v.by[account] || 0);
            const active = activeCat === c.id;
            return (
              <div key={c.id} style={sidebarStyles.cat(active)} onClick={() => setActiveCat(active ? null : c.id)}>
                <Icon name={c.icon} size={14} style={{ color: 'var(--ink-3)' }} />
                <span style={sidebarStyles.catName}>{c.name}</span>
                <span className="mono tnum" style={sidebarStyles.catAmt}>{amt ? fmt(amt) : '—'}</span>
              </div>
            );
          })}
          <button style={sidebarStyles.addBtn}>
            <Icon name="plus" size={12} /> Pridať kategóriu
          </button>
        </div>
      </div>

      <div style={sidebarStyles.footer}>
        <div style={sidebarStyles.avatar}>PK</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500 }}>Peter K.</div>
          <div style={{ fontSize: 11, color: 'var(--ink-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>sync: pred 2 min</div>
        </div>
        <Icon name="settings" size={14} style={{ color: 'var(--ink-3)', cursor: 'pointer' }} />
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
