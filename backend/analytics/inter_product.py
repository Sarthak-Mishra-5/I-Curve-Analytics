"""Inter-Product Lab: combine structures from DIFFERENT STIR curves (each its
own CurveHistoryStore/vendor-code namespace) into a relative-value trade, and
run the same regression/correlation/hedge-ratio analytics the single-curve
custom-structure engine already uses on each leg individually, on the
leg-vs-leg relationship, and on the combined RV series.

Deliberately builds ON TOP of custom_structure.py rather than duplicating it:
parse_weights/hedge-ratio math/rolling_correlation_points/the vendor+store
merge primitive are all reused as-is. The one thing that engine can't do is
merge two *different* curves' stores into one aligned series (every existing
cross-structure function there takes a single store for both sides) — that
per-leg merge + N-way date-keyed alignment is the only genuinely new logic
here; see _merged_leg_series (in custom_structure.py) and align_legs below.

No auto-rolling: every leg here is a fixed structure (e.g. "Sep26-Dec26"),
not a curve position to be rolled forward through time, so
custom_structure.roll_structures (which needs one homogeneous outright index
space) isn't used — this is what makes cross-product legs tractable at all.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from statsmodels.tsa.stattools import adfuller

from ..curves.registry import INSTRUMENT_TO_CURVE
from .curve_history import CurveHistoryStore
from .custom_structure import (
    CORR_HISTORY_DAYS,
    CORR_MIN_OBS,
    CORR_WINDOW_OBS,
    MIN_OBS,
    StructureError,
    _iso,
    _merged_leg_series,
    lowess_beta,
    parse_weights,
    rolling_correlation_points,
)
from .fast import rolling_mean_std
from .ols import ols

# Rolling-window presets exposed in the UI, mapped to a daily-observation
# count. Same "daily bar" cadence the rest of this data path (custom_structure
# / historical_correlation) already assumes.
WINDOW_TO_OBS: dict[str, int] = {
    "5D": 5, "10D": 10, "20D": 20, "30D": 30,
    "60D": 60, "90D": 90, "180D": 180, "1Y": 365,
}

MAX_LEGS = 8  # data-model ceiling; the route enforces exactly 2 for V1 (see inter_product_routes.py)


@dataclass(frozen=True)
class LegInput:
    """One leg as sent by the API: which curve, which store to read it from,
    that curve's own outrights (for parse_weights), a sparse weight dict, and
    the trade-level side/lots that only ever affect the RV combination —
    never how the leg's own value/statistics are computed."""

    curve_id: str
    store: CurveHistoryStore
    outrights: list[str]
    weights: dict[str, int]
    side: str  # "LONG" | "SHORT"
    lots: float = 1.0
    label: str = ""


@dataclass(frozen=True)
class ResolvedLeg:
    curve_id: str
    named: list[tuple[str, int]]
    formula_display: str
    label: str
    side: str
    lots: float


def _short_tenor(name: str) -> str:
    return name.split(" ", 1)[1] if " " in name else name


def resolve_leg(leg: LegInput) -> ResolvedLeg:
    """Two resolution paths, matching how this system already represents
    structures:

    1) A single-key {name: 1} weight dict where `name` is already one of this
       curve's own fed instruments (outright OR a direct-fed 3MS/6MS/3MF
       spread/fly) is taken directly — this is the REAL quoted price for
       that structure, consistent with spreads_mode="direct_feed" and with
       how the built-in 3MS/3MF tables already work. No tenor synthesis.
    2) Anything else is an arbitrary weight vector over this curve's
       outrights, resolved via the exact same parse_weights() the
       custom-structure builder already uses (condors, hand-built flies,
       etc.), unrolled (roll_structures is not needed here — see module
       docstring).
    """
    weights = leg.weights
    if len(weights) == 1:
        ((name, weight),) = weights.items()
        if weight == 1 and INSTRUMENT_TO_CURVE.get(name) == leg.curve_id:
            return ResolvedLeg(
                curve_id=leg.curve_id, named=[(name, 1)], formula_display=name,
                label=leg.label or name, side=leg.side, lots=leg.lots,
            )
    parsed = parse_weights(leg.outrights, weights)
    named = [(leg.outrights[i], w) for i, w in parsed]
    formula_display = " + ".join(f"({w:+d} × {_short_tenor(name)})" for name, w in named)
    return ResolvedLeg(
        curve_id=leg.curve_id, named=named, formula_display=formula_display,
        label=leg.label or f"{leg.curve_id} custom", side=leg.side, lots=leg.lots,
    )


