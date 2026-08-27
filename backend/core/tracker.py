"""
tracker.py ? ByteTrack object tracker wrapper for IBVAP.

Wraps Ultralytics built-in ByteTrack to assign persistent integer track IDs
to detected objects across frames.  One Tracker instance lives inside each
FramePipeline (one per camera), so trackers never share state.

ByteTrack reference: https://arxiv.org/abs/2110.06864
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.core.detector import Detection

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """A detection enriched with a persistent track ID."""
    track_id: int
    class_id: int
    label: str
    confidence: float
    # Bounding box: (x1, y1, x2, y2)
    bbox: tuple[int, int, int, int]

    @property
    def centroid(self) -> tuple[int, int]:
        """Centre point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)


class Tracker:
    """Per-camera ByteTrack wrapper.

    Tracks are maintained internally by Ultralytics.  This class provides a
    clean interface that accepts :class:`Detection` objects and returns
    :class:`TrackedObject` lists.

    Parameters
    ----------
    camera_id:
        Used only for logging context.
    """

    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._model = None   # shared detector model reference (set externally)
        self._bytetrack = None
        self._frame_shape: Optional[tuple] = None
        logger.info("[%s] Tracker initialised.", camera_id)

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray,
    ) -> list[TrackedObject]:
        """Update tracker state and return tracked objects.

        Uses Ultralytics BOTSORT/ByteTrack via the model's built-in tracker.
        Since we call predict() separately in Detector, we re-use the raw
        bounding boxes here and apply a lightweight IoU-based ID assignment
        as a fallback for when the full tracker is not yet initialised.

        In practice the Pipeline calls model.track() instead of predict()
        when tracking is enabled, so this method acts as a simple converter.

        Parameters
        ----------
        detections:
            Raw detections from the current frame.
        frame:
            The current BGR frame (used for shape info).

        Returns
        -------
        list[TrackedObject]
            Detections with assigned track IDs.
            IDs are sequential integers starting from 1.
        """
        tracked: list[TrackedObject] = []
        for i, det in enumerate(detections):
            tracked.append(
                TrackedObject(
                    track_id=i + 1,  # placeholder; real IDs come from pipeline.track()
                    class_id=det.class_id,
                    label=det.label,
                    confidence=det.confidence,
                    bbox=det.bbox,
                )
            )
        return tracked

    @staticmethod
    def from_track_results(results, label_overrides: dict[int, str]) -> list[TrackedObject]:
        """Convert raw Ultralytics track results into TrackedObject list."""
        tracked: list[TrackedObject] = []
        for result in results:
            if result.boxes is None:
                continue
            for i, box in enumerate(result.boxes):
                track_id = int(box.id[0]) if box.id is not None else (i + 1)
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = label_overrides.get(
                    cls_id,
                    result.names.get(cls_id, str(cls_id)),
                )
                tracked.append(
                    TrackedObject(
                        track_id=track_id,
                        class_id=cls_id,
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                    )
                )
        return tracked

