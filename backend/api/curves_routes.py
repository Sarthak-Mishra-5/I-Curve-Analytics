"""Generic REST endpoints for curve configs, live stats snapshots, and history."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..config import CHART_INTERVAL_SOURCE, TICK_SIZE
from ..curves.registry import get_curve, list_curves

router = APIRouter(prefix="/api/curves", tags=["curves"])

# Bucket width per UI timeframe, used when aggregating whatever source series
# backs it (see config.CHART_INTERVAL_SOURCE).
_CANDLE_INTERVAL_SEC = {name: bucket for name, (_res, bucket) in CHART_INTERVAL_SOURCE.items()}


@router.get("")
async def curves() -> dict:
    return {"curves": list_curves()}


@router.get("/{curve_id}")
async def curve_spec(curve_id: str) -> dict:
    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    return spec.to_dict()


@router.get("/{curve_id}/stats")
async def curve_stats(curve_id: str) -> dict:
    from .app import ctx

    engine = ctx.curve_stats_engines.get(curve_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    return engine.last_payload or {}


@router.get("/{curve_id}/correlation-history")
async def curve_correlation_history(
    curve_id: str,
    category: str = Query(..., description="'3ms' for spreads or '3mf' for flies"),
    current: str = Query(..., description="Current contract display name from the stats table"),
) -> dict:
    from .app import ctx

    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    try:
        return ctx.curve_correlation_cache.get_series(store, spec, category, current)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{curve_id}/history")
async def curve_history(
    curve_id: str,
    instrument: str = Query(..., description="Contract display name, e.g. 'I Sep26'"),
    minutes: int = Query(180, description="Minutes of recent history to return"),
) -> dict:
    from .app import ctx

    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    ts, prices = store.window(instrument)
    if ts.size == 0:
        return {"instrument": instrument, "bars": []}

    cutoff = ts[-1] - minutes * 60
    mask = ts >= cutoff
    bars = [
        {"t": _iso(t), "v": float(v)}
        for t, v in zip(ts[mask].tolist(), prices[mask].tolist())
    ]
    return {"instrument": instrument, "bars": bars}


@router.get("/{curve_id}/candles")
async def curve_candles(
    curve_id: str,
    instrument: str = Query(..., description="Contract display name, e.g. 'SR3 Sep27'"),
    interval: str = Query("30m", description="One of: 5m, 10m, 30m, 1h, 1d"),
) -> dict:
    from .app import ctx

    source_spec = CHART_INTERVAL_SOURCE.get(interval)
    if source_spec is None:
        raise HTTPException(status_code=400, detail=f"unknown interval '{interval}', expected one of {sorted(CHART_INTERVAL_SOURCE)}")
    res_key, bucket_sec = source_spec

    # Prefer the deep chart history at this timeframe's native resolution
    # (real vendor OHLCV, ~20+ days intraday / ~1 year daily). Instruments
    # without one fall back to the 30-day stats store.
    store = ctx.chart_histories.get((instrument, res_key))
    if store is None:
        store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    source = store.ohlcv_window(instrument)
    if not source:
        return {"instrument": instrument, "interval": interval, "bars": []}

    return {
        "instrument": instrument,
        "interval": interval,
        "tick_size": TICK_SIZE.get(instrument.split()[0]),
        "bars": _resample_ohlcv(source, bucket_sec),
    }


# Mirrors CurveHistoryStore's own glitch guard (analytics/curve_history.py) —
# a defensive second line against implausible one-off samples reaching a
# candle (e.g. a stale scale mismatch from the historical-backfill seam),
# applied here at read-time since that seam is a separate code path.
_MAX_PLAUSIBLE_JUMP = 20.0


def _resample_ohlcv(
    source: list[tuple[float, float, float, float, float, float]], bucket_sec: int
) -> list[dict]:
    """Aggregate ascending (t, o, h, l, c, v) base bars into `bucket_sec`-wide
    candles: open of the first bar, running high/low, close of the last, and
    summed volume. Buckets with no base bars are simply absent rather than
    interpolated, so market closures stay as real gaps in the series."""
    bars: list[dict] = []
    bucket: float | None = None
    o = h = l = c = 0.0
    v = 0.0
    last_close: float | None = None

    def flush() -> None:
        if bucket is not None:
            bars.append({"t": _iso(bucket), "o": o, "h": h, "l": l, "c": c, "v": v})

    for t, bo, bh, bl, bc, bv in source:
        if last_close is not None and abs(bc - last_close) > _MAX_PLAUSIBLE_JUMP:
            continue
        last_close = bc
        b = (t // bucket_sec) * bucket_sec
        if b != bucket:
            flush()
            bucket, o, h, l, c, v = b, bo, bh, bl, bc, bv
        else:
            h = max(h, bh)
            l = min(l, bl)
            c = bc
            v += bv
    flush()
    return bars


def _iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).isoformat()
