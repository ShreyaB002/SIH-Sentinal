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

from backend.config import JPEG_QUALITY, MJPEG_FPS
from backend.core.camera_stream import CameraStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRAME_INTERVAL: float = 1.0 / MJPEG_FPS


def _make_offline_frame(width: int = 640, height: int = 360) -> bytes:
    """Generate a placeholder JPEG image displayed when a camera is offline."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Dark grey background
    img[:] = (30, 30, 30)

    text = "OFFLINE"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = (width - tw) // 2
    y = (height + th) // 2
    cv2.putText(img, text, (x, y), font, font_scale, (80, 80, 80), thickness, cv2.LINE_AA)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes()


_OFFLINE_JPEG: bytes = _make_offline_frame()


def _encode_frame(frame: np.ndarray) -> bytes:
    """JPEG-encode an OpenCV BGR frame."""
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
