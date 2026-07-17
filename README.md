## RUN
Backend - **powershell -ExecutionPolicy Bypass -File run_backend.ps1**
Frontend - **powershell -ExecutionPolicy Bypass -File run_frontend.ps1**

Backend (Mock Data) **powershell -ExecutionPolicy Bypass -File run_backend.ps1 -Mock**

# SA3 / ER3 — Institutional RV Analytics Terminal

Live streaming relative-value analytics for **SARON 3M (SA3)** and **€STR 3M (ER3)** futures.

In-memory only (no persistent storage in v1). Lightstreamer → FastAPI → WebSocket → React/Plotly dashboard.

## Architecture

Lightstreamer (HGL1_Adapter)
        │  ticks (LS SDK, MERGE mode, TT-<InstrumentId>)
        ▼
backend/streaming/  LightstreamerStreamer  ──►  MarketState (rolling buffers)
                                  │                     │
                                  ▼                     ▼
                          asyncio.Queue           AnalyticsEngine
                                  │              (1Hz scheduler, executor)
                                  ▼                     │
                          tick-pump (batch 50ms) ◄──────┤
                                  │                     ▼
                                  ▼              AlertEngine
                          WSHub.broadcast ◄─────────────┘
                                  │
                                  ▼
                 frontend (Vite + React + Plotly)  ws://localhost:8000/ws

## Layout

backend/
  api/app.py              FastAPI + WS + REST + lifecycle wiring
  streaming/              LS client + MarketState + utils
  analytics/              spreads, flies, correlation, regression,
                          tick_sensitivity, cointegration, volatility,
                          microstructure, curve, engine (scheduler), fast (numba)
  alerts/engine.py        z-score / vol-spike / corr-shift alerts
  websocket/hub.py        fan-out broadcaster
  config.py               contracts, windows, alert thresholds
  main.py                 uvicorn entry point
  requirements.txt
frontend/
  src/components/         Panels: TopQuotes, Curve, Spread, Fly,
                                  Correlation, Regression, Alerts, Header
  src/store.ts            Zustand state
  src/ws.ts               WS client (auto-reconnect, 15s ping)
  src/plotlyTheme.ts      Dark institutional theme
  package.json

## Run

### Backend

```powershell
cd "backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Live mode (requires intranet access to ls-md.corp.hertshtengroup.com):
python -m backend.main

# Mock mode (no network required — synthetic ticks):
$env:RV_MOCK = "1"; python -m backend.main
```

Backend listens on `http://localhost:8000`.

### Frontend

```powershell
cd "frontend"
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/ws` to the backend.

## Configuration

Edit `backend/config.py`:

| Setting | Purpose |
|---|---|
| `ROLLING_BUFFER_SIZE` | Per-instrument tick history cap (default 5000) |
| `ROLLING_WINDOW_SHORT/MEDIUM/LONG` | Rolling stat windows (default 60 / 300 / 1200) |
| `ANALYTICS_INTERVAL_SEC` | Analytics recompute cadence (default 1.0s) |
| `ALERT_SPREAD_Z`, `ALERT_FLY_Z`, `ALERT_RESID_Z` | Alert |z| thresholds |
| `DV01_PER_TICK`, `TICK_SIZE` | Contract specs for DV01 normalisation (placeholders — verify) |

## API

- `GET /api/health` — stream/connect/analytics status
- `GET /api/contracts` — SA3/ER3 names
- `GET /api/quotes` — live snapshot
- `GET /api/analytics` — most recent computed payload
- `GET /api/alerts` — recent alerts (in-memory)
- `WS  /ws` — push channel; messages `{type: snapshot|tick|analytics|alert, payload}`

## Notes

- **OneDrive caveat**: this project lives in a OneDrive-synced folder. Exclude `backend/.venv` and `frontend/node_modules` from OneDrive sync to avoid file-locking issues during install / hot-reload.
- **Numba**: rolling stats (`backend/analytics/fast.py`) are JIT-compiled. First run includes a small warm-up cost.
- **No persistence**: rolling buffers are in-memory and reset on restart. Historical DB integration is a later phase.
- **DV01 placeholders**: `DV01_PER_TICK` and `TICK_SIZE` in config are nominal — confirm against exchange contract specs (Eurex/SIX) before using DV01-normalised analytics in any production decision.
- **Auth**: the LS endpoint is unauthenticated on the corp network (matches the reference client). If that changes, set credentials via `LightstreamerClient.connectionDetails.setUser/setPassword` in `streaming/lightstreamer_client.py`.

## Analytics modules covered

| # | Module | File |
|---|---|---|
| 1 | Calendar / curve / cross-product spreads + z, mean, std, percentile, vol | `analytics/spreads.py` |
| 2 | Butterflies (2M − F − B) + z, vol | `analytics/flies.py` |
| 3 | Rolling correlation matrix (returns-based) | `analytics/correlation.py` |
| 4 | OLS regression (α, β, R², residual z, rolling β) per tenor pair | `analytics/regression.py` |
| 5 | Tick sensitivity / vol ratio / tick-β / DV01-β | `analytics/tick_sensitivity.py` |
| 6 | DV01 normalisation (config-driven) | `config.py` |
| 7 | Cointegration (ADF, Engle-Granger, half-life) | `analytics/cointegration.py` |
| 8 | Realized vol, EWMA vol, regime classification | `analytics/volatility.py` |
| 9 | Order flow imbalance, book spread, liquidity | `analytics/microstructure.py` |
| + | Curve + PCA (level/slope/curvature variance share) | `analytics/curve.py` |
