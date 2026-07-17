import Plot from 'react-plotly.js';
import { useStore } from '../store';
import Panel from './Panel';
import { darkConfig, darkLayout } from '../plotlyTheme';

export default function CorrelationPanel() {
  const corr = useStore((s) => s.analytics?.correlation);
  const rows = corr?.rows ?? [];
  const matrix = corr?.matrix ?? [];

  const data: any[] = [{
    type: 'heatmap',
    z: matrix,
    x: rows,
    y: rows,
    colorscale: 'RdBu',
    reversescale: true,
    zmid: 0,
    zmin: -1,
    zmax: 1,
    colorbar: { tickfont: { color: '#e5e5e5' }, thickness: 8 },
    hovertemplate: '%{y} / %{x}<br>ρ=%{z:.2f}<extra></extra>',
  }];

  return (
    <Panel title="Correlation" subtitle="returns, medium window" className="min-h-[300px]">
      <Plot
        data={data}
        layout={{
          ...darkLayout,
          height: 280,
          xaxis: { ...darkLayout.xaxis, tickangle: -45, tickfont: { size: 9 } },
          yaxis: { ...darkLayout.yaxis, automargin: true, tickfont: { size: 9 } },
        }}
        config={darkConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </Panel>
  );
}
