"""Lightstreamer streaming client — bridges into MarketState + async tick queue.

Modeled on the user's reference PyQt snippet but stripped of Qt and reshaped
to push ticks into an asyncio.Queue consumed by the FastAPI app.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from ..config import (
    ADAPTER_SET,
    ALL_CONTRACTS,
    DATA_ADAPTER,
    FIELD_NAMES,
    LIVE_PRICE_SCALE,
    SERVER_URL,
)
from .state import MarketState
from .utils import derive_price, normalize_contract_id, parse_timestamp_from_values, rescale_price_fields

log = logging.getLogger(__name__)

try:
    from lightstreamer.client import LightstreamerClient, Subscription  # type: ignore
    _LS_AVAILABLE = True
except Exception:  # noqa: BLE001
    LightstreamerClient = None  # type: ignore
    Subscription = None  # type: ignore
    _LS_AVAILABLE = False


class _SubListener:
    """Lightstreamer SubscriptionListener — invoked on the LS thread."""

    def __init__(self, state: MarketState, push_tick) -> None:
        self._state = state
        self._push_tick = push_tick

    def onItemUpdate(self, update) -> None:  # noqa: N802 (LS API)
        try:
            values = {f: update.getValue(f) for f in FIELD_NAMES}
            item_name = update.getItemName() or ""
            iid_candidate = normalize_contract_id(values.get("InstrumentId") or item_name)
            name = MarketState.name_from_instrument_id(iid_candidate)
            if name is None:
                # Fallback: try the item_name itself (defensive)
                name = MarketState.name_from_instrument_id(normalize_contract_id(item_name))
            if name is None:
                return

            scale = LIVE_PRICE_SCALE.get(name.split()[0])
            if scale is not None:
                values = rescale_price_fields(values, scale)

            price = derive_price(values)
            if price is None:
                return
            ts = parse_timestamp_from_values(values)
            q = self._state.apply_tick(name, values, price, ts)
            self._push_tick(q.to_dict())
        except Exception:  # noqa: BLE001
            log.exception("LS update handler failed")

    # The LS SubscriptionListener protocol is duck-typed — extra no-ops below
    # avoid AttributeError warnings on older SDK versions.
    def onSubscription(self): pass        # noqa: N802
    def onUnsubscription(self): pass      # noqa: N802
    def onSubscriptionError(self, code, message): log.warning("LS sub error: %s %s", code, message)  # noqa: N802
    def onItemLostUpdates(self, item_name, item_pos, lost_updates):  # noqa: N802
        log.warning("LS lost %s updates on %s", lost_updates, item_name)
    def onClearSnapshot(self, item_name, item_pos): pass  # noqa: N802
    def onEndOfSnapshot(self, item_name, item_pos): pass  # noqa: N802
    def onCommandSecondLevelItemLostUpdates(self, lost, key): pass  # noqa: N802
    def onCommandSecondLevelSubscriptionError(self, code, message, key): pass  # noqa: N802
    def onRealMaxFrequency(self, freq): pass  # noqa: N802


class LightstreamerStreamer:
    """Owns the LS client lifecycle in a background thread.

    Bridges into an asyncio.Queue (thread-safe via loop.call_soon_threadsafe)
    so the FastAPI WS broadcaster can fan out ticks.
    """

    def __init__(
        self,
        state: MarketState,
        out_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        mock: bool = False,
    ) -> None:
        self.state = state
        self._queue = out_queue
        self._loop = loop
        self._mock = mock or not _LS_AVAILABLE
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ls_client = None
        self._sub = None
        self.status: str = "INIT"

    # --- public --------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        target = self._run_mock if self._mock else self._run_live
        self._thread = threading.Thread(target=target, name="ls-streamer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._cleanup()

    # --- queue bridge --------------------------------------------------------
    def _push(self, tick: dict) -> None:
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, tick)
        except RuntimeError:
            pass  # loop closed during shutdown

    # --- live ---------------------------------------------------------------
    def _run_live(self) -> None:
        assert LightstreamerClient is not None and Subscription is not None
        backoff = 1.0
        while not self._stop.is_set():
            try:
                self.status = "CONNECTING"
                log.info("LS connecting to %s adapter_set=%s", SERVER_URL, ADAPTER_SET)
                self._ls_client = LightstreamerClient(SERVER_URL, ADAPTER_SET)
                self._ls_client.connect()

                items = [f"TT-{iid}" for _, iid in ALL_CONTRACTS]
                self._sub = Subscription("MERGE", items, FIELD_NAMES)
                self._sub.setDataAdapter(DATA_ADAPTER)
                self._sub.setRequestedMaxFrequency("0.5")
                self._sub.setRequestedSnapshot("yes")
                listener = _SubListener(self.state, self._push)
                self._sub.addListener(listener)
                self._ls_client.subscribe(self._sub)

                self.status = "LIVE"
                backoff = 1.0
                while not self._stop.is_set():
                    time.sleep(0.2)
            except Exception as exc:  # noqa: BLE001
                self.status = f"ERROR: {exc}"
                log.exception("LS streamer error — reconnecting in %.1fs", backoff)
                self._cleanup()
                slept = 0.0
                while slept < backoff and not self._stop.is_set():
                    time.sleep(0.2)
                    slept += 0.2
                backoff = min(backoff * 2, 30.0)
        self.status = "STOPPED"

    # --- mock ---------------------------------------------------------------
    def _run_mock(self) -> None:
        """Synthetic tick generator for offline development.

        Every contract's move is one shared per-product shock (so adjacent
        quarters on the same curve track each other tightly, the way real
        STIR curves do) plus a small idiosyncratic residual, and every
        contract on a product now starts from that product's own single seed
        level rather than its own independently-drawn one. A previous
        version gave every one of the ~300 ALL_CONTRACTS entries both a
        fully independent starting level AND a fully independent random
        walk — with no shared component, a calendar spread/fly (whose
        weights sum to zero) ends up with MORE combined variance than a
        single outright instead of much less, since uncorrelated noise adds
        rather than cancelling. Fixing only the per-tick walk wasn't enough
        on its own: mean reversion here is deliberately slow (so a single
        tick doesn't overwhelm the curve), so two legs seeded a couple of
        points apart could take thousands of ticks to converge, producing
        exactly the kind of large, slowly-decaying spread/fly excursion this
        was meant to fix. Seeding every contract on a product from the same
        starting level removes that transient outright.
        """
        import random

        self.status = "LIVE (MOCK)"
        products = sorted({name.split()[0] for name, _ in ALL_CONTRACTS})
        # Reasonable seed levels: SARON/€STR 3M futures roughly 96.50–99.50.
        # One draw per product — every contract on that curve starts here.
        product_seed = {p: random.uniform(96.5, 99.5) for p in products}
        base = {name: product_seed[name.split()[0]] for name, _ in ALL_CONTRACTS}
        # Add a small curve slope so the curve panel is interesting.
        for name in base:
            order = sum(c.isdigit() for c in name)
            base[name] += order * 0.01

        while not self._stop.is_set():
            # One shock per product per round, shared by every contract on
            # that curve — this is what keeps a spread/fly's legs moving
            # together instead of drifting apart independently.
            product_shock = {p: random.gauss(0, 0.006) for p in products}
            for name, _iid in ALL_CONTRACTS:
                if self._stop.is_set():
                    break
                # Mean-reverting random walk: shared curve-level shock plus a
                # much smaller idiosyncratic residual per contract.
                prev = base[name]
                drift = (98.0 - prev) * 0.001
                shock = product_shock[name.split()[0]] + random.gauss(0, 0.0008)
                base[name] = prev + drift + shock
                mid = base[name]
                bid = round(mid - 0.0025, 4)
                ask = round(mid + 0.0025, 4)
                ts = datetime.now(timezone.utc)
                values = {
                    "BestBid": bid,
                    "BestAsk": ask,
                    "BestBidQty": random.randint(1, 50),
                    "BestAskQty": random.randint(1, 50),
                    "Last": round(mid, 4),
                    "LastQty": random.randint(1, 20),
                    "Price": round(mid, 4),
                    "Volume": random.randint(100, 10000),
                    "Settle": round(mid, 4),
                    "PrevSettle": round(mid - 0.01, 4),
                    "Exchange": "MOCK",
                    "Contract": name,
                    "Product": name.split()[0],
                }
                q = self.state.apply_tick(name, values, mid, ts)
                self._push(q.to_dict())
            time.sleep(0.5)
        self.status = "STOPPED"

    def _cleanup(self) -> None:
        try:
            if self._ls_client and self._sub:
                self._ls_client.unsubscribe(self._sub)
        except Exception:
            pass
        try:
            if self._ls_client:
                self._ls_client.disconnect()
        except Exception:
            pass
        self._ls_client = None
        self._sub = None
