"""REST endpoint for the Inter-Product Lab: a relative-value trade built from
structures on DIFFERENT curves/products, e.g. LONG "I Sep26-Dec26 3MS" vs
SHORT "SO3 Sep26-Dec26 3MS". Builds on analytics/inter_product.py, which in
turn reuses the single-curve custom-structure engine's weight parsing,
rolling-correlation, and hedge-ratio math — see that module's docstring."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..analytics.inter_product import LegInput, StructureError, WINDOW_TO_OBS, build_inter_product_analysis
from ..curves.registry import get_curve

router = APIRouter(prefix="/api/inter-product", tags=["inter-product"])

# V1 supports exactly 2 legs (the request/UI is built around a pairwise RV
# trade). The analytics layer underneath is already N-way — relaxing this to
# 3+ legs later is this one check plus a correlation-matrix UI, not a rewrite.
MAX_LEGS_V1 = 2


class LegRequest(BaseModel):
    curve_id: str
    weights: dict[str, int]
    side: Literal["LONG", "SHORT"] = "LONG"
    lots: float = 1.0
    label: str = ""


class InterProductAnalyzeRequest(BaseModel):
    legs: list[LegRequest]
    window: str = "30D"
    start_date: str | None = None
    end_date: str | None = None


@router.post("/analyze")
async def analyze(body: InterProductAnalyzeRequest) -> dict:
    from .app import ctx

    if len(body.legs) != MAX_LEGS_V1:
        raise HTTPException(
            status_code=400,
            detail=f"Inter-Product Lab currently supports exactly {MAX_LEGS_V1} legs, got {len(body.legs)}",
        )
    if body.window not in WINDOW_TO_OBS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown window '{body.window}'; expected one of {sorted(WINDOW_TO_OBS)}",
        )

    legs: list[LegInput] = []
    for leg in body.legs:
        spec = get_curve(leg.curve_id)
        if spec is None:
            raise HTTPException(status_code=404, detail=f"unknown curve '{leg.curve_id}'")
        store = ctx.curve_histories.get(leg.curve_id)
        if store is None:
            raise HTTPException(status_code=404, detail=f"unknown curve '{leg.curve_id}'")
        legs.append(LegInput(
            curve_id=leg.curve_id, store=store, outrights=spec.outrights,
            weights=leg.weights, side=leg.side, lots=leg.lots, label=leg.label,
        ))

    try:
        return build_inter_product_analysis(legs, body.window, body.start_date, body.end_date)
    except StructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
