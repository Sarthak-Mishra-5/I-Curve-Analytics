import Plot from 'react-plotly.js';
import { useStore } from '../store';
import Panel from './Panel';
import { darkConfig, darkLayout } from '../plotlyTheme';

interface Props {
  title: string;
  subtitle?: string;
  labels: string[]; // x-axis tick labels, in curve order
  instruments: string[]; // same length — instrument display names to read from live quotes
  color?: string;
}

// Term-structure snapshot chart, same shape as the existing SA3/ER3 CurvePanel:
// one line across the curve's contracts (x = tenor/structure, y = live price),
// redrawn on every tick via normal React re-render — cheap, since it's only
// as many points as there are contracts in the curve.
export default function CurveSnapshotChart({ title, subtitle, labels, instruments, color = '#00ff88' }: Props) {
  const quotes = useStore((s) => s.quotes);

  const y = instruments.map((name) => {
    const q = quotes[name];
    if (!q) return null;
    // Prefer volume-weighted average price over mid/last — falls back only
    // for instruments/moments where no trade (LastQty) has accumulated yet.
    return q.vwap ?? q.mid ?? q.price ?? q.last ?? null;
  });

  const data: any[] = [
    {
      x: labels,
      y,
      type: 'scatter',
      mode: 'lines+markers',
      name: title,
      line: { color, width: 2 },
      marker: { size: 6 },
      connectgaps: false,
      hovertemplate: '%{x}: %{y:.4f}<extra>' + title + '</extra>',
    },
  ];

  return (
    <Panel title={title} subtitle={subtitle} className="min-h-[300px]">
      <Plot
        data={data}
        layout={{ ...darkLayout, height: 320, showlegend: false }}
        config={darkConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </Panel>
  );
}