def align_legs(
    leg_series: list[dict[str, tuple[float, float]]],
    start_date: str | None,
    end_date: str | None,
    history_days: int,
) -> tuple[list[str], np.ndarray, list[np.ndarray]]:
    """N-way join of independently-built per-leg {date: (ts, value)} series on
    CALENDAR DATE — never on raw epoch timestamp and never on array index.
    Legs on different products/exchanges have no shared tick clock (unlike
    two legs of the same curve, which _merged_series/build_series can safely
    join on exact 60s-bucket ts); the only convention two different curves'
    "Sep26" tenors actually share is the calendar quarter itself
    (config.TENOR_ORDER is already product-agnostic), so date is the correct
    and only safe join key here. A date missing from any one leg's series is
    dropped for all legs, rather than silently reusing a stale value.
    """
    from .custom_structure import _dates_in_range  # local import: avoid widening the public reuse surface

    if not leg_series:
        return [], np.empty(0), []
    shared = set(leg_series[0])
    for m in leg_series[1:]:
        shared &= set(m)
    dates = _dates_in_range(sorted(shared), start_date, end_date, history_days)
    if not dates:
        return [], np.empty(0), [np.empty(0) for _ in leg_series]
    ts = np.array([leg_series[0][d][0] for d in dates], dtype=np.float64)
    values = [np.array([m[d][1] for d in dates], dtype=np.float64) for m in leg_series]
    return dates, ts, values


def _empty_leg_stats(n: int) -> dict:
    return {
        "n": n, "current": None, "mean": None, "std": None, "min": None, "max": None,
        "percentile": None, "z_score": None, "volatility": None, "rolling_volatility": None,
    }


def leg_statistics(values: np.ndarray, window_obs: int) -> dict:
    """Per-leg (or RV) point statistics. Conventions deliberately match the
    rest of this data path rather than backend/analytics/fast.py's tick-engine
    versions:
      - volatility = std of first differences (matches fast.realized_vol's
        definition exactly; NOT annualized — this codebase never annualizes).
      - percentile = (values <= current).mean()*100, matching
        custom_structure.build_comparison's existing formula (not
        fast.percentile_of_last's slightly different rank formula).
      - z_score is None (not fast.zscore's silent 0.0) when std is ~0 or
        there aren't enough observations — never a misleading "0".
    """
    n = int(values.size)
    if n < MIN_OBS:
        return _empty_leg_stats(n)
    mean, std = float(np.mean(values)), float(np.std(values))
    current = float(values[-1])
    diffs = np.diff(values)
    vol = float(np.std(diffs)) if diffs.size else None
    window_diffs = diffs[-window_obs:] if diffs.size > window_obs else diffs
    rolling_vol = float(np.std(window_diffs)) if window_diffs.size >= 2 else None
    z = (current - mean) / std if std > 1e-12 else None
    percentile = float((values <= current).mean() * 100.0)
    return {
        "n": n, "current": current, "mean": mean, "std": std,
        "min": float(values.min()), "max": float(values.max()),
        "percentile": percentile, "z_score": z,
        "volatility": vol, "rolling_volatility": rolling_vol,
    }


