import Plot from 'react-plotly.js';
import type { RVBandPoint } from '../../interproduct/types';
import { darkConfig, darkLayout } from '../../plotlyTheme';

interface Props {
  points: RVBandPoint[];
  loading: boolean;
  emptyMessage?: string;
  height?: number;
}

// RV level + rolling mean + +-1sd/+-2sd bands, in the same Plot/darkLayout/
// darkConfig/empty-state-annotation shape as StructurePriceHistoryChart and
// CorrelationOverTimeChart — no existing band chart to reuse, so this is new,
// but built to read as part of the same chart family.
export default function RVChart({ points, loading, emptyMessage = 'No RV history yet', height = 300 }: Props) {
  const x = points.map((p) => p.date);
  return (
    <Plot
      data={[
        {
          x, y: points.map((p) => p.upper_2sd), type: 'scatter', mode: 'lines', name: '+2sd',
          line: { color: '#444444', width: 1, dash: 'dot' }, hoverinfo: 'skip',
        },
        {
          x, y: points.map((p) => p.upper_1sd), type: 'scatter', mode: 'lines', name: '+1sd',
          line: { color: '#666666', width: 1, dash: 'dash' }, hoverinfo: 'skip',
        },
        {
          x, y: points.map((p) => p.rolling_mean), type: 'scatter', mode: 'lines', name: 'Rolling Mean',
          line: { color: '#ffaa00', width: 1.5 }, hovertemplate: 'Date: %{x}<br>Rolling Mean: %{y:.4f}<extra></extra>',
        },
        {
          x, y: points.map((p) => p.lower_1sd), type: 'scatter', mode: 'lines', name: '-1sd',
          line: { color: '#666666', width: 1, dash: 'dash' }, hoverinfo: 'skip',
        },
        {
          x, y: points.map((p) => p.lower_2sd), type: 'scatter', mode: 'lines', name: '-2sd',
          line: { color: '#444444', width: 1, dash: 'dot' }, hoverinfo: 'skip',
        },
        {
          x, y: points.map((p) => p.rv), type: 'scatter', mode: 'lines', name: 'RV',
          line: { color: '#4aa8ff', width: 2 }, hovertemplate: 'Date: %{x}<br>RV: %{y:.4f}<extra></extra>',
        },
      ]}
      layout={{
        ...darkLayout,
        height,
        showlegend: true,
        margin: { l: 54, r: 18, t: 12, b: 42 },
        yaxis: { ...darkLayout.yaxis, title: 'RV', zeroline: true },
        xaxis: { ...darkLayout.xaxis, title: 'Date' },
        annotations:
          points.length === 0 && !loading
            ? [{ text: emptyMessage, xref: 'paper', yref: 'paper', x: 0.5, y: 0.5, showarrow: false, font: { color: '#666666' } }]
            : [],
      }}
      config={darkConfig}
      style={{ width: '100%', height: `${height}px` }}
      useResizeHandler
    />
  );
}
