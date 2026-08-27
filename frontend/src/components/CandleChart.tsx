import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  createChart,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type MouseEventParams,
  type UTCTimestamp,
} from 'lightweight-charts';

export type Interval = '5m' | '10m' | '30m' | '1h' | '1d';
const INTERVALS: Interval[] = ['5m', '10m', '30m', '1h', '1d'];

// Intraday timeframes get date+time crosshair labels; the daily chart gets a
// date only (spec: no intraday times on the 1d chart).
const IS_INTRADAY: Record<Interval, boolean> = {
  '5m': true,
  '10m': true,
  '30m': true,
  '1h': true,
  '1d': false,
};

type ApiBar = { t: string; o: number; h: number; l: number; c: number; v: number };
type Bar = { time: UTCTimestamp; open: number; high: number; low: number; close: number; volume: number };

interface Props {
  curveId: string;
  instrument: string;
  title: string;
  /** Fixed reference levels, drawn as blue lines with blue axis labels.
   *  Held at exactly these prices across zoom/pan/timeframe changes. */
  levels?: number[];
}

const UP = '#26a69a';
const DOWN = '#ef5350';
const LEVEL_BLUE = '#2962ff';
const TEXT = '#d1d4dc';
const MUTED = '#666666';
const GRID = '#1c1c1c';
const BG = '#0a0a0a';

const REFRESH_MS = 15_000;
// How many of the newest candles the default view shows, per timeframe. The
// backfill is deep (weeks of intraday, ~a year of daily), so fitting all of
// it would render an unreadable smear.
const DEFAULT_VISIBLE_BARS = 120;

/** Decimals implied by the instrument's tick size (0.005 -> 3dp). */
function decimalsFor(tickSize: number | null): number {
  if (!tickSize || !Number.isFinite(tickSize)) return 3;
  const s = tickSize.toString();
  const dot = s.indexOf('.');
  return dot < 0 ? 0 : s.length - dot - 1;
}

