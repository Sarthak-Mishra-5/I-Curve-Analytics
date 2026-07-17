"""Yield curve: per-tenor mid prices + PCA decomposition (level/slope/curvature)."""
from __future__ import annotations

import numpy as np

from ..config import ER3_NAMES, ROLLING_WINDOW_MEDIUM, SA3_NAMES
from ..streaming.state import MarketState


def _curve_for(state: MarketState, names: list[str]) -> list[dict]:
    pts: list[dict] = []
    for n in names:
        q = state.quotes.get(n)
        if q is None:
            continue
        pts.append({
            "tenor": n.split()[-1],
            "instrument": n,
            "mid": q.mid,
            "price": q.price,
            "bid": q.bid,
            "ask": q.ask,
        })
    return pts


def _pca_factors(state: MarketState, names: list[str], n_obs: int = ROLLING_WINDOW_MEDIUM) -> dict:
    series = [state.prices(n, n_obs) for n in names]
    m = min(s.size for s in series) if series else 0
    if m < 10:
        return {"level": None, "slope": None, "curvature": None}
    aligned = np.vstack([s[-m:] for s in series])
    rets = np.diff(aligned, axis=1)
    if rets.shape[1] < 3:
        return {"level": None, "slope": None, "curvature": None}
    cov = np.cov(rets)
    try:
        eigvals, eigvecs = np.linalg.eigh(cov)
    except np.linalg.LinAlgError:
        return {"level": None, "slope": None, "curvature": None}
    # eigh returns ascending; take top 3.
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    total = float(eigvals.sum()) or 1.0
    return {
        "level_var_pct": float(eigvals[0] / total * 100) if eigvals.size > 0 else None,
        "slope_var_pct": float(eigvals[1] / total * 100) if eigvals.size > 1 else None,
        "curvature_var_pct": float(eigvals[2] / total * 100) if eigvals.size > 2 else None,
    }


def compute_curve(state: MarketState) -> dict:
    return {
        "SA3": _curve_for(state, SA3_NAMES),
        "ER3": _curve_for(state, ER3_NAMES),
        "pca": {
            "SA3": _pca_factors(state, SA3_NAMES),
            "ER3": _pca_factors(state, ER3_NAMES),
        },
    }
