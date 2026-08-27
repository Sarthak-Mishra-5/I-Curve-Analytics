import { useEffect, useMemo, useRef, useState } from 'react';
import type { ComparisonResponse, CorrelationHistoryPoint, CurveSpecDTO, StructurePriceHistoryPoint } from '../icurve/types';
import { shortTenor } from '../icurve/format';
import { fmt } from '../plotlyTheme';
import CorrelationOverTimeChart from './CorrelationOverTimeChart';
import Panel from './Panel';
import StructurePriceHistoryChart, { type StructureCandle } from './StructurePriceHistoryChart';
import WeightGrid, { MAX_LEGS, nonZeroLegCount } from './WeightGrid';

interface Props {
  curveId: string;
  curveSpec: CurveSpecDTO;
}

type Field = {
  key: keyof ComparisonResponse;
  label: string;
  render: (r: ComparisonResponse) => string;
};

const FIELDS: Field[] = [
  { key: 'correlation', label: 'Correlation', render: (r) => fmt.px(r.correlation, 2) },
  { key: 'lowess_beta', label: 'LOWESS Regression', render: (r) => fmt.px(r.lowess_beta, 2) },
  { key: 'regression_beta', label: 'Regression Beta', render: (r) => fmt.px(r.regression_beta, 2) },
  { key: 'hedge_ratio', label: 'Hedge Ratio', render: (r) => fmt.px(r.hedge_ratio, 2) },
  { key: 'cointegrated', label: 'Cointegration', render: (r) => (r.cointegrated == null ? '—' : r.cointegrated ? 'Yes' : 'No') },
  { key: 'current_spread', label: 'Current Spread', render: (r) => fmt.chg(r.current_spread, 3) },
  { key: 'z_score', label: 'Z-Score', render: (r) => fmt.z(r.z_score) },
  { key: 'historical_percentile', label: 'Historical Percentile', render: (r) => `${fmt.pct(r.historical_percentile)}%` },
  { key: 'volatility_ratio', label: 'Volatility Ratio', render: (r) => fmt.px(r.volatility_ratio, 2) },
];

function isoDateOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

// Today, in the same UTC calendar-date space the backend keys its merged
// series by (see custom_structure._date_key). Deliberately not persisted:
// the end of the range is always "now", so a range saved on an earlier day
// can never silently truncate the comparison to that day.
function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

type ComparisonLabState = {
  nameA?: string;
  nameB?: string;
  weightsA?: Record<string, number>;
  weightsB?: Record<string, number>;
  startDate?: string;
  result?: ComparisonResponse | null;
  points?: CorrelationHistoryPoint[];
  pricePoints?: StructurePriceHistoryPoint[];
  priceCandlesA?: StructureCandle[];
};

