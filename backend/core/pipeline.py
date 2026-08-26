"""
pipeline.py ? Per-camera AI processing pipeline for IBVAP Phase 2.

Each FramePipeline instance runs inside the CameraStream's background thread.
The pipeline receives raw frames from the reader and returns annotated frames
back for storage in the latest-frame buffer.

Processing chain
----------------
raw frame
    -> Detector (YOLOv8, every N frames)
    -> Tracker  (ByteTrack, assigns persistent IDs)
    -> VirtualFence (polygon intrusion check)
    -> Annotator (draw boxes, labels, zones)
    -> EventManager.receive(fence_events)
    -> annotated frame (returned to CameraStream)

The raw detection results are cached between detection frames so the
bounding boxes remain visible even on skipped frames.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

import cv2
import numpy as np

from backend.config import (
    BBOX_COLORS,
    DETECT_EVERY_N_FRAMES,
    LABEL_OVERRIDES,
    ZONES,
    AI_ENABLED,
)
from backend.core.fence import VirtualFence
from backend.core.tracker import TrackedObject, Tracker

if TYPE_CHECKING:
    from backend.core.detector import Detector
    from backend.core.event_manager import EventManager

logger = logging.getLogger(__name__)


class FramePipeline:
    """Orchestrates per-frame AI processing for one camera.

    Parameters
    ----------
    camera_id:
        Owning camera identifier.
    detector:
        Shared :class:`Detector` instance (shared across all cameras).
    event_manager:
        Shared :class:`EventManager` instance.
    """

    def __init__(
        self,
        camera_id: str,
        detector: "Detector",
        event_manager: "EventManager",
    ) -> None:
        self.camera_id = camera_id
        self._detector = detector
        self._event_manager = event_manager
        self._frame_count = 0

        # Each pipeline gets its own YOLO model so that persist=True tracker
        # state is completely isolated between cameras.
        self._model = None   # loaded lazily on first frame
        self._device = detector._device
        self._model_name = detector._model_name

        # Virtual fence
        zones_cfg = ZONES.get(camera_id, [])
        self._fence = VirtualFence(camera_id=camera_id, zones=zones_cfg)

        # Cache last tracked objects between detection frames
        self._last_tracked: list[TrackedObject] = []

        logger.info("[%s] FramePipeline ready (detect_every=%d).", camera_id, DETECT_EVERY_N_FRAMES)

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Run the full pipeline on one raw frame.

        Parameters
        ----------
        frame:
            BGR frame from CameraStream.

        Returns
        -------
        np.ndarray
            Annotated BGR frame ready for the MJPEG endpoint.
        """
        if not AI_ENABLED:
            return frame

        self._frame_count += 1

        # --- Detection (every N frames) ---
        if self._frame_count % DETECT_EVERY_N_FRAMES == 0:
            tracked = self._run_detection_and_tracking(frame)
            self._last_tracked = tracked
        else:
            tracked = self._last_tracked

        # --- Virtual fence check ---
        fence_events = self._fence.check(tracked)

        # --- Emit events ---
        if fence_events:
            self._event_manager.receive(fence_events)

        # --- Annotate frame ---
        annotated = self._annotate(frame.copy(), tracked, fence_events)

        return annotated

    # ------------------------------------------------------------------
    # Detection + tracking
    # ------------------------------------------------------------------

    def _run_detection_and_tracking(self, frame: np.ndarray) -> list[TrackedObject]:
        """Run YOLO track() and return tracked objects with persistent IDs."""
        try:
            from backend.config import YOLO_CONFIDENCE, YOLO_CLASSES

            # Lazy-load a dedicated YOLO model for this camera pipeline.
            # Each pipeline must have its own model instance so that
            # persist=True keeps tracker state isolated per camera.
            if self._model is None:
                from ultralytics import YOLO
                self._model = YOLO(self._model_name)
                self._model.to(self._device)
                logger.info("[%s] Per-pipeline YOLO model loaded on %s.", self.camera_id, self._device)

            results = self._model.track(
                source=frame,
                conf=YOLO_CONFIDENCE,
                classes=YOLO_CLASSES,
                device=self._device,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False,
            )
            return Tracker.from_track_results(results, LABEL_OVERRIDES)

        except Exception as exc:
            logger.warning("[%s] Detection/tracking error: %s", self.camera_id, exc)
            return []


    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _annotate(
        self,
        frame: np.ndarray,
        tracked: list[TrackedObject],
        fence_events,
    ) -> np.ndarray:
        """Draw zones, bounding boxes, labels, and track IDs onto the frame."""
        # Active zone names (have at least one intruder)
        active_zones = {ev.zone_name for ev in fence_events}

        # Draw fence zones first (underneath boxes)
        self._fence.draw_zones(frame, active_zones)

        # Draw each tracked object
        for obj in tracked:
            x1, y1, x2, y2 = obj.bbox
            color = BBOX_COLORS.get(obj.label, BBOX_COLORS["Unknown"])

            # Is this object in a zone?
            in_zone = any(ev.track_id == obj.track_id for ev in fence_events)
            if in_zone:
                # Brighter red border for intruders
                color = (0, 60, 220)
                cv2.rectangle(frame, (x1 - 1, y1 - 1), (x2 + 1, y2 + 1), color, 3)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label background
            label_text = f"{obj.label} #{obj.track_id} {obj.confidence:.0%}"
            (tw, th), baseline = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
            )
            cv2.rectangle(
                frame,
                (x1, y1 - th - baseline - 4),
                (x1 + tw + 4, y1),
                color, -1,
            )
            cv2.putText(
                frame, label_text,
                (x1 + 2, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

        # Intrusion alert banner
        if fence_events:
            banner = f"! INTRUSION DETECTED: {fence_events[0].label} in {fence_events[0].zone_name}"
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (0, h - 32), (w, h), (0, 0, 160), -1)
            cv2.putText(
                frame, banner,
                (8, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

        return frame
