"""Fetch historical OHLC data from Hertshten API and cache locally."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

# Dynamically load the Historical API module (handles space in filename).
def _load_historical_api_module():
    api_path = Path(__file__).parent.parent.parent / "Historical API.py"
    spec = spec_from_file_location("historical_api", api_path)
    module = module_from_spec(spec)
    sys.modules["historical_api"] = module
    spec.loader.exec_module(module)
    return module


_HISTORICAL_API = None


def _get_historical_api():
    global _HISTORICAL_API
    if _HISTORICAL_API is None:
        _HISTORICAL_API = _load_historical_api_module()
    return _HISTORICAL_API


def fetch_historical_ohlc(
    instruments: list[str],
    interval: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Fetch historical OHLC data from the API.

    Args:
        instruments: List of contract codes (accepts both "H26" or "SA3 Jun26")
        interval: "1H", "1D", etc.
        start_date: Start datetime (UTC)
        end_date: End datetime (UTC)

    Returns:
        DataFrame with columns: timestamp, instrument, price, bid, ask, volume
    """
    api_module = _get_historical_api()

    # Normalize input: "SA3 Jun26" -> "H26", etc.
    tenor_to_code = {
        'Jun': 'M', 'Sep': 'U', 'Dec': 'Z', 'Mar': 'H',
        'JUN': 'M', 'SEP': 'U', 'DEC': 'Z', 'MAR': 'H',
    }
    normalized_instruments = []
    for code in instruments:
        code = str(code).strip()
        # If it's already a tenor code (H26, M26, etc.), use it.
        if len(code) == 3 and code[0] in 'HMUZ' and code[1:].isdigit():
            normalized_instruments.append(code)
        else:
            # Try to extract tenor from full name (SA3 Jun26 -> M26).
            parts = code.split()
            if len(parts) >= 2:
                tenor_part = parts[-1]  # Jun26
                for month_str, quarter_letter in tenor_to_code.items():
                    if month_str in tenor_part:
                        year = tenor_part.replace(month_str, '', 1).replace(month_str.lower(), '', 1)
                        if year.isdigit():
                            normalized_instruments.append(f"{quarter_letter}{year}")
                        break
            else:
                normalized_instruments.append(code)

    # Convert to Unix timestamps.
    start_unix = api_module.datetime_to_unix_seconds(start_date)
    end_unix = api_module.datetime_to_unix_seconds(end_date)

    # Fetch from API.
    df = api_module.fetch_historical_ohlc(
        instruments=normalized_instruments,
        interval=interval,
        start_unix=start_unix,
        end_unix=end_unix,
        count=None,
    )

    return df


# --- I curve historical backfill --------------------------------------------
# The I curve's historical series uses its own vendor code convention
# ("ER" + quarter letter + 2-digit year, e.g. "ERU26" for Sep26; spreads join
# two legs with '-', e.g. "ERU26-Z26" for Sep26-Dec26) — distinct from the
# "FSR"-prefixed convention used by fetch_historical_ohlc() above for
# SA3/ER3, so it's fetched directly rather than through that function.
_CURVE_QUARTER_CODE = {"Mar": "H", "Jun": "M", "Sep": "U", "Dec": "Z"}
_CURVE_HISTORICAL_PREFIX = {
    "I": "ER",
    "SR3": "SRA",
    "SA3": "FSR",
    "SO3": "SON",
}
# The OHLC service accepts the requested symbols individually and in small
# groups, but rejects larger comma-separated batches with HTTP 400. Keep
# requests deliberately small so a custom structure with many rolled legs can
# still obtain its full history.
_HISTORICAL_BATCH_SIZE = 2


def tenor_to_i_curve_code(tenor: str) -> str:
    """'Sep26' -> 'ERU26'."""
    return tenor_to_curve_code("I", tenor)


def tenor_to_curve_code(curve_id: str, tenor: str) -> str:
    """Map a tenor to the curve's QH historical code, e.g. SR3 Sep26 -> SRAU26."""
    month, year = tenor[:3], tenor[3:]
    prefix = _CURVE_HISTORICAL_PREFIX[curve_id]
    return f"{prefix}{_CURVE_QUARTER_CODE[month]}{year}"