function readSavedState(key: string): ComparisonLabState {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function sanitizeWeights(weights: Record<string, number> | undefined, outrights: string[]): Record<string, number> {
  const clean: Record<string, number> = {};
  for (const key of Object.keys(weights ?? {})) {
    if (outrights.includes(key)) clean[key] = weights![key];
  }
  return clean;
}

// A comparison saved under an older build (before curve switching correctly
// reset component state) can still carry a leg from a different curve, e.g.
// "I Sep26" saved under the SR3 storage key. Drop anything that isn't one of
// the current curve's own outrights; if either side got contaminated, the
// saved comparison result is untrustworthy too — discard it so the user reruns.
function sanitizeSavedState(saved: ComparisonLabState, outrights: string[]): ComparisonLabState {
  const weightsA = sanitizeWeights(saved.weightsA, outrights);
  const weightsB = sanitizeWeights(saved.weightsB, outrights);
  const contaminated =
    Object.keys(saved.weightsA ?? {}).length !== Object.keys(weightsA).length ||
    Object.keys(saved.weightsB ?? {}).length !== Object.keys(weightsB).length;
  if (!contaminated) return saved;
  return { nameA: saved.nameA, nameB: saved.nameB, weightsA, weightsB, startDate: saved.startDate };
}

export default function ComparisonLab({ curveId, curveSpec }: Props) {
  const storageKey = useMemo(() => `rv-terminal:${curveId}:structure-comparison-lab`, [curveId]);
  const savedState = useMemo(
    () => sanitizeSavedState(readSavedState(storageKey), curveSpec.outrights),
    [storageKey, curveSpec.outrights],
  );

  const [nameA, setNameA] = useState(savedState.nameA ?? 'Structure A');
  const [nameB, setNameB] = useState(savedState.nameB ?? 'Structure B');
  const [weightsA, setWeightsA] = useState<Record<string, number>>(savedState.weightsA ?? {});
  const [weightsB, setWeightsB] = useState<Record<string, number>>(savedState.weightsB ?? {});
  const [startDate, setStartDate] = useState(savedState.startDate ?? isoDateOffset(180));
  const [endDate, setEndDate] = useState(todayIso());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComparisonResponse | null>(savedState.result ?? null);
  const [points, setPoints] = useState<CorrelationHistoryPoint[]>(savedState.points ?? []);
  const [pricePoints, setPricePoints] = useState<StructurePriceHistoryPoint[]>(savedState.pricePoints ?? []);
  // True daily OHLC for Structure A, drawn as candles (B stays a line).
  const [priceCandlesA, setPriceCandlesA] = useState<StructureCandle[]>(savedState.priceCandlesA ?? []);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify({ nameA, nameB, weightsA, weightsB, startDate, result, points, pricePoints, priceCandlesA }));
  }, [storageKey, nameA, nameB, weightsA, weightsB, startDate, result, points, pricePoints, priceCandlesA]);

  // A terminal left open overnight would otherwise keep yesterday's end date.
  // Re-pin it to today whenever the tab is looked at again — but only while it
  // still holds the auto value, so a deliberately chosen end date is kept.
  const autoEndRef = useRef(endDate);
  useEffect(() => {
    function syncEndToToday() {
      const today = todayIso();
      setEndDate((prev) => (prev === autoEndRef.current ? today : prev));
      autoEndRef.current = today;
    }
    window.addEventListener('focus', syncEndToToday);
    document.addEventListener('visibilitychange', syncEndToToday);
    return () => {
      window.removeEventListener('focus', syncEndToToday);
      document.removeEventListener('visibilitychange', syncEndToToday);
    };
  }, []);

  const legsA = nonZeroLegCount(weightsA);
  const legsB = nonZeroLegCount(weightsB);
  const canCompare = legsA > 0 && legsA <= MAX_LEGS && legsB > 0 && legsB <= MAX_LEGS && !loading && startDate <= endDate;

  async function compare() {
    setLoading(true);
    setError(null);
    try {
      const [comparisonRes, historyRes] = await Promise.all([
        fetch(`/api/curves/${curveId}/comparison`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ weights_a: weightsA, weights_b: weightsB, start_date: startDate, end_date: endDate }),
        }),
        fetch(`/api/curves/${curveId}/custom-structure/correlation-history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ legs_a: weightsA, legs_b: weightsB, label_a: nameA, label_b: nameB, start_date: startDate, end_date: endDate }),
        }),
      ]);

      const comparisonBody = await comparisonRes.json();
      if (!comparisonRes.ok) throw new Error(comparisonBody?.detail ?? `HTTP ${comparisonRes.status}`);
      setResult(comparisonBody as ComparisonResponse);

      const historyBody = await historyRes.json();
      setPoints(historyRes.ok ? historyBody.points ?? [] : []);
      setPricePoints(historyRes.ok ? historyBody.price_points ?? [] : []);
      setPriceCandlesA(historyRes.ok ? historyBody.candles_a ?? [] : []);
    } catch (err: any) {
      setResult(null);
      setPoints([]);
      setPricePoints([]);
      setPriceCandlesA([]);
      setError(err.message ?? 'Comparison failed');
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    if (loading) return;
    setNameA('Structure A');
    setNameB('Structure B');
    setWeightsA({});
    setWeightsB({});
    setStartDate(isoDateOffset(180));
    setEndDate(todayIso());
    setResult(null);
    setPoints([]);
    setPricePoints([]);
    setError(null);
    localStorage.removeItem(storageKey);
  }

  return (
    <Panel title="Structure Comparison Lab" subtitle="exact structures, no rolling">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px', marginBottom: '10px' }}>
        <div>
          <input
            value={nameA}
            onChange={(e) => setNameA(e.target.value)}
            disabled={loading}
            placeholder="Structure A name"
            style={{ width: '100%', color: '#4aa8ff', background: '#0a0a0a', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px', fontSize: '11px', fontWeight: 'bold', marginBottom: '6px' }}
          />
          <WeightGrid outrights={curveSpec.outrights} weights={weightsA} onChange={setWeightsA} disabled={loading} labelForName={shortTenor} />
        </div>
        <div>
          <input
            value={nameB}
            onChange={(e) => setNameB(e.target.value)}
            disabled={loading}
            placeholder="Structure B name"
            style={{ width: '100%', color: '#ff3355', background: '#0a0a0a', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px', fontSize: '11px', fontWeight: 'bold', marginBottom: '6px' }}
          />
          <WeightGrid outrights={curveSpec.outrights} weights={weightsB} onChange={setWeightsB} disabled={loading} labelForName={shortTenor} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '10px' }}>
        <span style={{ color: '#666666', fontSize: '11px', fontWeight: 'bold', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          Range
        </span>
        <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          From
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={loading}
            style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px' }}
          />
        </label>
        <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          To
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={loading}
            style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px' }}
          />
        </label>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
        <button
          onClick={compare}
          disabled={!canCompare}
          style={{
            background: canCompare ? '#00ff88' : '#262626',
            color: canCompare ? '#0a0a0a' : '#666666',
            border: 0,
            borderRadius: '4px',
            padding: '6px 14px',
            fontSize: '12px',
            fontWeight: 'bold',
            cursor: canCompare ? 'pointer' : 'default',
          }}
        >
          Compare
        </button>
        <button
          onClick={reset}
          disabled={loading}
          style={{
            background: '#262626',
            color: loading ? '#666666' : '#e5e5e5',
            border: '1px solid #444444',
            borderRadius: '4px',
            padding: '5px 10px',
            fontSize: '12px',
            cursor: loading ? 'default' : 'pointer',
          }}
        >
          Reset
        </button>
      </div>

      {loading && <div style={{ color: '#666666', fontSize: '12px' }}>computing…</div>}
      {!loading && error && <div style={{ color: '#ff3355', fontSize: '12px' }}>{error}</div>}

      {!loading && result && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px', marginBottom: '10px' }}>
            <div style={{ background: '#1a1a1a', border: '1px solid #262626', borderRadius: '4px', padding: '6px 8px' }}>
              <div style={{ color: '#666666', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{nameA || 'Structure A'} live price</div>
              <div style={{ color: '#e5e5e5', fontSize: '14px', fontWeight: 'bold', fontVariantNumeric: 'tabular-nums' }}>{fmt.px(result.live_price_a, 2)}</div>
            </div>
            <div style={{ background: '#1a1a1a', border: '1px solid #262626', borderRadius: '4px', padding: '6px 8px' }}>
              <div style={{ color: '#666666', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{nameB || 'Structure B'} live price</div>
              <div style={{ color: '#e5e5e5', fontSize: '14px', fontWeight: 'bold', fontVariantNumeric: 'tabular-nums' }}>{fmt.px(result.live_price_b, 2)}</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '8px', marginBottom: '12px' }}>
            {FIELDS.map((f) => (
              <div key={String(f.key)} style={{ background: '#1a1a1a', border: '1px solid #262626', borderRadius: '4px', padding: '6px 8px' }}>
                <div style={{ color: '#666666', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{f.label}</div>
                <div style={{ color: '#e5e5e5', fontSize: '14px', fontWeight: 'bold', fontVariantNumeric: 'tabular-nums' }}>{f.render(result)}</div>
              </div>
            ))}
          </div>

          <div style={{ color: '#666666', fontSize: '11px', marginBottom: '4px' }}>{nameA || 'Structure A'} and {nameB || 'Structure B'} price history — past 6 months</div>
          <StructurePriceHistoryChart points={pricePoints} loading={false} height={260} labelA={nameA || 'Structure A'} labelB={nameB || 'Structure B'} candlesA={priceCandlesA} />

          <div style={{ color: '#666666', fontSize: '11px', margin: '10px 0 4px' }}>{nameA || 'Structure A'} vs {nameB || 'Structure B'} correlation — past 6 months</div>
          <CorrelationOverTimeChart points={points} loading={false} height={260} lineColor="#4aa8ff" />
        </>
      )}
    </Panel>
  );
}
