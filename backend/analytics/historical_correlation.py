"""Cached historical correlation series for curve pair charts."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from ..config import CURVE_CORRELATION_HISTORY_DAYS, TENOR_ORDER
from ..curves.registry import CurveSpec
from .curve_history import CurveHistoryStore

log = logging.getLogger(__name__)

DEFAULT_WINDOW_OBS = 30
DEFAULT_MIN_OBS = 10
DEFAULT_HISTORY_DAYS = CURVE_CORRELATION_HISTORY_DAYS
SUPPORTED_CATEGORIES = {"3ms", "3mf"}


@dataclass(frozen=True)
class CorrelationPair:
    category: str
    previous: str
    current: str


def _safe_filename(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in value) + ".json"


def _date_key(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).date().isoformat()


class HistoricalCorrelationCache:
    """Persist one rolling-correlation series per curve/category/pair.

    The cache is updated from the in-memory CurveHistoryStore. It does not
    fetch historical data itself; startup/backfill remains owned by the curve
    history flow.
    """

    def __init__(
        self,
        root_dir: Path,
        window_obs: int = DEFAULT_WINDOW_OBS,
        min_obs: int = DEFAULT_MIN_OBS,
        history_days: int = DEFAULT_HISTORY_DAYS,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.window_obs = window_obs
        self.min_obs = min_obs
        self.history_days = history_days
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def get_series(
        self,
        store: CurveHistoryStore,
        spec: CurveSpec,
        category: str,
        current: str,
    ) -> dict:
        pair = self._resolve_pair(spec, category, current)
        path = self._path_for(spec.curve_id, pair)
        cached = self._load(path)
        historical = (
            []
            if self._has_enough_cached_history(cached)
            else self._compute_from_historical_api(spec, pair)
        )
        computed = self._compute_from_store(store, pair)

        merged_by_date = {point["date"]: point for point in cached.get("points", [])}
        for point in historical:
            merged_by_date[point["date"]] = point
        for point in computed:
            merged_by_date[point["date"]] = point
        all_points = [merged_by_date[k] for k in sorted(merged_by_date)]

        # Persist the full accumulated history (so future calls never need to
        # re-fetch older days from the vendor API), but only ever return a
        # trailing `history_days` window — every correlation chart (built-in
        # and custom-structure) shows the same fixed lookback, not
        # however-long this cache happens to have been running.
        self._save(path, {
            "curve_id": spec.curve_id,
            "category": pair.category,
            "previous": pair.previous,
            "current": pair.current,
            "window_obs": self.window_obs,
            "min_obs": self.min_obs,
            "history_days": self.history_days,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "points": all_points,
        })

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=self.history_days)).date().isoformat()
        windowed_points = [p for p in all_points if p["date"] >= cutoff_date]

        return {
            "curve_id": spec.curve_id,
            "category": pair.category,
            "previous": pair.previous,
            "current": pair.current,
            "window_obs": self.window_obs,
            "min_obs": self.min_obs,
            "history_days": self.history_days,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "points": windowed_points,
        }

    def _resolve_pair(self, spec: CurveSpec, category: str, current: str) -> CorrelationPair:
        category = category.lower()
        if category not in SUPPORTED_CATEGORIES:
            raise ValueError(f"unsupported correlation category '{category}'")
        for previous, pair_current in spec.pairs(category):
            if pair_current == current:
                return CorrelationPair(category, previous, pair_current)
        raise ValueError(f"unknown {category} pair current '{current}'")

    def _compute_from_store(self, store: CurveHistoryStore, pair: CorrelationPair) -> list[dict]:
        ts, previous_values, current_values = store.paired_window(pair.previous, pair.current)
        return self._compute_points(ts, previous_values, current_values)

    def _compute_from_historical_api(self, spec: CurveSpec, pair: CorrelationPair) -> list[dict]:
        if spec.curve_id != "I":
            return []
        try:
            if pair.category == "3ms":
                previous_rows, current_rows = self._fetch_direct_pair(pair.previous, pair.current)
            else:
                previous_rows, current_rows = self._fetch_fly_pair(pair.previous, pair.current)
        except Exception:  # noqa: BLE001
            log.exception("failed to fetch historical correlation source for %s/%s", pair.category, pair.current)
            return []

        shared = sorted(set(previous_rows) & set(current_rows))
        if not shared:
            return []
        ts = np.array(shared, dtype=np.float64)
        previous_values = np.array([previous_rows[t] for t in shared], dtype=np.float64)
        current_values = np.array([current_rows[t] for t in shared], dtype=np.float64)
        return self._compute_points(ts, previous_values, current_values)

    def _fetch_direct_pair(self, previous: str, current: str) -> tuple[dict[float, float], dict[float, float]]:
        from ..data.historical_api import fetch_i_curve_bars, i_curve_instrument_to_code

        previous_code = i_curve_instrument_to_code(previous)
        current_code = i_curve_instrument_to_code(current)
        if previous_code is None or current_code is None:
            return {}, {}
        bars_by_code = fetch_i_curve_bars(
            [previous_code, current_code],
            interval="1D",
            count=self._historical_fetch_count(),
        )
        return (
            self._rows_to_series(bars_by_code.get(previous_code, [])),
            self._rows_to_series(bars_by_code.get(current_code, [])),
        )

    def _fetch_fly_pair(self, previous: str, current: str) -> tuple[dict[float, float], dict[float, float]]:
        from ..data.historical_api import fetch_i_curve_bars, i_curve_instrument_to_code

        previous_legs = self._fly_leg_names(previous)
        current_legs = self._fly_leg_names(current)
        if previous_legs is None or current_legs is None:
            return {}, {}

        name_to_code = {
            name: code
            for name in [*previous_legs, *current_legs]
            if (code := i_curve_instrument_to_code(name)) is not None
        }
        bars_by_code = fetch_i_curve_bars(
            sorted(set(name_to_code.values())),
            interval="1D",
            count=self._historical_fetch_count(),
        )
        leg_series = {
            name: self._rows_to_series(bars_by_code.get(code, []))
            for name, code in name_to_code.items()
        }
        return self._synthesize_fly(previous_legs, leg_series), self._synthesize_fly(current_legs, leg_series)

    @staticmethod
    def _daily_last(
        ts: np.ndarray, a: np.ndarray, b: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Collapse a paired series to one point per calendar day (that
        day's last observation). The store's live data is per-minute
        cadence while the vendor's historical bars are daily — without this
        reduction, a `window_obs`-sized rolling window silently means "30
        calendar days" in the older, vendor-sourced portion of a series but
        "30 raw ticks" (often under an hour, on a thinly-traded spread) in
        the newer, store-sourced portion, producing spurious near-±1 or
        undefined correlations right where the two portions meet."""
        last_by_date: dict[str, tuple[float, float, float]] = {}
        for t, av, bv in zip(ts.tolist(), a.tolist(), b.tolist()):
            last_by_date[_date_key(t)] = (t, av, bv)
        dates = sorted(last_by_date)
        return (
            np.array([last_by_date[d][0] for d in dates], dtype=np.float64),
            np.array([last_by_date[d][1] for d in dates], dtype=np.float64),
            np.array([last_by_date[d][2] for d in dates], dtype=np.float64),
        )

    def _compute_points(
        self,
        ts: np.ndarray,
        previous_values: np.ndarray,
        current_values: np.ndarray,
    ) -> list[dict]:
        ts, previous_values, current_values = self._daily_last(ts, previous_values, current_values)
        if ts.size < self.min_obs:
            return []

        latest_by_date: dict[str, dict] = {}
        for idx, epoch_sec in enumerate(ts.tolist()):
            end = idx + 1
            start = max(0, end - self.window_obs)
            prev_window = previous_values[start:end]
            curr_window = current_values[start:end]
            n = int(prev_window.size)
            if n < self.min_obs:
                continue
            if np.std(prev_window) <= 1e-12 or np.std(curr_window) <= 1e-12:
                corr = None
            else:
                corr = float(np.corrcoef(prev_window, curr_window)[0, 1])
            latest_by_date[_date_key(epoch_sec)] = {
                "date": _date_key(epoch_sec),
                "correlation": corr,
                "n": n,
            }
        return [latest_by_date[k] for k in sorted(latest_by_date)]

    def _has_enough_cached_history(self, cached: dict) -> bool:
        points = cached.get("points", [])
        if not points:
            return False
        dated = [p.get("date") for p in points if isinstance(p, dict) and p.get("date")]
        if not dated:
            return False
        try:
            first = datetime.fromisoformat(min(dated)).date()
            last = datetime.fromisoformat(max(dated)).date()
        except ValueError:
            return False
        return (last - first).days >= self.history_days - 1

    def _historical_fetch_count(self) -> int:
        return self.history_days + self.window_obs + 10

    def _rows_to_series(self, rows: list[tuple[datetime, float]]) -> dict[float, float]:
        return {ts.timestamp(): price for ts, price in rows}

    def _fly_leg_names(self, fly_name: str) -> list[str] | None:
        parts = fly_name.split()
        if len(parts) < 3:
            return None
        prefix, tenor = parts[0], parts[1]
        if tenor not in TENOR_ORDER:
            return None
        idx = TENOR_ORDER.index(tenor)
        if idx + 2 >= len(TENOR_ORDER):
            return None
        return [f"{prefix} {TENOR_ORDER[idx + offset]}" for offset in range(3)]

    def _synthesize_fly(
        self,
        legs: list[str],
        leg_series: dict[str, dict[float, float]],
    ) -> dict[float, float]:
        first, middle, last = (leg_series.get(name, {}) for name in legs)
        shared = sorted(set(first) & set(middle) & set(last))
        return {t: first[t] - 2 * middle[t] + last[t] for t in shared}

    def _path_for(self, curve_id: str, pair: CorrelationPair) -> Path:
        name = _safe_filename(f"{pair.previous}__{pair.current}")
        return self.root_dir / curve_id / pair.category / name

    def _load(self, path: Path) -> dict:
        if not path.exists():
            return {"points": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and isinstance(payload.get("points"), list):
                return payload
        except (OSError, json.JSONDecodeError):
            log.exception("failed to load historical correlation cache %s", path)
        return {"points": []}

    def _save(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, separators=(",", ":"))
            os.replace(tmp, path)
        except OSError:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, separators=(",", ":"))
            except OSError:
                log.exception("failed to save historical correlation cache %s", path)
