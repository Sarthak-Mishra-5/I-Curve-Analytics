"""REST endpoints for user-defined structures: arbitrary integer-weight
combinations of a curve's outrights, auto-rolled (Custom Structure
Analytics) or compared exactly as entered (Structure Comparison Lab)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..analytics.custom_structure import (
    StructureError,
    build_comparison,
    build_custom_structure,
    build_structure_correlation_history,
    build_structure_price_history,
)
from ..curves.registry import get_curve

router = APIRouter(prefix="/api/curves", tags=["custom-structures"])


class CustomStructureRequest(BaseModel):
    name: str
    weights: dict[str, int]


class ComparisonRequest(BaseModel):
    weights_a: dict[str, int]
    weights_b: dict[str, int]
    start_date: str | None = None
    end_date: str | None = None


class StructureCorrelationHistoryRequest(BaseModel):
    legs_a: dict[str, int]
    legs_b: dict[str, int]
    label_a: str = ""
    label_b: str = ""
    start_date: str | None = None
    end_date: str | None = None


@router.post("/{curve_id}/custom-structure")
async def custom_structure(curve_id: str, body: CustomStructureRequest) -> dict:
    from .app import ctx

    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    try:
        return build_custom_structure(store, spec.outrights, body.name, body.weights, curve_id=spec.curve_id)
    except StructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{curve_id}/comparison")
async def comparison(curve_id: str, body: ComparisonRequest) -> dict:
    from .app import ctx

    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    try:
        return build_comparison(
            store, spec.outrights, body.weights_a, body.weights_b, body.start_date, body.end_date
        )
    except StructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{curve_id}/custom-structure/correlation-history")
async def custom_structure_correlation_history(curve_id: str, body: StructureCorrelationHistoryRequest) -> dict:
    from .app import ctx

    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    try:
        return build_structure_correlation_history(
            store, spec.outrights, body.legs_a, body.legs_b, body.label_a, body.label_b,
            start_date=body.start_date, end_date=body.end_date,
        )
    except StructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{curve_id}/custom-structure/price-history")
async def custom_structure_price_history(curve_id: str, body: StructureCorrelationHistoryRequest) -> dict:
    from .app import ctx

    spec = get_curve(curve_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")
    store = ctx.curve_histories.get(curve_id)
    if store is None:
        raise HTTPException(status_code=404, detail=f"unknown curve '{curve_id}'")

    try:
        return build_structure_price_history(
            store, spec.outrights, body.legs_a, body.legs_b, body.label_a, body.label_b,
            start_date=body.start_date, end_date=body.end_date,
        )
    except StructureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
