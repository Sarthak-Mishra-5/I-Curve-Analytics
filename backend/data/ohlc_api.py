"""Client for the QH v2 OHLC endpoint (config.OHLC_API_URL).

Returns real open/high/low/close/volume bars, unlike the older
``Historical API.py`` path which only carried a close. Response shape is a
flat list of
``{product, time(ms), open, high, low, close, volume[, buyvolume, sellvolume]}``.

Scale: this endpoint reports every product on this platform in display scale
already (SOFR comes back as 95.895, not 9589.5), so — unlike the live
Lightstreamer feed, which needs config.LIVE_PRICE_SCALE — nothing here is
rescaled. Verified against live quotes for SRA/SON/ER/FSR.

Two vendor limits shape every call here:
  * ``OHLC_API_RATE_LIMIT_PER_MINUTE`` requests per minute. The older module
    assumed 50/min and reliably tripped HTTP 429 during a multi-curve
    backfill; the real ceiling is much lower, so requests are spaced out.
  * ``OHLC_API_MAX_ROW`` rows per *request*, counted across every instrument
    in it — a 4-instrument request with count=3000 is 12000 rows and is
    rejected outright. Batches are therefore sized from the requested count,
    not fixed.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from ..config import (
    OHLC_API_MAX_ROW,
    OHLC_API_RATE_LIMIT_PER_MINUTE,
    OHLC_API_URL,
    get_auth_headers,
)

log = logging.getLogger(__name__)

VALID_INTERVALS = ("1M", "5M", "1H", "1D")

# --- intraday timestamp correction ------------------------------------------
# The endpoint's intraday bar timestamps are the exchange's LONDON wall-clock
# reading encoded as though it were UTC. Decoded naively they land in the
# future: on a BST afternoon the newest 5-minute bar decodes to 16:20 while
# the real time is 15:20, and its close matches the current live price.
#
# It is a timezone, not a constant: the session window in these timestamps is
# a fixed 02:00-21:00 on both sides of the October and March DST switches,
# which is only true of a clock that shifts with London — a genuine fixed
# +1h offset would make the window move by an hour across those boundaries,
# since the exchange defines its hours in local time. So the fix is a
# London->UTC conversion (-1h under BST, unchanged under GMT), not a
# subtraction, and it is verified against wall clock after every fetch.
#
# Daily bars are excluded: they are date keys already sitting exactly on
# 00:00, and converting them would drag each one back to 23:00 the previous
# day.
_VENDOR_INTRADAY_TZ = ZoneInfo("Europe/London")


def _correct_intraday_ts(ts_utc_naive_reading: datetime) -> datetime:
    """Reinterpret a vendor intraday timestamp as London wall time -> real UTC."""
    local_reading = ts_utc_naive_reading.replace(tzinfo=None)
    return local_reading.replace(tzinfo=_VENDOR_INTRADAY_TZ).astimezone(timezone.utc)

# (timestamp, open, high, low, close, volume)
OhlcvRow = tuple[datetime, float, float, float, float, float]

_REQUEST_TIMES: deque[float] = deque()
_RATE_LOCK = threading.Lock()
_MIN_SPACING_SEC = 60.0 / max(1, OHLC_API_RATE_LIMIT_PER_MINUTE)

_RETRY_STATUSES = {429, 502, 503, 504}
_MAX_RETRIES = 3
_TIMEOUT_SEC = 180


def _wait_for_rate_limit() -> None:
    """Hold requests to the vendor's per-minute quota AND space them at least
    _MIN_SPACING_SEC apart. The window cap alone would let the first N fire
    back-to-back, which trips the vendor's burst protection well before the
    per-minute cap is reached."""
    while True:
        with _RATE_LOCK:
            now = time.monotonic()
            cutoff = now - 60.0
            while _REQUEST_TIMES and _REQUEST_TIMES[0] < cutoff:
                _REQUEST_TIMES.popleft()
            since_last = (now - _REQUEST_TIMES[-1]) if _REQUEST_TIMES else _MIN_SPACING_SEC
            if len(_REQUEST_TIMES) < OHLC_API_RATE_LIMIT_PER_MINUTE and since_last >= _MIN_SPACING_SEC:
                _REQUEST_TIMES.append(now)
                return
            if len(_REQUEST_TIMES) >= OHLC_API_RATE_LIMIT_PER_MINUTE:
                sleep_for = max(0.05, 60.0 - (now - _REQUEST_TIMES[0]))
            else:
                sleep_for = max(0.05, _MIN_SPACING_SEC - since_last)
        time.sleep(sleep_for)


# The endpoint documents a ceiling of 50 instrument codes per request,
# independent of the row cap.
MAX_CODES_PER_REQUEST = 50


def max_batch_size(count: int) -> int:
    """How many instruments can share one request at `count` bars each —
    bounded by both the row cap (counted across all instruments in the
    request) and the vendor's per-request code limit."""
    return max(1, min(MAX_CODES_PER_REQUEST, OHLC_API_MAX_ROW // max(1, count)))


def _request(codes: list[str], interval: str, count: int, with_side_volume: bool) -> list[dict]:
    params: dict[str, str] = {
        "instruments": ",".join(codes),
        "interval": interval,
        "count": str(count),
    }
    if with_side_volume:
        params["extraFields"] = "buyvolume,sellvolume"

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        _wait_for_rate_limit()
        try:
            resp = requests.get(
                OHLC_API_URL, headers=get_auth_headers(), params=params, timeout=_TIMEOUT_SEC
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_MIN_SPACING_SEC * (2 ** attempt))
            continue

        if resp.status_code == 200:
            payload = resp.json()
            if isinstance(payload, dict) and "data" in payload:
                payload = payload["data"]
            if not isinstance(payload, list):
                raise RuntimeError(f"unexpected OHLC response shape: {type(payload).__name__}")
            return payload

        if resp.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
            retry_after = resp.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else _MIN_SPACING_SEC * (2 ** attempt)
            except ValueError:
                delay = _MIN_SPACING_SEC * (2 ** attempt)
            log.warning(
                "OHLC API %s for %s (attempt %d/%d) — retrying in %.1fs",
                resp.status_code, codes, attempt + 1, _MAX_RETRIES, delay,
            )
            time.sleep(delay)
            continue

        raise RuntimeError(
            f"OHLC API HTTP {resp.status_code} for {codes} {interval} count={count}: {resp.text[:300]}"
        )

    raise last_exc or RuntimeError("OHLC request failed")


def fetch_ohlcv(
    codes: list[str],
    interval: str,
    count: int,
    with_side_volume: bool = False,
) -> dict[str, list[OhlcvRow]]:
    """Fetch `count` bars of `interval` for each code.

    Returns ``{code: [(ts, open, high, low, close, volume), ...]}`` ascending,
    keyed by the code as passed in. Codes the vendor returns nothing for map
    to an empty list rather than being absent.
    """
    interval = interval.strip().upper()
    if interval not in VALID_INTERVALS:
        raise ValueError(f"interval must be one of {VALID_INTERVALS}, got {interval!r}")
    codes = [c.strip().upper() for c in codes if c and c.strip()]
    if not codes:
        return {}

    is_intraday = interval != "1D"
    out: dict[str, list[OhlcvRow]] = {c: [] for c in codes}
    batch = max_batch_size(count)
    for start in range(0, len(codes), batch):
        chunk = codes[start:start + batch]
        for item in _request(chunk, interval, count, with_side_volume):
            if not isinstance(item, dict):
                continue
            product = str(item.get("product", "")).strip().upper()
            if product not in out:
                continue
            ts_ms, close = item.get("time"), item.get("close")
            if ts_ms in (None, "") or close in (None, ""):
                continue
            try:
                ts = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
                if is_intraday:
                    ts = _correct_intraday_ts(ts)
                c = float(close)
                o = float(item["open"]) if item.get("open") not in (None, "") else c
                h = float(item["high"]) if item.get("high") not in (None, "") else max(o, c)
                low = float(item["low"]) if item.get("low") not in (None, "") else min(o, c)
                v = float(item["volume"]) if item.get("volume") not in (None, "") else 0.0
            except (TypeError, ValueError):
                continue
            # Guard against a malformed bar inverting the range — a candle
            # whose high sits below its low renders as a broken wick.
            h = max(h, o, c, low)
            low = min(low, o, c, h)
            out[product].append((ts, o, h, low, c, v))

    for rows in out.values():
        rows.sort(key=lambda r: r[0])

    if is_intraday:
        _warn_if_ahead_of_clock(interval, out)
    return out


def _warn_if_ahead_of_clock(interval: str, out: dict[str, list[OhlcvRow]]) -> None:
    """Sanity-check the intraday timestamp correction against wall clock.

    A bar dated meaningfully in the future means the London assumption no
    longer holds (vendor changed convention, or a tz database surprise).
    Better to say so loudly than to silently plot candles in the future,
    which also breaks the strictly-ascending contract the chart library
    asserts on once live bars are merged in.
    """
    now = datetime.now(timezone.utc)
    for code, rows in out.items():
        if not rows:
            continue
        newest = rows[-1][0]
        if newest > now + timedelta(hours=1):
            log.error(
                "OHLC %s newest bar for %s is %s, which is ahead of now (%s) — the "
                "intraday timestamp correction looks wrong; charts may be misaligned",
                interval, code, newest.isoformat(), now.isoformat(),
            )
