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
    """Stream real-time AI detection alerts and multi-device session sync events."""
    await websocket.accept()

    manager = websocket.app.state.stream_manager
    event_manager = manager.event_manager
    session_manager = manager.session_manager

    session_id = websocket.query_params.get("session_id")
    event_queue = event_manager.subscribe() if event_manager else None
    session_queue = session_manager.register_queue(session_id) if session_manager and session_id else None

    logger.info("WebSocket connected to /ws/alerts (session=%s).", session_id or "anonymous")

    async def get_next_message():
        tasks = []
        if event_queue:
            tasks.append(asyncio.create_task(event_queue.get()))
        if session_queue:
            tasks.append(asyncio.create_task(session_queue.get()))
        if not tasks:
            await asyncio.sleep(20)
            return '{"event_type":"PING"}'

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=20.0)
        for p in pending:
            p.cancel()
        if done:
            return list(done)[0].result()
        return '{"event_type":"PING"}'

    try:
        while True:
            payload = await get_next_message()
            await websocket.send_text(payload)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/alerts (session=%s).", session_id or "anonymous")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        if event_manager and event_queue:
            event_manager.unsubscribe(event_queue)
        if session_manager and session_id:
            session_manager.terminate_session(session_id)

