import { useEffect, useMemo, useRef, useState } from 'react';
import type { CurveSpecDTO, CustomStructureResponse, StructureRollRow } from '../icurve/types';
import { shortTenor } from '../icurve/format';
import { useICurveStore } from '../icurve/store';
import { fmt } from '../plotlyTheme';
import Panel from './Panel';
import WeightGrid, { MAX_LEGS, nonZeroLegCount } from './WeightGrid';

interface Props {
  curveId: string;
  curveSpec: CurveSpecDTO;
  defaultName: string;
}

const STAGES = [
  'Creating rolled structures',
  'Loading historical prices',
  'Calculating correlations',
  'Running LOWESS regression',
  'Computing hedge ratios',
  'Scanning previous highs/lows',
];

const STAGE_INTERVAL_MS = 450;

type ColumnDef = {
  key: string;
  label: string;
  render: (row: StructureRollRow) => string;
  color?: (row: StructureRollRow) => string;
};

function corrColor(c: number | null) {
  if (c == null) return '#666666';
  const a = Math.abs(c);
  if (a >= 0.7) return '#00ff88';
  if (a >= 0.4) return '#ffaa00';
  return '#e5e5e5';
}

// Modular by design: future columns (Z-Score, Half-Life, Volatility,
// Cointegration, Fair Value, Mispricing Score) append here without touching
// the fetch/roll/table-building logic above.
const COLUMNS: ColumnDef[] = [
  { key: 'correlation', label: 'Correlation', render: (r) => (r.correlation == null ? '—' : r.correlation.toFixed(2)), color: (r) => corrColor(r.correlation) },
  { key: 'lowess_beta', label: 'LOWESS Regression', render: (r) => fmt.px(r.lowess_beta, 2) },
  { key: 'regression_beta', label: 'Regression Beta', render: (r) => fmt.px(r.regression_beta, 2) },
  { key: 'hedge_ratio', label: 'Hedge Ratio', render: (r) => fmt.px(r.hedge_ratio, 2) },
  { key: 'prev_max', label: 'Previous Max', render: (r) => fmt.px(r.prev_max, 2) },
  { key: 'curr_at_prev_max', label: 'Current vs Previous Max', render: (r) => fmt.px(r.curr_at_prev_max, 2) },
  { key: 'prev_min', label: 'Previous Min', render: (r) => fmt.px(r.prev_min, 2) },
  { key: 'curr_at_prev_min', label: 'Current vs Previous Min', render: (r) => fmt.px(r.curr_at_prev_min, 2) },
];

type StructureBuilderState = {
  name?: string;
  weights?: Record<string, number>;
  data?: CustomStructureResponse | null;
};

