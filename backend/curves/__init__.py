"""Generic curve-mapping registry — one CurveSpec per STIR product."""
from .registry import CURVES, INSTRUMENT_TO_CURVE, CurveSpec, get_curve, list_curves

__all__ = ["CURVES", "INSTRUMENT_TO_CURVE", "CurveSpec", "get_curve", "list_curves"]
