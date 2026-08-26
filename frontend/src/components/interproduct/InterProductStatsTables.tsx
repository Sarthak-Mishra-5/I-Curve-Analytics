import { corrColor } from '../../icurve/format';
import type { InterProductAnalyzeResponse, LegStatistics, RVStatistics } from '../../interproduct/types';
import { fmt } from '../../plotlyTheme';
import Panel from '../Panel';

type Row = { label: string; render: () => string; color?: string };

function tileGrid(rows: Row[]) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '8px' }}>
      {rows.map((r) => (
        <div key={r.label} style={{ background: '#1a1a1a', border: '1px solid #262626', borderRadius: '4px', padding: '6px 8px' }}>
          <div style={{ color: '#666666', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{r.label}</div>
          <div style={{ color: r.color ?? '#e5e5e5', fontSize: '13px', fontWeight: 'bold', fontVariantNumeric: 'tabular-nums' }}>{r.render()}</div>
        </div>
      ))}
    </div>
  );
}

function legRows(s: LegStatistics): Row[] {
  return [
    { label: 'Current', render: () => fmt.px(s.current, 4) },
    { label: 'Mean', render: () => fmt.px(s.mean, 4) },
    { label: 'Std Dev', render: () => fmt.px(s.std, 4) },
    { label: 'Volatility', render: () => fmt.px(s.volatility, 4) },
    { label: 'Rolling Vol', render: () => fmt.px(s.rolling_volatility, 4) },
    { label: 'Min', render: () => fmt.px(s.min, 4) },
    { label: 'Max', render: () => fmt.px(s.max, 4) },
    { label: 'Percentile', render: () => (s.percentile == null ? '—' : `${fmt.pct(s.percentile)}%`) },
    { label: 'Z-Score', render: () => fmt.z(s.z_score) },
    { label: 'Observations', render: () => String(s.n) },
  ];
}

function rvRows(s: RVStatistics): Row[] {
  return [
    ...legRows(s),
    { label: 'Median', render: () => fmt.px(s.median, 4) },
    { label: 'Rolling Mean', render: () => fmt.px(s.rolling_mean, 4) },
    { label: 'Rolling Std Dev', render: () => fmt.px(s.rolling_std, 4) },
    { label: 'Rolling Z-Score', render: () => fmt.z(s.rolling_z_score) },
    { label: 'Range', render: () => fmt.px(s.range, 4) },
    { label: 'Max Drawdown', render: () => fmt.px(s.max_drawdown, 4) },
    { label: 'Sharpe-Like', render: () => fmt.px(s.sharpe_like, 3) },
    { label: 'Win Rate', render: () => (s.win_rate == null ? '—' : `${(s.win_rate * 100).toFixed(0)}%`) },
    { label: 'Avg Positive Move', render: () => fmt.chg(s.avg_positive_move, 4) },
    { label: 'Avg Negative Move', render: () => fmt.chg(s.avg_negative_move, 4) },
  ];
}

interface Props {
  result: InterProductAnalyzeResponse;
  showHedgeAdjusted: boolean;
}

export default function InterProductStatsTables({ result, showHedgeAdjusted }: Props) {
  const [legA, legB] = result.legs;
  const rel = result.relationship;
  const rv = showHedgeAdjusted ? result.rv.hedge_adjusted : result.rv.raw;

  const relationshipRows: Row[] = [
    { label: 'Correlation (Levels)', render: () => fmt.px(rel.correlation, 3), color: corrColor(rel.correlation) },
    { label: 'Correlation (Returns)', render: () => fmt.px(rel.correlation_returns, 3), color: corrColor(rel.correlation_returns) },
    { label: `Rolling Corr (${result.window})`, render: () => fmt.px(rel.rolling_correlation, 3), color: corrColor(rel.rolling_correlation) },
    { label: 'Regression Beta', render: () => fmt.px(rel.regression_beta, 3) },
    { label: 'R²', render: () => fmt.px(rel.r_squared, 3) },
    { label: 'LOWESS Beta', render: () => fmt.px(rel.lowess_beta, 3) },
    { label: 'Hedge Ratio', render: () => fmt.px(rel.hedge_ratio, 3) },
    { label: 'Residual Std Dev', render: () => fmt.px(rel.residual_std, 4) },
    { label: 'Residual Z-Score', render: () => fmt.z(rel.residual_z_score) },
    { label: 'Cointegrated', render: () => (rel.cointegrated == null ? '—' : rel.cointegrated ? 'Yes' : 'No') },
    { label: 'ADF p-value', render: () => fmt.px(rel.adf_pvalue, 3) },
    { label: 'Observations', render: () => String(rel.n) },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
        <Panel title={`Leg 1 — ${legA.label}`} subtitle={legA.curve_id}>
          {tileGrid(legRows(legA.statistics))}
        </Panel>
        <Panel title={`Leg 2 — ${legB.label}`} subtitle={legB.curve_id}>
          {tileGrid(legRows(legB.statistics))}
        </Panel>
      </div>

      <Panel title="Inter-Product Relationship" subtitle={rel.n > 0 ? undefined : 'insufficient overlapping history'}>
        {tileGrid(relationshipRows)}
        <div style={{ color: '#666666', fontSize: '10px', marginTop: '8px', lineHeight: 1.4 }}>{rel.regression_definition}</div>
      </Panel>

      <Panel
        title={showHedgeAdjusted ? 'Relative Value — Hedge-Ratio Adjusted' : 'Relative Value — Raw Trade'}
        subtitle={rv.side_summary || undefined}
      >
        {tileGrid(rvRows(rv.statistics))}
      </Panel>
    </div>
  );
}
