"""
fence.py ? Virtual fence / ROI intrusion detection for IBVAP.

Each camera can have one or more named polygon zones defined in config.py.
On every frame, this module checks whether a tracked object's centroid
falls inside any zone polygon.

Uses cv2.pointPolygonTest for the containment check (fast, C-level).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from backend.core.tracker import TrackedObject

logger = logging.getLogger(__name__)


@dataclass
class FenceEvent:
    """Raised when a tracked object enters a virtual fence zone."""
    camera_id: str
    zone_name: str
    track_id: int
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    centroid: tuple[int, int]


class VirtualFence:
    """Checks tracked objects against configured polygon zones.

    Parameters
    ----------
    camera_id:
        Camera this fence belongs to (for logging + events).
    zones:
        List of zone dicts: ``[{"name": str, "polygon": [(x,y), ...]}, ...]``
    """

    def __init__(self, camera_id: str, zones: list[dict]) -> None:
        self.camera_id = camera_id
        self._zones: list[tuple[str, np.ndarray]] = []

        for z in zones:
            name = z.get("name", "Zone")
            pts = np.array(z["polygon"], dtype=np.int32)
            self._zones.append((name, pts))

        logger.info("[%s] VirtualFence: %d zone(s) configured.", camera_id, len(self._zones))

    def check(self, tracked: list[TrackedObject]) -> list[FenceEvent]:
        """Return intrusion events for objects whose centroid is inside a zone.

        Parameters
        ----------
        tracked:
            List of tracked objects from the current frame.

        Returns
        -------
        list[FenceEvent]
            One event per (object, zone) pair where the object is inside.
        """
        events: list[FenceEvent] = []
        for obj in tracked:
            cx, cy = obj.centroid
            for zone_name, polygon in self._zones:
                # pointPolygonTest returns positive if point is inside
                dist = cv2.pointPolygonTest(polygon, (float(cx), float(cy)), measureDist=False)
                if dist >= 0:
                    events.append(
                        FenceEvent(
                            camera_id=self.camera_id,
                            zone_name=zone_name,
                            track_id=obj.track_id,
                            label=obj.label,
                            confidence=obj.confidence,
                            bbox=obj.bbox,
                            centroid=(cx, cy),
                        )
                    )
        return events

    def draw_zones(self, frame: np.ndarray, active_zone_names: set[str]) -> np.ndarray:
        """Overlay zone polygons onto a frame.

        Parameters
        ----------
        frame:
            BGR image to draw on (modified in-place).
        active_zone_names:
            Zone names that currently have at least one intruder ?
            these are drawn in red/amber; inactive zones in dim green.
        """
        for zone_name, polygon in self._zones:
            is_active = zone_name in active_zone_names
            color = (0, 60, 200) if is_active else (0, 120, 0)
            alpha = 0.25 if is_active else 0.10

            # Fill with semi-transparent overlay
            overlay = frame.copy()
            cv2.fillPoly(overlay, [polygon], color)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

            # Border
            border_color = (0, 80, 255) if is_active else (0, 200, 0)
            cv2.polylines(frame, [polygon], isClosed=True, color=border_color, thickness=2)

            # Label
            x, y = polygon[0]
            cv2.putText(
                frame, zone_name,
                (int(x) + 4, int(y) + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                border_color, 1, cv2.LINE_AA,
            )

        return frame
