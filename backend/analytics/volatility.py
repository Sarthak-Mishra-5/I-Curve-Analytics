"""Volatility analytics: realized, EWMA, regime classification."""
from __future__ import annotations

import numpy as np

from ..config import ALL_CONTRACTS, ROLLING_WINDOW_MEDIUM, ROLLING_WINDOW_SHORT
from ..streaming.state import MarketState
from .fast import ewma, realized_vol


def compute_volatility(state: MarketState) -> list[dict]:
    out: list[dict] = []
    for name, _iid in ALL_CONTRACTS:
        p = state.prices(name, ROLLING_WINDOW_MEDIUM)
        if p.size < 3:
            continue
        rv = realized_vol(p, ROLLING_WINDOW_SHORT)
        rv_med = realized_vol(p, ROLLING_WINDOW_MEDIUM)
        rets = np.diff(p)
        ew = ewma(np.abs(rets), 0.06) if rets.size > 0 else np.zeros(0)
        ewma_vol = float(ew[-1]) if ew.size else 0.0
        regime = "low"
        if rv_med > 1e-12:
            ratio = rv / rv_med
            if ratio > 1.5:
                regime = "high"
            elif ratio > 1.1:
                regime = "elevated"
        out.append({
            "instrument": name,
            "realized_vol_short": rv,
            "realized_vol_medium": rv_med,
            "ewma_vol": ewma_vol,
            "regime": regime,
        })
    return out
