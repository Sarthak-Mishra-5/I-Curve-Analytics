"""WebSocket hub: fan-out broadcast to all connected dashboard clients."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import orjson
from fastapi import WebSocket

log = logging.getLogger(__name__)


class WSHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def add(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)

    async def remove(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        payload = orjson.dumps(message).decode()
        dead: list[WebSocket] = []
        # Snapshot to avoid mutation while iterating.
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)

    async def send(self, ws: WebSocket, message: dict) -> None:
        try:
            await ws.send_text(orjson.dumps(message).decode())
        except Exception:  # noqa: BLE001
            await self.remove(ws)
