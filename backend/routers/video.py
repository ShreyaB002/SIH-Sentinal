"""
Video router — MJPEG streaming and camera status endpoints.

Endpoints
---------
GET /cameras
    Returns the configured cameras and their current statuses.

GET /stream/{camera_id}
    Streams a live MJPEG video feed for the given camera.

MJPEG transport
---------------
MJPEG (Motion JPEG) is a simple streaming format understood natively by
every browser's ``<img>`` element:

    <img src="/stream/cam_01">

Each frame is sent as a JPEG-encoded image inside a ``multipart/x-mixed-replace``
HTTP response.  The browser replaces the displayed image with each incoming
part, giving the appearance of a live video feed without any JavaScript.

This approach is intentionally simple for Phase 1.  In later phases,
bounding boxes and alert overlays will be composited onto frames before
JPEG encoding, so the MJPEG endpoint remains the correct delivery mechanism
for annotated video.

WebSockets (added in Phase 3) will carry *event data* (alert metadata, JSON)
separately from the video stream, keeping the two concerns decoupled.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

import cv2
import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.config import JPEG_QUALITY, MJPEG_FPS, STREAM_WIDTH, STREAM_HEIGHT
from backend.core.camera_stream import CameraStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRAME_INTERVAL: float = 1.0 / MJPEG_FPS


def _make_offline_frame(width: int = STREAM_WIDTH, height: int = STREAM_HEIGHT) -> bytes:
    """Generate a placeholder JPEG image displayed when a camera is offline."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (30, 30, 30)

    text = "OFFLINE"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (width - tw) // 2
    y = (height + th) // 2
    cv2.putText(img, text, (x, y), font, font_scale, (80, 80, 80), thickness, cv2.LINE_AA)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes()


_OFFLINE_JPEG: bytes = _make_offline_frame()


def _encode_frame(frame: np.ndarray, target_w: int = STREAM_WIDTH, target_h: int = STREAM_HEIGHT) -> bytes:
    """Compress and JPEG-encode an OpenCV BGR frame for high-speed streaming."""
    h, w = frame.shape[:2]
    # Resize down if frame is larger than stream target
    if w > target_w or h > target_h:
        frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # Encode with optimized quality compression
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes()


def _wrap_mjpeg_part(jpeg_bytes: bytes) -> bytes:
    """Wrap JPEG bytes in a multipart MJPEG boundary part."""
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n"
        + jpeg_bytes
        + b"\r\n"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/cameras", summary="List all cameras and their statuses")
async def list_cameras(request: Request) -> JSONResponse:
    """Return configured cameras and their current statuses.

    Example response::

        [
            {"id": "cam_01", "name": "Camera 01", "status": "ONLINE"},
            {"id": "cam_02", "name": "Camera 02", "status": "OFFLINE"}
        ]
    """
    manager = request.app.state.stream_manager
    statuses = manager.get_statuses()
    return JSONResponse(content=statuses)


@router.get("/stream/{camera_id}", summary="MJPEG live stream for a single camera")
async def mjpeg_stream(camera_id: str, request: Request) -> StreamingResponse:
    """Stream live video as ``multipart/x-mixed-replace`` (MJPEG).

    The browser can consume this directly with::

        <img src="/stream/cam_01">

    The endpoint reads the **latest** frame from the :class:`CameraStream`
    buffer; it never creates its own ``cv2.VideoCapture``.  Frame delivery
    is rate-limited to ``MJPEG_FPS`` to avoid overwhelming slow clients.
    """
    manager = request.app.state.stream_manager

    async def frame_generator() -> AsyncGenerator[bytes, None]:
        while True:
            # Honour client disconnect
            if await request.is_disconnected():
                logger.debug("[%s] MJPEG client disconnected.", camera_id)
                break

            stream = manager.get_stream(camera_id)

            if stream is None:
                # Unknown camera_id — send offline placeholder indefinitely
                yield _wrap_mjpeg_part(_OFFLINE_JPEG)
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            if stream.status == CameraStatus.OFFLINE:
                yield _wrap_mjpeg_part(_OFFLINE_JPEG)
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            frame = stream.get_frame()
            if frame is None:
                # Camera is connecting / warming up
                yield _wrap_mjpeg_part(_OFFLINE_JPEG)
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            jpeg_bytes = await asyncio.get_event_loop().run_in_executor(
                None, _encode_frame, frame
            )
            yield _wrap_mjpeg_part(jpeg_bytes)
            await asyncio.sleep(_FRAME_INTERVAL)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/system/status", summary="Real-time GPU VRAM, active model, and stream telemetry")
async def system_status(request: Request) -> JSONResponse:
    """Return real-time hardware, model, and stream telemetry."""
    from backend.core.model_manager import ModelManager
    manager = request.app.state.stream_manager
    mm = ModelManager()

    # Stream health metrics
    health_list = []
    for s in manager.get_streams():
        health_list.append(s.get_health())

    status_data = {
        "hardware": mm.get_status(),
        "streams": health_list,
        "total_streams": len(health_list),
    }
    return JSONResponse(content=status_data)


@router.get("/zones/{camera_id}", summary="Get polygon zones for a camera")
async def get_zones(camera_id: str) -> JSONResponse:
    """Get active virtual fence zones for a camera."""
    from backend.config import ZONES
    zones = ZONES.get(camera_id, [])
    return JSONResponse(content={"camera_id": camera_id, "zones": zones})


@router.post("/zones/{camera_id}", summary="Update polygon zones for a camera in real time")
async def update_zones(camera_id: str, request: Request) -> JSONResponse:
    """Save new polygon zones for a camera and update running pipeline."""
    from backend.config import ZONES
    from backend.core.fence import VirtualFence
    try:
        body = await request.json()
        new_zones = body.get("zones", [])

        # Update global config dictionary
        ZONES[camera_id] = new_zones

        # Update running pipeline instance if active
        manager = request.app.state.stream_manager
        stream = manager.get_stream(camera_id)
        if stream and hasattr(stream, "_pipeline") and stream._pipeline:
            stream._pipeline._fence = VirtualFence(camera_id=camera_id, zones=new_zones)
            logger.info("[%s] VirtualFence zones updated live from Web UI: %d zone(s)", camera_id, len(new_zones))

        return JSONResponse(content={"status": "success", "camera_id": camera_id, "zones_count": len(new_zones)})
    except Exception as exc:
        logger.error("Failed to update zones for %s: %s", camera_id, exc)
        return JSONResponse(content={"status": "error", "message": str(exc)}, status_code=400)


@router.get("/plates", summary="Get recent ANPR detected vehicle plates")
async def get_plates(request: Request) -> JSONResponse:
    """Return recent license plate events."""
    try:
        manager = request.app.state.stream_manager
        # Fetch from database if available
        from backend.config import DB_PATH
        from backend.core.database import Database
        db = Database(DB_PATH)
        records = db.query(event_type="PLATE", limit=100)
        plates = [
            {
                "id": r.id,
                "camera_id": r.camera_id,
                "plate_text": r.details.get("plate", r.label),
                "confidence": r.confidence,
                "vehicle_type": r.details.get("vehicle", "Car"),
                "timestamp": r.timestamp,
            }
            for r in records
        ]
        return JSONResponse(content=plates)
    except Exception as exc:
        logger.debug("Plate query error: %s", exc)
        return JSONResponse(content=[])
