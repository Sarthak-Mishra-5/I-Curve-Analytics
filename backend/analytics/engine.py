"""Analytics scheduler — runs all modules at a fixed cadence on the asyncio loop."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

from ..config import ANALYTICS_INTERVAL_SEC
from ..streaming.state import MarketState
from .cointegration import compute_cointegration
from .correlation import compute_correlation
from .curve import compute_curve
from .flies import compute_flies
from .microstructure import compute_microstructure
from .regression import compute_regressions
from .spreads import compute_spreads
from .tick_sensitivity import compute_tick_sensitivity
from .volatility import compute_volatility

log = logging.getLogger(__name__)


class AnalyticsEngine:
    """Runs analytics off the main event loop (executor) and broadcasts results."""

    def __init__(
        self,
        state: MarketState,
        broadcast: Callable[[dict], Awaitable[None]],
        on_compute: Callable[[dict], None] | None = None,
    ) -> None:
        self.state = state
        self._broadcast = broadcast
        self._on_compute = on_compute
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.last_payload: dict | None = None
        self.last_compute_ms: float = 0.0

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="analytics-engine")

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
                if self._on_compute:
                    self._on_compute(payload)
                await self._broadcast({"type": "analytics", "payload": payload})
            except Exception:  # noqa: BLE001
                log.exception("analytics tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=ANALYTICS_INTERVAL_SEC)
            except asyncio.TimeoutError:
                pass

    def _compute_sync(self) -> dict:
        return {
            "spreads": compute_spreads(self.state),
            "flies": compute_flies(self.state),
            "regressions": compute_regressions(self.state),
            "tick_sensitivity": compute_tick_sensitivity(self.state),
            "cointegration": compute_cointegration(self.state),
            "volatility": compute_volatility(self.state),
            "microstructure": compute_microstructure(self.state),
            "curve": compute_curve(self.state),
        }
