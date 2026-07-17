export const darkLayout: any = {
  paper_bgcolor: '#0a0a0a',
  plot_bgcolor: '#0a0a0a',
  font: { family: 'JetBrains Mono, Consolas, monospace', color: '#e5e5e5', size: 11 },
  margin: { l: 50, r: 20, t: 30, b: 40 },
  xaxis: { gridcolor: '#262626', zerolinecolor: '#404040', linecolor: '#404040', tickcolor: '#404040' },
  yaxis: { gridcolor: '#262626', zerolinecolor: '#404040', linecolor: '#404040', tickcolor: '#404040' },
  legend: { bgcolor: 'rgba(0,0,0,0)', font: { color: '#e5e5e5' } },
  hoverlabel: { bgcolor: '#141414', bordercolor: '#404040', font: { color: '#e5e5e5' } },
};

export const darkConfig: any = {
  displayModeBar: false,
  responsive: true,
};

export const fmt = {
  px: (n: number | null | undefined, d = 4) =>
    n == null || !Number.isFinite(n) ? '—' : n.toFixed(d),
  z: (n: number | null | undefined) =>
    n == null || !Number.isFinite(n) ? '—' : (n >= 0 ? '+' : '') + n.toFixed(2),
  pct: (n: number | null | undefined) =>
    n == null || !Number.isFinite(n) ? '—' : Math.round(n).toString(),
  chg: (n: number | null | undefined, d = 4) =>
    n == null || !Number.isFinite(n) ? '—' : (n >= 0 ? '+' : '') + n.toFixed(d),
};
