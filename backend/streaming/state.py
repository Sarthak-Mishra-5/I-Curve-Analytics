"""In-memory live market state with per-instrument rolling buffers."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

import numpy as np

from ..config import (
    ALL_CONTRACTS,
    ER3_NAMES,
    INSTRUMENT_ID_TO_NAME,
    ROLLING_BUFFER_SIZE,
    SA3_NAMES,
)


@dataclass
class Quote:
    instrument: str
    bid: float | None = None
    bid_qty: float | None = None
    ask: float | None = None
    ask_qty: float | None = None
    last: float | None = None
    mid: float | None = None
    vwap: float | None = None         # volume-weighted average price, accumulated since process start
    price: float | None = None        # derived per fallback chain
    open_: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    settle: float | None = None
    prev_settle: float | None = None
    volume: float | None = None
    exchange: str = ""
    contract: str = ""
    product: str = ""
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        chg = None
        if self.price is not None and self.prev_settle is not None:
            chg = self.price - self.prev_settle
        return {
            "instrument": self.instrument,
            "bid": self.bid,
            "bid_qty": self.bid_qty,
            "ask": self.ask,
            "ask_qty": self.ask_qty,
            "last": self.last,
            "mid": self.mid,
            "vwap": self.vwap,
            "price": self.price,
            "settle": self.settle,
            "prev_settle": self.prev_settle,
            "open": self.open_,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "net_change": chg,
            "ts": self.ts.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "product": self.product or self.instrument.split()[0],
        }


class MarketState:
    """Thread-safe live state + rolling buffers for analytics."""

    def __init__(self, buffer_size: int = ROLLING_BUFFER_SIZE) -> None:
        self._lock = threading.RLock()
        self._buffer_size = buffer_size
        self.quotes: dict[str, Quote] = {n: Quote(instrument=n) for n, _ in ALL_CONTRACTS}

        # Per-instrument price + timestamp rolling buffers (numpy-backed via deque).
        self._prices: dict[str, deque[float]] = {
            n: deque(maxlen=buffer_size) for n, _ in ALL_CONTRACTS
        }
        self._times: dict[str, deque[float]] = {
            n: deque(maxlen=buffer_size) for n, _ in ALL_CONTRACTS
        }

        # VWAP accumulators (sum of trade_price*trade_qty, sum of trade_qty),
        # accumulated since process start — no session/day boundary concept
        # exists elsewhere in this app, so neither does this.
        self._vwap_pv: dict[str, float] = {n: 0.0 for n, _ in ALL_CONTRACTS}
        self._vwap_v: dict[str, float] = {n: 0.0 for n, _ in ALL_CONTRACTS}

        # Stats
        self.tick_count: int = 0
        self.last_tick_at: datetime | None = None

    # --- ingest ---------------------------------------------------------------
    def apply_tick(
        self,
        instrument: str,
        values: dict,
        price: float,
        ts: datetime,
    ) -> Quote:
        from .utils import safe_float

        with self._lock:
            q = self.quotes.get(instrument)
            if q is None:
                q = Quote(instrument=instrument)
                self.quotes[instrument] = q

            def upd(attr: str, key: str) -> None:
                v = safe_float(values.get(key))
                if v is not None:
                    setattr(q, attr, v)

            upd("bid", "BestBid")
            upd("bid_qty", "BestBidQty")
            upd("ask", "BestAsk")
            upd("ask_qty", "BestAskQty")
            upd("last", "Last")
            upd("open_", "Open")
            upd("high", "High")
            upd("low", "Low")
            upd("close", "Close")
            upd("settle", "Settle")
            upd("prev_settle", "PrevSettle")
            upd("volume", "Volume")

            if q.bid is not None and q.ask is not None:
                q.mid = (q.bid + q.ask) / 2.0

            # VWAP: weight each trade's price by its own size (LastQty), not
            # the feed's cumulative session Volume field.
            last_qty = safe_float(values.get("LastQty"))
            trade_price = q.last if q.last is not None else price
            if last_qty is not None and last_qty > 0 and trade_price is not None:
                self._vwap_pv[instrument] = self._vwap_pv.get(instrument, 0.0) + trade_price * last_qty
                self._vwap_v[instrument] = self._vwap_v.get(instrument, 0.0) + last_qty
                q.vwap = self._vwap_pv[instrument] / self._vwap_v[instrument]

            q.price = price
            q.ts = ts
            q.updated_at = datetime.now(timezone.utc)
            q.exchange = str(values.get("Exchange") or q.exchange)
            q.contract = str(values.get("Contract") or q.contract)
            q.product = str(values.get("Product") or q.product)

            self._prices[instrument].append(float(price))
            self._times[instrument].append(ts.timestamp())
            self.tick_count += 1
            self.last_tick_at = q.updated_at
            return q

    # --- snapshots ------------------------------------------------------------
    def snapshot_quotes(self) -> dict[str, dict]:
        with self._lock:
            return {k: v.to_dict() for k, v in self.quotes.items()}

    def prices(self, instrument: str, n: int | None = None) -> np.ndarray:
        with self._lock:
            buf = self._prices.get(instrument)
            if buf is None or len(buf) == 0:
                return np.empty(0, dtype=np.float64)
            arr = np.fromiter(buf, dtype=np.float64, count=len(buf))
            return arr if n is None else arr[-n:]

    def latest_price(self, instrument: str) -> float | None:
        with self._lock:
            buf = self._prices.get(instrument)
            if not buf:
                q = self.quotes.get(instrument)
                return q.price if q else None
            return buf[-1]

    def aligned_pair(
        self, a: str, b: str, n: int | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the last n element-wise aligned prices for two instruments.
        Alignment is positional (tick index), not timestamp — sufficient for
        the in-memory rolling analytics in v1."""
        with self._lock:
            pa = self._prices.get(a) or deque()
            pb = self._prices.get(b) or deque()
            m = min(len(pa), len(pb))
            if m == 0:
                return np.empty(0), np.empty(0)
            if n is not None:
                m = min(m, n)
            arr_a = np.fromiter(list(pa)[-m:], dtype=np.float64, count=m)
            arr_b = np.fromiter(list(pb)[-m:], dtype=np.float64, count=m)
            return arr_a, arr_b

    @staticmethod
    def name_from_instrument_id(iid: str) -> str | None:
        return INSTRUMENT_ID_TO_NAME.get(iid)

    @staticmethod
    def product_names(product: str) -> Iterable[str]:
        return SA3_NAMES if product.upper() == "SA3" else ER3_NAMES
