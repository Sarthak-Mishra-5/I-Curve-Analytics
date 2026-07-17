import Panel from './Panel';
import { fmt } from '../plotlyTheme';
import type { CurvePairStatRow } from '../icurve/types';

interface Props {
  title: string;
  subtitle?: string;
  rows: CurvePairStatRow[];
  onRowClick?: (row: CurvePairStatRow) => void;
  selectedCurrent?: string | null;
}

function corrColor(c: number | null) {
  if (c == null) return '#666666';
  const a = Math.abs(c);
  if (a >= 0.7) return '#00ff88';
  if (a >= 0.4) return '#ffaa00';
  return '#e5e5e5';
}

export default function CurveStatsTable({ title, subtitle, rows, onRowClick, selectedCurrent }: Props) {
  return (
    <Panel title={title} subtitle={subtitle}>
      {rows.length === 0 ? (
        <div style={{ color: '#666666', textAlign: 'center', padding: '16px' }}>awaiting data…</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: '14px', fontVariantNumeric: 'tabular-nums', borderCollapse: 'collapse' }}>
            <thead style={{ color: '#666666' }}>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                <th style={{ textAlign: 'left', fontWeight: 'normal', padding: '4px' }}>Current Contract</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Correlation</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Regression β</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Previous Max</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Current @ Previous Max</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Previous Min</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Current @ Previous Min</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.current}
                  onClick={onRowClick ? () => onRowClick(r) : undefined}
                  style={{
                    borderBottom: '1px solid #262626',
                    cursor: onRowClick ? 'pointer' : undefined,
                    backgroundColor: selectedCurrent === r.current ? '#1f1f1f' : undefined,
                  }}
                >
                  <td style={{ padding: '4px', color: '#e5e5e5' }}>{r.current}</td>
                  <td style={{ padding: '4px', textAlign: 'right', fontWeight: 'bold', color: corrColor(r.correlation) }}>
                    {r.correlation == null ? '—' : r.correlation.toFixed(2)}
                  </td>
                  <td style={{ padding: '4px', textAlign: 'right', color: '#4aa8ff' }}>{fmt.px(r.beta, 2)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', color: '#e5e5e5' }}>{fmt.px(r.prev_max, 2)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', color: '#d1a6a6' }}>{fmt.px(r.curr_at_prev_max, 2)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', color: '#e5e5e5' }}>{fmt.px(r.prev_min, 2)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', color: '#98ac64' }}>{fmt.px(r.curr_at_prev_min, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
