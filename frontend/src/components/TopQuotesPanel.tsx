import { useStore } from '../store';
import Panel from './Panel';
import { fmt } from '../plotlyTheme';
import clsx from 'clsx';

export default function TopQuotesPanel() {
  const quotes = useStore((s) => s.quotes);
  const contracts = useStore((s) => s.contracts);
  const order = [...contracts.SR3, ...contracts.SO3, ...contracts.I, ...contracts.SA3];

  return (
    <Panel title="Live Quotes" subtitle={`${order.length} contracts`} scroll={false}>
      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
        {order.map((name) => {
          const q = quotes[name];
          const chg = q?.net_change ?? null;
          const chgColor = chg == null ? '#666666'
            : chg > 0 ? '#00ff88'
            : chg < 0 ? '#ff3355' : '#666666';
          return (
            <div key={name}
              style={{ flexShrink: 0, width: '140px', backgroundColor: '#1a1a1a', border: '1px solid #262626', borderRadius: '4px', padding: '6px' }}>
              <div style={{ fontSize: '10px', color: '#666666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</div>
              <div style={{ fontSize: '16px', fontVariantNumeric: 'tabular-nums', color: '#e5e5e5', fontWeight: 'bold' }}>
                {fmt.px(q?.price ?? q?.mid ?? null)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontVariantNumeric: 'tabular-nums' }}>
                <span style={{ color: '#ff3355' }}>{fmt.px(q?.bid ?? null)}</span>
                <span style={{ color: '#00ff88' }}>{fmt.px(q?.ask ?? null)}</span>
              </div>
              <div style={{ fontSize: '10px', fontVariantNumeric: 'tabular-nums', color: chgColor }}>
                {fmt.chg(chg)} {q?.volume != null && (
                  <span style={{ color: '#666666', marginLeft: '4px' }}>v{Math.round(q.volume)}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
