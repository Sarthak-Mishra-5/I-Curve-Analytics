"""Shared OLS helper: Y = alpha + beta * X."""
from __future__ import annotations

import numpy as np


def ols(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    if x.size < 5:
        return 0.0, 0.0, 0.0, np.empty(0)
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    yhat = X @ coef
    resid = y - yhat
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return alpha, beta, r2, resid
