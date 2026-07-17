"""Persistent, calendar-time rolling history for curve instruments.

MarketState's rolling buffers are tick-count bounded and reset on restart —
fine for the existing 1Hz analytics, but not for a true 30-calendar-day
statistical window. CurveHistoryStore keeps one fixed-resolution bar series
per instrument, persisted to disk so the window survives restarts, and
evicts anything older than the window.
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


def _safe_filename(instrument: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in instrument) + ".jsonl"


class CurveHistoryStore:
    """Fixed-resolution (bar_sec) last-price bars per instrument, capped to
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

        # Closed, persisted bars: instrument -> deque[(bucket_ts, price)], ascending.
        self._bars: dict[str, deque[tuple[float, float]]] = {n: deque() for n in instruments}
        # Currently-open (not yet closed/persisted) bar: instrument -> [bucket_ts, price].
        self._open: dict[str, list[float]] = {}

        self._load_all(instruments)

    # --- ingestion --------------------------------------------------------
    def on_tick(self, instrument: str, ts: datetime, price: float) -> None:
        """Call once per raw tick. O(1) amortized."""
        if instrument not in self._bars:
            return
        bucket = self._bucket_ts(ts)
        with self._lock:
            if self._is_implausible(instrument, bucket, price):
                log.warning(
                    "rejecting implausible tick for %s: price=%.6g bucket=%s", instrument, price, bucket
                )
                return
            open_bar = self._open.get(instrument)
            if open_bar is None:
                self._open[instrument] = [bucket, price]
                return
            if bucket == open_bar[0]:
                open_bar[1] = price  # still in the same bucket — update last price
                return
            if bucket > open_bar[0]:
                self._commit_bar(instrument, open_bar[0], open_bar[1])
                self._open[instrument] = [bucket, price]
            # bucket < open_bar[0] (out-of-order/late tick) — ignore, keep current bar.

    def _is_implausible(self, instrument: str, bucket: float, price: float) -> bool:
        """True if `price` is an implausible jump from the last known price
        for `instrument` (the open bar's running price, or else the last
        committed bar) — the guard against the kind of feed glitch that once
        put an outright-scale print into a spread/fly's history. Skipped if
        that reference is stale, so a genuinely large move across a long gap
        (closure, restart) isn't rejected forever."""
        open_bar = self._open.get(instrument)
        if open_bar is not None:
            ref_ts, ref_price = open_bar[0], open_bar[1]
        else:
            buf = self._bars.get(instrument)
            if not buf:
                return False
            ref_ts, ref_price = buf[-1]
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
                if open_bar[0] < current_bucket:
                    self._commit_bar(instrument, open_bar[0], open_bar[1])
                    del self._open[instrument]

    def _bucket_ts(self, ts: datetime) -> float:
        epoch = ts.timestamp()
        return (epoch // self._bar_sec) * self._bar_sec

    def _commit_bar(self, instrument: str, bucket_ts: float, price: float) -> None:
        buf = self._bars.setdefault(instrument, deque())
        buf.append((bucket_ts, price))
        self._evict_stale(instrument, bucket_ts)
        self._append_to_disk(instrument, bucket_ts, price)

    def _evict_stale(self, instrument: str, now_bucket: float) -> None:
        buf = self._bars[instrument]
        cutoff = now_bucket - self._window_sec
        while buf and buf[0][0] < cutoff:
            buf.popleft()

    # --- reads --------------------------------------------------------------
    def window(self, instrument: str) -> tuple[np.ndarray, np.ndarray]:
        """(timestamps [unix sec], prices), ascending, trimmed to window_days."""
        with self._lock:
            buf = self._bars.get(instrument)
            if not buf:
                return np.empty(0), np.empty(0)
            arr = np.array(buf, dtype=np.float64)
            return arr[:, 0], arr[:, 1]

    def bars_map(self, instrument: str) -> dict[float, float]:
        """All closed bars for `instrument` as {bucket_ts: price}. Used for
        N-way joins (more than two instruments) — see
        analytics/custom_structure.py — where paired_window's 2-series join
        doesn't apply."""
        with self._lock:
            return dict(self._bars.get(instrument, ()))

    def paired_window(self, prev: str, curr: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Inner-join prev/curr on shared bucket timestamp. Because both series
        sit on the same fixed bar_sec grid, matching on the bucket key IS the
        timestamp-tolerant join (tolerance = bar_sec)."""
        with self._lock:
            pa = dict(self._bars.get(prev, ()))
            pb = dict(self._bars.get(curr, ()))
        shared = sorted(set(pa) & set(pb))
        if not shared:
            return np.empty(0), np.empty(0), np.empty(0)
        ts = np.array(shared, dtype=np.float64)
        pv = np.array([pa[t] for t in shared], dtype=np.float64)
        cv = np.array([pb[t] for t in shared], dtype=np.float64)
        return ts, pv, cv

    # --- backfill seam (no-op today) ----------------------------------------
    def seed_from(self, instrument: str, rows: Iterable[tuple[datetime, float]]) -> int:
        """Backfill hook for a future historical-data source. Buckets `rows`
        the same way live ticks are bucketed; a bucket already populated by a
        live tick is left untouched (live data wins on overlap). Nothing calls
        this today — it's the seam the follow-up historical-API integration
        will use. Returns the number of buckets written."""
        if instrument not in self._bars:
            return 0
        written = 0
        with self._lock:
            existing = {t for t, _ in self._bars[instrument]}
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
                buf.append((bucket, price))
                written += 1
            merged = sorted(buf)
            buf.clear()
            buf.extend(merged)
            if merged:
                self._evict_stale(instrument, merged[-1][0])
            self._rewrite_disk(instrument)
        return written

    # --- persistence ---------------------------------------------------------
    def _path_for(self, instrument: str) -> Path:
        return self._dir / _safe_filename(instrument)

    def _append_to_disk(self, instrument: str, bucket_ts: float, price: float) -> None:
        try:
            with open(self._path_for(instrument), "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": bucket_ts, "p": price}) + "\n")
        except OSError:
            log.exception("failed to append curve history bar for %s", instrument)

    def _rewrite_disk(self, instrument: str) -> None:
        """Atomically rewrite an instrument's file from its in-memory deque
        (used after seed_from merges out-of-order rows)."""
        path = self._path_for(instrument)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                for bucket_ts, price in self._bars[instrument]:
                    f.write(json.dumps({"t": bucket_ts, "p": price}) + "\n")
            os.replace(tmp, path)
        except OSError:
            log.exception("failed to rewrite curve history file for %s", instrument)

    def persist_all(self) -> None:
        """Flush any still-open bars to disk and compact each file (dedupe by
        bucket, drop stale rows). Call on shutdown and periodically."""
        with self._lock:
            now = datetime.now(timezone.utc)
            for instrument, open_bar in list(self._open.items()):
                self._commit_bar(instrument, open_bar[0], open_bar[1])
            self._open.clear()
            for instrument in self._bars:
                self._evict_stale(instrument, self._bucket_ts(now))
                self._rewrite_disk(instrument)

    def _load_all(self, instruments: list[str]) -> None:
        cutoff = datetime.now(timezone.utc).timestamp() - self._window_sec
        for instrument in instruments:
            path = self._path_for(instrument)
            if not path.exists():
                continue
            bars: dict[float, float] = {}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                            t, p = float(row["t"]), float(row["p"])
                        except (ValueError, KeyError, TypeError):
                            continue
                        if t >= cutoff:
                            bars[t] = p  # later line for same bucket wins
            except OSError:
                log.exception("failed to load curve history for %s", instrument)
                continue
            self._bars[instrument] = deque(sorted(bars.items()))
