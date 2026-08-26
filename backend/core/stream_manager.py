"""
stream_manager.py - Phase 4 (complete).

Creates shared FaceRecognizer + WatchlistDB (one instance across all cameras
for consistent watchlist state), then creates one FramePipeline per camera.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from backend.config import AI_ENABLED, CAMERAS, DB_PATH
from backend.core.camera_stream import CameraStream, CameraStatus
from backend.core.database import Database

logger = logging.getLogger(__name__)


class StreamManager:

    def __init__(self) -> None:
        self._streams: dict[str, CameraStream] = {}
        self._event_manager = None
        self._database: Optional[Database] = None
        self._face_recognizer = None
        self._watchlist_db = None
        self._session_manager = None

    def start_all(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        from backend.core.session_manager import SessionManager
        self._session_manager = SessionManager(loop=loop)

        if AI_ENABLED:
            try:
                from backend.core.event_manager import EventManager
                self._database = Database(DB_PATH)
                self._event_manager = EventManager(database=self._database, loop=loop)

                # Face recognizer (shared — one watchlist across all cameras)
                from backend.core.face_recognition import FaceRecognizer
                self._face_recognizer = FaceRecognizer(device="cuda")

                # Watchlist DB
                from backend.core.watchlist import WatchlistDB
                wl_db_path = Path(str(DB_PATH).replace("events.db", "watchlist.db"))
                face_img_dir = Path("data/watchlist_images")
                self._watchlist_db = WatchlistDB(wl_db_path, face_img_dir)

                # Load existing watchlist entries into face recognizer
                entries = self._watchlist_db.all_entries()
                if entries:
                    self._face_recognizer.load_watchlist(entries)
                    logger.info("Watchlist loaded: %d entries.", len(entries))

                logger.info("AI Phase 4 enabled: YOLO + YOLO-World + FRS + ANPR + Night.")
            except Exception as exc:
                logger.error("AI setup failed: %s", exc)
                self._event_manager = None

        for cam_id, cfg in CAMERAS.items():
            pipeline = None
            if AI_ENABLED and self._event_manager is not None:
                try:
                    from backend.core.pipeline import FramePipeline
                    pipeline = FramePipeline(
                        camera_id=cam_id,
                        event_manager=self._event_manager,
                        face_recognizer=self._face_recognizer,
                    )
                except Exception as exc:
                    logger.warning("[%s] Pipeline creation failed: %s", cam_id, exc)

            stream = CameraStream(
                camera_id=cam_id,
                name=cfg["name"],
                source=cfg["source"],
                source_type=cfg.get("type", "file"),
                pipeline=pipeline,
            )
            self._streams[cam_id] = stream
            stream.start()

        logger.info("StreamManager: %d stream(s) started.", len(self._streams))

    def stop_all(self) -> None:
        logger.info("Stopping %d streams...", len(self._streams))
        for stream in self._streams.values():
            stream.stop()
        self._streams.clear()

    def get_stream(self, camera_id: str) -> Optional[CameraStream]:
        return self._streams.get(camera_id)

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        stream = self.get_stream(camera_id)
        return stream.get_frame() if stream else None

    def get_statuses(self) -> list[dict]:
        result = []
        for cam_id, cfg in CAMERAS.items():
            stream = self._streams.get(cam_id)
            status = stream.status.value if stream else CameraStatus.OFFLINE.value
            result.append({"id": cam_id, "name": cfg["name"], "status": status})
        return result

    def camera_ids(self) -> list[str]:
        return list(CAMERAS.keys())

    @property
    def event_manager(self):
        return self._event_manager

    @property
    def session_manager(self):
        return self._session_manager
