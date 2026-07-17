"""Statistical arbitrage: Engle-Granger, ADF stationarity, half-life."""
from __future__ import annotations

import numpy as np

from ..config import ER3_NAMES, ROLLING_WINDOW_LONG, SA3_NAMES
from ..streaming.state import MarketState

try:
    from statsmodels.tsa.stattools import adfuller, coint  # type: ignore
    _SM = True
except Exception:  # noqa: BLE001
    _SM = False


def _half_life(resid: np.ndarray) -> float:
    if resid.size < 5:
        return float("nan")
    lag = resid[:-1]
    delta = np.diff(resid)
    # Regress delta on lag: delta = phi * lag + eps; half-life = -ln(2)/ln(1+phi).
    denom = float(np.dot(lag, lag))
    if denom < 1e-12:
        return float("nan")
    phi = float(np.dot(lag, delta) / denom)
    if phi >= 0:
        return float("nan")
    return float(-np.log(2.0) / np.log1p(phi))


def compute_cointegration(state: MarketState) -> list[dict]:
    out: list[dict] = []
    for sa, er in zip(SA3_NAMES, ER3_NAMES):
        y, x = state.aligned_pair(sa, er, ROLLING_WINDOW_LONG)
        if y.size < 50:
            continue
        resid = y - x  # Simple Engle-Granger residual (beta=1 assumption for in-memory speed).
        hl = _half_life(resid)
        rec = {
            "y": sa,
            "x": er,
            "half_life": hl,
            "spread_mean": float(resid.mean()),
            "spread_std": float(resid.std()),
        }
        if _SM:
            try:
                adf_stat, adf_p, *_ = adfuller(resid, maxlag=5, autolag=None)
                rec["adf_stat"] = float(adf_stat)
                rec["adf_pvalue"] = float(adf_p)
            except Exception:  # noqa: BLE001
                rec["adf_stat"] = None
                rec["adf_pvalue"] = None
            try:
                t_stat, p_val, _ = coint(y, x, maxlag=3)
                rec["coint_t"] = float(t_stat)
                rec["coint_pvalue"] = float(p_val)
            except Exception:  # noqa: BLE001
                rec["coint_t"] = None
                rec["coint_pvalue"] = None
        out.append(rec)
    return out
