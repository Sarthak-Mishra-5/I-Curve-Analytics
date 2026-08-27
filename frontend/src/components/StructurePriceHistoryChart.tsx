import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineSeries,
  createChart,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type MouseEventParams,
  type UTCTimestamp,
  type WhitespaceData,
} from 'lightweight-charts';
import type { StructurePriceHistoryPoint } from '../icurve/types';

export type PriceDisplayMode = 'raw' | 'normalized' | 'zscore';

/** Daily OHLC candle for structure A, as returned by the backend. */
export type StructureCandle = { date: string; o: number; h: number; l: number; c: number };

interface Props {
  points: StructurePriceHistoryPoint[];
  loading: boolean;
  emptyMessage?: string;
  height?: number;
  labelA?: string;
  labelB?: string;
  // True daily OHLC for structure A. When supplied AND mode is 'raw', A is
  // drawn as candles (B stays a line). Ignored for 'normalized'/'zscore',
  // where the series are rescaled and a candle's open/high/low/close would
  // no longer correspond to anything the structure actually traded at.
  candlesA?: StructureCandle[];
  // 'raw' (default) plots levels as-is; 'normalized' rebases each series to
  // 100 at its first observation; 'zscore' plots each series' own
  // (value-mean)/std over the given points. Useful for comparing relative
  // movement of two series on very different scales (e.g. legs from two
  // different curves/currencies).
  mode?: PriceDisplayMode;
}

const A_COLOR = '#4aa8ff';
const B_COLOR = '#ff3355';
const UP = '#26a69a';
const DOWN = '#ef5350';
const TEXT = '#d1d4dc';
const MUTED = '#666666';
const GRID = '#1c1c1c';
const BG = '#0a0a0a';
const DEFAULT_VISIBLE_POINTS = 180;

function transform(values: (number | null)[], mode: PriceDisplayMode): (number | null)[] {
  if (mode === 'raw') return values;
  const numeric = values.filter((v): v is number => v != null && Number.isFinite(v));
  if (numeric.length === 0) return values;
  if (mode === 'normalized') {
    const base = numeric[0];
    if (!base) return values;
    return values.map((v) => (v == null ? null : (v / base) * 100));
  }
  // zscore
  const mean = numeric.reduce((s, v) => s + v, 0) / numeric.length;
  const variance = numeric.reduce((s, v) => s + (v - mean) ** 2, 0) / numeric.length;
  const std = Math.sqrt(variance);
  if (std < 1e-12) return values.map((v) => (v == null ? null : 0));
  return values.map((v) => (v == null ? null : (v - mean) / std));
}

/** Chart-library time for a 'YYYY-MM-DD' (or any parseable) date string. */
function toTime(date: string): UTCTimestamp | null {
  const ms = Date.parse(date.length === 10 ? `${date}T00:00:00Z` : date);
  return Number.isNaN(ms) ? null : (Math.floor(ms / 1000) as UTCTimestamp);
}

