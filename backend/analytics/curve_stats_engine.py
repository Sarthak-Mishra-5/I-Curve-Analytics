"""Periodic (60s) scheduler that computes and broadcasts a curve's stats tables.

Modeled on AnalyticsEngine (analytics/engine.py): runs off the event loop via
an executor, broadcasts a WS message, sleeps on a cancellable interval.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ..config import CURVE_HISTORY_WINDOW_DAYS, CURVE_STATS_INTERVAL_SEC
from ..curves.registry import CurveSpec
from .curve_history import CurveHistoryStore
from .pair_stats import compute_curve_tables

log = logging.getLogger(__name__)


class CurveStatsEngine:
    def __init__(
        self,
        spec: CurveSpec,
        store: CurveHistoryStore,
        broadcast: Callable[[dict], Awaitable[None]],
        interval_sec: float = CURVE_STATS_INTERVAL_SEC,
    ) -> None:
        self.spec = spec
        self.store = store
        self._broadcast = broadcast
        self.interval_sec = interval_sec
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.last_payload: dict | None = None
        self.last_compute_ms: float = 0.0

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=f"curve-stats-{self.spec.curve_id}")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.wait([self._task], timeout=2)

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                payload = await loop.run_in_executor(None, self._compute_sync)
                payload["compute_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                self.last_compute_ms = payload["compute_ms"]
                self.last_payload = payload
                await self._broadcast({"type": "curve_stats", "payload": payload})
            except Exception:  # noqa: BLE001
                log.exception("curve stats tick failed for %s", self.spec.curve_id)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_sec)
            except asyncio.TimeoutError:
                pass

    def _compute_sync(self) -> dict:
        self.store.flush_stale()
        return {
            "curve_id": self.spec.curve_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_days": CURVE_HISTORY_WINDOW_DAYS,
            "tables": compute_curve_tables(self.store, self.spec),
        }
