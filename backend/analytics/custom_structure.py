"""Generic engine: derive a structure's historical time series from a sparse
integer weight vector over a curve's outright contracts, auto-roll it forward
across the curve, and run the same previous/current pairwise analytics used
by the built-in 3MS/3MF tables (see pair_stats.py) on each consecutive rolled
pair. A Structure Comparison (two exact, non-rolled structures) reuses the
same series-building and regression/hedge-ratio pieces but produces a single
relationship row instead of a table.

The engine never distinguishes "built-in" vs "custom" structures — every
structure here is just a weighted sum of outright prices.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from statsmodels.tsa.stattools import adfuller

from .curve_history import CurveHistoryStore
from .ols import ols

MAX_LEGS = 8
MIN_OBS = 30
LOWESS_FRAC = 0.3
CORR_WINDOW_OBS = 30
CORR_MIN_OBS = 10
CORR_HISTORY_DAYS = 180
BENCHMARK_HISTORY_COUNT = 1400


class StructureError(ValueError):
    """Invalid weight-vector input (bad legs, too many legs, curve too short to roll)."""


@dataclass(frozen=True)
class Structure:
    """One instance of a structure: an ordered list of (instrument_name,
    weight) legs, labeled by the tenor of its first (nearest-dated) leg."""

    label: str
    legs: list[tuple[str, int]]


def parse_weights(outrights: list[str], weights: dict[str, int]) -> list[tuple[int, int]]:
    """Validate a sparse {instrument_name: weight} map and return
    [(index_in_outrights, weight), ...] sorted by index, ascending."""
    legs: list[tuple[int, int]] = []
    for name, weight in weights.items():
        if not weight:
            continue
        if not isinstance(weight, int):
            raise StructureError(f"weight for '{name}' must be an integer")
        try:
            idx = outrights.index(name)
        except ValueError:
            raise StructureError(f"'{name}' is not an outright on this curve") from None
        legs.append((idx, weight))
    if not legs:
        raise StructureError("at least one non-zero leg is required")
    if len(legs) > MAX_LEGS:
        raise StructureError(f"at most {MAX_LEGS} non-zero legs are allowed, got {len(legs)}")
    legs.sort(key=lambda pair: pair[0])
    return legs


def dense_formula(outrights: list[str], weights: dict[str, int]) -> list[int]:
    """Render weights as a full-width row aligned to `outrights`, for display
    exactly as the user typed it (zeros included, never converted to signed
    contract names)."""
    return [int(weights.get(name, 0) or 0) for name in outrights]


def roll_structures(outrights: list[str], legs: list[tuple[int, int]]) -> list[Structure]:
    """Auto-roll: shift every leg's index forward by the same amount, one
    quarterly contract at a time, until the furthest leg would run off the
    end of the curve. Roll 0 is exactly as entered by the user."""
    base = legs[0][0]
    offsets = [(idx - base, weight) for idx, weight in legs]
    max_offset = offsets[-1][0]
    structures: list[Structure] = []
    shift = 0
    while base + shift + max_offset < len(outrights):
        rolled = [(outrights[base + shift + offset], weight) for offset, weight in offsets]
        structures.append(Structure(label=outrights[base + shift], legs=rolled))
        shift += 1
    return structures


def build_series(store: CurveHistoryStore, legs: list[tuple[str, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Weighted sum of leg prices, inner-joined on shared bar timestamp
    (generalizes CurveHistoryStore.paired_window's 2-series join to N legs)."""
    leg_bars = [store.bars_map(name) for name, _ in legs]
    if any(not bars for bars in leg_bars):
        return np.empty(0), np.empty(0)
    shared = sorted(set.intersection(*(set(bars) for bars in leg_bars)))
    if not shared:
        return np.empty(0), np.empty(0)
    ts = np.array(shared, dtype=np.float64)
    values = np.zeros(len(shared), dtype=np.float64)
    for bars, (_, weight) in zip(leg_bars, legs):
        values += weight * np.array([bars[t] for t in shared], dtype=np.float64)
    return ts, values


def _iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).isoformat()


def _date_key(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).date().isoformat()


