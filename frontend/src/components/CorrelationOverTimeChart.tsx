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
  // Shown over the chart while `loading`, so the previous series doesn't
  // read as the newly selected one during a slow fetch.
  loadingMessage?: string;
}

export default function CorrelationOverTimeChart({
  points,
  loading,
  emptyMessage = 'No cached points yet',
  yMin = -1,
  yMax = 1,
  height = 330,
  lineColor = '#ffaa00',
  loadingMessage = 'Loading chart...',
}: Props) {
  return (
    <div style={{ position: 'relative' }}>
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
      {loading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            background: 'rgba(10, 10, 10, 0.72)',
            color: '#bbbbbb',
            fontSize: '12px',
            zIndex: 1,
          }}
        >
          <style>{'@keyframes corr-chart-spin { to { transform: rotate(360deg); } }'}</style>
          <div
            style={{
              width: '26px',
              height: '26px',
              border: '3px solid #333333',
              borderTopColor: lineColor,
              borderRadius: '50%',
              animation: 'corr-chart-spin 0.8s linear infinite',
            }}
          />
          {loadingMessage}
        </div>
      )}
    </div>
  );
}
