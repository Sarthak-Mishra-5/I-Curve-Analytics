"""Registry of STIR curve definitions.

Each CurveSpec lists a curve's outrights and its ordered 3-month-spread /
6-month-spread / 3-month-fly instrument names. Adding a new STIR product
(ER3, SOFR, SARON, SONIA, ...) means adding one more CurveSpec entry here —
no changes to the history store, stats engine, REST routes, or frontend.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import (
    CURVE_BENCHMARK_NAMES,
    I_3MF_NAMES,
    I_3MS_NAMES,
    I_6MS_NAMES,
    I_OUTRIGHT_NAMES,
    SA3_3MF_NAMES,
    SA3_3MS_NAMES,
    SA3_6MS_NAMES,
    SA3_OUTRIGHT_NAMES,
    SO3_3MF_NAMES,
    SO3_3MS_NAMES,
    SO3_6MS_NAMES,
    SO3_OUTRIGHT_NAMES,
    SR3_3MF_NAMES,
    SR3_3MS_NAMES,
    SR3_6MS_NAMES,
    SR3_OUTRIGHT_NAMES,
)

_PAIR_CATEGORIES = ("3ms", "6ms", "3mf")


@dataclass(frozen=True)
class CurveSpec:
    curve_id: str
    label: str
    outrights: list[str]
    three_month_spreads: list[str]
    six_month_spreads: list[str]
    flies_3m: list[str]
    # "direct_feed": spreads/flies are their own subscribed instruments (I curve today).
    # "computed": spreads/flies must be derived from outrights (reserved for future curves).
    spreads_mode: str = "direct_feed"

    def _names(self, category: str) -> list[str]:
        return {
            "3ms": self.three_month_spreads,
            "6ms": self.six_month_spreads,
            "3mf": self.flies_3m,
        }[category]

    def pairs(self, category: str) -> list[tuple[str, str]]:
        """Ordered (previous, current) row pairs for a stats table category."""
        names = self._names(category)
        return list(zip(names[:-1], names[1:]))

    def all_instruments(self) -> list[str]:
        return [*self.outrights, *self.three_month_spreads, *self.six_month_spreads, *self.flies_3m]

    @property
    def benchmark_names(self) -> list[str]:
        return CURVE_BENCHMARK_NAMES.get(self.curve_id, [])

    def to_dict(self) -> dict:
        return {
            "curve_id": self.curve_id,
            "label": self.label,
            "outrights": self.outrights,
            "three_month_spreads": self.three_month_spreads,
            "six_month_spreads": self.six_month_spreads,
            "flies_3m": self.flies_3m,
            "spreads_mode": self.spreads_mode,
            "benchmark_names": self.benchmark_names,
        }


CURVES: dict[str, CurveSpec] = {
    "I": CurveSpec(
        curve_id="I",
        label="Euribor I-Curve",
        outrights=I_OUTRIGHT_NAMES,
        three_month_spreads=I_3MS_NAMES,
        six_month_spreads=I_6MS_NAMES,
        flies_3m=I_3MF_NAMES,
        spreads_mode="direct_feed",
    ),
    "SR3": CurveSpec(
        curve_id="SR3",
        label="SOFR SR3 Curve",
        outrights=SR3_OUTRIGHT_NAMES,
        three_month_spreads=SR3_3MS_NAMES,
        six_month_spreads=SR3_6MS_NAMES,
        flies_3m=SR3_3MF_NAMES,
        spreads_mode="direct_feed",
    ),
    "SA3": CurveSpec(
        curve_id="SA3",
        label="SARON SA3 Curve",
        outrights=SA3_OUTRIGHT_NAMES,
        three_month_spreads=SA3_3MS_NAMES,
        six_month_spreads=SA3_6MS_NAMES,
        flies_3m=SA3_3MF_NAMES,
        spreads_mode="direct_feed",
    ),
    "SO3": CurveSpec(
        curve_id="SO3",
        label="SONIA SO3 Curve",
        outrights=SO3_OUTRIGHT_NAMES,
        three_month_spreads=SO3_3MS_NAMES,
        six_month_spreads=SO3_6MS_NAMES,
        flies_3m=SO3_3MF_NAMES,
        spreads_mode="direct_feed",
    ),
}

# Instrument display name -> curve_id, for routing live ticks to the right store.
INSTRUMENT_TO_CURVE: dict[str, str] = {
    name: spec.curve_id for spec in CURVES.values() for name in spec.all_instruments()
}


def get_curve(curve_id: str) -> CurveSpec | None:
    return CURVES.get(curve_id)


def list_curves() -> list[dict]:
    return [{"curve_id": c.curve_id, "label": c.label} for c in CURVES.values()]