def _paired(
    prev_ts: np.ndarray, prev_val: np.ndarray, curr_ts: np.ndarray, curr_val: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Inner-join two independently-built series on shared timestamp."""
    prev_map = dict(zip(prev_ts.tolist(), prev_val.tolist()))
    curr_map = dict(zip(curr_ts.tolist(), curr_val.tolist()))
    shared = sorted(set(prev_map) & set(curr_map))
    if not shared:
        return np.empty(0), np.empty(0), np.empty(0)
    ts = np.array(shared, dtype=np.float64)
    pv = np.array([prev_map[t] for t in shared], dtype=np.float64)
    cv = np.array([curr_map[t] for t in shared], dtype=np.float64)
    return ts, pv, cv


def lowess_beta(y: np.ndarray, x: np.ndarray) -> float | None:
    """Local (non-parametric) slope near the most recent observation, from a
    LOWESS smooth of y against x — a robustness check against the single
    global OLS beta. Estimated via a local linear fit over a small window of
    smoothed grid points around the most recent x, rather than a 2-point
    finite difference between adjacent grid points: the smoothed grid can
    have near-duplicate x's (common with tick-quantized prices), which made
    the finite-difference version either bail to None or, worse, return
    floating-point noise (e.g. -2e-15) disguised as a real near-zero slope."""
    if x.size < 10:
        return None
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    smoothed = lowess(ys, xs, frac=LOWESS_FRAC, return_sorted=True)
    sx, sy = smoothed[:, 0], smoothed[:, 1]
    if sx.size < 5:
        return None
    i = int(np.searchsorted(sx, x[-1]))
    i = min(max(i, 0), sx.size - 1)
    half_window = max(3, sx.size // 20)
    lo, hi = max(0, i - half_window), min(sx.size, i + half_window + 1)
    window_x, window_y = sx[lo:hi], sy[lo:hi]
    if window_x.size < 5 or np.ptp(window_x) < 1e-9:
        return None
    _, beta, _, _ = ols(window_y, window_x)
    return beta


def hedge_ratio(beta: float | None) -> float | None:
    """Units of 'previous'/'A' needed per unit of 'current'/'B' to be beta-
    neutral. Kept as its own function so a future DV01-weighted definition
    can replace it without touching the callers."""
    if not beta:
        return None
    return 1.0 / beta


def _empty_row(previous: str, current: str, n: int) -> dict:
    return {
        "previous": previous, "current": current, "n": n,
        "correlation": None, "regression_beta": None, "lowess_beta": None, "hedge_ratio": None,
        "prev_max": None, "prev_max_ts": None, "curr_at_prev_max": None,
        "prev_min": None, "prev_min_ts": None, "curr_at_prev_min": None,
        "live_price": None,
    }


def row_stats(
    prev_ts: np.ndarray, prev_val: np.ndarray, curr_ts: np.ndarray, curr_val: np.ndarray,
    previous_label: str, current_label: str,
) -> dict:
    ts, pv, cv = _paired(prev_ts, prev_val, curr_ts, curr_val)
    n = int(ts.size)
    if n < MIN_OBS:
        return _empty_row(previous_label, current_label, n)

    corr = (
        float(np.corrcoef(pv, cv)[0, 1])
        if np.std(pv) > 1e-12 and np.std(cv) > 1e-12
        else None
    )
    _, beta, _, _ = ols(cv, pv)  # Y = current, X = previous
    i_max, i_min = int(np.argmax(pv)), int(np.argmin(pv))

    return {
        "previous": previous_label,
        "current": current_label,
        "n": n,
        "correlation": corr,
        "regression_beta": beta,
        "lowess_beta": lowess_beta(cv, pv),
        "hedge_ratio": hedge_ratio(beta),
        "prev_max": float(pv[i_max]), "prev_max_ts": _iso(ts[i_max]), "curr_at_prev_max": float(cv[i_max]),
        "prev_min": float(pv[i_min]), "prev_min_ts": _iso(ts[i_min]), "curr_at_prev_min": float(cv[i_min]),
        "live_price": float(curr_val[-1]) if curr_val.size else None,
    }


def build_custom_structure(
    store: CurveHistoryStore, outrights: list[str], name: str, weights: dict[str, int], curve_id: str = ""
) -> dict:
    legs = parse_weights(outrights, weights)
    rolls = roll_structures(outrights, legs)
    if len(rolls) < 2:
        raise StructureError("not enough curve room to roll this structure forward even once")

    series_by_roll = [build_series(store, s.legs) for s in rolls]
    table = [
        row_stats(*series_by_roll[i - 1], *series_by_roll[i], rolls[i - 1].label, rolls[i].label)
        for i in range(1, len(rolls))
    ]
    benchmark_table = build_benchmark_correlations(store, rolls, curve_id)

    return {
        "name": name,
        "outrights": outrights,
        "formula": dense_formula(outrights, weights),
        "rolls": [{"label": s.label, "legs": dict(s.legs)} for s in rolls],
        "table": table,
        "benchmark_table": benchmark_table,
        "generated_at": _iso(datetime.now(timezone.utc).timestamp()),
    }


def _empty_comparison(formula_a: list[int], formula_b: list[int], n: int) -> dict:
    return {
        "formula_a": formula_a, "formula_b": formula_b, "n": n,
        "correlation": None, "regression_beta": None, "lowess_beta": None, "hedge_ratio": None,
        "current_spread": None, "z_score": None, "historical_percentile": None, "volatility_ratio": None,
        "cointegrated": None, "adf_pvalue": None,
        "live_price_a": None, "live_price_b": None,
    }


def build_comparison(
    store: CurveHistoryStore,
    outrights: list[str],
    weights_a: dict[str, int],
    weights_b: dict[str, int],
    start_date: str | None = None,
    end_date: str | None = None,
    history_days: int = CORR_HISTORY_DAYS,
) -> dict:
    """Exact (non-rolled) comparison of two structures — one relationship
    analysis (a plain, whole-period correlation — not a rolling series), not
    a rolling table. `start_date`/`end_date` (ISO 'YYYY-MM-DD') pick the
    comparison window; by default it's the trailing `history_days` (6mo),
    matching the correlation-history chart's default span. Stats are
    computed over the long-range vendor-API-plus-live-store series (see
    _merged_series) so the picked range isn't limited to the live store's
    own ~30-day retention."""
    legs_a = parse_weights(outrights, weights_a)
    legs_b = parse_weights(outrights, weights_b)
    named_a = [(outrights[i], w) for i, w in legs_a]
    named_b = [(outrights[i], w) for i, w in legs_b]

    formula_a, formula_b = dense_formula(outrights, weights_a), dense_formula(outrights, weights_b)

    # Live price: each structure's own most-recent value straight from the
    # store, independent of the comparison window/pairing above.
    _, live_val_a = build_series(store, named_a)
    _, live_val_b = build_series(store, named_b)
    live_price_a = float(live_val_a[-1]) if live_val_a.size else None
    live_price_b = float(live_val_b[-1]) if live_val_b.size else None

    merged = _merged_series(store, named_a, named_b, history_days)
    dates = _dates_in_range(sorted(merged), start_date, end_date, history_days)
    ts = np.array([merged[d][0] for d in dates], dtype=np.float64)
    va = np.array([merged[d][1] for d in dates], dtype=np.float64)
    vb = np.array([merged[d][2] for d in dates], dtype=np.float64)
    n = int(ts.size)

    result = _empty_comparison(formula_a, formula_b, n)
    result["generated_at"] = _iso(datetime.now(timezone.utc).timestamp())
    result["live_price_a"] = live_price_a
    result["live_price_b"] = live_price_b
    if n < MIN_OBS:
        return result

    corr = float(np.corrcoef(va, vb)[0, 1]) if np.std(va) > 1e-12 and np.std(vb) > 1e-12 else None
    _, beta, _, resid = ols(vb, va)  # Y = B, X = A
    spread = vb - va
    mean, std = float(spread.mean()), float(spread.std())
    z = float((spread[-1] - mean) / std) if std > 1e-12 else None
    percentile = float((spread <= spread[-1]).mean() * 100.0)

    vol_ratio = None
    if va.size > 1 and vb.size > 1:
        ret_a, ret_b = np.diff(va) / va[:-1], np.diff(vb) / vb[:-1]
        vol_a, vol_b = float(np.std(ret_a)), float(np.std(ret_b))
        vol_ratio = (vol_a / vol_b) if vol_b > 1e-12 else None

    cointegrated, adf_pvalue = None, None
    try:
        adf_stat, adf_p, *_ = adfuller(resid, maxlag=5, autolag=None)
        adf_pvalue = float(adf_p)
        cointegrated = adf_pvalue < 0.05
    except Exception:  # noqa: BLE001
        pass

    result.update({
        "correlation": corr,
        "regression_beta": beta,
        "lowess_beta": lowess_beta(vb, va),
        "hedge_ratio": hedge_ratio(beta),
        "current_spread": float(spread[-1]),
        "z_score": z,
        "historical_percentile": percentile,
        "volatility_ratio": vol_ratio,
        "cointegrated": cointegrated,
        "adf_pvalue": adf_pvalue,
    })
    return result


def rolling_correlation_points(
    ts: np.ndarray, a: np.ndarray, b: np.ndarray,
    window_obs: int = CORR_WINDOW_OBS, min_obs: int = CORR_MIN_OBS,
) -> list[dict]:
    """Day-bucketed rolling correlation between two already-paired series,
    one point per day using the last `window_obs` days up to and including
    that day (mirrors HistoricalCorrelationCache._compute_points).

    Reduces to one observation per calendar day *before* sliding the
    window: the vendor's historical bars are daily cadence but the live
    store is per-minute, so without this reduction `window_obs` silently
    means "30 days" in the older portion of a series and "30 raw ticks"
    (often under an hour) in the newer portion — producing spurious
    near-±1 or undefined correlations right where the two portions meet."""
    daily: dict[str, tuple[float, float, float]] = {}
    for t, av, bv in zip(ts.tolist(), a.tolist(), b.tolist()):
        daily[_date_key(t)] = (t, av, bv)
    dates = sorted(daily)
    ts = np.array([daily[d][0] for d in dates], dtype=np.float64)
    a = np.array([daily[d][1] for d in dates], dtype=np.float64)
    b = np.array([daily[d][2] for d in dates], dtype=np.float64)

    if ts.size < min_obs:
        return []
    points: list[dict] = []
    for idx in range(ts.size):
        end = idx + 1
        start = max(0, end - window_obs)
        a_window, b_window = a[start:end], b[start:end]
        n = int(a_window.size)
        if n < min_obs:
            continue
        corr = (
            float(np.corrcoef(a_window, b_window)[0, 1])
            if np.std(a_window) > 1e-12 and np.std(b_window) > 1e-12
            else None
        )
        points.append({"date": _date_key(ts[idx]), "correlation": corr, "n": n})
    return points


def _fetch_outright_history(names: list[str], count: int) -> dict[str, dict[float, float]]:
    """Daily historical bars for a set of outright names, fetched directly
    from the vendor historical API — independent of CurveHistoryStore, whose
    on-disk/in-memory retention is capped at CURVE_HISTORY_WINDOW_DAYS (30),
    far short of a 6-month chart. Returns {name: {epoch_sec: price}}; missing
    names on error/lookup-failure are simply absent (best-effort)."""
    from ..data.historical_api import curve_instrument_to_code, fetch_curve_bars

    curve_id = names[0].split()[0] if names else ""
    name_to_code = {
        name: code
        for name in names
        if (code := curve_instrument_to_code(curve_id, name)) is not None
    }
    if not name_to_code:
        return {}
    try:
        bars_by_code = fetch_curve_bars(sorted(set(name_to_code.values())), interval="1D", count=count)
    except Exception:  # noqa: BLE001
        return {}
    return {
        name: {ts.timestamp(): price for ts, price in bars_by_code.get(code, [])}
        for name, code in name_to_code.items()
    }


def _fetch_benchmark_history(curve_id: str, benchmark_names: list[str]) -> dict[str, dict[float, float]]:
    """Fetch this curve's configured benchmark structures using their native
    vendor product codes. A name with an explicit historical-code override
    (e.g. the ER3 anchor used for the "I" curve, which can't be derived from
    I outrights) uses that code; every other benchmark derives its code from
    the requesting curve's own naming convention (SA3/SO3/SR3 native spreads)."""
    from ..config import STRUCTURE_BENCHMARK_HISTORICAL_CODES
    from ..data.historical_api import curve_instrument_to_code, fetch_curve_bars

    name_to_code: dict[str, str] = {}
    for name in benchmark_names:
        code = STRUCTURE_BENCHMARK_HISTORICAL_CODES.get(name) or curve_instrument_to_code(curve_id, name)
        if code is not None:
            name_to_code[name] = code
    if not name_to_code:
        return {}
    try:
        bars_by_code = fetch_curve_bars(
            sorted(set(name_to_code.values())), interval="1D", count=BENCHMARK_HISTORY_COUNT,
        )
    except Exception:  # noqa: BLE001
        return {}
    return {
        name: {ts.timestamp(): price for ts, price in bars_by_code.get(code, [])}
        for name, code in name_to_code.items()
    }


def build_benchmark_correlations(store: CurveHistoryStore, rolls: list[Structure], curve_id: str) -> list[dict]:
    """Latest daily rolling correlation for every generated formula roll
    against this curve's own configured benchmark structures.

    Formula rolls are rebuilt from 1,400 daily OHLC observations; benchmark
    levels come from the curve's native spread codes (or an explicit override
    for the "I" curve's ER3 anchor). The output deliberately retains
    unavailable cells as ``None`` so one missing vendor series never prevents
    the rest of the matrix from being shown.
    """
    from ..config import CURVE_BENCHMARK_NAMES

    benchmark_names = CURVE_BENCHMARK_NAMES.get(curve_id, [])
    names = sorted({name for roll in rolls for name, _ in roll.legs})
    formula_bars = _fetch_outright_history(names, BENCHMARK_HISTORY_COUNT)
    benchmark_bars = _fetch_benchmark_history(curve_id, benchmark_names)
    output: list[dict] = []

    for roll in rolls:
        formula_ts, formula_values = _weighted_series_from_bars(formula_bars, roll.legs)
        cells: dict[str, dict] = {}
        for benchmark, values_by_ts in benchmark_bars.items():
            benchmark_ts = np.array(sorted(values_by_ts), dtype=np.float64)
            benchmark_values = np.array([values_by_ts[t] for t in benchmark_ts], dtype=np.float64)
            ts, left, right = _paired(formula_ts, formula_values, benchmark_ts, benchmark_values)
            points = rolling_correlation_points(ts, left, right)
            latest = points[-1] if points else None
            cells[benchmark] = {
                "correlation": latest["correlation"] if latest else None,
                "n": latest["n"] if latest else int(ts.size),
                "date": latest["date"] if latest else None,
            }
        # Preserve all configured columns even if the API returned no bars.
        for benchmark in benchmark_names:
            cells.setdefault(benchmark, {"correlation": None, "n": 0, "date": None})
        _, live_values = build_series(store, roll.legs)
        output.append({
            "roll": roll.label,
            "live_price": float(live_values[-1]) if live_values.size else None,
            "benchmarks": cells,
        })
    return output


def _weighted_series_from_bars(
    leg_bars: dict[str, dict[float, float]], legs: list[tuple[str, int]]
) -> tuple[np.ndarray, np.ndarray]:
    """Same weighted-sum-with-inner-join as build_series(), but sourced from
    a plain {name: {ts: price}} map (e.g. vendor historical bars) instead of
    a CurveHistoryStore."""
    maps = [leg_bars.get(name, {}) for name, _ in legs]
    if any(not m for m in maps):
        return np.empty(0), np.empty(0)
    shared = sorted(set.intersection(*(set(m) for m in maps)))
    if not shared:
        return np.empty(0), np.empty(0)
    ts = np.array(shared, dtype=np.float64)
    values = np.zeros(len(shared), dtype=np.float64)
    for m, (_, weight) in zip(maps, legs):
        values += weight * np.array([m[t] for t in shared], dtype=np.float64)
    return ts, values


def _merged_series(
    store: CurveHistoryStore,
    named_a: list[tuple[str, int]],
    named_b: list[tuple[str, int]],
    history_days: int,
) -> dict[str, tuple[float, float, float]]:
    """Long-range (vendor API) + fresh (live store) merged, paired series for
    two weighted leg lists, as {date_str: (epoch_ts, a_value, b_value)}, not
    yet trimmed to any window. Shared by build_comparison,
    build_structure_correlation_history, and build_structure_price_history
    so all three read from the exact same long-range-plus-live pipeline —
    mirrors HistoricalCorrelationCache's two-source approach for the
    built-in charts. The store wins on any date it also covers, since it's
    fresher (up-to-the-minute) than the vendor's last cached day."""
    all_names = sorted({name for name, _ in [*named_a, *named_b]})
    vendor_bars = _fetch_outright_history(all_names, count=history_days + CORR_WINDOW_OBS + 10)
    vendor_ts, vendor_va, vendor_vb = _paired(
        *_weighted_series_from_bars(vendor_bars, named_a),
        *_weighted_series_from_bars(vendor_bars, named_b),
    )
    store_ts, store_va, store_vb = _paired(
        *build_series(store, named_a),
        *build_series(store, named_b),
    )
    merged: dict[str, tuple[float, float, float]] = {
        _date_key(t): (t, a, b) for t, a, b in zip(vendor_ts.tolist(), vendor_va.tolist(), vendor_vb.tolist())
    }
    for t, a, b in zip(store_ts.tolist(), store_va.tolist(), store_vb.tolist()):
        merged[_date_key(t)] = (t, a, b)
    return merged


def _dates_in_range(
    dates: list[str], start_date: str | None, end_date: str | None, default_history_days: int
) -> list[str]:
    """Filter sorted ISO date-strings to an explicit [start_date, end_date]
    range (either bound optional) when given, else fall back to a trailing
    `default_history_days` window from the latest available date."""
    if start_date or end_date:
        if start_date:
            dates = [d for d in dates if d >= start_date]
        if end_date:
            dates = [d for d in dates if d <= end_date]
        return dates
    if dates:
        cutoff = date.fromisoformat(dates[-1]) - timedelta(days=default_history_days)
        dates = [d for d in dates if date.fromisoformat(d) >= cutoff]
    return dates


def build_structure_correlation_history(
    store: CurveHistoryStore,
    outrights: list[str],
    legs_a: dict[str, int],
    legs_b: dict[str, int],
    label_a: str = "",
    label_b: str = "",
    window_obs: int = CORR_WINDOW_OBS,
    min_obs: int = CORR_MIN_OBS,
    history_days: int = CORR_HISTORY_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Generic rolling-correlation-over-time series between any two weighted
    legs. Used both for a custom structure's roll-to-roll row click
    (legs_a/legs_b = consecutive rolls' legs) and the Structure Comparison
    Lab's A/B chart (legs_a/legs_b = weights_a/weights_b as entered, no
    rolling). `start_date`/`end_date` (ISO 'YYYY-MM-DD') override the
    trailing `history_days` window when given."""
    named_a = [(outrights[i], w) for i, w in parse_weights(outrights, legs_a)]
    named_b = [(outrights[i], w) for i, w in parse_weights(outrights, legs_b)]

    merged = _merged_series(store, named_a, named_b, history_days)
    dates = _dates_in_range(sorted(merged), start_date, end_date, history_days)
    ts = np.array([merged[d][0] for d in dates], dtype=np.float64)
    va = np.array([merged[d][1] for d in dates], dtype=np.float64)
    vb = np.array([merged[d][2] for d in dates], dtype=np.float64)

    return {
        "label_a": label_a,
        "label_b": label_b,
        "window_obs": window_obs,
        "min_obs": min_obs,
        "history_days": history_days,
        "updated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "points": rolling_correlation_points(ts, va, vb, window_obs, min_obs),
        "price_points": [
            {"date": d, "a": float(merged[d][1]), "b": float(merged[d][2])}
            for d in dates
        ],
    }


def build_structure_price_history(
    store: CurveHistoryStore,
    outrights: list[str],
    legs_a: dict[str, int],
    legs_b: dict[str, int],
    label_a: str = "",
    label_b: str = "",
    history_days: int = CORR_HISTORY_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Daily price history for two exact weighted structures — same
    long-range-vendor-plus-live-store merge as
    build_structure_correlation_history(), but returns the paired structure
    levels directly for plotting above the rolling-correlation chart."""
    named_a = [(outrights[i], w) for i, w in parse_weights(outrights, legs_a)]
    named_b = [(outrights[i], w) for i, w in parse_weights(outrights, legs_b)]

    merged = _merged_series(store, named_a, named_b, history_days)
    dates = _dates_in_range(sorted(merged), start_date, end_date, history_days)

    return {
        "label_a": label_a,
        "label_b": label_b,
        "history_days": history_days,
        "updated_at": _iso(datetime.now(timezone.utc).timestamp()),
        "points": [
            {"date": d, "a": float(merged[d][1]), "b": float(merged[d][2])}
            for d in dates
        ],
    }