def curve_instrument_to_code(curve_id: str, name: str) -> str | None:
    """Map outrights, spreads, and 3MF flies to QH historical-API codes."""
    if curve_id not in _CURVE_HISTORICAL_PREFIX:
        return None
    body = name.split(" ", 1)[1]
    if "3MF" in body:
        from ..config import TENOR_ORDER

        tenor = body.split()[0]
        if tenor not in TENOR_ORDER:
            return None
        idx = TENOR_ORDER.index(tenor)
        if idx + 2 >= len(TENOR_ORDER):
            return None
        legs = TENOR_ORDER[idx:idx + 3]
    elif "-" in body:
        legs = body.split("-")
    else:
        return tenor_to_curve_code(curve_id, body)

    first = tenor_to_curve_code(curve_id, legs[0])
    suffixes = [f"{_CURVE_QUARTER_CODE[leg[:3]]}{leg[3:]}" for leg in legs[1:]]
    return "-".join([first, *suffixes])


def i_curve_instrument_to_code(name: str) -> str | None:
    """Map an I-curve display name to its vendor historical-API code.
    Handles outrights ('I Sep26' -> 'ERU26') and calendar spreads
    ('I Sep26-Dec26' -> 'ERU26-Z26'). Returns None for names this mapping
    doesn't cover (3MF flies are synthesized from outright legs instead —
    see historical_loader.backfill_curve_from_historical_api)."""
    return curve_instrument_to_code("I", name)


def fetch_vendor_bars(
    codes: list[str], interval: str = "1D", count: int = 60
) -> dict[str, list[tuple[datetime, float]]]:
    """Fetch recent OHLC bars for native vendor product codes.

    Returns ``{code: [(timestamp, close), ...]}``, keyed by the exact code
    passed in. This works for both I-curve codes (for example ``ERZ26-M27``)
    and the ER3 benchmark code ``FERM26-Z26``.
    """
    if len(codes) > _HISTORICAL_BATCH_SIZE:
        merged: dict[str, list[tuple[datetime, float]]] = {code: [] for code in codes}
        for start in range(0, len(codes), _HISTORICAL_BATCH_SIZE):
            merged.update(fetch_vendor_bars(codes[start:start + _HISTORICAL_BATCH_SIZE], interval, count))
        return merged

    api_module = _get_historical_api()
    api_module._wait_for_rate_limit()

    params = {"instruments": ",".join(codes), "interval": interval, "count": str(count)}
    url = f"{api_module.API_URL}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_module.API_ACCESS_TOKEN.strip()}",
            "Accept": "application/json",
            "User-Agent": "dash-pyqt6/1.0",
        },
        method="GET",
    )

    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    data_list = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(data_list, list):
        raise api_module.HistoricalApiError(f"unexpected response shape for {url}")

    wanted = {c.strip().upper(): c for c in codes}
    out: dict[str, list[tuple[datetime, float]]] = {c: [] for c in codes}
    for item in data_list:
        if not isinstance(item, dict):
            continue
        ts_ms, close = item.get("time"), item.get("close")
        if ts_ms in (None, "") or close in (None, ""):
            continue
        raw_code = str(item.get("product", "")).strip().upper()
        stripped_code = raw_code[3:] if raw_code.startswith("FSR") else raw_code
        orig = wanted.get(raw_code) or wanted.get(stripped_code)
        if orig is None:
            continue
        ts = datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
        # Unlike fetch_historical_ohlc()'s SA3/ER3 path, the I curve's vendor
        # codes already return `close` in display scale (e.g. 97.51, not
        # 0.9751) — no PRICE_SCALE multiplication needed here.
        out[orig].append((ts, float(close)))
    return out


def fetch_i_curve_bars(
    codes: list[str], interval: str = "1D", count: int = 60
) -> dict[str, list[tuple[datetime, float]]]:
    """Backward-compatible I-curve wrapper around :func:`fetch_vendor_bars`."""
    return fetch_vendor_bars(codes, interval, count)


def fetch_curve_bars(
    codes: list[str], interval: str = "1D", count: int = 60
) -> dict[str, list[tuple[datetime, float]]]:
    """Generic curve historical wrapper around :func:`fetch_vendor_bars`."""
    return fetch_vendor_bars(codes, interval, count)


def cache_to_csv(df: pd.DataFrame, output_path: str | Path) -> None:
    """Cache historical data to CSV for faster subsequent loads."""
    df.to_csv(output_path, index=False)


def load_cached_csv(csv_path: str | Path) -> pd.DataFrame | None:
    """Load cached CSV if it exists."""
    path = Path(csv_path)
    if path.exists():
        return pd.read_csv(path)
    return None
