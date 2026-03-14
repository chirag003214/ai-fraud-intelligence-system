"""
WebSocket connection manager for real-time fraud alert broadcasting.

All connected dashboard clients receive BLOCK decisions in real-time.
Dead connections are automatically cleaned up during broadcast.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    """Thread-safe WebSocket connection pool for broadcast messaging."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("ws_connected", total=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("ws_disconnected", total=len(self.active_connections))

    async def broadcast_fraud_alert(self, alert: dict[str, Any]) -> None:
        """Send a BLOCK decision to all connected dashboard clients."""
        message = json.dumps(alert)
        dead: list[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Module-level singleton
manager = ConnectionManager()
