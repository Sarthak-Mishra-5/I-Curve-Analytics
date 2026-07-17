import { useStore } from '../store';
import Panel from './Panel';
import { fmt } from '../plotlyTheme';
import clsx from 'clsx';

function zColor(z: number) {
  const a = Math.abs(z);
  if (a >= 2) return '#ff3355';
  if (a >= 1) return '#ffaa00';
  return '#e5e5e5';
}

export default function RegressionPanel() {
  const regs = useStore((s) => s.analytics?.regressions) ?? [];

  return (
    <Panel title="Regressions" subtitle="SA3 ~ α + β·ER3 per tenor">
      {regs.length === 0 ? (
        <div style={{ color: '#666666', textAlign: 'center', padding: '16px' }}>awaiting data…</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: '10px', fontVariantNumeric: 'tabular-nums', borderCollapse: 'collapse' }}>
            <thead style={{ color: '#666666' }}>
              <tr style={{ borderBottom: '1px solid #262626' }}>
                <th style={{ textAlign: 'left', fontWeight: 'normal', padding: '4px' }}>Tenor</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>α</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>β</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>R²</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>resid z</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>roll β</th>
              </tr>
            </thead>
            <tbody>
              {regs.map((r) => {
                const tenor = r.y.split(' ')[1];
                return (
                  <tr key={`${r.y}/${r.x}`} style={{ borderBottom: '1px solid #262626' }}>
                    <td style={{ padding: '4px', color: '#e5e5e5' }}>{tenor}</td>
                    <td style={{ padding: '4px', textAlign: 'right', color: '#e5e5e5' }}>{fmt.px(r.alpha, 4)}</td>
                    <td style={{ padding: '4px', textAlign: 'right', fontWeight: 'bold', color: '#00ff88' }}>{fmt.px(r.beta, 4)}</td>
                    <td style={{ padding: '4px', textAlign: 'right', color: '#666666' }}>{(r.r2 * 100).toFixed(1)}%</td>
                    <td style={{ padding: '4px', textAlign: 'right', fontWeight: 'bold', color: zColor(r.residual_z) }}>{fmt.z(r.residual_z)}</td>
                    <td style={{ padding: '4px', textAlign: 'right', color: '#666666' }}>{Number.isFinite(r.rolling_beta) ? fmt.px(r.rolling_beta, 4) : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-terminal-panel2 border border-terminal-border p-1.5 rounded-sm">
      <div className="text-[9px] text-terminal-muted uppercase">{label}</div>
      <div className={clsx('text-sm tabular-nums font-semibold', color ?? 'text-terminal-text')}>{value}</div>
    </div>
  );
}
