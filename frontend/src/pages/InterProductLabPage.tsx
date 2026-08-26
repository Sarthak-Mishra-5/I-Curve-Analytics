import { useEffect, useMemo, useRef, useState } from 'react';
import LegBuilder from '../components/interproduct/LegBuilder';
import LegFormulaDisplay from '../components/interproduct/LegFormulaDisplay';
import RVChart from '../components/interproduct/RVChart';
import ScatterRegressionChart from '../components/interproduct/ScatterRegressionChart';
import ZScoreChart from '../components/interproduct/ZScoreChart';
import InterProductStatsTables from '../components/interproduct/InterProductStatsTables';
import CorrelationOverTimeChart from '../components/CorrelationOverTimeChart';
import Panel from '../components/Panel';
import StructurePriceHistoryChart, { PriceDisplayMode } from '../components/StructurePriceHistoryChart';
import { useICurveStore } from '../icurve/store';
import {
  InterProductAnalyzeResponse, LegConfig, WINDOW_OPTIONS, WindowOption,
  defaultLegConfig, legConfigIsReady, legConfigToRequest,
} from '../interproduct/types';

const STORAGE_KEY = 'rv-terminal:interproduct-lab';

const STAGES = [
  'Resolving structures',
  'Loading each product’s historical prices',
  'Aligning legs by calendar date',
  'Computing relationship & regression',
  'Building combined RV series',
];
const STAGE_INTERVAL_MS = 450;

function isoDateOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

type SavedState = {
  legA?: LegConfig;
  legB?: LegConfig;
  window?: WindowOption;
  startDate?: string;
};

