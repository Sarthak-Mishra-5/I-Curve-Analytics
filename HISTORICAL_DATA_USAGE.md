# Historical Data Integration

Your RV platform now has integrated historical data fetching and analytics. Use it to compute correlation matrices, regressions, beta, and other analytics on backfilled historical data.

## Quick Start

### 1. Fetch Historical Data (CLI)

```bash
# Fetch last 30 days of 1H data for all contracts and cache locally
python fetch_and_backfill.py

# Fetch custom date range and interval
python fetch_and_backfill.py --days-back 90 --interval 1D

# Fetch specific contracts only
python fetch_and_backfill.py --contracts "H26,M26,U26,H27" --days-back 60

# Load from cache instead of API
python fetch_and_backfill.py --cache-only historical_1H_30d.csv
```

The script will:
- Fetch OHLC data from the Hertshten API
- Cache it to `data_cache/` for reuse
- Backfill a `MarketState` in-memory
- Compute correlation and regression analytics
- Print a summary

### 2. REST API Endpoints

Once the backend is running, use these endpoints:

#### Fetch and cache data
```
GET /api/historical/fetch?instruments=H26,M26,U26&interval=1H&days_back=30
```
Response:
```json
{
  "status": "success",
  "instruments": ["H26", "M26", "U26"],
  "rows": 720,
  "cached_at": "data_cache/historical_1H_30d.csv"
}
```

#### Load cached data into state
```
GET /api/historical/backfill?cache_file=historical_1H_30d.csv
```
Response:
```json
{
  "status": "success",
  "ticks_ingested": 2160,
  "tick_count_total": 2160
}
```

#### Get correlation matrix
```
GET /api/historical/correlation?top_n=6
```
Response:
```json
{
  "rows": ["SA3 Jun26", "SA3 Sep26", ...],
  "cols": ["SA3 Jun26", "SA3 Sep26", ...],
  "matrix": [[1.0, 0.95, ...], ...]
}
```

#### Get pair-by-tenor regressions
```
GET /api/historical/regression
```
Response:
```json
{
  "regressions": [
    {
      "x": "ER3 Jun26",
      "y": "SA3 Jun26",
      "alpha": 0.001,
      "beta": 0.98,
      "r2": 0.92,
      "residual": 0.05,
      "residual_z": 1.2,
      "rolling_beta": 0.97,
      "n": 720
    },
    ...
  ],
  "count": 15
}
```

#### Get state summary
```
GET /api/historical/state/summary
```
Response:
```json
{
  "total_instruments": 30,
  "total_ticks": 2160,
  "instruments": {
    "SA3 Jun26": {"buffer_size": 72, "latest_price": 99.95},
    ...
  }
}
```

## Data Layout

After fetching, your `data_cache/` directory will contain CSVs like:
```
data_cache/
  historical_1H_30d.csv
  historical_1D_90d.csv
  ...
```

CSV columns: `timestamp`, `instrument`, `price`, `bid`, `ask`, `volume`

## Code Structure

- **`backend/data/historical_api.py`** — Fetches from Hertshten API, handles dynamic module loading
- **`backend/data/historical_loader.py`** — Loads CSV and backfills `MarketState`
- **`backend/api/historical_routes.py`** — REST endpoints for fetch, backfill, analytics
- **`fetch_and_backfill.py`** — CLI utility for one-shot fetch + backfill + analysis

## Workflow for Analysis

1. **Fetch historical data:**
   ```bash
   python fetch_and_backfill.py --days-back 90 --interval 1D
   ```

2. **Start the backend:**
   ```bash
   python -m backend.main
   ```

3. **Query analytics via REST or WebSocket:**
   - Correlation matrices for spread trading analysis
   - Regressions for beta / alpha decomposition
   - Residual z-scores for anomaly detection

4. **Iterate:**
   - Adjust windows, date ranges, contracts
   - Re-fetch or re-load from cache
   - Export results for further analysis

## Integration with Live Streaming

Once backfilled, the in-memory buffers seamlessly transition to live Lightstreamer data. Analytics continue to work with whatever data is in the rolling buffers, whether historical or live.

To reset and start fresh: restart the backend (`python -m backend.main`), which reinitializes `MarketState`.

## Common Recipes

### Quick 30-day analysis
```bash
python fetch_and_backfill.py --interval 1H
```

### Multi-year daily data
```bash
python fetch_and_backfill.py --days-back 1095 --interval 1D
```

### Specific tenor pairs
```bash
python fetch_and_backfill.py --contracts "H26,M26,H27,M27" --days-back 60
```

### Manual DataFrame inspection
```python
import pandas as pd
df = pd.read_csv("data_cache/historical_1H_30d.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(df.describe())
print(df.groupby('instrument').size())
```
