// Tiny sparkline + mini bar components

function Sparkline({ values = [], width = 56, height = 18, stroke, fill }) {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const pts = values.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * (height - 2) - 1;
    return [x, y];
  });
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const last = pts[pts.length - 1];
  return (
    <svg width={width} height={height} style={{ display: 'block' }} aria-hidden="true">
      <path d={d} fill="none" stroke={stroke || 'currentColor'} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="1.8" fill={stroke || 'currentColor'} />
    </svg>
  );
}

function MiniBars({ values = [], width = 56, height = 18, color }) {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const bw = (width - (values.length - 1) * 2) / values.length;
  return (
    <svg width={width} height={height} style={{ display: 'block' }} aria-hidden="true">
      {values.map((v, i) => {
        const h = Math.max(1, (v / max) * (height - 1));
        const x = i * (bw + 2);
        const y = height - h;
        return <rect key={i} x={x} y={y} width={bw} height={h} rx="0.5" fill={color || 'currentColor'} opacity={i === values.length - 1 ? 1 : 0.35} />;
      })}
    </svg>
  );
}

window.Sparkline = Sparkline;
window.MiniBars = MiniBars;
