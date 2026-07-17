"""Generic REST endpoints for curve configs, live stats snapshots, and history."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..curves.registry import get_curve, list_curves

router = APIRouter(prefix="/api/curves", tags=["curves"])


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


def _iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).isoformat()
