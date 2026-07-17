import { useState } from 'react';
import { erLabel } from '../icurve/format';

export const MAX_LEGS = 8;

interface Props {
  outrights: string[];
  weights: Record<string, number>;
  onChange: (weights: Record<string, number>) => void;
  disabled?: boolean;
  labelForName?: (name: string, outrights: string[]) => string;
}

export function nonZeroLegCount(weights: Record<string, number>): number {
  return Object.values(weights).filter((w) => w !== 0).length;
}

// Integers only (optionally signed), or empty while the user is mid-edit.
const INT_PATTERN = /^-?\d*$/;

export default function WeightGrid({ outrights, weights, onChange, disabled, labelForName }: Props) {
  // Raw keystroke text per cell, tracked separately from the committed
  // `weights` map: "-" and "-0" don't parse to a stored weight yet, but a
  // fully-controlled input bound straight to `weights` would snap back to
  // "" the instant those are typed, wiping the "-" before a digit follows.
  const [text, setText] = useState<Record<string, string>>({});
  const legCount = nonZeroLegCount(weights);
  const overLimit = legCount > MAX_LEGS;

  function setWeight(name: string, raw: string) {
    if (!INT_PATTERN.test(raw)) return;
    setText((t) => ({ ...t, [name]: raw }));

    const next = { ...weights };
    const parsed = raw === '' || raw === '-' ? NaN : parseInt(raw, 10);
    if (!Number.isFinite(parsed) || parsed === 0) delete next[name];
    else next[name] = parsed;
    onChange(next);
  }

  function displayValue(name: string): string {
    if (name in text) return text[name];
    return weights[name] != null ? String(weights[name]) : '';
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '4px' }}>
        {outrights.map((name) => {
          const value = weights[name];
          const isNegative = value < 0;
          return (
            <div key={name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '52px' }}>
              <span style={{ color: '#666666', fontSize: '10px', marginBottom: '2px' }}>
                {labelForName ? labelForName(name, outrights) : erLabel(outrights, name)}
              </span>
              <input
                inputMode="numeric"
                disabled={disabled}
                value={displayValue(name)}
                onChange={(e) => setWeight(name, e.target.value)}
                placeholder="0"
                style={{
                  width: '48px',
                  background: '#0a0a0a',
                  color: isNegative ? '#ff3355' : value ? '#e5e5e5' : '#444444',
                  border: `1px solid ${isNegative ? '#ff3355' : value ? '#4aa8ff' : '#262626'}`,
                  borderRadius: '4px',
                  padding: '4px',
                  textAlign: 'center',
                  fontSize: '12px',
                  fontVariantNumeric: 'tabular-nums',
                }}
              />
            </div>
          );
        })}
      </div>
      <div style={{ color: overLimit ? '#ff3355' : '#666666', fontSize: '11px', marginTop: '2px' }}>
        {legCount}/{MAX_LEGS} legs{overLimit ? ' — remove some, max 8 non-zero weights' : ''}
      </div>
    </div>
  );
}
