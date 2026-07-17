"""Market microstructure: order flow imbalance, liquidity, buy/sell pressure."""
from __future__ import annotations

from ..streaming.state import MarketState


def compute_microstructure(state: MarketState) -> list[dict]:
    out: list[dict] = []
    snap = state.snapshot_quotes()
    for name, q in snap.items():
        bid_qty = q.get("bid_qty") or 0.0
        ask_qty = q.get("ask_qty") or 0.0
        total = bid_qty + ask_qty
        ofi = (bid_qty - ask_qty) / total if total > 0 else 0.0
        spread = (q.get("ask") or 0) - (q.get("bid") or 0) if q.get("ask") and q.get("bid") else None
        out.append({
            "instrument": name,
            "bid_qty": bid_qty,
            "ask_qty": ask_qty,
            "order_flow_imbalance": ofi,
            "book_spread": spread,
            "liquidity": total,
        })
    return out
