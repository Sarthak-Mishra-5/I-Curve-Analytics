#!/usr/bin/env python3
"""CLI to fetch historical data and backfill MarketState for analysis."""
import sys
import io
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.config import SA3_NAMES, ER3_NAMES
from backend.data.historical_api import fetch_historical_ohlc, cache_to_csv
from backend.data.historical_loader import backfill_from_csv
from backend.streaming.state import MarketState


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and backfill historical data for correlation/regression analysis"
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="Days to fetch back from today (default: 30)"
    )
    parser.add_argument(
        "--interval",
        default="1H",
        choices=["1M", "5M", "1H", "1D"],
        help="OHLC interval (default: 1H)"
    )
    parser.add_argument(
        "--contracts",
        type=str,
        help="Comma-separated contract codes (e.g., 'H26,M26,U26'). "
             "If omitted, fetches all SA3 and ER3 contracts."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't cache the result to disk"
    )
    parser.add_argument(
        "--cache-only",
        type=str,
        metavar="FILE",
        help="Load from cached CSV instead of fetching (e.g., 'historical_1H_30d.csv')"
    )

    args = parser.parse_args()

    # Resolve contracts. If fetching all, group by product to preserve SA3 vs ER3 distinction.
    if args.contracts:
        contracts = [c.strip().upper() for c in args.contracts.split(",")]
        mixed_products = True
    else:
        contracts = SA3_NAMES + ER3_NAMES
        mixed_products = False

    # If loading from cache, skip fetch.
    if args.cache_only:
        cache_dir = Path(__file__).parent / "data_cache"
        cache_file = cache_dir / args.cache_only
        if not cache_file.exists():
            print(f"ERROR: Cache file not found: {cache_file}")
            sys.exit(1)
        print(f"Loading cached data from {cache_file}...")
        df = __import__('pandas').read_csv(cache_file)
        df['timestamp'] = __import__('pandas').to_datetime(df['timestamp'], utc=True)
    else:
        # Fetch from API.
        print(f"Fetching {args.interval} data for {len(contracts)} contracts ({args.days_back} days back)...")
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=args.days_back)

        try:
            df = fetch_historical_ohlc(contracts, args.interval, start_date, end_date)

            # Add product column if missing: infer from contract names.
            if 'product' not in df.columns or df['product'].isna().all():
                def infer_product(row):
                    instrument = row['instrument']
                    for sa_name in SA3_NAMES:
                        if instrument in sa_name.replace(' ', ''):
                            return sa_name.split()[0] + ' ' + instrument
                    for er_name in ER3_NAMES:
                        if instrument in er_name.replace(' ', ''):
                            return er_name.split()[0] + ' ' + instrument
                    return None
                df['product'] = df.apply(infer_product, axis=1)

            print(f"[OK] Fetched {len(df)} rows")
        except Exception as e:
            print(f"ERROR: Failed to fetch data: {e}")
            sys.exit(1)

        # Cache to disk.
        if not args.no_cache:
            cache_dir = Path(__file__).parent / "data_cache"
            cache_dir.mkdir(exist_ok=True)
            cache_file = cache_dir / f"historical_{args.interval}_{args.days_back}d.csv"
            cache_to_csv(df, cache_file)
            print(f"[OK] Cached to {cache_file}")

    # Backfill state.
    print("Backfilling MarketState...")
    state = MarketState()
    from backend.data.historical_loader import backfill_state
    ticks = backfill_state(state, df)

    print(f"[OK] Backfilled {ticks} ticks")

    # Print summary.
    print("\nState Summary:")
    print(f"  Total ticks: {state.tick_count}")
    print(f"  Instruments: {len(state.quotes)}")
    for name in SA3_NAMES[:3] + ER3_NAMES[:3]:
        prices = state.prices(name)
        if len(prices) > 0:
            print(f"    {name}: {len(prices)} obs, latest={prices[-1]:.2f}")

    # Compute analytics.
    print("\nComputing Analytics...")
    from backend.analytics.correlation import compute_correlation
    from backend.analytics.regression import compute_regressions

    corr = compute_correlation(state, top_n=3)
    print(f"[OK] Correlation matrix computed: {len(corr['rows'])}x{len(corr['cols'])}")

    regs = compute_regressions(state)
    print(f"[OK] Regressions computed: {len(regs)} pairs")
    for reg in regs[:3]:
        print(f"    {reg['y']} ~ {reg['x']}: beta={reg['beta']:.4f}, R2={reg['r2']:.4f}")

    print("\n[OK] All done! Data is ready for analysis.")


if __name__ == "__main__":
    main()
