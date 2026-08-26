"""
event_manager.py ? Central event hub for IBVAP Phase 2.

The EventManager:
  1. Receives raw FenceEvent objects from every FramePipeline.
  2. Deduplicates: suppresses repeated alerts for the same
     (camera_id, track_id, zone_name) within EVENT_COOLDOWN seconds.
  3. Persists each unique event to SQLite via Database.
  4. Broadcasts a JSON payload to all connected WebSocket clients.

WebSocket clients subscribe by calling ``subscribe()`` and receive an
asyncio.Queue that the event manager pushes packets into.  They unsubscribe
via ``unsubscribe()``.

Thread safety
-------------
``receive()`` is called from camera background threads.
Queue operations are thread-safe by design.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import threading
from typing import Optional

from backend.config import EVENT_COOLDOWN, CAMERAS
from backend.core.database import Database
from backend.core.fence import FenceEvent

logger = logging.getLogger(__name__)


class EventManager:
    """Central router for AI-detected events.

    Parameters
    ----------
    database:
        An open :class:`Database` instance for persistence.
    loop:
        The asyncio event loop that WebSocket coroutines run on.
        Pass ``None`` to disable WebSocket broadcasting (useful for tests).
    """

    def __init__(self, database: Database, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._db = database
        self._loop = loop

        # Cooldown tracker: key = (camera_id, track_id, zone_name) ? last_alert_time
        self._cooldown: dict[tuple, float] = {}
        self._cooldown_lock = threading.Lock()

        # Connected WebSocket client queues
        self._subscribers: list[asyncio.Queue] = []
        self._sub_lock = threading.Lock()

    # ------------------------------------------------------------------
    # WebSocket subscription management
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        """Register a new WebSocket client and return its message queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        with self._sub_lock:
            self._subscribers.append(q)
        logger.debug("EventManager: WebSocket client subscribed (%d total).", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a WebSocket client queue."""
        with self._sub_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass
        logger.debug("EventManager: WebSocket client unsubscribed (%d remaining).", len(self._subscribers))

    # ------------------------------------------------------------------
    # Event ingestion (called from camera threads)
    # ------------------------------------------------------------------

    def receive(self, events: list[FenceEvent]) -> None:
        """Process a batch of fence events from one camera frame.

        Called from the camera background thread ? must be fast and
        non-blocking.  WebSocket broadcast is scheduled onto the event loop
        rather than awaited directly.
        """
        now = time.monotonic()
        for ev in events:
            key = (ev.camera_id, ev.track_id, ev.zone_name)
            with self._cooldown_lock:
                last = self._cooldown.get(key, 0.0)
                if now - last < EVENT_COOLDOWN:
                    continue  # suppress duplicate within cooldown window
                self._cooldown[key] = now

            # Persist to SQLite
            cam_name = CAMERAS.get(ev.camera_id, {}).get("name", ev.camera_id)
            row_id = self._db.insert_event(
                camera_id=ev.camera_id,
                camera_name=cam_name,
                event_type="INTRUSION",
                label=ev.label,
                confidence=ev.confidence,
                zone=ev.zone_name,
                track_id=ev.track_id,
                bbox=ev.bbox,
            )

            # Build broadcast payload
            payload = json.dumps({
                "id": row_id,
                "camera_id": ev.camera_id,
                "camera_name": cam_name,
                "event_type": "INTRUSION",
                "label": ev.label,
                "confidence": round(ev.confidence, 3),
                "zone": ev.zone_name,
                "track_id": ev.track_id,
                "bbox": list(ev.bbox),
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            })

            logger.info(
                "EVENT [%s] %s track=%d zone=%s conf=%.2f",
                ev.camera_id, ev.label, ev.track_id, ev.zone_name, ev.confidence,
            )

            self._broadcast(payload)

    def receive_detection(
        self,
        camera_id: str,
        label: str,
        confidence: float,
        track_id: int,
        bbox: tuple[int, int, int, int],
    ) -> None:
        """Record a plain detection event (no fence zone required).

        Used for logging detected objects even when no zone is configured.
        Applies the same cooldown logic.
        """
        now = time.monotonic()
        key = (camera_id, track_id, "__detection__")
        with self._cooldown_lock:
            last = self._cooldown.get(key, 0.0)
            if now - last < EVENT_COOLDOWN:
                return
            self._cooldown[key] = now

        cam_name = CAMERAS.get(camera_id, {}).get("name", camera_id)
        row_id = self._db.insert_event(
            camera_id=camera_id,
            camera_name=cam_name,
            event_type="DETECTED",
            label=label,
            confidence=confidence,
            zone="",
            track_id=track_id,
            bbox=bbox,
        )

        payload = json.dumps({
            "id": row_id,
            "camera_id": camera_id,
            "camera_name": cam_name,
            "event_type": "DETECTED",
            "label": label,
            "confidence": round(confidence, 3),
            "zone": "",
            "track_id": track_id,
            "bbox": list(bbox),
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        })

        self._broadcast(payload)

    # ------------------------------------------------------------------
    # WebSocket broadcast (non-blocking, thread-safe)
    # ------------------------------------------------------------------

    def _broadcast(self, payload: str) -> None:
        """Push a JSON string to all connected WebSocket client queues.

        Called from camera threads. Uses call_soon_threadsafe to safely
        schedule onto the asyncio event loop.
        """
        if not self._loop or self._loop.is_closed():
            return

        with self._sub_lock:
            subscribers = list(self._subscribers)

        for q in subscribers:
            try:
                self._loop.call_soon_threadsafe(q.put_nowait, payload)
            except asyncio.QueueFull:
                pass  # slow client ? skip this event rather than blocking
            except Exception as exc:
                logger.debug("Broadcast error: %s", exc)
