"""Timestamp-aligned previous-vs-current pairwise statistics for a curve.

For every (previous, current) pair in a CurveSpec's 3ms/6ms/3mf ordering:
correlation, OLS beta (Y=current, X=previous), and the current contract's
value at the exact bar-timestamp the previous contract hit its 30-day max
and min.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from ..curves.registry import CurveSpec
from .curve_history import CurveHistoryStore
from .ols import ols

MIN_OBS = 30  # minimum overlapping bars before a pair's stats are trusted


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _empty_row(previous: str, current: str, n: int) -> dict:
    return {
        "previous": previous,
        "current": current,
        "n": n,
        "correlation": None,
        "beta": None,
        "prev_max": None,
        "prev_max_ts": None,
        "curr_at_prev_max": None,
        "prev_min": None,
        "prev_min_ts": None,
        "curr_at_prev_min": None,
    }


def compute_pair_stats(store: CurveHistoryStore, previous: str, current: str) -> dict:
    ts, pv, cv = store.paired_window(previous, current)
    n = int(ts.size)
    if n < MIN_OBS:
        return _empty_row(previous, current, n)

    corr = (
        float(np.corrcoef(pv, cv)[0, 1])
        if np.std(pv) > 1e-12 and np.std(cv) > 1e-12
        else None
    )
    _, beta, _, _ = ols(cv, pv)  # Y = current, X = previous

    i_max = int(np.argmax(pv))
    i_min = int(np.argmin(pv))

    return {
        "previous": previous,
        "current": current,
        "n": n,
        "correlation": corr,
        "beta": beta,
        "prev_max": float(pv[i_max]),
        "prev_max_ts": _iso(ts[i_max]),
        "curr_at_prev_max": float(cv[i_max]),
        "prev_min": float(pv[i_min]),
        "prev_min_ts": _iso(ts[i_min]),
        "curr_at_prev_min": float(cv[i_min]),
    }


def compute_curve_tables(store: CurveHistoryStore, spec: CurveSpec) -> dict[str, list[dict]]:
    if spec.spreads_mode != "direct_feed":
        raise NotImplementedError(
            f"curve '{spec.curve_id}': computed spreads/flies are not yet supported"
        )
    return {
        category: [compute_pair_stats(store, prev, curr) for prev, curr in spec.pairs(category)]
        for category in ("3ms", "6ms", "3mf")
    }