def rv_statistics(values: np.ndarray, window_obs: int) -> dict:
    """Everything leg_statistics gives, plus the RV-only stats the user asked
    for that have no existing precedent anywhere in this codebase (median,
    drawdown, win rate, avg move, a Sharpe-*like* ratio). Each new one is
    defined plainly here rather than borrowed from an unrelated convention:
      - max_drawdown: largest peak-to-trough decline of the RV LEVEL itself
        (RV is a spread/price level, not a cumulative return index), i.e.
        min(value - running_max(value)) <= 0.
      - sharpe_like: mean(diff) / vol(diff) — explicitly NOT a risk-free-rate
        -adjusted Sharpe ratio; labeled to avoid that impression.
    """
    base = leg_statistics(values, window_obs)
    n = base["n"]
    extra = {
        "median": None, "rolling_mean": None, "rolling_std": None, "rolling_z_score": None,
        "max_drawdown": None, "sharpe_like": None, "win_rate": None,
        "avg_positive_move": None, "avg_negative_move": None, "range": None,
    }
    if n < MIN_OBS:
        return {**base, **extra}

    diffs = np.diff(values)
    window = values[-window_obs:] if values.size > window_obs else values
    rolling_mean = float(np.mean(window)) if window.size else None
    rolling_std = float(np.std(window)) if window.size >= 2 else None
    rolling_z = (
        (float(values[-1]) - rolling_mean) / rolling_std
        if rolling_mean is not None and rolling_std and rolling_std > 1e-12
        else None
    )
    running_max = np.maximum.accumulate(values)
    max_drawdown = float((values - running_max).min())
    mean_diff = float(np.mean(diffs)) if diffs.size else None
    vol_diff = base["volatility"]
    sharpe_like = (
        mean_diff / vol_diff if mean_diff is not None and vol_diff and vol_diff > 1e-12 else None
    )
    pos, neg = diffs[diffs > 0], diffs[diffs < 0]
    extra.update({
        "median": float(np.median(values)),
        "rolling_mean": rolling_mean, "rolling_std": rolling_std, "rolling_z_score": rolling_z,
        "max_drawdown": max_drawdown, "sharpe_like": sharpe_like,
        "win_rate": float((diffs > 0).mean()) if diffs.size else None,
        "avg_positive_move": float(pos.mean()) if pos.size else None,
        "avg_negative_move": float(neg.mean()) if neg.size else None,
        "range": float(base["max"] - base["min"]),
    })
    return {**base, **extra}


def _empty_relationship_stats(n: int, label_a: str, label_b: str) -> dict:
    return {
        "n": n, "correlation": None, "correlation_returns": None,
        "rolling_correlation": None, "rolling_correlation_points": [],
        "regression_alpha": None, "regression_beta": None, "r_squared": None,
        "lowess_beta": None, "hedge_ratio": None,
        "residual_std": None, "residual_z_score": None,
        "cointegrated": None, "adf_pvalue": None,
        "regression_definition": f"insufficient aligned observations (n={n}) between {label_a} and {label_b}",
    }


