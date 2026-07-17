import Plot from 'react-plotly.js';
import type { CorrelationHistoryPoint } from '../icurve/types';
import { darkConfig, darkLayout } from '../plotlyTheme';

interface Props {
  points: CorrelationHistoryPoint[];
  loading: boolean;
  emptyMessage?: string;
  yMin?: number;
  yMax?: number;
  height?: number;
  lineColor?: string;
}

export default function CorrelationOverTimeChart({
  points,
  loading,
  emptyMessage = 'No cached points yet',
  yMin = -1,
  yMax = 1,
  height = 330,
  lineColor = '#ffaa00',
}: Props) {
  return (
    <Plot
      data={[
        {
          x: points.map((p) => p.date),
          y: points.map((p) => p.correlation),
          customdata: points.map((p) => [p.n]),
          type: 'scatter',
          mode: 'lines+markers',
          name: 'Correlation',
          line: { color: lineColor, width: 2 },
          marker: { size: 5 },
          connectgaps: false,
          hovertemplate: 'Date: %{x}<br>Correlation: %{y:.4f}<br>Obs: %{customdata[0]}<extra></extra>',
        },
      ]}
      layout={{
        ...darkLayout,
        height,
        showlegend: false,
        margin: { l: 54, r: 18, t: 12, b: 42 },
        yaxis: {
          ...darkLayout.yaxis,
          title: 'Correlation',
          range: [yMin, yMax],
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
