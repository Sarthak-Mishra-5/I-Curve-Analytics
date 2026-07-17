import Plot from 'react-plotly.js';
import type { StructurePriceHistoryPoint } from '../icurve/types';
import { darkConfig, darkLayout } from '../plotlyTheme';

interface Props {
  points: StructurePriceHistoryPoint[];
  loading: boolean;
  emptyMessage?: string;
  height?: number;
  labelA?: string;
  labelB?: string;
}

export default function StructurePriceHistoryChart({
  points,
  loading,
  emptyMessage = 'No price history yet',
  height = 260,
  labelA = 'Structure A',
  labelB = 'Structure B',
}: Props) {
  return (
    <Plot
      data={[
        {
          x: points.map((p) => p.date),
          y: points.map((p) => p.a),
          type: 'scatter',
          mode: 'lines',
          name: labelA,
          line: { color: '#4aa8ff', width: 2 },
          connectgaps: false,
          hovertemplate: `Date: %{x}<br>${labelA}: %{y:.4f}<extra></extra>`,
        },
        {
          x: points.map((p) => p.date),
          y: points.map((p) => p.b),
          type: 'scatter',
          mode: 'lines',
          name: labelB,
          line: { color: '#ff3355', width: 2 },
          connectgaps: false,
          hovertemplate: `Date: %{x}<br>${labelB}: %{y:.4f}<extra></extra>`,
        },
      ]}
      layout={{
        ...darkLayout,
        height,
        showlegend: true,
        margin: { l: 54, r: 18, t: 12, b: 42 },
        yaxis: {
          ...darkLayout.yaxis,
          title: 'Price',
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