function fmtVolume(v: number): string {
  if (!Number.isFinite(v)) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (v >= 1_000) return (v / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
  return Math.round(v).toString();
}

export default function CandleChart({ curveId, instrument, title, levels = [] }: Props) {
  const [interval, setInterval_] = useState<Interval>('30m');
  const [bars, setBars] = useState<Bar[]>([]);
  const [tickSize, setTickSize] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Which bar the crosshair is over; null means "show the latest bar".
  const [hovered, setHovered] = useState<Bar | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  // Whether the user has manually panned/zoomed away from the live edge. Once
  // true, refreshes must not yank the viewport back to the latest candle.
  const userMovedRef = useRef(false);
  // Set while we programmatically move the viewport, so our own scroll calls
  // aren't mistaken for user navigation.
  const selfScrollingRef = useRef(false);
  // Bumped by the reset button to re-frame THIS chart only. Each CandleChart
  // owns its own state, so nothing here reaches the sibling charts.
  const [resetNonce, setResetNonce] = useState(0);

  const decimals = decimalsFor(tickSize);

  // Restore this chart's default view: newest candles visible at a readable
  // density, price axis auto-fitted to them. Reads bar count off the series
  // itself so it's safe to call from an effect that doesn't depend on `bars`.
  const frameToDefault = useCallback(() => {
    const chart = chartRef.current;
    const candles = candleRef.current;
    if (!chart || !candles) return;
    const count = candles.data().length;
    if (count === 0) return;
    selfScrollingRef.current = true;
    try {
      chart.timeScale().fitContent();
      // Then tighten to a sensible default density rather than squeezing the
      // entire backfilled history into the panel.
      const visible = Math.min(count, DEFAULT_VISIBLE_BARS);
      chart.timeScale().setVisibleLogicalRange({ from: count - visible, to: count });
      // Undo any manual vertical price-scale drag as well.
      candles.priceScale().applyOptions({ autoScale: true });
    } finally {
      selfScrollingRef.current = false;
    }
  }, []);

  // --- chart construction: once per mount ---------------------------------
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
      timeScale: {
        borderColor: '#2a2a2a',
        // Intraday series need seconds-resolution tick labels; the library
        // picks label density from the visible range on its own.
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 4,
      },
      // Wheel zooms the time axis (centred on the cursor), drag pans, and the
      // price axis can be dragged independently — the interaction split the
      // spec asks for.
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
      },
      autoSize: true,
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      borderUpColor: UP,
      borderDownColor: DOWN,
      wickUpColor: UP,
      wickDownColor: DOWN,
    });
    // Reserve the bottom ~18% of the pane for volume, keeping both on one
    // shared time axis so candles and their volume bars stay aligned.
    candles.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });

    const volume = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      priceFormat: { type: 'volume' },
      // Volume keeps its own scale (independent of price), but contributes no
      // axis labels or last-value/price lines of its own — those would
      // collide with the price axis in a compact 2x2 panel.
      priceLineVisible: false,
      lastValueVisible: false,
      baseLineVisible: false,
    });
    volume.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    chartRef.current = chart;
    candleRef.current = candles;
    volumeRef.current = volume;

    const onCrosshair = (param: MouseEventParams) => {
      const d = param.seriesData.get(candles) as CandlestickData<UTCTimestamp> | undefined;
      if (!param.time || !d) {
        setHovered(null);
        return;
      }
      const vd = param.seriesData.get(volume) as { value?: number } | undefined;
      setHovered({
        time: param.time as UTCTimestamp,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
        volume: vd?.value ?? 0,
      });
    };
    chart.subscribeCrosshairMove(onCrosshair);

    const onRangeChange = () => {
      if (selfScrollingRef.current) return;
      userMovedRef.current = true;
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);

    return () => {
      chart.unsubscribeCrosshairMove(onCrosshair);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
      priceLinesRef.current = [];
    };
  }, []);

  // --- data loading: on contract/timeframe change, then on a timer --------
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // A timeframe switch is a dataset change, not a pan — allow the viewport
    // to re-fit to the new candles.
    userMovedRef.current = false;

    const load = () => {
      const url = `/api/curves/${encodeURIComponent(curveId)}/candles`
        + `?instrument=${encodeURIComponent(instrument)}&interval=${interval}`;
      fetch(url)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((d: { bars?: ApiBar[]; tick_size?: number | null }) => {
          if (cancelled) return;
          const mapped: Bar[] = (d.bars ?? []).map((b) => ({
            time: Math.floor(new Date(b.t).getTime() / 1000) as UTCTimestamp,
            open: b.o,
            high: b.h,
            low: b.l,
            close: b.c,
            volume: b.v ?? 0,
          }));
          setTickSize(d.tick_size ?? null);
          setBars(mapped);
          setLoading(false);
          setError(null);
        })
        .catch((e: unknown) => {
          if (cancelled) return;
          setLoading(false);
          setError(e instanceof Error ? e.message : 'request failed');
        });
    };

    load();
    const id = window.setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [curveId, instrument, interval]);

  // --- push data into the series -----------------------------------------
  useEffect(() => {
    const candles = candleRef.current;
    const volume = volumeRef.current;
    const chart = chartRef.current;
    if (!candles || !volume || !chart || bars.length === 0) return;

    candles.setData(
      bars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })),
    );
    volume.setData(
      bars.map((b) => ({
        time: b.time,
        value: b.volume,
        color: b.close >= b.open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
      })),
    );

    // Only auto-frame while the user hasn't taken over navigation.
    if (!userMovedRef.current) frameToDefault();
  }, [bars]);

  // Re-frame on demand (the per-chart reset button). Separate from the data
  // effect so pressing it doesn't refetch — it's a viewport action only, and
  // leaves the candles, levels and timeframe untouched.
  useEffect(() => {
    if (resetNonce === 0) return;
    userMovedRef.current = false;
    frameToDefault();
  }, [resetNonce]);

  // --- price precision ----------------------------------------------------
  useEffect(() => {
    const candles = candleRef.current;
    if (!candles) return;
    candles.applyOptions({
      priceFormat: {
        type: 'price',
        precision: decimals,
        minMove: tickSize ?? Math.pow(10, -decimals),
      },
    });
  }, [decimals, tickSize]);

  // Compared by value, so a caller passing a fresh array literal each render
  // doesn't cause the level lines to be torn down and rebuilt every time.
  const levelsKey = levels.filter((p) => Number.isFinite(p)).join(',');

  // --- fixed reference levels --------------------------------------------
  useEffect(() => {
    const candles = candleRef.current;
    if (!candles) return;
    for (const line of priceLinesRef.current) candles.removePriceLine(line);
    priceLinesRef.current = (levelsKey === '' ? [] : levelsKey.split(',').map(Number)).map((price) =>
      candles.createPriceLine({
        price,
        color: LEVEL_BLUE,
        lineWidth: 1,
        lineStyle: 0,
        axisLabelVisible: true,
        title: '',
      }),
    );
  }, [levelsKey, decimals]);

  const latest = bars.length > 0 ? bars[bars.length - 1] : null;
  const shown = hovered ?? latest;
  const change = shown ? shown.close - shown.open : null;
  const changePct = shown && shown.open !== 0 ? ((shown.close - shown.open) / shown.open) * 100 : null;
  const changeColor = change == null || change === 0 ? MUTED : change > 0 ? UP : DOWN;

  const stamp = useMemo(() => {
    if (!shown) return '';
    const d = new Date(shown.time * 1000);
    return IS_INTRADAY[interval]
      ? d.toLocaleString('en-GB', {
          weekday: 'short', day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
        })
      : d.toLocaleDateString('en-GB', {
          day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',
        });
  }, [shown, interval]);

  const px = (n: number | null | undefined) =>
    n == null || !Number.isFinite(n) ? '—' : n.toFixed(decimals);

  return (
    <div
      style={{
        backgroundColor: '#141414',
        border: '1px solid #262626',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minHeight: 0,
        height: '100%',
      }}
    >
      {/* header: contract + timeframe switch */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 8px', backgroundColor: '#1a1a1a', borderBottom: '1px solid #262626', flexShrink: 0 }}>
        <span style={{ color: TEXT, fontWeight: 'bold', letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {title}
        </span>
        <div style={{ display: 'flex', gap: '3px', flexShrink: 0 }}>
          {INTERVALS.map((iv) => (
            <button
              key={iv}
              onClick={() => setInterval_(iv)}
              style={{
                padding: '2px 7px',
                fontSize: '10px',
                fontWeight: 'bold',
                fontFamily: 'inherit',
                borderRadius: '3px',
                border: '1px solid ' + (interval === iv ? '#3a3a3a' : '#262626'),
                backgroundColor: interval === iv ? '#2a2a2a' : 'transparent',
                color: interval === iv ? '#e5e5e5' : MUTED,
                cursor: 'pointer',
              }}
            >
              {iv}
            </button>
          ))}
          {/* Per-chart view reset. Scoped to this chart's own viewport —
              siblings are untouched — and it does not change the selected
              timeframe, refetch, or move the reference levels. */}
          <button
            onClick={() => setResetNonce((n) => n + 1)}
            title="Reset this chart's view"
            aria-label="Reset this chart's view"
            data-testid="chart-reset"
            data-instrument={instrument}
            style={{
              marginLeft: '4px',
              padding: '2px 7px',
              fontSize: '11px',
              lineHeight: 1.1,
              fontFamily: 'inherit',
              borderRadius: '3px',
              border: '1px solid #262626',
              backgroundColor: 'transparent',
              color: MUTED,
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = '#e5e5e5'; e.currentTarget.style.borderColor = '#3a3a3a'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = MUTED; e.currentTarget.style.borderColor = '#262626'; }}
          >
            ⟲
          </button>
        </div>
      </div>

      {/* OHLC readout for the hovered candle (or the latest when not hovering) */}
      <div
        data-testid="ohlc-readout"
        data-instrument={instrument}
        // Stays on ONE line at every panel width. Wrapping to a second row
        // (which it did below ~500px of panel width, i.e. any zoomed-in view)
        // doubled this strip's height and stole it from the chart. Instead the
        // numbers are pinned and the timestamp is the only flexible item, so
        // it ellipsises away first and O/H/L/C/V never move or get clipped.
        style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'nowrap', whiteSpace: 'nowrap', overflow: 'hidden', padding: '3px 8px', fontSize: '10px', fontVariantNumeric: 'tabular-nums', color: MUTED, borderBottom: '1px solid #1c1c1c', minHeight: '18px', flexShrink: 0 }}
      >
        {shown ? (
          <>
            <span style={{ color: '#8a8a8a', flex: '0 1 auto', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{stamp}</span>
            <span style={{ flexShrink: 0 }}>O <span style={{ color: TEXT }}>{px(shown.open)}</span></span>
            <span style={{ flexShrink: 0 }}>H <span style={{ color: TEXT }}>{px(shown.high)}</span></span>
            <span style={{ flexShrink: 0 }}>L <span style={{ color: TEXT }}>{px(shown.low)}</span></span>
            <span style={{ flexShrink: 0 }}>C <span style={{ color: TEXT }}>{px(shown.close)}</span></span>
            <span style={{ flexShrink: 0 }}>V <span style={{ color: TEXT }}>{fmtVolume(shown.volume)}</span></span>
            <span style={{ color: changeColor, flexShrink: 0 }}>
              {change == null ? '—' : (change > 0 ? '+' : '') + change.toFixed(decimals)}
              {changePct != null && ` (${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%)`}
            </span>
          </>
        ) : (
          <span>&nbsp;</span>
        )}
      </div>

      {/* chart viewport — the library owns all interaction inside here */}
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
        {(loading || error || (!loading && bars.length === 0)) && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              // Let a background refresh stay non-blocking once candles exist.
              backgroundColor: bars.length > 0 ? 'transparent' : BG,
              pointerEvents: 'none',
              color: error ? DOWN : MUTED,
              fontSize: '11px',
            }}
          >
            {error
              ? `Unable to load historical data (${error})`
              : loading && bars.length === 0
                ? `Loading ${interval} data…`
                : !loading && bars.length === 0
                  ? 'No history yet'
                  : ''}
          </div>
        )}
      </div>
    </div>
  );
}
