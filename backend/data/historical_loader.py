"""Load and integrate historical OHLC data into MarketState for backtesting."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..analytics.curve_history import CurveHistoryStore
    from ..curves.registry import CurveSpec
    from ..streaming.state import MarketState


def load_historical_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load historical OHLC data from CSV.

    Expected columns: timestamp, instrument, price, bid, ask, volume
    timestamp should be ISO format or convertible to datetime.
    """
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    return df.sort_values('timestamp').reset_index(drop=True)


def backfill_state(state: MarketState, df: pd.DataFrame) -> int:
    """Feed historical data into MarketState's rolling buffers.

    Returns the number of ticks ingested. Normalizes contract codes
    (H26 -> SA3 Jun26 or ER3 Jun26, etc.) using config.
    """
    from ..config import SA3_NAMES, ER3_NAMES

    # Map tenor order (H=Mar, M=Jun, U=Sep, Z=Dec) to month names.
    tenor_map = {
        'H': 'Mar',
        'M': 'Jun',
        'U': 'Sep',
        'Z': 'Dec',
    }

    # Build lookup: tenor_code -> full name (try SA3 first, then ER3).
    tenor_lookup = {}
    for name in SA3_NAMES:
        tenor = name.split()[-1]  # Jun26, Sep26, etc.
        if tenor not in tenor_lookup:
            tenor_lookup[tenor] = name
    for name in ER3_NAMES:
        tenor = name.split()[-1].title()  # Normalize case
        if tenor.upper() not in tenor_lookup:
            # Try to map ER3 tenor (JUN26) to key.
            tenor_lookup[tenor.upper()] = name

    # Map short codes (H26) to full names.
    def normalize_contract(code: str) -> str | None:
        code = code.strip().upper()
        if len(code) < 2:
            return None

        quarter_letter = code[0]
        year_code = code[1:]

        month_name = tenor_map.get(quarter_letter)
        if month_name is None:
            return None

        tenor_code = f"{month_name}{year_code}"

        # Try both title and upper case.
        result = tenor_lookup.get(tenor_code) or tenor_lookup.get(tenor_code.upper())
        if result:
            return result

        # Fallback: try to find by partial match.
        for name in SA3_NAMES + ER3_NAMES:
            if tenor_code in name or tenor_code.upper() in name.upper():
                return name

        return None

    count = 0
    skipped = 0
    for _, row in df.iterrows():
        ts = row['timestamp']
        price = row['price']

        # Use instrument column to resolve contract.
        contract_code = row.get('instrument') or row.get('product')
        if pd.isna(contract_code):
            skipped += 1
            continue

        full_name = normalize_contract(str(contract_code))

        if full_name is None or full_name not in state.quotes:
            skipped += 1
            continue

        # Build values dict for apply_tick (bid/ask optional).
        values = {
            'BestBid': row.get('bid', price),
            'BestAsk': row.get('ask', price),
            'Volume': row.get('volume', 0.0),
        }

        state.apply_tick(full_name, values, price, ts)
        count += 1

    if skipped > 0:
        import logging
        logging.debug(f"Skipped {skipped} rows with unrecognized contract codes")

    return count


def backfill_from_csv(state: MarketState, csv_path: str | Path, product_hint: str | None = None) -> int:
    """Load CSV and backfill state in one step.

    Args:
        state: MarketState to backfill
        csv_path: Path to CSV file
        product_hint: If set to "SA3" or "ER3", all unrecognized contracts are assumed to be that product

    Returns:
        Number of ticks ingested
    """
    df = load_historical_csv(csv_path)

    # If product_hint is set, add it to all rows with missing/bare product.
    if product_hint in ("SA3", "ER3"):
        for idx, row in df.iterrows():
            product = row.get('product', '')
            if pd.isna(product) or len(str(product).strip()) <= 2:
                df.at[idx, 'product'] = f"{product_hint} {row['instrument']}"

    return backfill_state(state, df)


def backfill_curve_from_historical_api(
    store: CurveHistoryStore, spec: CurveSpec, interval: str = "1D", count: int = 150
) -> dict[str, int]:
    """Best-effort startup backfill for a curve's outrights/3ms/6ms from the
    historical API. Flies (3MF) aren't fetched directly — the vendor's fly
    quoting convention isn't guaranteed to match our live direct-feed 3MF
    quotes — instead each fly is synthesized from its 3 outright legs
    (leg1 - 2*leg2 + leg3) once those legs' history has been seeded.

    Non-fatal by construction (network/shape errors propagate to the caller,
    which should treat this as best-effort and continue with live-only
    history on failure). Returns {instrument_name: bars_written}.
    """
    from .historical_api import curve_instrument_to_code, fetch_curve_bars

    directly_fetchable = [
        *spec.outrights,
        *spec.three_month_spreads,
        *spec.six_month_spreads,
        *spec.flies_3m,
    ]
    name_to_code = {
        name: code
        for name in directly_fetchable
        if (code := curve_instrument_to_code(spec.curve_id, name)) is not None
    }

    bars_by_code = fetch_curve_bars(list(name_to_code.values()), interval=interval, count=count)

    written: dict[str, int] = {}
    for name, code in name_to_code.items():
        rows = bars_by_code.get(code, [])
        n = store.seed_from(name, rows)
        if n:
            written[name] = n

    return written