def relationship_statistics(
    ts: np.ndarray, values_a: np.ndarray, values_b: np.ndarray, window_obs: int,
    label_a: str = "Leg 1", label_b: str = "Leg 2",
) -> dict:
    """Leg-vs-leg relationship. Correlation of price LEVELS is the primary/
    default figure — matches rolling_correlation_points / historical_
    correlation.py / build_comparison, the established convention everywhere
    else in this codebase. correlation_returns (day-over-day change
    correlation) is computed too but kept under its own clearly-separate
    field so the two are never conflated, per an explicit requirement.

    beta/hedge_ratio direction: beta is the OLS slope regressing Leg 1's
    values (Y) on Leg 2's values (X), i.e. Leg1 ~= alpha + beta*Leg2 — and
    hedge_ratio is defined as exactly that beta (not its reciprocal), so that
    "SHORT hedge_ratio x Leg 2" hedges "LONG 1x Leg 1", matching the worked
    example in the spec directly. regression_definition spells this out so
    it's never ambiguous which series was Y and which was X.
    """
    n = int(ts.size)
    if n < MIN_OBS:
        return _empty_relationship_stats(n, label_a, label_b)

    corr = (
        float(np.corrcoef(values_a, values_b)[0, 1])
        if np.std(values_a) > 1e-12 and np.std(values_b) > 1e-12 else None
    )
    ret_a, ret_b = np.diff(values_a), np.diff(values_b)
    corr_returns = (
        float(np.corrcoef(ret_a, ret_b)[0, 1])
        if ret_a.size >= 2 and np.std(ret_a) > 1e-12 and np.std(ret_b) > 1e-12 else None
    )

    alpha, beta, r2, resid = ols(values_a, values_b)  # Y = Leg 1, X = Leg 2
    hedge_ratio_val = beta if beta else None
    resid_std = float(np.std(resid)) if resid.size else None
    resid_z = (
        float((resid[-1] - np.mean(resid)) / resid_std)
        if resid.size and resid_std and resid_std > 1e-12 else None
    )
    cointegrated, adf_pvalue = None, None
    try:
        _, adf_p, *_ = adfuller(resid, maxlag=5, autolag=None)
        adf_pvalue = float(adf_p)
        cointegrated = adf_pvalue < 0.05
    except Exception:  # noqa: BLE001
        pass

    rc_points = rolling_correlation_points(
        ts, values_a, values_b, window_obs=window_obs, min_obs=min(CORR_MIN_OBS, window_obs),
    )

    return {
        "n": n,
        "correlation": corr,
        "correlation_returns": corr_returns,
        "rolling_correlation": rc_points[-1]["correlation"] if rc_points else None,
        "rolling_correlation_points": rc_points,
        "regression_alpha": alpha, "regression_beta": beta, "r_squared": r2,
        "lowess_beta": lowess_beta(values_a, values_b),
        "hedge_ratio": hedge_ratio_val,
        "residual_std": resid_std, "residual_z_score": resid_z,
        "cointegrated": cointegrated, "adf_pvalue": adf_pvalue,
        "regression_definition": (
            f"beta = OLS slope of {label_a} (Y) regressed on {label_b} (X) over {n} "
            f"calendar-date-aligned observations; hedge_ratio = beta directly, i.e. "
            f"the units of {label_b} that hedge one unit of {label_a}. Correlation "
            f"above is of price LEVELS (this platform's default convention) — "
            f"correlation_returns (day-over-day change correlation) is separate and "
            f"must not be conflated with it."
        ),
    }


def _rv_band_points(dates: list[str], values: np.ndarray, window_obs: int) -> list[dict]:
    if not dates:
        return []
    means, stds = rolling_mean_std(values, window_obs)
    return [
        {
            "date": d, "rv": float(values[i]), "rolling_mean": float(means[i]),
            "upper_1sd": float(means[i] + stds[i]), "lower_1sd": float(means[i] - stds[i]),
            "upper_2sd": float(means[i] + 2 * stds[i]), "lower_2sd": float(means[i] - 2 * stds[i]),
        }
        for i, d in enumerate(dates)
    ]


def _rv_zscore_points(dates: list[str], values: np.ndarray, window_obs: int) -> list[dict]:
    if not dates:
        return []
    means, stds = rolling_mean_std(values, window_obs)
    return [
        {"date": d, "z_score": float((values[i] - means[i]) / stds[i]) if stds[i] > 1e-12 else None}
        for i, d in enumerate(dates)
    ]


