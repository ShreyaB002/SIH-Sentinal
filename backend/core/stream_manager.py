"""
StreamManager ? lifecycle manager for all configured camera streams.

Phase 2: StreamManager now creates a shared Detector and EventManager,
then builds one FramePipeline per camera and injects it into each
CameraStream.  The rest of the system is unchanged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

from backend.config import AI_ENABLED, CAMERAS, DB_PATH, YOLO_MODEL, YOLO_CONFIDENCE, YOLO_CLASSES
from backend.core.camera_stream import CameraStream, CameraStatus
from backend.core.database import Database

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages the lifecycle of all active :class:`CameraStream` instances.

    Usage::

        manager = StreamManager()
        manager.start_all(loop=asyncio.get_event_loop())
        ...
        manager.stop_all()
    """

    def __init__(self) -> None:
        self._streams: dict[str, CameraStream] = {}
        self._event_manager = None
        self._database: Optional[Database] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_all(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Create and start all camera streams, optionally with AI pipelines."""
        # --- Phase 2: set up shared AI components ---
        if AI_ENABLED:
            try:
                from backend.core.detector import Detector
                from backend.core.event_manager import EventManager

                self._database = Database(DB_PATH)
                self._event_manager = EventManager(database=self._database, loop=loop)

                detector = Detector(
                    model_name=YOLO_MODEL,
                    confidence=YOLO_CONFIDENCE,
                    class_ids=YOLO_CLASSES,
                )
                logger.info("AI pipeline enabled (YOLO + ByteTrack + VirtualFence).")
            except Exception as exc:
                logger.error("AI pipeline setup failed, falling back to Phase 1 mode: %s", exc)
                detector = None
                self._event_manager = None
        else:
            detector = None
            logger.info("AI_ENABLED=False ? running in Phase 1 mode (no detection).")

        # --- Create one CameraStream per configured camera ---
        for cam_id, cfg in CAMERAS.items():
            pipeline = None
            if AI_ENABLED and detector is not None and self._event_manager is not None:
                try:
                    from backend.core.pipeline import FramePipeline
                    pipeline = FramePipeline(
                        camera_id=cam_id,
                        detector=detector,
                        event_manager=self._event_manager,
                    )
                except Exception as exc:
                    logger.warning("[%s] Could not create FramePipeline: %s", cam_id, exc)

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
        """Signal all streams to stop and clean up resources."""
        logger.info("StreamManager: stopping %d stream(s)...", len(self._streams))
        for stream in self._streams.values():
            stream.stop()
        self._streams.clear()
        logger.info("StreamManager: all streams stopped.")

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get_stream(self, camera_id: str) -> Optional[CameraStream]:
        return self._streams.get(camera_id)

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        stream = self.get_stream(camera_id)
        if stream is None:
            return None
        return stream.get_frame()

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
        """Return the shared EventManager (or None if AI is disabled)."""
        return self._event_manager
