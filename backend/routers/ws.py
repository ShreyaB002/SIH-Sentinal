"""
ws.py — WebSocket endpoint for real-time AI event alerts.

Endpoint
--------
GET /ws/alerts

The browser connects once on page load.  The EventManager pushes JSON alert
packets into each client's asyncio.Queue whenever a new event occurs.

Each alert packet looks like:
{
    "id": 42,
    "camera_id": "cam_03",
    "camera_name": "Camera 03",
    "event_type": "INTRUSION",
    "label": "Person",
    "confidence": 0.873,
    "zone": "Entry Point",
    "track_id": 7,
    "bbox": [120, 80, 300, 400],
    "timestamp": "2026-08-26T09:00:00+00:00"
}

Clients that disconnect are cleaned up automatically.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """Stream real-time AI detection events to the browser."""
    await websocket.accept()

    manager = websocket.app.state.stream_manager
    event_manager = manager.event_manager

    if event_manager is None:
        # AI is disabled ? send a single info message and hold the connection
        await websocket.send_text(
            '{"event_type":"INFO","message":"AI pipeline is disabled (AI_ENABLED=False)"}'
        )
        try:
            while True:
                await asyncio.sleep(30)
        except WebSocketDisconnect:
            return

    # Subscribe to the event stream
    queue = event_manager.subscribe()
    logger.info("WebSocket client connected to /ws/alerts.")

    try:
        while True:
            # Wait for next event from the queue (with a periodic ping)
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=20.0)
                await websocket.send_text(payload)
            except asyncio.TimeoutError:
                # Send a keep-alive ping so the browser does not close the connection
                await websocket.send_text('{"event_type":"PING"}')
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/alerts.")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        event_manager.unsubscribe(queue)
