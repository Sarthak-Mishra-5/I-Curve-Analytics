import Plot from 'react-plotly.js';
import type { ZScorePoint } from '../../interproduct/types';
import { darkConfig, darkLayout } from '../../plotlyTheme';

interface Props {
  points: ZScorePoint[];
  loading: boolean;
  emptyMessage?: string;
  height?: number;
}

const REFERENCE_LEVELS = [2, 1, 0, -1, -2];

// RV z-score with +-2/+-1/0 reference lines, so extreme RV levels are
// visually obvious. Shares the exact chart-building conventions of
// CorrelationOverTimeChart/StructurePriceHistoryChart (Plot/darkLayout/
// darkConfig/empty-state annotation) but adds Plotly `shapes` for the
// reference lines rather than overloading CorrelationOverTimeChart (which
// has no shapes support and is used elsewhere for plain bounded correlation).
export default function ZScoreChart({ points, loading, emptyMessage = 'No z-score history yet', height = 260 }: Props) {
  const x = points.map((p) => p.date);
  const y = points.map((p) => p.z_score);

  return (
    <Plot
      data={[
        {
          x, y, type: 'scatter', mode: 'lines', name: 'RV Z-Score',
          line: { color: '#4aa8ff', width: 2 },
          connectgaps: false,
          hovertemplate: 'Date: %{x}<br>Z-Score: %{y:.2f}<extra></extra>',
        },
      ]}
      layout={{
        ...darkLayout,
        height,
        showlegend: false,
        margin: { l: 54, r: 18, t: 12, b: 42 },
        yaxis: { ...darkLayout.yaxis, title: 'Z-Score', range: [-3.2, 3.2], zeroline: false },
        xaxis: { ...darkLayout.xaxis, title: 'Date' },
        shapes: REFERENCE_LEVELS.map((level) => ({
          type: 'line', xref: 'paper', x0: 0, x1: 1, yref: 'y', y0: level, y1: level,
          line: { color: level === 0 ? '#666666' : Math.abs(level) === 2 ? '#ff3355' : '#ffaa00', width: 1, dash: level === 0 ? 'solid' : 'dot' },
        })),
        annotations:
          points.length === 0 && !loading
            ? [{ text: emptyMessage, xref: 'paper', yref: 'paper', x: 0.5, y: 0.5, showarrow: false, font: { color: '#666666' } }]
            : REFERENCE_LEVELS.map((level) => ({
                text: level > 0 ? `+${level}` : `${level}`, xref: 'paper', x: 1.0, xanchor: 'left',
                yref: 'y', y: level, showarrow: false, font: { color: '#666666', size: 9 },
              })),
      }}
      config={darkConfig}
      style={{ width: '100%', height: `${height}px` }}
      useResizeHandler
    />
  );
}
