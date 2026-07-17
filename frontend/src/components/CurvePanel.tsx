import Plot from 'react-plotly.js';
import { useStore } from '../store';
import Panel from './Panel';
import { darkConfig, darkLayout } from '../plotlyTheme';

export default function CurvePanel() {
  const curve = useStore((s) => s.analytics?.curve);

  const sa = curve?.SA3 ?? [];
  const er = curve?.ER3 ?? [];

  const data: any[] = [
    {
      x: sa.map((p) => p.tenor),
      y: sa.map((p) => p.mid ?? p.price),
      type: 'scatter',
      mode: 'lines+markers',
      name: 'SA3 (SARON)',
      line: { color: '#00ff88', width: 2 },
      marker: { size: 6 },
    },
    {
      x: er.map((p) => p.tenor),
      y: er.map((p) => p.mid ?? p.price),
      type: 'scatter',
      mode: 'lines+markers',
      name: 'ER3 (€STR)',
      line: { color: '#4aa8ff', width: 2 },
      marker: { size: 6 },
    },
  ];

  const pcaSa = curve?.pca?.SA3;
  const pcaEr = curve?.pca?.ER3;
  const sub = pcaSa && pcaSa.level_var_pct != null
    ? `PCA SA3 L/S/C: ${pcaSa.level_var_pct?.toFixed(0)}/${pcaSa.slope_var_pct?.toFixed(0)}/${pcaSa.curvature_var_pct?.toFixed(0)}%  •  ER3: ${pcaEr?.level_var_pct?.toFixed(0)}/${pcaEr?.slope_var_pct?.toFixed(0)}/${pcaEr?.curvature_var_pct?.toFixed(0)}%`
    : 'awaiting PCA…';

  return (
    <Panel title="Curve" subtitle={sub} className="min-h-[300px]">
      <Plot
        data={data}
        layout={{ ...darkLayout, height: 280, showlegend: true, legend: { ...darkLayout.legend, orientation: 'h', y: 1.1 } }}
        config={darkConfig}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    </Panel>
  );
}
