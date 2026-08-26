"""FastAPI application — WS + REST endpoints, lifecycle wiring."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..alerts.engine import AlertEngine
from ..analytics.curve_history import CurveHistoryStore
from ..analytics.curve_stats_engine import CurveStatsEngine
from ..analytics.engine import AnalyticsEngine
from ..analytics.historical_correlation import HistoricalCorrelationCache
from ..config import (
    ALL_CONTRACTS,
    CURVE_CORRELATION_HISTORY_DIR,
    CURVE_HISTORY_BAR_SEC,
    CURVE_HISTORY_DIR,
    CURVE_HISTORY_WINDOW_DAYS,
    ER3_NAMES,
    SA3_NAMES,
    SO3_NAMES,
    SR3_NAMES,
)
from ..curves.registry import CURVES, INSTRUMENT_TO_CURVE
from ..streaming.lightstreamer_client import LightstreamerStreamer
from ..streaming.state import MarketState
from ..websocket.hub import WSHub
from .curves_routes import router as curves_router
from .custom_structure_routes import router as custom_structure_router
from .historical_routes import router as historical_router
from .inter_product_routes import router as inter_product_router

log = logging.getLogger(__name__)


class AppCtx:
    state: MarketState
    hub: WSHub
    streamer: LightstreamerStreamer
    analytics: AnalyticsEngine
    alerts: AlertEngine
    tick_queue: asyncio.Queue
    tick_pump_task: asyncio.Task | None = None
    curve_histories: dict[str, CurveHistoryStore]
    curve_stats_engines: dict[str, CurveStatsEngine]
    curve_correlation_cache: HistoricalCorrelationCache


ctx = AppCtx()


async def _tick_pump() -> None:
    """Drain the tick queue and broadcast batched ticks to WS clients.
    Batches up to ~50ms of ticks into a single message to reduce overhead."""
    while True:
        batch: list[dict] = []
        try:
            first = await ctx.tick_queue.get()
            batch.append(first)
        except asyncio.CancelledError:
            return
        # Drain pending without waiting.
        try:
            await asyncio.wait_for(asyncio.sleep(0.05), timeout=0.05)
        except asyncio.TimeoutError:
            pass
        while not ctx.tick_queue.empty() and len(batch) < 500:
            try:
                batch.append(ctx.tick_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        for item in batch:
            price = item.get("price")
            curve_id = INSTRUMENT_TO_CURVE.get(item["instrument"])
            if curve_id and price is not None:
                store = ctx.curve_histories.get(curve_id)
                if store is not None:
                    store.on_tick(
                        item["instrument"],
                        datetime.fromisoformat(item["ts"]),
                        price,
                        item.get("volume"),
                    )
        await ctx.hub.broadcast({"type": "tick", "payload": batch})


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    ctx.state = MarketState()
    ctx.hub = WSHub()
    ctx.tick_queue = asyncio.Queue(maxsize=10_000)
    loop = asyncio.get_running_loop()

    use_mock = os.environ.get("RV_MOCK", "").lower() in ("1", "true", "yes")
    ctx.streamer = LightstreamerStreamer(ctx.state, ctx.tick_queue, loop, mock=use_mock)
    ctx.alerts = AlertEngine(ctx.hub.broadcast)
    ctx.analytics = AnalyticsEngine(ctx.state, ctx.hub.broadcast,
                                    on_compute=ctx.alerts.on_analytics)
    ctx.curve_correlation_cache = HistoricalCorrelationCache(CURVE_CORRELATION_HISTORY_DIR)

    # Mock ticks are synthetic random-walk prices. Persisting them into the
    # live history cache silently poisons every downstream consumer (charts,
    # correlation/beta tables) with prints that never traded, and they're
    # indistinguishable from real bars once on disk — so mock runs get their
    # own directory rather than sharing the live one.
    history_root = CURVE_HISTORY_DIR.parent / "curve_history_mock" if use_mock else CURVE_HISTORY_DIR
    if use_mock:
        log.warning("RV_MOCK enabled — curve history will be written to %s", history_root)

    ctx.curve_histories = {}
    ctx.curve_stats_engines = {}
    for curve_id, spec in CURVES.items():
        store = CurveHistoryStore(
            spec.all_instruments(),
            history_root / curve_id,
            bar_sec=CURVE_HISTORY_BAR_SEC,
            window_days=CURVE_HISTORY_WINDOW_DAYS,
        )
        try:
            from ..data.historical_loader import backfill_curve_from_historical_api

            written = backfill_curve_from_historical_api(store, spec)
            log.info("curve history backfill for %s: seeded %d instruments", curve_id, len(written))
        except Exception:  # noqa: BLE001
            log.exception(
                "curve history backfill failed for %s (continuing with live-only history)", curve_id
            )
        engine = CurveStatsEngine(spec, store, ctx.hub.broadcast)
        ctx.curve_histories[curve_id] = store
        ctx.curve_stats_engines[curve_id] = engine
        engine.start()

    ctx.streamer.start()
    ctx.analytics.start()
    ctx.tick_pump_task = asyncio.create_task(_tick_pump(), name="tick-pump")

    log.info("RV platform started. contracts=%d mock=%s", len(ALL_CONTRACTS), use_mock)
    try:
        yield
    finally:
        if ctx.tick_pump_task:
            ctx.tick_pump_task.cancel()
        await ctx.analytics.stop()
        for engine in ctx.curve_stats_engines.values():
            await engine.stop()
        for store in ctx.curve_histories.values():
            store.persist_all()
        ctx.streamer.stop()
        log.info("RV platform stopped.")


app = FastAPI(title="SA3/ER3 RV Analytics", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(historical_router)
app.include_router(curves_router)
app.include_router(custom_structure_router)
app.include_router(inter_product_router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "stream_status": ctx.streamer.status,
        "clients": ctx.hub.client_count,
        "tick_count": ctx.state.tick_count,
        "last_tick_at": ctx.state.last_tick_at.isoformat() if ctx.state.last_tick_at else None,
        "analytics_ms": ctx.analytics.last_compute_ms,
    }


@app.get("/api/contracts")
async def contracts():
    return {"SA3": SA3_NAMES, "ER3": ER3_NAMES, "I": CURVES["I"].outrights, "SR3": SR3_NAMES, "SO3": SO3_NAMES}


@app.get("/api/quotes")
async def quotes():
    return ctx.state.snapshot_quotes()


@app.get("/api/analytics")
async def analytics_snapshot():
    return JSONResponse(ctx.analytics.last_payload or {})


@app.get("/api/alerts")
async def alerts():
    return list(ctx.alerts.recent)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await ctx.hub.add(ws)
    try:
        # Initial snapshot.
        await ctx.hub.send(ws, {"type": "snapshot", "payload": {
            "quotes": ctx.state.snapshot_quotes(),
            "analytics": ctx.analytics.last_payload or {},
            "alerts": list(ctx.alerts.recent),
            "contracts": {
                "SA3": SA3_NAMES,
                "ER3": ER3_NAMES,
                "I": CURVES["I"].outrights,
                "SR3": SR3_NAMES,
                "SO3": SO3_NAMES,
            },
            "stream_status": ctx.streamer.status,
        }})
        while True:
            # Keep the socket open; ignore client messages (pings handled by ASGI).
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        log.exception("ws session error")
    finally:
        await ctx.hub.remove(ws)
