"""Parsing helpers — preserves the semantics from the user's reference snippet."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if text in ("", "-", "--", "N/A", "n/a", "null", "None"):
                return None
            return float(text)
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_contract_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("TT-"):
        text = text[3:]
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _is_plausible(dt: datetime) -> bool:
    return 2000 <= dt.year <= 2100


def _candidates_from_numeric(value: int) -> list[datetime]:
    out: list[datetime] = []
    for div in (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0):
        try:
            out.append(datetime.fromtimestamp(value / div, tz=timezone.utc))
        except (OverflowError, OSError, ValueError):
            pass
    return out


def parse_timestamp_from_values(values: dict[str, Any]) -> datetime:
    """Pick the most plausible UTC timestamp from any of the *RecvTime fields."""
    now = datetime.now(timezone.utc)
    for key in ("ExchangeRecvTime", "ServerRecvTime", "ClientRecvTime"):
        raw = values.get(key)
        if raw in (None, ""):
            continue
        text = str(raw).strip()
        if text.lstrip("-").isdigit():
            try:
                value = int(text)
            except ValueError:
                continue
            plausible = [dt for dt in _candidates_from_numeric(value) if _is_plausible(dt)]
            if plausible:
                return min(plausible, key=lambda d: abs((d - now).total_seconds()))
            continue
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
            if _is_plausible(dt):
                return dt
        except ValueError:
            continue
    return now


_PRICE_FIELDS = (
    "Open", "High", "Low", "Close", "Settle", "PrevSettle",
    "BestBid", "BestAsk", "IndSettle", "Price", "AdminPrice", "Last",
)


def rescale_price_fields(values: dict[str, Any], factor: float) -> dict[str, Any]:
    """Return a copy of `values` with every price-like field multiplied by
    `factor`. Used to correct products whose live feed reports prices on a
    different scale than the rest of the platform (see config.LIVE_PRICE_SCALE)."""
    out = dict(values)
    for field in _PRICE_FIELDS:
        v = safe_float(out.get(field))
        if v is not None:
            out[field] = v * factor
    return out


def derive_price(values: dict[str, Any]) -> float | None:
    """Apply the same fallback chain used by the reference client."""
    bid = safe_float(values.get("BestBid"))
    ask = safe_float(values.get("BestAsk"))
    for k in ("Price", "Last", "Close", "Settle"):
        v = safe_float(values.get(k))
        if v is not None:
            return v
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    return bid if bid is not None else ask
