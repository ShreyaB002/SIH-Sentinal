"""
watchlist.py router - REST API for face watchlist management (Phase 4).

Endpoints
---------
GET    /api/watchlist           - List all entries (no embeddings)
POST   /api/watchlist/add       - Add person (multipart: name + face image)
DELETE /api/watchlist/{id}      - Remove person by ID
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _wl(request: Request):
    mgr = request.app.state.stream_manager
    if not hasattr(mgr, "_watchlist_db") or mgr._watchlist_db is None:
        raise HTTPException(503, "Watchlist DB not initialised")
    return mgr._watchlist_db


def _fr(request: Request):
    mgr = request.app.state.stream_manager
    if not hasattr(mgr, "_face_recognizer") or mgr._face_recognizer is None:
        raise HTTPException(503, "Face recognizer not initialised")
    return mgr._face_recognizer


@router.get("")
def list_watchlist(request: Request):
    """List all watchlist entries (no embeddings returned)."""
    return _wl(request).list_metadata()


@router.post("/add")
async def add_to_watchlist(
    request: Request,
    name: str = Form(...),
    image: UploadFile = File(...),
):
    """Add a face to the watchlist from an uploaded photo.

    - **name**: Person's name or ID
    - **image**: Clear front-facing face photo (JPG/PNG)
    """
    wl_db = _wl(request)
    fr    = _fr(request)

    img_bytes = await image.read()
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Invalid image ? could not decode. Use JPG or PNG.")

    results = fr.recognize(frame)
    if not results:
        raise HTTPException(422, "No face detected. Use a clear, well-lit, front-facing photo.")

    best = max(results, key=lambda r: (r.bbox[2]-r.bbox[0]) * (r.bbox[3]-r.bbox[1]))
    if best.embedding is None:
        raise HTTPException(422, "Could not extract face embedding.")

    ext = f".{image.filename.rsplit('.', 1)[-1].lower()}" if "." in image.filename else ".jpg"
    entry_id = wl_db.add(name=name, embedding=best.embedding,
                         image_bytes=img_bytes, image_ext=ext)

    # Reload watchlist into face recognizer
    fr.load_watchlist(wl_db.all_entries())

    logger.info("Watchlist: added '%s' id=%s", name, entry_id)
    return {"status": "ok", "id": entry_id, "name": name,
            "message": f"'{name}' added to watchlist successfully."}


@router.delete("/{entry_id}")
def remove_from_watchlist(entry_id: str, request: Request):
    """Remove a person from the watchlist by ID."""
    wl_db = _wl(request)
    deleted = wl_db.delete(entry_id)
    if not deleted:
        raise HTTPException(404, f"Entry '{entry_id}' not found")
    # Reload
    _fr(request).load_watchlist(wl_db.all_entries())
    return {"status": "ok", "message": f"Entry '{entry_id}' removed."}
