import Plot from 'react-plotly.js';
import type { StructurePriceHistoryPoint } from '../icurve/types';
import { darkConfig, darkLayout } from '../plotlyTheme';

export type PriceDisplayMode = 'raw' | 'normalized' | 'zscore';

interface Props {
  points: StructurePriceHistoryPoint[];
  loading: boolean;
  emptyMessage?: string;
  height?: number;
  labelA?: string;
  labelB?: string;
  // 'raw' (default, unchanged behavior) plots levels as-is; 'normalized'
  // rebases each series to 100 at its first observation; 'zscore' plots
  // each series' own (value-mean)/std over the given points. Useful for
  // comparing relative movement of two series on very different scales
  // (e.g. legs from two different curves/currencies).
  mode?: PriceDisplayMode;
}

function transform(values: (number | null)[], mode: PriceDisplayMode): (number | null)[] {
  if (mode === 'raw') return values;
  const numeric = values.filter((v): v is number => v != null && Number.isFinite(v));
  if (numeric.length === 0) return values;
  if (mode === 'normalized') {
    const base = numeric[0];
    if (!base) return values;
    return values.map((v) => (v == null ? null : (v / base) * 100));
  }
  // zscore
  const mean = numeric.reduce((s, v) => s + v, 0) / numeric.length;
  const variance = numeric.reduce((s, v) => s + (v - mean) ** 2, 0) / numeric.length;
  const std = Math.sqrt(variance);
  if (std < 1e-12) return values.map((v) => (v == null ? null : 0));
  return values.map((v) => (v == null ? null : (v - mean) / std));
}

export default function StructurePriceHistoryChart({
  points,
  loading,
  emptyMessage = 'No price history yet',
  height = 260,
  labelA = 'Structure A',
  labelB = 'Structure B',
  mode = 'raw',
}: Props) {
  const yA = transform(points.map((p) => p.a), mode);
  const yB = transform(points.map((p) => p.b), mode);
  const yAxisTitle = mode === 'raw' ? 'Price' : mode === 'normalized' ? 'Indexed (100 = start)' : 'Z-Score';
  const valueFmt = mode === 'raw' ? '%{y:.4f}' : '%{y:.2f}';

  return (
    <Plot
      data={[
        {
          x: points.map((p) => p.date),
          y: yA,
          type: 'scatter',
          mode: 'lines',
          name: labelA,
          line: { color: '#4aa8ff', width: 2 },
          connectgaps: false,
          hovertemplate: `Date: %{x}<br>${labelA}: ${valueFmt}<extra></extra>`,
        },
        {
          x: points.map((p) => p.date),
          y: yB,
          type: 'scatter',
          mode: 'lines',
          name: labelB,
          line: { color: '#ff3355', width: 2 },
          connectgaps: false,
          hovertemplate: `Date: %{x}<br>${labelB}: ${valueFmt}<extra></extra>`,
        },
      ]}
      layout={{
        ...darkLayout,
        height,
        showlegend: true,
        margin: { l: 54, r: 18, t: 12, b: 42 },
        yaxis: {
          ...darkLayout.yaxis,
          title: yAxisTitle,
          zeroline: true,
        },
        xaxis: {
          ...darkLayout.xaxis,
          title: 'Date',
        },
        annotations:
          points.length === 0 && !loading
            ? [{
                text: emptyMessage,
                xref: 'paper',
                yref: 'paper',
                x: 0.5,
                y: 0.5,
                showarrow: false,
                font: { color: '#666666' },
              }]
            : [],
      }}
      config={darkConfig}
      style={{ width: '100%', height: `${height}px` }}
      useResizeHandler
    />
  );
}
