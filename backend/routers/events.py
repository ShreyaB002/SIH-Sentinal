"""
events.py ? REST endpoint for querying stored detection events.

Endpoints
---------
GET /api/events
    Query recent events from SQLite.
    Optional query params:
        camera_id=cam_01   filter by camera
        limit=50           max rows (default 100, max 500)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events", summary="Query stored detection events")
async def get_events(
    request: Request,
    camera_id: str | None = Query(default=None, description="Filter by camera ID"),
    limit: int = Query(default=100, ge=1, le=500, description="Max number of events"),
) -> JSONResponse:
    """Return recent AI detection events from the database, newest first.

    Example response::

        [
            {
                "id": 42,
                "timestamp": "2026-08-26T09:00:00+00:00",
                "camera_id": "cam_01",
                "camera_name": "Camera 01",
                "event_type": "INTRUSION",
                "label": "Person",
                "confidence": 0.87,
                "zone": "Zone A",
                "track_id": 3,
                "bbox_json": "[120, 80, 300, 400]"
            }
        ]
    """
    manager = request.app.state.stream_manager

    # Access the database through the stream manager
    db = getattr(manager, "_database", None)
    if db is None:
        return JSONResponse(content=[], status_code=200)

    events = db.query_events(camera_id=camera_id, limit=limit)
    return JSONResponse(content=events)
