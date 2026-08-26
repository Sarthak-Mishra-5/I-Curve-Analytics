import { useStore } from '../store';
import Panel from './Panel';
import { fmt } from '../plotlyTheme';

// SR3, SO3, I, and SA3 all trade in 0.005 ticks on this platform (config.py TICK_SIZE).
const TICK_SIZE = 0.005;

const ROWS: { label: string; instrument: string }[] = [
  { label: 'SR3', instrument: 'SR3 Sep27' },
  { label: 'SO3', instrument: 'SO3 Sep27' },
  { label: 'I', instrument: 'I Sep27' },
  { label: 'SA3', instrument: 'SA3 Sep27' },
];

export default function DailyChangeTable() {
  const quotes = useStore((s) => s.quotes);

  return (
    <Panel title="Daily Change" subtitle="vs today's opening" scroll={false}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
        <thead>
          <tr style={{ color: '#666666' }}>
            <th style={{ textAlign: 'left', padding: '4px 8px' }}>Curve</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Opening</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Live</th>
            <th style={{ textAlign: 'right', padding: '4px 8px' }}>Change (ticks)</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ label, instrument }) => {
            const q = quotes[instrument];
            const open = q?.open ?? null;
            const live = q?.price ?? q?.mid ?? q?.last ?? null;
            const rawTicks = open != null && live != null ? (live - open) / TICK_SIZE : null;
            const ticks = rawTicks != null ? Math.round(rawTicks) : null;
            const color = ticks == null || ticks === 0 ? '#666666' : ticks > 0 ? '#4aa8ff' : '#ff3355';
            return (
              <tr key={instrument} style={{ borderTop: '1px solid #262626' }}>
                <td style={{ padding: '6px 8px', color: '#e5e5e5', fontWeight: 'bold' }}>{label}</td>
                <td style={{ padding: '6px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#e5e5e5' }}>
                  {fmt.px(open)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#e5e5e5' }}>
                  {fmt.px(live)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 'bold', color }}>
                  {ticks == null ? '—' : (ticks > 0 ? '+' : '') + ticks}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
