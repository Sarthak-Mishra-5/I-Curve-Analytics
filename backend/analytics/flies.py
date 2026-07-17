"""Butterfly analytics: fly = 2*M - F - B."""
from __future__ import annotations

import numpy as np

from ..config import ER3_NAMES, ROLLING_WINDOW_LONG, ROLLING_WINDOW_SHORT, SA3_NAMES
from ..streaming.state import MarketState
from .fast import realized_vol, zscore


def compute_flies(state: MarketState) -> list[dict]:
    """Butterflies: fly = 2*M - F - B for consecutive 3-leg: Jun/Sep/Dec, Sep/Dec/Mar, etc."""
    out: list[dict] = []
    window_n = ROLLING_WINDOW_LONG

    for names in (SA3_NAMES, ER3_NAMES):
        prod = "SA3" if names == SA3_NAMES else "ER3"
        # Consecutive 3-leg butterflies: [i], [i+1], [i+2]
        for i in range(len(names) - 2):
            front, mid, back = names[i], names[i + 1], names[i + 2]
            tf = front.split()[-1]
            tm = mid.split()[-1]
            tb = back.split()[-1]
            label = f"{tf}/{tm}/{tb} {prod}"

            pf, pm = state.aligned_pair(front, mid, window_n)
            pf2, pb = state.aligned_pair(front, back, window_n)
            k = min(pf.size, pm.size, pf2.size, pb.size)
            if k < 2:
                continue
            series = 2.0 * pm[-k:] - pf[-k:] - pb[-k:]

            out.append({
                "name": label,
                "legs": [front, mid, back],
                "value": float(series[-1]),
                "mean": float(np.mean(series)),
                "std": float(np.std(series)),
                "zscore": zscore(series, ROLLING_WINDOW_SHORT),
                "vol": realized_vol(series, ROLLING_WINDOW_SHORT),
            })
    return out