def build_inter_product_analysis(
    legs: list[LegInput], window: str, start_date: str | None = None, end_date: str | None = None,
    history_days: int = CORR_HISTORY_DAYS,
) -> dict:
    """Top-level orchestrator. V1 is written for exactly 2 legs (the route
    enforces this), but the alignment/summation below is N-way from the
    start (set-intersection over all legs' date keys, elementwise sum of all
    signed leg series) — extending to 3+ legs later only needs the route's
    len(legs)==2 check relaxed plus a correlation-MATRIX UI, not a rewrite of
    this function. The pairwise relationship/regression/scatter outputs are
    explicitly between legs[0] and legs[1] only; documented, not silently
    assumed.
    """
    if len(legs) < 2:
        raise StructureError("at least 2 legs are required")
    if len(legs) > MAX_LEGS:
        raise StructureError(f"at most {MAX_LEGS} legs are supported, got {len(legs)}")
    if window not in WINDOW_TO_OBS:
        raise StructureError(f"unknown window '{window}'; expected one of {sorted(WINDOW_TO_OBS)}")
    window_obs = WINDOW_TO_OBS[window]

    resolved = [resolve_leg(leg) for leg in legs]
    count = history_days + CORR_WINDOW_OBS + 10
    leg_maps = [_merged_leg_series(leg.store, r.named, count) for leg, r in zip(legs, resolved)]
    dates, ts, value_arrays = align_legs(leg_maps, start_date, end_date, history_days)
    n = len(dates)

    signed = [
        (vals * (1.0 if r.side == "LONG" else -1.0) * r.lots) if n else np.empty(0)
        for vals, r in zip(value_arrays, resolved)
    ]
    rv_raw = np.sum(signed, axis=0) if n else np.empty(0)

    leg_stats = [leg_statistics(vals, window_obs) for vals in value_arrays]

    relationship = (
        relationship_statistics(ts, value_arrays[0], value_arrays[1], window_obs, resolved[0].label, resolved[1].label)
        if n else _empty_relationship_stats(0, resolved[0].label, resolved[1].label)
    )
    rv_stats = rv_statistics(rv_raw, window_obs)

    # Hedge-ratio-adjusted alternative: computed alongside the raw trade on
    # every request (so the frontend can toggle instantly, no re-fetch), but
    # never substituted for the raw trade automatically. Leg 1's lots are the
    # anchor; Leg 2's lots are replaced (not scaled) by lots(Leg1) * hedge_ratio.
    hedge_ratio_val = relationship.get("hedge_ratio")
    if hedge_ratio_val is not None and n:
        adjusted_lots_leg2 = resolved[0].lots * hedge_ratio_val
        hedge_signed = [
            signed[0],
            value_arrays[1] * (1.0 if resolved[1].side == "LONG" else -1.0) * adjusted_lots_leg2,
        ]
        rv_hedge = np.sum(hedge_signed, axis=0)
        rv_hedge_stats = rv_statistics(rv_hedge, window_obs)
    else:
        adjusted_lots_leg2 = None
        rv_hedge_stats = rv_statistics(np.empty(0), window_obs)

    def _side_summary(lots_2: float | None) -> str:
        if lots_2 is None:
            return ""
        return (
            f"{resolved[0].side} {resolved[0].lots:g}x {resolved[0].label} / "
            f"{resolved[1].side} {lots_2:g}x {resolved[1].label}"
        )

    return {
        "generated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "window": window,
        "n": n,
        "legs": [
            {
                "curve_id": r.curve_id, "label": r.label, "side": r.side, "lots": r.lots,
                "formula": r.formula_display, "statistics": stats,
            }
            for r, stats in zip(resolved, leg_stats)
        ],
        "relationship": relationship,
        "rv": {
            "raw": {"side_summary": _side_summary(resolved[1].lots), "statistics": rv_stats},
            "hedge_adjusted": {
                "hedge_ratio": hedge_ratio_val,
                "adjusted_lots_leg2": adjusted_lots_leg2,
                "side_summary": _side_summary(adjusted_lots_leg2),
                "statistics": rv_hedge_stats,
            },
        },
        "chart_data": {
            "leg_price_points": [
                {"date": d, "a": float(value_arrays[0][i]), "b": float(value_arrays[1][i])}
                for i, d in enumerate(dates)
            ],
            "rolling_correlation_points": relationship.get("rolling_correlation_points", []),
            "rv_points": _rv_band_points(dates, rv_raw, window_obs),
            "zscore_points": _rv_zscore_points(dates, rv_raw, window_obs),
            "scatter_points": [
                {"a": float(a), "b": float(b)} for a, b in zip(value_arrays[0], value_arrays[1])
            ],
        },
    }