// Interactive comparison chart, sharing the Live OR chart's engine and feel:
// crosshair, wheel zoom, drag-pan, independent price-axis drag, and a
// per-chart view reset. Two lines rather than candles, because these are two
// structures being compared — a pair of candle series on one pane would be
// unreadable, and a computed structure has no genuine open/high/low anyway.
export default function StructurePriceHistoryChart({
  points,
  loading,
  emptyMessage = 'No price history yet',
  height = 260,
  labelA = 'Structure A',
  labelB = 'Structure B',
  mode = 'raw',
  candlesA,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const aRef = useRef<ISeriesApi<'Line'> | null>(null);
  const aCandleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const bRef = useRef<ISeriesApi<'Line'> | null>(null);
  const userMovedRef = useRef(false);
  const selfScrollingRef = useRef(false);
  const [resetNonce, setResetNonce] = useState(0);
  const [hover, setHover] = useState<{
    time: UTCTimestamp;
    a: number | null;
    b: number | null;
    ohlc?: { o: number; h: number; l: number; c: number } | null;
  } | null>(null);

  const decimals = mode === 'raw' ? 4 : 2;
  // Candles only make sense on untransformed levels.
  const showCandles = mode === 'raw' && !!candlesA && candlesA.length > 0;

  // Build strictly-ascending, de-duplicated series. Nulls become whitespace
  // points so genuine gaps stay gaps instead of being bridged by a
  // straight line (matching the previous connectgaps:false behaviour).
  const { dataA, dataB, count } = useMemo(() => {
    const yA = transform(points.map((p) => p.a), mode);
    const yB = transform(points.map((p) => p.b), mode);
    const byTime = new Map<number, { a: number | null; b: number | null }>();
    points.forEach((p, i) => {
      const t = toTime(p.date);
      if (t == null) return;
      byTime.set(t, { a: yA[i] ?? null, b: yB[i] ?? null });
    });
    const times = [...byTime.keys()].sort((x, y) => x - y);
    const mk = (pick: 'a' | 'b'): (LineData<UTCTimestamp> | WhitespaceData<UTCTimestamp>)[] =>
      times.map((t) => {
        const v = byTime.get(t)![pick];
        return v == null || !Number.isFinite(v)
          ? ({ time: t as UTCTimestamp } as WhitespaceData<UTCTimestamp>)
          : ({ time: t as UTCTimestamp, value: v } as LineData<UTCTimestamp>);
      });
    return { dataA: mk('a'), dataB: mk('b'), count: times.length };
  }, [points, mode]);

  const candleData = useMemo(() => {
    if (!showCandles || !candlesA) return [];
    const byTime = new Map<number, CandlestickData<UTCTimestamp>>();
    for (const c of candlesA) {
      const t = toTime(c.date);
      if (t == null) continue;
      if (![c.o, c.h, c.l, c.c].every((v) => typeof v === 'number' && Number.isFinite(v))) continue;
      // Clamp so a malformed bar can't render an inverted wick.
      const high = Math.max(c.h, c.o, c.c, c.l);
      const low = Math.min(c.l, c.o, c.c, c.h);
      byTime.set(t, { time: t, open: c.o, high, low, close: c.c });
    }
    return [...byTime.keys()].sort((x, y) => x - y).map((t) => byTime.get(t)!);
  }, [candlesA, showCandles]);

  const frameToDefault = useCallback(() => {
    const chart = chartRef.current;
    if (!chart || count === 0) return;
    void showCandles;
    selfScrollingRef.current = true;
    try {
      chart.timeScale().fitContent();
      if (count > DEFAULT_VISIBLE_POINTS) {
        chart.timeScale().setVisibleLogicalRange({ from: count - DEFAULT_VISIBLE_POINTS, to: count });
      }
      (showCandles ? aCandleRef.current : aRef.current)?.priceScale().applyOptions({ autoScale: true });
    } finally {
      selfScrollingRef.current = false;
    }
  }, [count, showCandles]);

  // --- construction: once per mount ---------------------------------------
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: BG },
        textColor: TEXT,
        fontFamily: 'JetBrains Mono, Consolas, monospace',
        fontSize: 10,
        attributionLogo: false,
      },
      grid: { vertLines: { color: GRID }, horzLines: { color: GRID } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#2a2a2a' },
      timeScale: { borderColor: '#2a2a2a', timeVisible: false, secondsVisible: false, rightOffset: 2 },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
      },
      autoSize: true,
    });

    // Both an A-line and an A-candle series exist for the lifetime of the
    // chart; whichever the current mode doesn't use is fed an empty dataset.
    // Adding/removing series on a mode switch would otherwise force a
    // teardown and lose the viewport.
    const sA = chart.addSeries(LineSeries, { color: A_COLOR, lineWidth: 2, priceLineVisible: false });
    const sACandle = chart.addSeries(CandlestickSeries, {
      upColor: UP, downColor: DOWN,
      borderUpColor: UP, borderDownColor: DOWN,
      wickUpColor: UP, wickDownColor: DOWN,
    });
    const sB = chart.addSeries(LineSeries, { color: B_COLOR, lineWidth: 2, priceLineVisible: false });

    chartRef.current = chart;
    aRef.current = sA;
    aCandleRef.current = sACandle;
    bRef.current = sB;

    const onCrosshair = (param: MouseEventParams) => {
      if (!param.time) {
        setHover(null);
        return;
      }
      const va = param.seriesData.get(sA) as { value?: number } | undefined;
      const vb = param.seriesData.get(sB) as { value?: number } | undefined;
      const vc = param.seriesData.get(sACandle) as CandlestickData<UTCTimestamp> | undefined;
      setHover({
        time: param.time as UTCTimestamp,
        a: vc ? vc.close : va?.value ?? null,
        b: vb?.value ?? null,
        ohlc: vc ? { o: vc.open, h: vc.high, l: vc.low, c: vc.close } : null,
      });
    };
    chart.subscribeCrosshairMove(onCrosshair);

    const onRange = () => {
      if (!selfScrollingRef.current) userMovedRef.current = true;
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange);

    return () => {
      chart.unsubscribeCrosshairMove(onCrosshair);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange);
      chart.remove();
      chartRef.current = null;
      aRef.current = null;
      aCandleRef.current = null;
      bRef.current = null;
    };
  }, []);

  // --- data ---------------------------------------------------------------
  useEffect(() => {
    const sA = aRef.current;
    const sACandle = aCandleRef.current;
    const sB = bRef.current;
    if (!sA || !sACandle || !sB) return;
    // Exactly one representation of A carries data at a time.
    sA.setData(showCandles ? [] : dataA);
    sACandle.setData(showCandles ? candleData : []);
    sB.setData(dataB);
    // A mode switch rescales both series, so re-frame rather than keeping a
    // viewport that was meaningful only for the previous scale.
    userMovedRef.current = false;
    frameToDefault();
  }, [dataA, dataB, candleData, showCandles, frameToDefault]);

  useEffect(() => {
    const opts = { priceFormat: { type: 'price' as const, precision: decimals, minMove: Math.pow(10, -decimals) } };
    aRef.current?.applyOptions(opts);
    aCandleRef.current?.applyOptions(opts);
    bRef.current?.applyOptions(opts);
  }, [decimals]);

  useEffect(() => {
    if (resetNonce === 0) return;
    userMovedRef.current = false;
    frameToDefault();
  }, [resetNonce, frameToDefault]);

  const fmt = (v: number | null) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(decimals));
  const stamp = hover
    ? new Date(hover.time * 1000).toLocaleDateString('en-GB', {
        day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
      })
    : '';
  const showEmpty = !loading && count === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      {/* legend + hover readout + per-chart reset */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', fontSize: '10px', fontVariantNumeric: 'tabular-nums', color: MUTED, minHeight: '16px', marginBottom: '2px' }}>
        <span style={{ color: '#8a8a8a', minWidth: '78px' }}>{stamp}</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          <span style={{ width: '8px', height: '2px', background: showCandles ? UP : A_COLOR, display: 'inline-block' }} />
          <span style={{ color: MUTED }}>{labelA}</span>
          {showCandles && hover?.ohlc ? (
            <>
              <span>O <span style={{ color: TEXT }}>{fmt(hover.ohlc.o)}</span></span>
              <span>H <span style={{ color: TEXT }}>{fmt(hover.ohlc.h)}</span></span>
              <span>L <span style={{ color: TEXT }}>{fmt(hover.ohlc.l)}</span></span>
              <span>C <span style={{ color: TEXT }}>{fmt(hover.ohlc.c)}</span></span>
            </>
          ) : (
            <span style={{ color: TEXT }}>{fmt(hover?.a ?? null)}</span>
          )}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ width: '8px', height: '2px', background: B_COLOR, display: 'inline-block' }} />
          <span style={{ color: MUTED }}>{labelB}</span>
          <span style={{ color: TEXT }}>{fmt(hover?.b ?? null)}</span>
        </span>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>{mode === 'raw' ? 'Price' : mode === 'normalized' ? 'Indexed (100 = start)' : 'Z-Score'}</span>
          <button
            onClick={() => setResetNonce((n) => n + 1)}
            title="Reset this chart's view"
            aria-label="Reset this chart's view"
            data-testid="chart-reset"
            style={{
              padding: '1px 6px', fontSize: '11px', lineHeight: 1.1, fontFamily: 'inherit',
              borderRadius: '3px', border: '1px solid #262626', backgroundColor: 'transparent',
              color: MUTED, cursor: 'pointer',
            }}
          >
            ⟲
          </button>
        </span>
      </div>

      <div style={{ position: 'relative', width: '100%', height: `${height}px` }}>
        <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
        {(loading || showEmpty) && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: count > 0 ? 'transparent' : BG, pointerEvents: 'none', color: MUTED, fontSize: '11px' }}>
            {loading && count === 0 ? 'Loading…' : showEmpty ? emptyMessage : ''}
          </div>
        )}
      </div>
    </div>
  );
}
