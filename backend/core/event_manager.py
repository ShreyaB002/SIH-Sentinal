"""
event_manager.py - Central event hub for IBVAP Phase 3.

Phase 3 adds weapon events and activity events on top of Phase 2 fence events.
All event types flow through the same dedup -> SQLite -> WebSocket pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timezone
from typing import Optional

from backend.config import (
    ACTIVITY_COOLDOWN,
    CAMERAS,
    EVENT_COOLDOWN,
    INTRUSION_MIN_CONFIDENCE,
    WEAPONS_ALERT_CONFIDENCE,
)
from backend.core.database import Database
from backend.core.fence import FenceEvent

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventManager:
    """Central router for all AI-detected events (Phase 3).

    Handles: INTRUSION, WEAPON, LOITERING, RUNNING, CROWD
    """

    def __init__(self, database: Database, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._db = database
        self._loop = loop
        self._cooldown: dict[tuple, float] = {}
        self._cooldown_lock = threading.Lock()
        self._subscribers: list[asyncio.Queue] = []
        self._sub_lock = threading.Lock()

    # ------------------------------------------------------------------
    # WebSocket subscription
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        with self._sub_lock:
            self._subscribers.append(q)
        logger.debug("EventManager: WS client subscribed (%d total).", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._sub_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def receive(self, events: list[FenceEvent]) -> None:
        """Handle fence intrusion events (called from camera threads)."""
        now = time.monotonic()
        for ev in events:
            if ev.confidence < INTRUSION_MIN_CONFIDENCE:
                logger.debug(
                    "Suppressing low-confidence intrusion [%s] %s conf=%.2f zone=%s",
                    ev.camera_id,
                    ev.label,
                    ev.confidence,
                    ev.zone_name,
                )
                continue
            key = ("INTRUSION", ev.camera_id, ev.track_id, ev.zone_name)
            if not self._check_cooldown(key, now, EVENT_COOLDOWN):
                continue
            cam_name = CAMERAS.get(ev.camera_id, {}).get("name", ev.camera_id)
            row_id = self._db.insert_event(
                camera_id=ev.camera_id, camera_name=cam_name,
                event_type="INTRUSION", label=ev.label,
                confidence=ev.confidence, zone=ev.zone_name,
                track_id=ev.track_id, bbox=ev.bbox,
            )
            self._broadcast_payload({
                "id": row_id, "event_type": "INTRUSION",
                "camera_id": ev.camera_id, "camera_name": cam_name,
                "label": ev.label, "confidence": round(ev.confidence, 3),
                "zone": ev.zone_name, "track_id": ev.track_id,
                "bbox": list(ev.bbox), "timestamp": _now_iso(),
            })
            logger.info("EVENT INTRUSION [%s] %s track=%d zone=%s",
                        ev.camera_id, ev.label, ev.track_id, ev.zone_name)

    def receive_weapon(self, camera_id: str, weapon) -> None:
        """Handle a weapon detection event."""
        if weapon.confidence < WEAPONS_ALERT_CONFIDENCE:
            logger.debug(
                "Suppressing low-confidence weapon [%s] %s conf=%.2f",
                camera_id,
                weapon.label,
                weapon.confidence,
            )
            return
        now = time.monotonic()
        key = ("WEAPON", camera_id, weapon.label, str(weapon.bbox))
        if not self._check_cooldown(key, now, EVENT_COOLDOWN):
            return
        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id, camera_name=cam_name,
            event_type="WEAPON", label=weapon.label,
            confidence=weapon.confidence, zone="",
            track_id=0, bbox=weapon.bbox,
        )
        self._broadcast_payload({
            "id": row_id, "event_type": "WEAPON",
            "camera_id": camera_id, "camera_name": cam_name,
            "label": weapon.label, "confidence": round(weapon.confidence, 3),
            "zone": "", "track_id": 0,
            "bbox": list(weapon.bbox), "timestamp": _now_iso(),
        })
        logger.warning("!!! WEAPON [%s] %s conf=%.0f%%",
                       camera_id, weapon.label, weapon.confidence * 100)

    def receive_activity(self, activity) -> None:
        """Handle a suspicious activity event (loitering/running/crowd)."""
        from backend.core.activity import ActivityEvent
        now = time.monotonic()
        key = (activity.event_type, activity.camera_id, activity.track_id, activity.zone)
        if not self._check_cooldown(key, now, ACTIVITY_COOLDOWN):
            return
        cam_name = CAMERAS.get(activity.camera_id, {}).get("name", activity.camera_id)
        row_id = self._db.insert_event(
            camera_id=activity.camera_id, camera_name=cam_name,
            event_type=activity.event_type, label=activity.label,
            confidence=1.0, zone=activity.zone,
            track_id=activity.track_id, bbox=activity.bbox,
        )
        payload = {
            "id": row_id, "event_type": activity.event_type,
            "camera_id": activity.camera_id, "camera_name": cam_name,
            "label": activity.label, "confidence": 1.0,
            "zone": activity.zone, "track_id": activity.track_id,
            "bbox": list(activity.bbox), "timestamp": _now_iso(),
        }
        if activity.event_type == "LOITERING":
            payload["duration_seconds"] = activity.duration_seconds
        elif activity.event_type == "RUNNING":
            payload["speed"] = activity.speed
        elif activity.event_type == "CROWD":
            payload["crowd_count"] = activity.crowd_count
        self._broadcast_payload(payload)
        logger.info("ACTIVITY %s [%s] track=%d zone=%s",
                    activity.event_type, activity.camera_id,
                    activity.track_id, activity.zone)

    def receive_detection(self, camera_id, label, confidence, track_id, bbox) -> None:
        """Generic detection event (backwards compat)."""
        now = time.monotonic()
        key = (camera_id, track_id, "__detection__")
        if not self._check_cooldown(key, now, EVENT_COOLDOWN):
            return
        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id, camera_name=cam_name,
            event_type="DETECTED", label=label,
            confidence=confidence, zone="",
            track_id=track_id, bbox=bbox,
        )
        self._broadcast_payload({
            "id": row_id, "event_type": "DETECTED",
            "camera_id": camera_id, "camera_name": cam_name,
            "label": label, "confidence": round(confidence, 3),
            "zone": "", "track_id": track_id,
            "bbox": list(bbox), "timestamp": _now_iso(),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_cooldown(self, key: tuple, now: float, window: float) -> bool:
        """Return True if event should fire (outside cooldown). Updates tracker."""
        with self._cooldown_lock:
            last = self._cooldown.get(key, 0.0)
            if now - last < window:
                return False
            self._cooldown[key] = now
        return True


    def receive_face(self, camera_id: str, face) -> None:
        """Handle a face recognition result."""
        now = time.monotonic()
        event_type = "FACE_MATCH" if face.matched else "UNKNOWN_FACE"
        # Only alert on matches (unknown face alerts would be too noisy)
        if not face.matched:
            return
        key = ("FACE_MATCH", camera_id, face.person_id)
        if not self._check_cooldown(key, now, EVENT_COOLDOWN * 3):
            return
        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id, camera_name=cam_name,
            event_type="FACE_MATCH", label=face.name,
            confidence=face.similarity, zone="",
            track_id=0, bbox=face.bbox,
        )
        self._broadcast_payload({
            "id": row_id, "event_type": "FACE_MATCH",
            "camera_id": camera_id, "camera_name": cam_name,
            "label": f"WATCHLIST: {face.name}", "confidence": round(face.similarity, 3),
            "zone": "", "track_id": 0,
            "bbox": list(face.bbox), "timestamp": _now_iso(),
            "person_name": face.name,
        })
        logger.warning("!!! FACE MATCH [%s] -> '%s' (sim=%.0f%%)",
                       camera_id, face.name, face.similarity * 100)

    def receive_plate(self, camera_id: str, plate) -> None:
        """Handle an ANPR plate reading result."""
        now = time.monotonic()
        key = ("PLATE", camera_id, plate.plate_text)
        if not self._check_cooldown(key, now, EVENT_COOLDOWN * 2):
            return
        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id, camera_name=cam_name,
            event_type="PLATE_DETECTED", label=plate.plate_text,
            confidence=plate.confidence, zone="",
            track_id=0, bbox=plate.plate_bbox,
        )
        self._broadcast_payload({
            "id": row_id, "event_type": "PLATE_DETECTED",
            "camera_id": camera_id, "camera_name": cam_name,
            "label": plate.plate_text, "confidence": round(plate.confidence, 3),
            "zone": "", "track_id": 0,
            "bbox": list(plate.plate_bbox), "timestamp": _now_iso(),
            "plate_text": plate.plate_text, "raw_text": plate.raw_text,
        })
        logger.info("ANPR [%s] plate=%s conf=%.0f%%",
                    camera_id, plate.plate_text, plate.confidence * 100)

    def receive_night_movement(self, camera_id: str, object_count: int) -> None:
        """Handle night-time movement detection."""
        now = time.monotonic()
        key = ("NIGHT_MOVEMENT", camera_id)
        if not self._check_cooldown(key, now, EVENT_COOLDOWN * 4):
            return
        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id, camera_name=cam_name,
            event_type="NIGHT_MOVEMENT", label="Movement",
            confidence=1.0, zone="",
            track_id=0, bbox=(0,0,0,0),
        )
        self._broadcast_payload({
            "id": row_id, "event_type": "NIGHT_MOVEMENT",
            "camera_id": camera_id, "camera_name": cam_name,
            "label": f"Night Movement ({object_count} objects)",
            "confidence": 1.0, "zone": "", "track_id": 0,
            "bbox": [0,0,0,0], "timestamp": _now_iso(),
            "object_count": object_count,
        })
        logger.info("NIGHT MOVEMENT [%s] %d object(s)", camera_id, object_count)
    def _broadcast_payload(self, payload: dict) -> None:
        """JSON-encode and push to all WebSocket queues (thread-safe)."""
        if not self._loop or self._loop.is_closed():
            return
        text = json.dumps(payload)
        with self._sub_lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                self._loop.call_soon_threadsafe(q.put_nowait, text)
            except (asyncio.QueueFull, Exception):
                pass

