"""Persistent, calendar-time rolling history for curve instruments.

MarketState's rolling buffers are tick-count bounded and reset on restart —
fine for the existing 1Hz analytics, but not for a true 30-calendar-day
statistical window. CurveHistoryStore keeps one fixed-resolution bar series
per instrument, persisted to disk so the window survives restarts, and
evicts anything older than the window.

Each bar records true OHLCV observed across the bucket, not just a closing
sample: open/high/low/close are tracked from the individual ticks that fell
inside the bucket, and volume is the increase in the feed's cumulative
session volume over that bucket. The statistical readers (`window`,
`bars_map`, `paired_window`) project the close, so their contract is
unchanged; `ohlcv_window` exposes the full candles for charting.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

log = logging.getLogger(__name__)

# Sanity guard against feed glitches (e.g. a spread/fly instrument briefly
# receiving an outright-scale price): no outright, spread, or fly on these
# curves plausibly moves this many points in a single bar. Gated on the last
# known price being recent — after a long gap (market closure, restart), a
# genuinely large move shouldn't be rejected forever.
MAX_PLAUSIBLE_JUMP = 20.0
STALE_REFERENCE_SEC = 86400  # 1 day

# Internal bar layout: (bucket_ts, open, high, low, close, volume).
_T, _O, _H, _L, _C, _V = range(6)


def _safe_filename(instrument: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in instrument) + ".jsonl"


class CurveHistoryStore:
    """Fixed-resolution (bar_sec) OHLCV bars per instrument, capped to
    window_days and persisted as one append-only JSONL file per instrument."""

    def __init__(
        self,
        instruments: list[str],
        persist_dir: Path,
        bar_sec: int = 60,
        window_days: int = 30,
    ) -> None:
        self._lock = threading.RLock()
        self._bar_sec = bar_sec
        self._window_sec = window_days * 86400
        self._dir = Path(persist_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

        # Closed, persisted bars: instrument -> deque[(t, o, h, l, c, v)], ascending.
        self._bars: dict[str, deque[tuple[float, float, float, float, float, float]]] = {
            n: deque() for n in instruments
        }
        # Currently-open (not yet closed/persisted) bar: instrument -> [t, o, h, l, c, v].
        self._open: dict[str, list[float]] = {}
        # Last cumulative session volume seen per instrument, for per-bar deltas.
        self._last_cum_vol: dict[str, float] = {}

        self._load_all(instruments)

    # --- ingestion --------------------------------------------------------
    def on_tick(
        self, instrument: str, ts: datetime, price: float, volume: float | None = None
    ) -> None:
        """Call once per raw tick. O(1) amortized.

        `volume` is the feed's cumulative session volume; the per-bar volume
        is accumulated from its increments, so a session reset (cumulative
        value going backwards) contributes nothing rather than a negative.
        """
        if instrument not in self._bars:
            return
        bucket = self._bucket_ts(ts)
        with self._lock:
            if self._is_implausible(instrument, bucket, price):
                log.warning(
                    "rejecting implausible tick for %s: price=%.6g bucket=%s", instrument, price, bucket
                )
                return

            dv = 0.0
            if volume is not None:
                prev_cum = self._last_cum_vol.get(instrument)
                if prev_cum is not None and volume >= prev_cum:
                    dv = volume - prev_cum
                self._last_cum_vol[instrument] = volume

            open_bar = self._open.get(instrument)
            if open_bar is None:
                self._open[instrument] = [bucket, price, price, price, price, dv]
                return
            if bucket == open_bar[_T]:
                # Still inside the same bucket — extend the forming candle.
                open_bar[_H] = max(open_bar[_H], price)
                open_bar[_L] = min(open_bar[_L], price)
                open_bar[_C] = price
                open_bar[_V] += dv
                return
            if bucket > open_bar[_T]:
                self._commit_bar(instrument, tuple(open_bar))  # type: ignore[arg-type]
                self._open[instrument] = [bucket, price, price, price, price, dv]
            # bucket < open_bar[_T] (out-of-order/late tick) — ignore, keep current bar.

    def _is_implausible(self, instrument: str, bucket: float, price: float) -> bool:
        """True if `price` is an implausible jump from the last known price
        for `instrument` (the open bar's running close, or else the last
        committed bar's close) — the guard against the kind of feed glitch
        that once put an outright-scale print into a spread/fly's history.
        Skipped if that reference is stale, so a genuinely large move across
        a long gap (closure, restart) isn't rejected forever."""
        open_bar = self._open.get(instrument)
        if open_bar is not None:
            ref_ts, ref_price = open_bar[_T], open_bar[_C]
        else:
            buf = self._bars.get(instrument)
            if not buf:
                return False
            ref_ts, ref_price = buf[-1][_T], buf[-1][_C]
        if bucket - ref_ts > STALE_REFERENCE_SEC:
            return False
        return abs(price - ref_price) > MAX_PLAUSIBLE_JUMP

    def flush_stale(self, now: datetime | None = None) -> None:
        """Force-close any open bar whose bucket has fully elapsed, even if no
        new tick has arrived. Call at the top of each stats cycle."""
        now = now or datetime.now(timezone.utc)
        current_bucket = self._bucket_ts(now)
        with self._lock:
            for instrument, open_bar in list(self._open.items()):
                if open_bar[_T] < current_bucket:
                    self._commit_bar(instrument, tuple(open_bar))  # type: ignore[arg-type]
                    del self._open[instrument]

    def _bucket_ts(self, ts: datetime) -> float:
        epoch = ts.timestamp()
        return (epoch // self._bar_sec) * self._bar_sec

    def _commit_bar(
        self, instrument: str, bar: tuple[float, float, float, float, float, float]
    ) -> None:
        buf = self._bars.setdefault(instrument, deque())
        buf.append(bar)
        self._evict_stale(instrument, bar[_T])
        self._append_to_disk(instrument, bar)

    def _evict_stale(self, instrument: str, now_bucket: float) -> None:
        buf = self._bars[instrument]
        cutoff = now_bucket - self._window_sec
        while buf and buf[0][_T] < cutoff:
            buf.popleft()

    # --- reads --------------------------------------------------------------
    def window(self, instrument: str) -> tuple[np.ndarray, np.ndarray]:
        """(timestamps [unix sec], close prices), ascending, trimmed to window_days."""
        with self._lock:
            buf = self._bars.get(instrument)
            if not buf:
                return np.empty(0), np.empty(0)
            arr = np.array(buf, dtype=np.float64)
            return arr[:, _T], arr[:, _C]

    def ohlcv_window(
        self, instrument: str, include_open: bool = True
    ) -> list[tuple[float, float, float, float, float, float]]:
        """Full (t, o, h, l, c, v) bars, ascending. When `include_open`, the
        still-forming bar is appended so a live chart's most recent candle
        reflects the current price rather than lagging by up to bar_sec."""
        with self._lock:
            bars = list(self._bars.get(instrument, ()))
            if include_open:
                open_bar = self._open.get(instrument)
                if open_bar is not None:
                    bars.append(tuple(open_bar))  # type: ignore[arg-type]
        return bars

    def bars_map(self, instrument: str) -> dict[float, float]:
        """All closed bars for `instrument` as {bucket_ts: close}. Used for
        N-way joins (more than two instruments) — see
        analytics/custom_structure.py — where paired_window's 2-series join
        doesn't apply."""
        with self._lock:
            return {b[_T]: b[_C] for b in self._bars.get(instrument, ())}

    def paired_window(self, prev: str, curr: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Inner-join prev/curr on shared bucket timestamp. Because both series
        sit on the same fixed bar_sec grid, matching on the bucket key IS the
        timestamp-tolerant join (tolerance = bar_sec)."""
        with self._lock:
            pa = {b[_T]: b[_C] for b in self._bars.get(prev, ())}
            pb = {b[_T]: b[_C] for b in self._bars.get(curr, ())}
        shared = sorted(set(pa) & set(pb))
        if not shared:
            return np.empty(0), np.empty(0), np.empty(0)
        ts = np.array(shared, dtype=np.float64)
        pv = np.array([pa[t] for t in shared], dtype=np.float64)
        cv = np.array([pb[t] for t in shared], dtype=np.float64)
        return ts, pv, cv

    # --- backfill seam ------------------------------------------------------
    def seed_from(self, instrument: str, rows: Iterable[tuple[datetime, float]]) -> int:
        """Backfill hook for the historical-data source. Buckets `rows` the
        same way live ticks are bucketed; a bucket already populated by a
        live tick is left untouched (live data wins on overlap). Historical
        rows carry a single close price, so the seeded bar is flat
        (o=h=l=c) with zero volume. Returns the number of buckets written."""
        if instrument not in self._bars:
            return 0
        written = 0
        with self._lock:
            existing = {b[_T] for b in self._bars[instrument]}
            new_bars: dict[float, float] = {}
            for ts, price in rows:
                bucket = self._bucket_ts(ts)
                if bucket in existing:
                    continue
                new_bars[bucket] = price  # last write per bucket wins among seeded rows
            if not new_bars:
                return 0
            buf = self._bars[instrument]
            for bucket, price in new_bars.items():
                buf.append((bucket, price, price, price, price, 0.0))
                written += 1
            merged = sorted(buf)
            buf.clear()
            buf.extend(merged)
            if merged:
                self._evict_stale(instrument, merged[-1][_T])
            self._rewrite_disk(instrument)
        return written

    # --- persistence ---------------------------------------------------------
    def _path_for(self, instrument: str) -> Path:
        return self._dir / _safe_filename(instrument)

    @staticmethod
    def _encode(bar: tuple[float, float, float, float, float, float]) -> str:
        return json.dumps(
            {
                "t": bar[_T],
                "o": bar[_O],
                "h": bar[_H],
                "l": bar[_L],
                "c": bar[_C],
                "v": bar[_V],
            }
        )

    def _append_to_disk(
        self, instrument: str, bar: tuple[float, float, float, float, float, float]
    ) -> None:
        try:
            with open(self._path_for(instrument), "a", encoding="utf-8") as f:
                f.write(self._encode(bar) + "\n")
        except OSError:
            log.exception("failed to append curve history bar for %s", instrument)

    def _rewrite_disk(self, instrument: str) -> None:
        """Atomically rewrite an instrument's file from its in-memory deque
        (used after seed_from merges out-of-order rows)."""
        path = self._path_for(instrument)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                for bar in self._bars[instrument]:
                    f.write(self._encode(bar) + "\n")
            os.replace(tmp, path)
        except OSError:
            log.exception("failed to rewrite curve history file for %s", instrument)

    def persist_all(self) -> None:
        """Flush any still-open bars to disk and compact each file (dedupe by
        bucket, drop stale rows). Call on shutdown and periodically."""
        with self._lock:
            now = datetime.now(timezone.utc)
            for instrument, open_bar in list(self._open.items()):
                self._commit_bar(instrument, tuple(open_bar))  # type: ignore[arg-type]
            self._open.clear()
            for instrument in self._bars:
                self._evict_stale(instrument, self._bucket_ts(now))
                self._rewrite_disk(instrument)

    @staticmethod
    def _decode(row: dict) -> tuple[float, float, float, float, float, float]:
        """Parse one persisted row. Files written before OHLCV tracking hold
        a single last price as {"t", "p"} — read those as a flat bar so the
        existing on-disk window stays usable."""
        t = float(row["t"])
        if "c" in row:
            close = float(row["c"])
            return (
                t,
                float(row.get("o", close)),
                float(row.get("h", close)),
                float(row.get("l", close)),
                close,
                float(row.get("v", 0.0) or 0.0),
            )
        p = float(row["p"])
        return (t, p, p, p, p, 0.0)

    def _load_all(self, instruments: list[str]) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - self._window_sec
        for instrument in instruments:
            path = self._path_for(instrument)
            if not path.exists():
                continue
            bars: dict[float, tuple[float, float, float, float, float, float]] = {}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            bar = self._decode(json.loads(line))
                        except (ValueError, KeyError, TypeError):
                            continue
                        if bar[_T] >= cutoff:
                            bars[bar[_T]] = bar  # later line for same bucket wins
            except OSError:
                log.exception("failed to load curve history for %s", instrument)
                continue
            self._bars[instrument] = deque(bars[t] for t in sorted(bars))
