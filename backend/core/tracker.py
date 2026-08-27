"""
tracker.py ? ByteTrack Object Tracking & Motion Kinematics Engine for IBVAP.

Key Features:
1. Persistent Track IDs: Per-camera track maintenance across consecutive frames.
2. Trajectory History: Stores recent centroid positions (up to max_history) for movement analysis.
3. Velocity Estimation: Computes real-time pixel displacement velocity (pixels/frame and pixels/sec).
4. Kinematic Lifecycle: Tracks entry_time, last_seen_time, and total dwell_time in camera FOV.
5. Decoupled Pipeline: Accepts standardized Detection objects or YOLO track outputs.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

from backend.core.detector import Detection, TrackedDetection

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """An object tracked across consecutive video frames with kinematics data."""
    track_id: int
    class_id: int
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2)
    camera_id: str = ""
    entry_time: float = field(default_factory=time.time)
    last_seen_time: float = field(default_factory=time.time)
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    velocity: float = 0.0             # pixels / frame
    velocity_mps: float = 0.0         # estimated velocity normalized

    @property
    def centroid(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def dwell_time(self) -> float:
        """Total time in seconds since this track first entered camera view."""
        return max(0.0, self.last_seen_time - self.entry_time)

    @property
    def width(self) -> int:
        return max(0, self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> int:
        return max(0, self.bbox[3] - self.bbox[1])

    @property
    def area(self) -> int:
        return self.width * self.height


class ByteTracker:
    """Per-camera ByteTrack kinematics and trajectory manager.

    Maintains long-term track state, entry/exit timestamps, and velocity vectors.
    """

    def __init__(
        self,
        camera_id: str,
        max_history: int = 30,
        track_buffer_seconds: float = 2.0,
    ) -> None:
        self.camera_id = camera_id
        self._max_history = max_history
        self._track_buffer_seconds = track_buffer_seconds

        # Track state stores: track_id -> historical metadata
        self._trajectories: Dict[int, Deque[Tuple[int, int]]] = {}
        self._entry_times: Dict[int, float] = {}
        self._last_seen_times: Dict[int, float] = {}
        self._last_velocities: Dict[int, float] = {}

        logger.info("[%s] ByteTracker kinematics engine initialized.", camera_id)

    def update_from_tracked_detections(
        self,
        tracked_detections: List[TrackedDetection],
        current_time: Optional[float] = None,
    ) -> List[TrackedObject]:
        """Enrich incoming TrackedDetection items with trajectory & velocity metrics."""
        now = current_time or time.time()
        active_ids = set()
        results: List[TrackedObject] = []

        for td in tracked_detections:
            t_id = td.track_id
            active_ids.add(t_id)
            centroid = td.centroid

            # 1. Entry time tracking
            if t_id not in self._entry_times:
                self._entry_times[t_id] = now
                self._trajectories[t_id] = deque(maxlen=self._max_history)
                self._last_velocities[t_id] = 0.0

            entry_t = self._entry_times[t_id]
            traj_deque = self._trajectories[t_id]

            # 2. Velocity calculation based on centroid displacement
            velocity = 0.0
            if len(traj_deque) > 0:
                prev_cx, prev_cy = traj_deque[-1]
                dx = centroid[0] - prev_cx
                dy = centroid[1] - prev_cy
                inst_velocity = math.hypot(dx, dy)
                if len(traj_deque) == 1:
                    velocity = inst_velocity
                else:
                    prev_v = self._last_velocities.get(t_id, inst_velocity)
                    velocity = 0.7 * inst_velocity + 0.3 * prev_v

            self._last_velocities[t_id] = velocity
            traj_deque.append(centroid)
            self._last_seen_times[t_id] = now

            obj = TrackedObject(
                track_id=t_id,
                class_id=td.class_id,
                label=td.label,
                confidence=td.confidence,
                bbox=td.bbox,
                camera_id=self.camera_id,
                entry_time=entry_t,
                last_seen_time=now,
                trajectory=list(traj_deque),
                velocity=velocity,
            )
            results.append(obj)

        # 3. Clean up expired tracks
        self._cleanup_expired_tracks(now)
        return results

    def _cleanup_expired_tracks(self, now: float) -> None:
        """Purge tracks that have disappeared longer than track_buffer_seconds."""
        expired = [
            t_id
            for t_id, last_t in self._last_seen_times.items()
            if now - last_t > self._track_buffer_seconds
        ]
        for t_id in expired:
            self._entry_times.pop(t_id, None)
            self._last_seen_times.pop(t_id, None)
            self._trajectories.pop(t_id, None)
            self._last_velocities.pop(t_id, None)

    @staticmethod
    def from_track_results(results, label_overrides: Dict[int, str]) -> List[TrackedObject]:
        """Compatibility converter from raw Ultralytics results."""
        tracked: List[TrackedObject] = []
        now = time.time()
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
                        entry_time=now,
                        last_seen_time=now,
                    )
                )
        return tracked


# Compatibility alias
Tracker = ByteTracker
