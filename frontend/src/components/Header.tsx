import { useEffect, useState } from 'react';
import { useStore } from '../store';
import clsx from 'clsx';

export type ActiveView = 'sa3er3' | 'icurve';

interface Props {
  activeView: ActiveView;
  onChangeView: (view: ActiveView) => void;
}

function ViewTab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '3px 10px',
        fontSize: '10px',
        fontWeight: 'bold',
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        borderRadius: '3px',
        border: '1px solid #262626',
        backgroundColor: active ? '#262626' : 'transparent',
        color: active ? '#e5e5e5' : '#666666',
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

export default function Header({ activeView, onChangeView }: Props) {
  const connected = useStore((s) => s.connected);
  const streamStatus = useStore((s) => s.streamStatus);
  const analytics = useStore((s) => s.analytics);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#141414', borderBottom: '1px solid #262626', padding: '6px 12px', fontSize: '11px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ color: '#e5e5e5', fontWeight: 'bold', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          RV Terminal
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ViewTab label="I Curve Analytics" active={activeView === 'icurve'} onClick={() => onChangeView('icurve')} />
          <ViewTab label="SA3 / ER3" active={activeView === 'sa3er3'} onClick={() => onChangeView('sa3er3')} />
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <span style={{ color: '#666666' }}>
          analytics: <span style={{ color: '#e5e5e5' }}>{analytics?.compute_ms?.toFixed(1) ?? '—'}ms</span>
        </span>
        <span style={{ color: '#666666' }}>
          stream: <span style={{ color: '#e5e5e5' }}>{streamStatus}</span>
        </span>
        <span style={{ fontVariantNumeric: 'tabular-nums', color: '#e5e5e5' }}>{now.toISOString().replace('T', ' ').slice(0, 19)}Z</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: connected ? '#00ff88' : '#ff3355', boxShadow: connected ? '0 0 6px #00ff88' : 'none' }} />
          <span style={{ color: connected ? '#00ff88' : '#ff3355' }}>
            {connected ? 'LIVE' : 'DISCONNECTED'}
          </span>
        </span>
      </div>
    </header>
  );
}
