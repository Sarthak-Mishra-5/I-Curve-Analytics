"""REST endpoints for historical data queries and analytics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Query
import pandas as pd

router = APIRouter(prefix="/api/historical", tags=["historical"])


@router.get("/fetch")
async def fetch_historical(
    instruments: str = Query(..., description="Comma-separated contract codes, e.g., 'H26,M26,U26'"),
    interval: str = Query("1H", description="Interval: 1H, 1D, 1M, 5M"),
    days_back: int = Query(30, description="Days to fetch back from today"),
) -> dict:
    """Fetch and cache historical data from the API."""
    from ..config import SA3_NAMES, ER3_NAMES
    from ..data.historical_api import fetch_historical_ohlc, cache_to_csv

    # Validate and normalize contracts.
    all_names = SA3_NAMES + ER3_NAMES
    requested = [c.strip().upper() for c in instruments.split(",")]
    invalid = [c for c in requested if c not in all_names]
    if invalid:
        return {"error": f"Invalid contracts: {invalid}"}

    # Fetch from API.
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    try:
        df = fetch_historical_ohlc(requested, interval, start_date, end_date)

        # Cache to disk.
        cache_dir = Path(__file__).parent.parent.parent / "data_cache"
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f"historical_{interval}_{days_back}d.csv"
        cache_to_csv(df, cache_file)

        return {
            "status": "success",
            "instruments": requested,
            "interval": interval,
            "rows": len(df),
            "cached_at": cache_file.as_posix(),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/backfill")
async def backfill_state(
    cache_file: str | None = Query(None, description="Path to cached CSV (relative to data_cache/)")
) -> dict:
    """Load historical data into MarketState for analysis.

    If cache_file is not provided, loads the most recent cache.
    """
    from .app import ctx
    from ..data.historical_loader import backfill_from_csv

    try:
        if cache_file:
            csv_path = Path(__file__).parent.parent.parent / "data_cache" / cache_file
        else:
            # Find most recent cache.
            cache_dir = Path(__file__).parent.parent.parent / "data_cache"
            if not cache_dir.exists():
                return {"error": "No cache directory found"}
            csvs = sorted(cache_dir.glob("historical_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not csvs:
                return {"error": "No cached historical data found"}
            csv_path = csvs[0]

        ticks_ingested = backfill_from_csv(ctx.state, csv_path)

        return {
            "status": "success",
            "ticks_ingested": ticks_ingested,
            "buffer_size": ctx.state._buffer_size,
            "tick_count_total": ctx.state.tick_count,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/correlation")
async def correlation_matrix(
    top_n: int = Query(6, description="Number of tenors per product")
) -> dict:
    """Compute rolling correlation matrix from historical state."""
    from .app import ctx
    from ..analytics.correlation import compute_correlation

    result = compute_correlation(ctx.state, top_n=top_n)
    return result


@router.get("/regression")
async def regression_analytics() -> dict:
    """Compute pair-by-tenor OLS regressions from historical state."""
    from .app import ctx
    from ..analytics.regression import compute_regressions

    regressions = compute_regressions(ctx.state)
    return {
        "regressions": regressions,
        "count": len(regressions),
    }


@router.get("/state/summary")
async def state_summary() -> dict:
    """Summary stats on current MarketState (buffer occupancy, etc.)."""
    from .app import ctx
    from ..config import SA3_NAMES, ER3_NAMES

    summary = {}
    for name in SA3_NAMES + ER3_NAMES:
        prices = ctx.state.prices(name)
        summary[name] = {
            "buffer_size": len(prices),
            "latest_price": float(prices[-1]) if len(prices) > 0 else None,
        }

    return {
        "total_instruments": len(summary),
        "total_ticks": ctx.state.tick_count,
        "instruments": summary,
    }
