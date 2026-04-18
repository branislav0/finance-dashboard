// Minimal, geometric line icons — 1.5px stroke, currentColor.
// Intentionally abstract & simple (no emoji, no complex SVG drawing).

const ICONS = {
  briefcase: (
    <g>
      <rect x="3" y="7" width="18" height="12" rx="1.5" />
      <path d="M8 7V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" />
      <path d="M3 12h18" />
    </g>
  ),
  sparkle: (
    <g>
      <path d="M12 4v6M12 14v6M4 12h6M14 12h6" />
    </g>
  ),
  heart: (
    <path d="M12 19s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 9c0 5.5-7 10-7 10z" />
  ),
  dot: (
    <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" />
  ),
  home: (
    <g>
      <path d="M4 11l8-6 8 6" />
      <path d="M6 10v9h12v-9" />
    </g>
  ),
  fuel: (
    <g>
      <rect x="5" y="4" width="9" height="16" rx="1" />
      <path d="M14 10h2a2 2 0 0 1 2 2v4a1 1 0 0 0 2 0V8l-2-2" />
      <path d="M5 12h9" />
    </g>
  ),
  cart: (
    <g>
      <path d="M3 4h2l2 12h12" />
      <path d="M7 8h14l-2 7H7" />
      <circle cx="9" cy="19" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="17" cy="19" r="1.2" fill="currentColor" stroke="none" />
    </g>
  ),
  shirt: (
    <path d="M7 5l-4 3 2 3 2-1v10h10V10l2 1 2-3-4-3-3 2a2 2 0 0 1-4 0l-3-2z" />
  ),
  flame: (
    <path d="M12 3s4 4 4 8a4 4 0 0 1-8 0c0-2 1-3 1-5 2 0 3 2 3 2s0-3 0-5z" />
  ),
  fork: (
    <g>
      <path d="M7 3v7a2 2 0 0 0 4 0V3" />
      <path d="M9 10v11" />
      <path d="M16 3c-1.5 0-3 1.5-3 4v4h3v10" />
    </g>
  ),
  repeat: (
    <g>
      <path d="M4 11V9a3 3 0 0 1 3-3h10l-2-2m2 2-2 2" />
      <path d="M20 13v2a3 3 0 0 1-3 3H7l2 2m-2-2 2-2" />
    </g>
  ),
  tram: (
    <g>
      <rect x="5" y="5" width="14" height="12" rx="2" />
      <path d="M9 5V3h6v2" />
      <path d="M5 11h14" />
      <path d="M8 20l2-3M16 20l-2-3" />
      <circle cx="9" cy="14.5" r="0.8" fill="currentColor" stroke="none" />
      <circle cx="15" cy="14.5" r="0.8" fill="currentColor" stroke="none" />
    </g>
  ),
  bolt: (
    <path d="M13 3L5 14h6l-1 7 8-11h-6l1-7z" />
  ),
  gift: (
    <g>
      <rect x="3" y="8" width="18" height="4" />
      <rect x="4" y="12" width="16" height="9" />
      <path d="M12 8v13" />
      <path d="M12 8s-1.5-5-4.5-5a2.5 2.5 0 0 0 0 5H12z" />
      <path d="M12 8s1.5-5 4.5-5a2.5 2.5 0 0 1 0 5H12z" />
    </g>
  ),
  joystick: (
    <g>
      <rect x="3" y="9" width="18" height="9" rx="4" />
      <path d="M8 13h3M9.5 11.5v3" />
      <circle cx="16" cy="13" r="1" fill="currentColor" stroke="none" />
    </g>
  ),
  pulse: (
    <path d="M3 12h4l2-5 3 10 2-5h7" />
  ),
  drop: (
    <path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" />
  ),
  banknote: (
    <g>
      <rect x="3" y="7" width="18" height="10" rx="1" />
      <circle cx="12" cy="12" r="2" />
      <circle cx="6" cy="12" r="0.6" fill="currentColor" stroke="none" />
      <circle cx="18" cy="12" r="0.6" fill="currentColor" stroke="none" />
    </g>
  ),
  trend: (
    <g>
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </g>
  ),
  coin: (
    <g>
      <circle cx="12" cy="12" r="8" />
      <path d="M9.5 10.5c0-1 1-1.5 2.5-1.5s2.5 .5 2.5 1.5S13.5 12 12 12s-2.5 .5-2.5 1.5S10.5 15 12 15s2.5-.5 2.5-1.5" />
      <path d="M12 8v8" />
    </g>
  ),
  // UI chrome
  search: (
    <g>
      <circle cx="11" cy="11" r="6" />
      <path d="m20 20-4-4" />
    </g>
  ),
  plus: <g><path d="M12 5v14M5 12h14" /></g>,
  chevDown: <path d="m6 9 6 6 6-6" />,
  chevRight: <path d="m9 6 6 6-6 6" />,
  menu: <g><path d="M4 7h16M4 12h16M4 17h16"/></g>,
  arrowDown: <path d="M12 5v14m-5-5 5 5 5-5" />,
  arrowUp: <path d="M12 19V5m-5 5 5-5 5 5" />,
  arrowRight: <path d="M5 12h14m-5-5 5 5-5 5" />,
  bell: <g><path d="M6 16V11a6 6 0 0 1 12 0v5l1 2H5l1-2z"/><path d="M10 20a2 2 0 0 0 4 0"/></g>,
  settings: <g><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></g>,
  filter: <g><path d="M4 5h16l-6 8v5l-4-2v-3L4 5z"/></g>,
  download: <g><path d="M12 4v12m-5-5 5 5 5-5"/><path d="M4 20h16"/></g>,
  dashboard: <g><rect x="4" y="4" width="7" height="9"/><rect x="13" y="4" width="7" height="5"/><rect x="13" y="11" width="7" height="9"/><rect x="4" y="15" width="7" height="5"/></g>,
  list: <g><path d="M8 6h13M8 12h13M8 18h13M4 6h.01M4 12h.01M4 18h.01"/></g>,
  folder: <g><path d="M3 6a1 1 0 0 1 1-1h5l2 2h8a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z"/></g>,
  wallet: <g><rect x="3" y="6" width="18" height="13" rx="2"/><path d="M17 13h2"/><path d="M3 9h15a3 3 0 0 1 0 6H3"/></g>,
  target: <g><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/></g>,
  chart: <g><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></g>,
  check: <path d="m5 12 5 5 9-11" />,
};

function Icon({ name, size = 16, strokeWidth = 1.5, className = '', style }) {
  const body = ICONS[name] || ICONS.dot;
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round"
      className={className} style={style} aria-hidden="true"
    >
      {body}
    </svg>
  );
}

window.Icon = Icon;
window.ICONS = ICONS;
