import type { ResolvedLegResponse } from '../../interproduct/types';

interface Props {
  legs: ResolvedLegResponse[];
}

function sideColor(side: string): string {
  return side === 'LONG' ? '#00ff88' : '#ff3355';
}

export default function LegFormulaDisplay({ legs }: Props) {
  if (legs.length < 2) return null;
  const [a, b] = legs;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {legs.map((leg) => (
        <div key={`${leg.curve_id}:${leg.label}`} style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ color: sideColor(leg.side), fontWeight: 'bold', fontSize: '12px', letterSpacing: '0.04em' }}>
            {leg.side}
          </span>
          <span style={{ color: '#e5e5e5', fontSize: '13px', fontWeight: 'bold' }}>
            {leg.lots}x {leg.label}
          </span>
          <span style={{ color: '#666666', fontSize: '11px' }}>
            {leg.curve_id}: {leg.formula}
          </span>
        </div>
      ))}
      <div style={{ marginTop: '2px', paddingTop: '8px', borderTop: '1px solid #262626', color: '#e5e5e5', fontSize: '12px' }}>
        <span style={{ color: '#666666' }}>Combined: </span>
        <span style={{ color: sideColor(a.side), fontWeight: 'bold' }}>{a.side} {a.lots}x {a.label}</span>
        <span style={{ color: '#444444' }}> / </span>
        <span style={{ color: sideColor(b.side), fontWeight: 'bold' }}>{b.side} {b.lots}x {b.label}</span>
      </div>
    </div>
  );
}
