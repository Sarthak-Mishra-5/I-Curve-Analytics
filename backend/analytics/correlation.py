"""Rolling correlation matrix across the front N contracts of SA3 and ER3."""
from __future__ import annotations

import numpy as np

from ..config import ER3_NAMES, ROLLING_WINDOW_MEDIUM, SA3_NAMES
from ..streaming.state import MarketState


def compute_correlation(state: MarketState, top_n: int = 6) -> dict:
    names = SA3_NAMES[:top_n] + ER3_NAMES[:top_n]
    series: list[np.ndarray] = []
    for n in names:
        series.append(state.prices(n, ROLLING_WINDOW_MEDIUM))

    m = min(s.size for s in series) if series else 0
    if m < 5:
        return {"rows": names, "cols": names, "matrix": np.eye(len(names)).tolist()}

    # Use returns (diffs) so correlations reflect co-movement, not levels.
    aligned = np.vstack([s[-m:] for s in series])
    rets = np.diff(aligned, axis=1)
    if rets.shape[1] < 2:
        return {"rows": names, "cols": names, "matrix": np.eye(len(names)).tolist()}
    # Guard against zero-variance rows.
    std = rets.std(axis=1)
    std[std < 1e-12] = 1.0
    centered = (rets - rets.mean(axis=1, keepdims=True)) / std[:, None]
    corr = (centered @ centered.T) / rets.shape[1]
    # Clamp numerical drift.
    corr = np.clip(corr, -1.0, 1.0)
    return {"rows": names, "cols": names, "matrix": corr.tolist()}
