import Plot from 'react-plotly.js';
import type { ScatterPoint } from '../../interproduct/types';
import { darkConfig, darkLayout } from '../../plotlyTheme';

interface Props {
  points: ScatterPoint[]; // {a: Leg 1 value, b: Leg 2 value}
  regressionAlpha: number | null;
  regressionBeta: number | null;
  rSquared: number | null;
  correlation: number | null;
  loading: boolean;
  emptyMessage?: string;
  height?: number;
  labelA?: string;
  labelB?: string;
}

// X = Leg 2, Y = Leg 1 (matches relationship_statistics' Y=Leg1/X=Leg2 OLS
// convention exactly, so the fitted line here is the same regression whose
// beta/R2/hedge-ratio are shown in the stats table). No existing analog in
// the codebase for a scatter+fit chart — new, but same Plot/darkLayout/
// darkConfig conventions as every other chart here.
export default function ScatterRegressionChart({
  points, regressionAlpha, regressionBeta, rSquared, correlation, loading,
  emptyMessage = 'No aligned observations yet', height = 320,
  labelA = 'Leg 1', labelB = 'Leg 2',
}: Props) {
  const xs = points.map((p) => p.b);
  const ys = points.map((p) => p.a);
  const hasFit = regressionAlpha != null && regressionBeta != null && xs.length > 0;

  let fitLine: { x: number[]; y: number[] } | null = null;
  if (hasFit) {
    const xMin = Math.min(...xs);
    const xMax = Math.max(...xs);
    fitLine = { x: [xMin, xMax], y: [regressionAlpha! + regressionBeta! * xMin, regressionAlpha! + regressionBeta! * xMax] };
  }

  const subtitle = hasFit
    ? `beta ${regressionBeta!.toFixed(3)} · R² ${rSquared != null ? rSquared.toFixed(3) : '—'} · corr ${correlation != null ? correlation.toFixed(3) : '—'}`
    : '';

  return (
    <div>
      {subtitle && <div style={{ color: '#666666', fontSize: '11px', marginBottom: '4px' }}>{subtitle}</div>}
      <Plot
        data={[
          {
            x: xs, y: ys, type: 'scatter', mode: 'markers', name: `${labelA} vs ${labelB}`,
            marker: { color: '#4aa8ff', size: 5, opacity: 0.65 },
            hovertemplate: `${labelB}: %{x:.4f}<br>${labelA}: %{y:.4f}<extra></extra>`,
          },
          ...(fitLine
            ? [{
                x: fitLine.x, y: fitLine.y, type: 'scatter' as const, mode: 'lines' as const, name: 'OLS fit',
                line: { color: '#ffaa00', width: 2 }, hoverinfo: 'skip' as const,
              }]
            : []),
        ]}
        layout={{
          ...darkLayout,
          height,
          showlegend: true,
          margin: { l: 54, r: 18, t: 12, b: 42 },
          yaxis: { ...darkLayout.yaxis, title: labelA },
          xaxis: { ...darkLayout.xaxis, title: labelB },
          annotations:
            points.length === 0 && !loading
              ? [{ text: emptyMessage, xref: 'paper', yref: 'paper', x: 0.5, y: 0.5, showarrow: false, font: { color: '#666666' } }]
              : [],
        }}
        config={darkConfig}
        style={{ width: '100%', height: `${height}px` }}
        useResizeHandler
      />
    </div>
  );
}
