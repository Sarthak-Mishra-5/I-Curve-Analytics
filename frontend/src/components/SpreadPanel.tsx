import { useStore } from '../store';
import Panel from './Panel';
import { fmt } from '../plotlyTheme';

function zColor(z: number) {
  const a = Math.abs(z);
  if (a >= 2) return '#ff3355';
  if (a >= 1) return '#ffaa00';
  return '#666666';
}

export default function SpreadPanel() {
  const spreads = useStore((s) => s.analytics?.spreads) ?? [];
  const sorted = [...spreads].sort((a, b) => Math.abs(b.zscore) - Math.abs(a.zscore)).slice(0, 30);

  return (
    <Panel title="Spreads" subtitle={`${spreads.length} pairs (top 30 by |z|)`}>
      <table style={{ width: '100%', fontSize: '11px', fontVariantNumeric: 'tabular-nums', borderCollapse: 'collapse' }}>
        <thead style={{ color: '#666666' }}>
          <tr style={{ borderBottom: '1px solid #262626' }}>
            <th style={{ textAlign: 'left', fontWeight: 'normal', padding: '4px' }}>Name</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Value</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Mean</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Std</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Z</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Pctile</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => (
            <tr key={s.name} style={{ borderBottom: '1px solid #262626' }}>
              <td style={{ padding: '4px', color: '#e5e5e5' }}>{s.name}</td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#e5e5e5' }}>{fmt.px(s.value)}</td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#666666' }}>{fmt.px(s.mean)}</td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#666666' }}>{fmt.px(s.std)}</td>
              <td style={{ padding: '4px', textAlign: 'right', fontWeight: 'bold', color: zColor(s.zscore) }}>{fmt.z(s.zscore)}</td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#666666' }}>{fmt.pct(s.percentile)}</td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr><td colSpan={6} style={{ color: '#666666', textAlign: 'center', padding: '16px' }}>awaiting data…</td></tr>
          )}
        </tbody>
      </table>
    </Panel>
  );
}
