import { useStore } from '../store';
import Panel from './Panel';

const sevColor: Record<string, { bg: string; text: string; border: string }> = {
  info: { bg: 'rgba(74, 168, 255, 0.1)', text: '#4aa8ff', border: 'rgba(74, 168, 255, 0.4)' },
  warn: { bg: 'rgba(255, 170, 0, 0.1)', text: '#ffaa00', border: 'rgba(255, 170, 0, 0.4)' },
  critical: { bg: 'rgba(255, 51, 85, 0.1)', text: '#ff3355', border: 'rgba(255, 51, 85, 0.4)' },
};

export default function AlertsPanel() {
  const alerts = useStore((s) => s.alerts);

  return (
    <Panel title="Alerts" subtitle={`${alerts.length} recent`}>
      {alerts.length === 0 ? (
        <div style={{ color: '#666666', textAlign: 'center', padding: '16px' }}>no alerts</div>
      ) : (
        <div>
          {alerts.map((a) => {
            const color = sevColor[a.severity] ?? sevColor.info;
            return (
              <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid rgba(38, 38, 38, 0.5)' }}>
                <span style={{ color: '#666666', fontVariantNumeric: 'tabular-nums', width: '80px', flexShrink: 0 }}>
                  {a.ts.slice(11, 19)}
                </span>
                <span style={{ display: 'inline-block', padding: '2px 8px', border: `1px solid ${color.border}`, borderRadius: '4px', fontSize: '9px', textTransform: 'uppercase', fontWeight: 'bold', width: '64px', textAlign: 'center', backgroundColor: color.bg, color: color.text }}>
                  {a.severity}
                </span>
                <span style={{ color: '#666666', width: '80px', flexShrink: 0, textTransform: 'uppercase', fontSize: '10px' }}>{a.category}</span>
                <span style={{ color: '#e5e5e5', flex: 1 }}>{a.message}</span>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
