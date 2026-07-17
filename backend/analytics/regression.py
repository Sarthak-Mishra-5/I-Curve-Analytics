"""OLS regression analytics: alpha, beta, R², residuals, residual z-score, rolling beta."""
from __future__ import annotations

import numpy as np

from ..config import ER3_NAMES, ROLLING_WINDOW_LONG, ROLLING_WINDOW_MEDIUM, SA3_NAMES
from ..streaming.state import MarketState
from .fast import zscore
from .ols import ols as _ols


def compute_regressions(state: MarketState) -> list[dict]:
    out: list[dict] = []
    # Pair-by-tenor regressions SA3 ~ ER3
    for sa, er in zip(SA3_NAMES, ER3_NAMES):
        y, x = state.aligned_pair(sa, er, ROLLING_WINDOW_LONG)
        if y.size < 10:
            continue
        alpha, beta, r2, resid = _ols(y, x)
        rz = zscore(resid, ROLLING_WINDOW_MEDIUM) if resid.size else 0.0

        # Rolling beta — last short window vs prior window.
        rolling_beta = float("nan")
        if y.size >= 60:
            ys, xs = y[-30:], x[-30:]
            _, rolling_beta, _, _ = _ols(ys, xs)

        out.append({
            "x": er,
            "y": sa,
            "alpha": alpha,
            "beta": beta,
            "r2": r2,
            "residual": float(resid[-1]) if resid.size else 0.0,
            "residual_z": rz,
            "rolling_beta": rolling_beta,
            "n": int(y.size),
        })
    return out