function readSaved(): SavedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export default function InterProductLabPage() {
  const products = useICurveStore((s) => s.products);
  const setProducts = useICurveStore((s) => s.setProducts);
  const curveSpecs = useICurveStore((s) => s.curveSpecs);
  const setCurveSpec = useICurveStore((s) => s.setCurveSpec);

  const saved = useMemo(readSaved, []);

  const [legA, setLegA] = useState<LegConfig>(saved.legA ?? defaultLegConfig('I'));
  const [legB, setLegB] = useState<LegConfig>(saved.legB ?? defaultLegConfig('SO3'));
  const [window_, setWindow] = useState<WindowOption>(saved.window ?? '30D');
  const [startDate, setStartDate] = useState(saved.startDate ?? isoDateOffset(180));
  const [endDate, setEndDate] = useState(todayIso());
  const [priceMode, setPriceMode] = useState<PriceDisplayMode>('normalized');
  const [showHedgeAdjusted, setShowHedgeAdjusted] = useState(false);

  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [result, setResult] = useState<InterProductAnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch the registered products once (GET /api/curves) — shared cache in
  // the icurve store rather than a page-local fetch.
  useEffect(() => {
    if (products.length > 0) return;
    fetch('/api/curves')
      .then((r) => r.json())
      .then((body) => setProducts(body.curves ?? []))
      .catch(() => {});
  }, [products.length, setProducts]);

  // Once products load, snap the leg defaults onto real curve ids if the
  // guessed defaults ("I"/"SO3") aren't actually registered.
  useEffect(() => {
    if (products.length === 0) return;
    const ids = products.map((p) => p.curve_id);
    if (!ids.includes(legA.curveId)) setLegA((l) => ({ ...l, curveId: ids[0] }));
    if (!ids.includes(legB.curveId)) setLegB((l) => ({ ...l, curveId: ids[Math.min(1, ids.length - 1)] }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [products]);

  // Each leg's curve spec (outrights/3ms/6ms/3mf name lists) — reuses the
  // same curveSpecs cache ICurveAnalyticsPage populates, fetched on demand
  // whenever a leg picks a curve that isn't cached yet.
  useEffect(() => {
    for (const curveId of new Set([legA.curveId, legB.curveId])) {
      if (curveSpecs[curveId]) continue;
      fetch(`/api/curves/${curveId}`)
        .then((r) => r.json())
        .then(setCurveSpec)
        .catch(() => {});
    }
  }, [legA.curveId, legB.curveId, curveSpecs, setCurveSpec]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ legA, legB, window: window_, startDate }));
  }, [legA, legB, window_, startDate]);

  useEffect(() => () => {
    if (stageTimer.current) clearInterval(stageTimer.current);
  }, []);

  const canAnalyze = legConfigIsReady(legA) && legConfigIsReady(legB) && !loading && startDate <= endDate;

  async function analyze() {
    setLoading(true);
    setError(null);
    setStageIndex(0);
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = setInterval(() => setStageIndex((i) => Math.min(i + 1, STAGES.length - 1)), STAGE_INTERVAL_MS);

    try {
      const res = await fetch('/api/inter-product/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          legs: [legConfigToRequest(legA), legConfigToRequest(legB)],
          window: window_,
          start_date: startDate,
          end_date: endDate,
        }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`);
      setResult(body as InterProductAnalyzeResponse);
    } catch (err: any) {
      setResult(null);
      setError(err.message ?? 'Analysis failed');
    } finally {
      if (stageTimer.current) clearInterval(stageTimer.current);
      setLoading(false);
    }
  }

  function reset() {
    if (loading) return;
    setLegA(defaultLegConfig(products[0]?.curve_id ?? 'I'));
    setLegB(defaultLegConfig(products[Math.min(3, products.length - 1)]?.curve_id ?? 'SO3'));
    setWindow('30D');
    setStartDate(isoDateOffset(180));
    setEndDate(todayIso());
    setResult(null);
    setError(null);
    localStorage.removeItem(STORAGE_KEY);
  }

  const legAName = result?.legs[0]?.label ?? 'Leg 1';
  const legBName = result?.legs[1]?.label ?? 'Leg 2';

  // Once results render, this page grows tall (4 stat panels + 5 charts);
  // without pinning, scrolling down to see them scrolls the builder/Analyze/
  // Reset controls above out of view with no way back to them short of
  // scrolling all the way back up. Sticking this panel to the top of the
  // scroll container keeps "change a leg" and "Reset" reachable at all times.
  const [buildersExpanded, setBuildersExpanded] = useState(true);

  return (
    <main className="flex-1 overflow-auto p-1.5" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 30, background: '#0a0a0a', paddingBottom: '2px', boxShadow: '0 6px 10px -6px rgba(0,0,0,0.6)' }}>
      <Panel
        title="Inter-Product Lab"
        subtitle="relative value across different STIR curves"
        actions={
          result ? (
            <button
              onClick={() => setBuildersExpanded((v) => !v)}
              style={{ background: 'transparent', color: '#666666', border: '1px solid #333333', borderRadius: '3px', padding: '3px 8px', fontSize: '10px', cursor: 'pointer' }}
            >
              {buildersExpanded ? 'Collapse legs ▲' : 'Edit legs ▼'}
            </button>
          ) : undefined
        }
      >
        {buildersExpanded && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px', marginBottom: '10px' }}>
          <LegBuilder leg={legA} onChange={setLegA} products={products} curveSpec={curveSpecs[legA.curveId] ?? null} accentColor="#4aa8ff" legLabel="Leg 1" disabled={loading} />
          <LegBuilder leg={legB} onChange={setLegB} products={products} curveSpec={curveSpecs[legB.curveId] ?? null} accentColor="#ff3355" legLabel="Leg 2" disabled={loading} />
        </div>
        )}

        {/* Window/date/Analyze/Reset always render, even with legs collapsed
            — these are the controls the sticky panel exists to keep reachable. */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '10px' }}>
          <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            Rolling Window
            <select
              value={window_}
              disabled={loading}
              onChange={(e) => setWindow(e.target.value as WindowOption)}
              style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px', fontSize: '12px' }}
            >
              {WINDOW_OPTIONS.map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </label>
          <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            From
            <input type="date" value={startDate} disabled={loading} onChange={(e) => setStartDate(e.target.value)}
              style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px' }} />
          </label>
          <label style={{ color: '#888888', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            To
            <input type="date" value={endDate} disabled={loading} onChange={(e) => setEndDate(e.target.value)}
              style={{ background: '#0a0a0a', color: '#e5e5e5', border: '1px solid #333333', borderRadius: '4px', padding: '5px 8px' }} />
          </label>

          <button
            onClick={analyze}
            disabled={!canAnalyze}
            style={{
              background: canAnalyze ? '#00ff88' : '#262626', color: canAnalyze ? '#0a0a0a' : '#666666',
              border: 0, borderRadius: '4px', padding: '6px 16px', fontSize: '12px', fontWeight: 'bold',
              cursor: canAnalyze ? 'pointer' : 'default',
            }}
          >
            Analyze
          </button>
          <button
            onClick={reset}
            disabled={loading}
            style={{
              background: '#262626', color: loading ? '#666666' : '#e5e5e5', border: '1px solid #444444',
              borderRadius: '4px', padding: '5px 10px', fontSize: '12px', cursor: loading ? 'default' : 'pointer',
            }}
          >
            Reset
          </button>
        </div>

        {loading && (
          <div>
            <div style={{ background: '#1a1a1a', borderRadius: '4px', height: '6px', overflow: 'hidden', marginBottom: '6px' }}>
              <div style={{ background: '#4aa8ff', height: '100%', width: `${Math.round(((stageIndex + 1) / STAGES.length) * 95)}%`, transition: 'width 300ms ease' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {STAGES.map((stage, i) => (
                <div key={stage} style={{ fontSize: '11px', color: i < stageIndex ? '#00ff88' : i === stageIndex ? '#ffaa00' : '#444444' }}>
                  {i < stageIndex ? '✓ ' : i === stageIndex ? '… ' : '  '}{stage}
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && error && <div style={{ color: '#ff3355', fontSize: '12px' }}>{error}</div>}
      </Panel>
      </div>

      {!loading && result && (
        <>
          <Panel title="Leg Summary">
            <LegFormulaDisplay legs={result.legs} />
          </Panel>

          <InterProductStatsTables result={result} showHedgeAdjusted={showHedgeAdjusted} />

          {result.relationship.hedge_ratio != null && (
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              <span style={{ color: '#666666', fontSize: '11px' }}>RV display:</span>
              {[{ v: false, l: 'Raw Trade' }, { v: true, l: 'Hedge-Ratio Adjusted' }].map((opt) => (
                <button
                  key={String(opt.v)}
                  onClick={() => setShowHedgeAdjusted(opt.v)}
                  style={{
                    padding: '4px 10px', fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.04em',
                    borderRadius: '3px', border: '1px solid #333333',
                    background: showHedgeAdjusted === opt.v ? '#262626' : 'transparent',
                    color: showHedgeAdjusted === opt.v ? '#e5e5e5' : '#666666', cursor: 'pointer',
                  }}
                >
                  {opt.l}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '10px' }}>
            <Panel
              title="Component Structures"
              subtitle={legAName + ' vs ' + legBName}
              actions={
                <div style={{ display: 'flex', gap: '4px' }}>
                  {(['raw', 'normalized', 'zscore'] as PriceDisplayMode[]).map((m) => (
                    <button
                      key={m}
                      onClick={() => setPriceMode(m)}
                      style={{
                        padding: '3px 8px', fontSize: '10px', borderRadius: '3px', border: '1px solid #333333',
                        background: priceMode === m ? '#262626' : 'transparent',
                        color: priceMode === m ? '#e5e5e5' : '#666666', cursor: 'pointer', textTransform: 'capitalize',
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              }
            >
              <StructurePriceHistoryChart
                points={result.chart_data.leg_price_points}
                loading={false}
                labelA={legAName}
                labelB={legBName}
                mode={priceMode}
              />
            </Panel>

            <Panel title="Rolling Correlation" subtitle={`window: ${result.window}`}>
              <CorrelationOverTimeChart points={result.chart_data.rolling_correlation_points} loading={false} lineColor="#4aa8ff" />
            </Panel>

            <Panel title="Relative Value" subtitle={showHedgeAdjusted ? 'hedge-ratio adjusted' : 'raw trade'}>
              <RVChart points={result.chart_data.rv_points} loading={false} />
            </Panel>

            <Panel title="RV Z-Score">
              <ZScoreChart points={result.chart_data.zscore_points} loading={false} />
            </Panel>
          </div>

          <Panel title="Scatter / Regression" subtitle={`Y = ${legAName}, X = ${legBName}`}>
            <ScatterRegressionChart
              points={result.chart_data.scatter_points}
              regressionAlpha={result.relationship.regression_alpha}
              regressionBeta={result.relationship.regression_beta}
              rSquared={result.relationship.r_squared}
              correlation={result.relationship.correlation}
              loading={false}
              labelA={legAName}
              labelB={legBName}
            />
          </Panel>
        </>
      )}
    </main>
  );
}
