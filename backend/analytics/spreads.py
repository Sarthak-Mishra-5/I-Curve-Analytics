"""Calendar, curve, and cross-product spread analytics."""
from __future__ import annotations

from typing import Iterable

import numpy as np

from ..config import (
    ER3_NAMES,
    ROLLING_WINDOW_LONG,
    ROLLING_WINDOW_MEDIUM,
    ROLLING_WINDOW_SHORT,
    SA3_NAMES,
)
from ..streaming.state import MarketState
from .fast import percentile_of_last, realized_vol, zscore


def compute_spreads(state: MarketState) -> list[dict]:
    """Spreads: front-back (3M + 6M only). E.g. Jun26 - Sep26 (3M), Sep26 - Dec26 (6M)."""
    out: list[dict] = []
    window_n = ROLLING_WINDOW_LONG

    for names in (SA3_NAMES, ER3_NAMES):
        prod = "SA3" if names == SA3_NAMES else "ER3"
        # Only consecutive pairs: [0]-[1], [1]-[2], [2]-[3], ... (3M spreads)
        # and [0]-[2], [1]-[3], [2]-[4], ... (6M spreads)
        for i in range(len(names) - 1):
            near, far = names[i], names[i + 1]
            tenor_near = near.split()[-1]
            tenor_far = far.split()[-1]
            label = f"{tenor_near}-{tenor_far} {prod}"
            a, b = state.aligned_pair(far, near, window_n)
            if a.size < 2:
                continue
            series = a - b
            last = float(series[-1])
            mu = float(np.mean(series))
            sd = float(np.std(series))
            z = zscore(series, ROLLING_WINDOW_SHORT)
            pct = percentile_of_last(series, ROLLING_WINDOW_LONG)
            vol = realized_vol(series, ROLLING_WINDOW_MEDIUM)
            out.append({
                "name": label,
                "legs": [far, near],
                "value": last,
                "mean": mu,
                "std": sd,
                "zscore": z,
                "percentile": pct,
                "vol": vol,
            })
    return out
