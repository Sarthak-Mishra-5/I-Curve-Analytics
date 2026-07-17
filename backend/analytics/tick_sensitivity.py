"""Relative volatility / tick beta: how many ER3 ticks per 1 SA3 tick?"""
from __future__ import annotations

import numpy as np

from ..config import DV01_PER_TICK, ER3_NAMES, ROLLING_WINDOW_MEDIUM, SA3_NAMES, TICK_SIZE
from ..streaming.state import MarketState


def compute_tick_sensitivity(state: MarketState) -> list[dict]:
    out: list[dict] = []
    for sa, er in zip(SA3_NAMES, ER3_NAMES):
        y, x = state.aligned_pair(sa, er, ROLLING_WINDOW_MEDIUM)
        if y.size < 10:
            continue
        ry = np.diff(y)
        rx = np.diff(x)
        if ry.size < 5 or rx.size < 5:
            continue
        vol_y = float(np.std(ry))
        vol_x = float(np.std(rx))
        vol_ratio = vol_y / vol_x if vol_x > 1e-12 else 0.0
        denom = float(np.dot(rx, rx))
        tick_beta = float(np.dot(ry, rx) / denom) if denom > 1e-12 else 0.0
        # Express in ticks (price moves / tick size).
        ts_sa = TICK_SIZE["SA3"]
        ts_er = TICK_SIZE["ER3"]
        ticks_er_per_sa = (1.0 / tick_beta) * (ts_sa / ts_er) if abs(tick_beta) > 1e-12 else 0.0
        dv01_beta = tick_beta * (DV01_PER_TICK["SA3"] / DV01_PER_TICK["ER3"])
        out.append({
            "y": sa,
            "x": er,
            "vol_ratio": vol_ratio,
            "tick_beta": tick_beta,
            "ticks_er_per_sa": ticks_er_per_sa,
            "dv01_beta": dv01_beta,
        })
    return out
