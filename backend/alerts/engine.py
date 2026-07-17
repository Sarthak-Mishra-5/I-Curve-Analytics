"""Alert engine — turns analytics payloads into alert events."""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Awaitable, Callable

from ..config import (
    ALERT_CORR_DROP,
    ALERT_FLY_Z,
    ALERT_RESID_Z,
    ALERT_SPREAD_Z,
    ALERT_VOL_SPIKE,
)

log = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self, broadcast: Callable[[dict], Awaitable[None]]) -> None:
        self._broadcast = broadcast
        self.recent: deque[dict] = deque(maxlen=200)
        self._dedup: dict[str, datetime] = {}
        self._prev_corr: dict[tuple[str, str], float] = {}

    def _emit(self, severity: str, category: str, key: str, message: str) -> None:
        # 30s dedup window per key.
        now = datetime.now(timezone.utc)
        last = self._dedup.get(key)
        if last and (now - last).total_seconds() < 30:
            return
        self._dedup[key] = now
        alert = {
            "id": f"{int(now.timestamp() * 1000)}-{key}",
            "ts": now.isoformat(),
            "severity": severity,
            "category": category,
            "message": message,
        }
        self.recent.append(alert)
        import asyncio
        try:
            asyncio.get_event_loop().create_task(self._broadcast({"type": "alert", "payload": alert}))
        except RuntimeError:
            pass

    def on_analytics(self, payload: dict) -> None:
        try:
            for s in payload.get("spreads", []):
                z = s.get("zscore", 0.0)
                if abs(z) >= ALERT_SPREAD_Z:
                    sev = "critical" if abs(z) >= 3.5 else "warn"
                    self._emit(sev, "spread",
                               f"spread:{s['name']}",
                               f"Spread {s['name']} z={z:+.2f} value={s['value']:+.4f}")
            for f in payload.get("flies", []):
                z = f.get("zscore", 0.0)
                if abs(z) >= ALERT_FLY_Z:
                    sev = "critical" if abs(z) >= 3.5 else "warn"
                    self._emit(sev, "fly",
                               f"fly:{f['name']}",
                               f"Fly {f['name']} z={z:+.2f} value={f['value']:+.4f}")
            for r in payload.get("regressions", []):
                rz = r.get("residual_z", 0.0)
                if abs(rz) >= ALERT_RESID_Z:
                    sev = "critical" if abs(rz) >= 3.5 else "warn"
                    self._emit(sev, "regression",
                               f"resid:{r['y']}/{r['x']}",
                               f"{r['y']}~{r['x']} residual z={rz:+.2f} β={r['beta']:.3f}")
            for v in payload.get("volatility", []):
                rv_s = v.get("realized_vol_short", 0.0)
                rv_m = v.get("realized_vol_medium", 0.0)
                if rv_m > 1e-9 and rv_s / rv_m >= ALERT_VOL_SPIKE:
                    self._emit("warn", "volatility",
                               f"vol:{v['instrument']}",
                               f"Vol spike {v['instrument']} {rv_s/rv_m:.2f}× medium baseline")
            # Correlation regime shift: detect any pair whose corr moved > ALERT_CORR_DROP since last tick.
            corr = payload.get("correlation") or {}
            rows = corr.get("rows") or []
            matrix = corr.get("matrix") or []
            for i, a in enumerate(rows):
                for j, b in enumerate(rows):
                    if j <= i:
                        continue
                    val = float(matrix[i][j])
                    prev = self._prev_corr.get((a, b))
                    if prev is not None and abs(val - prev) >= ALERT_CORR_DROP:
                        self._emit("warn", "correlation",
                                   f"corr:{a}/{b}",
                                   f"Correlation {a}/{b} shifted {prev:+.2f} → {val:+.2f}")
                    self._prev_corr[(a, b)] = val
        except Exception:  # noqa: BLE001
            log.exception("alert evaluation failed")