function readSavedStructure(key: string): StructureBuilderState {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export default function StructureBuilder({ curveId, curveSpec, defaultName }: Props) {
  const setSelection = useICurveStore((s) => s.setCorrelationSelection);
  const selection = useICurveStore((s) => s.correlationSelection);

  const storageKey = useMemo(() => `rv-terminal:${curveId}:structure-builder:${defaultName}`, [curveId, defaultName]);
  const savedState = useMemo(() => readSavedStructure(storageKey), [storageKey]);

  const [name, setName] = useState(savedState.name ?? defaultName);
  const [weights, setWeights] = useState<Record<string, number>>(savedState.weights ?? {});
  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [data, setData] = useState<CustomStructureResponse | null>(savedState.data ?? null);
  const [error, setError] = useState<string | null>(null);
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (stageTimer.current) clearInterval(stageTimer.current);
  }, []);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify({ name, weights, data }));
  }, [storageKey, name, weights, data]);

  const legCount = nonZeroLegCount(weights);
  const canBuild = legCount > 0 && legCount <= MAX_LEGS && name.trim().length > 0 && !loading;

  async function build() {
    setLoading(true);
    setError(null);
    setStageIndex(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, STAGE_INTERVAL_MS);

    try {
      const res = await fetch(`/api/curves/${curveId}/custom-structure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, weights }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`);
      setData(body as CustomStructureResponse);
    } catch (err: any) {
      setData(null);
      setError(err.message ?? 'Build failed');
    } finally {
      if (stageTimer.current) clearInterval(stageTimer.current);
      setLoading(false);
    }
  }

  function selectRow(row: StructureRollRow, idx: number) {
    if (!data) return;
    const legsPrevious = data.rolls[idx]?.legs ?? {};
    const legsCurrent = data.rolls[idx + 1]?.legs ?? {};
    setSelection({
      kind: 'custom',
      structureName: data.name,
      previous: row.previous,
      current: row.current,
      legsPrevious,
      legsCurrent,
    });
  }

  const progressPct = loading ? Math.round(((stageIndex + 1) / STAGES.length) * 95) : data ? 100 : 0;

  return (
    <Panel title={name || 'Custom Structure'} subtitle={`${legCount}/${MAX_LEGS} legs`}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Structure name"
          disabled={loading}
          style={{ flex: 1, background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px', fontSize: '12px' }}
        />
        <button
          onClick={build}
          disabled={!canBuild}
          style={{
            background: canBuild ? '#00ff88' : '#262626',
            color: canBuild ? '#0a0a0a' : '#666666',
            border: 0,
            borderRadius: '4px',
            padding: '6px 14px',
            fontSize: '12px',
            fontWeight: 'bold',
            cursor: canBuild ? 'pointer' : 'default',
            whiteSpace: 'nowrap',
          }}
        >
          Build Structure
        </button>
      </div>

      <WeightGrid outrights={curveSpec.outrights} weights={weights} onChange={setWeights} disabled={loading} />

      {loading && (
        <div style={{ marginTop: '10px' }}>
          <div style={{ color: '#e5e5e5', fontSize: '11px', marginBottom: '4px' }}>
            {name}: {formulaText(curveSpec.outrights, weights)}
          </div>
          <div style={{ background: '#1a1a1a', borderRadius: '4px', height: '6px', overflow: 'hidden', marginBottom: '6px' }}>
            <div style={{ background: '#4aa8ff', height: '100%', width: `${progressPct}%`, transition: 'width 300ms ease' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginBottom: '8px' }}>
            {STAGES.map((stage, i) => (
              <div key={stage} style={{ fontSize: '11px', color: i < stageIndex ? '#00ff88' : i === stageIndex ? '#ffaa00' : '#444444' }}>
                {i < stageIndex ? '✓ ' : i === stageIndex ? '… ' : '  '}{stage}
              </div>
            ))}
          </div>
          <SkeletonTable />
        </div>
      )}

      {!loading && error && (
        <div style={{ color: '#ff3355', fontSize: '12px', marginTop: '8px' }}>{error}</div>
      )}

      {!loading && data && (
        <div style={{ marginTop: '10px' }}>
          <div style={{ color: '#e5e5e5', fontSize: '11px', marginBottom: '6px' }}>
            {data.name}: {formulaText(data.outrights, weights)}
          </div>
          {data.table.length === 0 ? (
            <div style={{ color: '#666666', textAlign: 'center', padding: '16px' }}>no rolled pairs yet</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '13px', fontVariantNumeric: 'tabular-nums', borderCollapse: 'collapse' }}>
                <thead style={{ color: '#666666' }}>
                  <tr style={{ borderBottom: '1px solid #262626' }}>
                <th style={{ textAlign: 'left', fontWeight: 'normal', padding: '4px' }}>Current Roll</th>
                <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Live Price</th>
                {COLUMNS.map((c) => (
                  <th key={c.key} style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>{c.label}</th>
                ))}
                  </tr>
                </thead>
                <tbody>
                  {data.table.map((row, idx) => {
                    const isSelected = selection?.kind === 'custom' && selection.structureName === data.name && selection.current === row.current;
                    return (
                      <tr
                        key={row.current}
                        onClick={() => selectRow(row, idx)}
                        style={{ borderBottom: '1px solid #262626', cursor: 'pointer', backgroundColor: isSelected ? '#1f1f1f' : undefined }}
                      >
                        <td style={{ padding: '4px', color: '#e5e5e5' }}>{shortTenor(row.current)} {data.name}</td>
                        <td style={{ padding: '4px', textAlign: 'right', color: '#e5e5e5' }}>{fmt.px(row.live_price, 2)}</td>
                        {COLUMNS.map((c) => (
                          <td key={c.key} style={{ padding: '4px', textAlign: 'right', color: c.color ? c.color(row) : '#e5e5e5' }}>
                            {c.render(row)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function formulaText(outrights: string[], weights: Record<string, number>): string {
  const parts = outrights
    .map((name) => ({ name, w: weights[name] ?? 0 }))
    .filter((p) => p.w !== 0)
    .map((p) => `${p.w > 0 ? '+' : ''}${p.w}×${shortTenor(p.name)}`);
  return parts.length ? parts.join(' ') : '—';
}

function SkeletonTable() {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
        <thead style={{ color: '#666666' }}>
          <tr style={{ borderBottom: '1px solid #262626' }}>
            <th style={{ textAlign: 'left', fontWeight: 'normal', padding: '4px' }}>Current Roll</th>
            <th style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>Live Price</th>
            {COLUMNS.map((c) => (
              <th key={c.key} style={{ textAlign: 'right', fontWeight: 'normal', padding: '4px' }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[0, 1, 2].map((rowIdx) => (
            <tr key={rowIdx} style={{ borderBottom: '1px solid #262626' }}>
              <td style={{ padding: '4px' }}><div className="animate-pulse" style={{ background: '#1a1a1a', height: '12px', borderRadius: '2px', width: '70px' }} /></td>
              <td style={{ padding: '4px' }}><div className="animate-pulse" style={{ background: '#1a1a1a', height: '12px', borderRadius: '2px', marginLeft: 'auto', width: '48px' }} /></td>
              {COLUMNS.map((c) => (
                <td key={c.key} style={{ padding: '4px' }}>
                  <div className="animate-pulse" style={{ background: '#1a1a1a', height: '12px', borderRadius: '2px', marginLeft: 'auto', width: '48px' }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
