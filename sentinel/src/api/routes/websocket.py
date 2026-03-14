"""
WebSocket route: WS /ws/alerts.

Streams real-time fraud alerts (BLOCK decisions) to connected dashboards.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

from sentinel.src.services.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/alerts")
async def fraud_alert_feed(websocket: WebSocket) -> None:
    """Accept WebSocket connections and stream BLOCK alerts."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive: wait for client pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
