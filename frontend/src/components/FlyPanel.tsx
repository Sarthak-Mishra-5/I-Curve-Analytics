import Plot from 'react-plotly.js';
import { useStore } from '../store';
import Panel from './Panel';
import { darkConfig, darkLayout } from '../plotlyTheme';

export default function FlyPanel() {
  const flies = useStore((s) => s.analytics?.flies) ?? [];
  const top = [...flies].sort((a, b) => Math.abs(b.zscore) - Math.abs(a.zscore)).slice(0, 12);

  const data: any[] = [{
    type: 'bar',
    x: top.map((f) => f.zscore),
    y: top.map((f) => f.name),
    orientation: 'h',
    marker: {
      color: top.map((f) => f.zscore >= 0 ? '#00ff88' : '#ff3355'),
    },
    hovertemplate: '%{y}<br>z=%{x:.2f}<extra></extra>',
  }];

  return (
    <Panel title="Butterflies" subtitle={`${flies.length} flies (top 12 |z|)`} className="min-h-[300px]">
      <Plot
        data={data}
        layout={{
          ...darkLayout,
          height: 280,
          xaxis: { ...darkLayout.xaxis, title: { text: 'z-score', font: { color: '#888' } }, zeroline: true },
          yaxis: { ...darkLayout.yaxis, automargin: true, tickfont: { size: 10 } },
          showlegend: false,
        }}
        config={darkConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </Panel>
  );
}
