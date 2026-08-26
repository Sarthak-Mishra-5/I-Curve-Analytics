import { useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import type { CurveSpecDTO, ProductSummary } from '../../icurve/types';
import type { LegConfig, StructureKind } from '../../interproduct/types';
import WeightGrid from '../WeightGrid';

interface Props {
  leg: LegConfig;
  onChange: (leg: LegConfig) => void;
  products: ProductSummary[];
  curveSpec: CurveSpecDTO | null;
  accentColor: string;
  legLabel: string;
  disabled?: boolean;
}

const STRUCTURE_KINDS: { kind: StructureKind; label: string }[] = [
  { kind: 'outright', label: 'Outright' },
  { kind: '3ms', label: '3MS' },
  { kind: '6ms', label: '6MS' },
  { kind: '3mf', label: '3MF' },
];

function namesForKind(spec: CurveSpecDTO, kind: StructureKind): string[] {
  switch (kind) {
    case 'outright': return spec.outrights;
    case '3ms': return spec.three_month_spreads;
    case '6ms': return spec.six_month_spreads;
    case '3mf': return spec.flies_3m;
  }
}

// Front (lowest-index) non-zero leg's sign, for the "front contract positive
// -> LONG, negative -> SHORT" default hinted at in the spec. Only used to
// seed a sensible default for a freshly-entered custom formula — never
// overrides a side the user picked deliberately (see sideTouched ref below).
function frontLegSign(weights: Record<string, number>, outrights: string[]): 1 | -1 | null {
  for (const name of outrights) {
    const w = weights[name];
    if (w) return w > 0 ? 1 : -1;
  }
  return null;
}

const selectStyle: CSSProperties = {
  background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333',
  borderRadius: '4px', padding: '5px 8px', fontSize: '12px',
};

export default function LegBuilder({ leg, onChange, products, curveSpec, accentColor, legLabel, disabled }: Props) {
  // Tracks whether the user has explicitly chosen a side since the last time
  // this leg's weights went from empty to non-empty in custom mode — once
  // true, auto-derivation from the front leg's sign stops for this leg.
  const sideTouchedRef = useRef(false);

  useEffect(() => {
    sideTouchedRef.current = false;
  }, [leg.curveId, leg.mode]);

  function update(patch: Partial<LegConfig>) {
    onChange({ ...leg, ...patch });
  }

  function updateWeights(weights: Record<string, number>) {
    if (!sideTouchedRef.current) {
      const sign = frontLegSign(weights, curveSpec?.outrights ?? []);
      if (sign != null) {
        onChange({ ...leg, weights, side: sign > 0 ? 'LONG' : 'SHORT' });
        return;
      }
    }
    onChange({ ...leg, weights });
  }

  function setSide(side: LegConfig['side']) {
    sideTouchedRef.current = true;
    update({ side });
  }

  const names = curveSpec ? namesForKind(curveSpec, leg.structureKind) : [];

  return (
    <div style={{ border: `1px solid ${accentColor}55`, borderRadius: '6px', padding: '10px' }}>
      <div style={{ color: accentColor, fontSize: '11px', fontWeight: 'bold', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '8px' }}>
        {legLabel}
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666' }}>
          Product
          <select
            value={leg.curveId}
            disabled={disabled}
            onChange={(e) => update({ curveId: e.target.value, structureName: '', weights: {} })}
            style={selectStyle}
          >
            {products.map((p) => (
              <option key={p.curve_id} value={p.curve_id}>{p.label}</option>
            ))}
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666' }}>
          Side
          <div style={{ display: 'flex', gap: '4px' }}>
            {(['LONG', 'SHORT'] as const).map((side) => (
              <button
                key={side}
                disabled={disabled}
                onClick={() => setSide(side)}
                style={{
                  padding: '5px 10px', fontSize: '11px', fontWeight: 'bold', borderRadius: '4px',
                  border: `1px solid ${leg.side === side ? (side === 'LONG' ? '#00ff88' : '#ff3355') : '#333333'}`,
                  background: leg.side === side ? (side === 'LONG' ? '#00ff8822' : '#ff335522') : '#0a0a0a',
                  color: leg.side === side ? (side === 'LONG' ? '#00ff88' : '#ff3355') : '#666666',
                  cursor: disabled ? 'default' : 'pointer',
                }}
              >
                {side}
              </button>
            ))}
          </div>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666' }}>
          Lots
          <input
            type="number"
            step="any"
            value={leg.lots}
            disabled={disabled}
            onChange={(e) => update({ lots: parseFloat(e.target.value) || 0 })}
            style={{ ...selectStyle, width: '70px' }}
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666', flex: 1, minWidth: '120px' }}>
          Label (optional)
          <input
            value={leg.label}
            disabled={disabled}
            placeholder={leg.mode === 'predefined' ? (leg.structureName || 'auto') : `${leg.curveId} custom`}
            onChange={(e) => update({ label: e.target.value })}
            style={selectStyle}
          />
        </label>
      </div>

      <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
        {(['predefined', 'custom'] as const).map((mode) => (
          <button
            key={mode}
            disabled={disabled}
            onClick={() => update({ mode })}
            style={{
              padding: '4px 10px', fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.04em',
              borderRadius: '3px', border: '1px solid #333333',
              background: leg.mode === mode ? '#262626' : 'transparent',
              color: leg.mode === mode ? '#e5e5e5' : '#666666',
              cursor: disabled ? 'default' : 'pointer',
            }}
          >
            {mode === 'predefined' ? 'Predefined Structure' : 'Custom Formula'}
          </button>
        ))}
      </div>

      {!curveSpec && <div style={{ color: '#666666', fontSize: '11px' }}>loading curve config…</div>}

      {curveSpec && leg.mode === 'predefined' && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666' }}>
            Kind
            <select
              value={leg.structureKind}
              disabled={disabled}
              onChange={(e) => update({ structureKind: e.target.value as StructureKind, structureName: '' })}
              style={selectStyle}
            >
              {STRUCTURE_KINDS.map((k) => (
                <option key={k.kind} value={k.kind}>{k.label}</option>
              ))}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '10px', color: '#666666', flex: 1, minWidth: '160px' }}>
            Structure
            <select
              value={leg.structureName}
              disabled={disabled || names.length === 0}
              onChange={(e) => update({ structureName: e.target.value })}
              style={selectStyle}
            >
              <option value="">— select —</option>
              {names.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>
        </div>
      )}

      {curveSpec && leg.mode === 'custom' && (
        <WeightGrid
          curveId={leg.curveId}
          outrights={curveSpec.outrights}
          weights={leg.weights}
          onChange={updateWeights}
          disabled={disabled}
        />
      )}
    </div>
  );
}
