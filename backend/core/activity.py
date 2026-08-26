"""
activity.py - Suspicious activity analyzer for IBVAP Phase 3.

Runs AFTER YOLO tracking each frame. Maintains a rolling history of tracked
object positions per camera and applies behavioral rules to detect:

  - LOITERING   : Person stays in a zone longer than LOITER_SECONDS
  - RUNNING     : Person centroid velocity exceeds RUNNING_SPEED px/frame
  - CROWD       : More than CROWD_THRESHOLD persons in a zone simultaneously

Each rule has its own cooldown (via EventManager) to suppress repeats.
This module is stateful (history accumulates across frames) and NOT thread-safe
across cameras - each camera pipeline owns its own ActivityAnalyzer instance.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backend.core.tracker import TrackedObject

logger = logging.getLogger(__name__)


@dataclass
class ActivityEvent:
    """An event raised by the activity analyzer."""
    event_type: str          # "LOITERING" | "RUNNING" | "CROWD"
    camera_id: str
    label: str
    track_id: int
    zone: str
    bbox: tuple[int, int, int, int]
    # Extra payload per event type
    duration_seconds: float = 0.0   # LOITERING
    speed: float = 0.0              # RUNNING (px/frame)
    crowd_count: int = 0            # CROWD


@dataclass
class _TrackEntry:
    """Internal rolling history for one tracked object."""
    track_id: int
    label: str
    # Deque of (timestamp, centroid_x, centroid_y, zone_names_set)
    history: deque = field(default_factory=lambda: deque(maxlen=300))
    # Zone entry timestamps  {zone_name -> first_seen_monotonic}
    zone_entry: dict = field(default_factory=dict)


class ActivityAnalyzer:
    """Per-camera suspicious activity detector.

    Parameters
    ----------
    camera_id : str
        Owning camera ID (for logging and event payloads).
    loiter_seconds : float
        How long a person must stay in a zone to trigger LOITERING.
    running_speed : float
        Centroid displacement (pixels/frame) above which RUNNING fires.
    crowd_threshold : int
        Number of persons in a zone at once to trigger CROWD.
    """

    def __init__(
        self,
        camera_id: str,
        loiter_seconds: float = 10.0,
        running_speed: float = 25.0,
        crowd_threshold: int = 3,
    ) -> None:
        self.camera_id = camera_id
        self._loiter_seconds = loiter_seconds
        self._running_speed = running_speed
        self._crowd_threshold = crowd_threshold

        # track_id -> _TrackEntry
        self._tracks: dict[int, _TrackEntry] = {}
        # Cooldown for activity events: key=(event_type, track_id, zone) -> last_fired_time
        self._cooldown: dict[tuple, float] = {}
        self._activity_cooldown = 15.0

        logger.info(
            "[%s] ActivityAnalyzer: loiter=%.0fs speed=%.0fpx crowd=%d",
            camera_id, loiter_seconds, running_speed, crowd_threshold,
        )

    def analyze(
        self,
        tracked: list[TrackedObject],
        active_zones: dict[int, list[str]],   # track_id -> list of zone names it's in
    ) -> list[ActivityEvent]:
        """Update history and return activity events for this frame.

        Parameters
        ----------
        tracked : list[TrackedObject]
            Current frame tracked objects.
        active_zones : dict[int, list[str]]
            Maps track_id -> list of zone names the object is currently inside.
            Build this from VirtualFence.check() results.

        Returns
        -------
        list[ActivityEvent]
            Activity events detected this frame (de-duped by cooldown).
        """
        now = time.monotonic()
        events: list[ActivityEvent] = []

        # Update history for each current tracked object
        current_ids = set()
        for obj in tracked:
            current_ids.add(obj.track_id)
            cx, cy = obj.centroid
            zones_now = set(active_zones.get(obj.track_id, []))

            if obj.track_id not in self._tracks:
                self._tracks[obj.track_id] = _TrackEntry(
                    track_id=obj.track_id,
                    label=obj.label,
                )

            entry = self._tracks[obj.track_id]
            entry.history.append((now, cx, cy, zones_now))

            # --- Rule: RUNNING ---
            if len(entry.history) >= 2 and obj.label == "Person":
                prev = entry.history[-2]
                dx = cx - prev[1]
                dy = cy - prev[2]
                speed = (dx**2 + dy**2) ** 0.5
                if speed > self._running_speed:
                    ev = self._maybe_fire(
                        "RUNNING", obj.track_id, "",
                        ActivityEvent(
                            event_type="RUNNING",
                            camera_id=self.camera_id,
                            label=obj.label,
                            track_id=obj.track_id,
                            zone="",
                            bbox=obj.bbox,
                            speed=round(speed, 1),
                        ),
                        now,
                    )
                    if ev:
                        events.append(ev)

            # --- Rule: LOITERING ---
            if obj.label == "Person":
                for zone_name in zones_now:
                    if zone_name not in entry.zone_entry:
                        entry.zone_entry[zone_name] = now
                    elapsed = now - entry.zone_entry[zone_name]
                    if elapsed >= self._loiter_seconds:
                        ev = self._maybe_fire(
                            "LOITERING", obj.track_id, zone_name,
                            ActivityEvent(
                                event_type="LOITERING",
                                camera_id=self.camera_id,
                                label=obj.label,
                                track_id=obj.track_id,
                                zone=zone_name,
                                bbox=obj.bbox,
                                duration_seconds=round(elapsed, 1),
                            ),
                            now,
                        )
                        if ev:
                            events.append(ev)

                # Clear zone_entry for zones the person has left
                for zone_name in list(entry.zone_entry.keys()):
                    if zone_name not in zones_now:
                        del entry.zone_entry[zone_name]

        # Prune disappeared tracks
        disappeared = set(self._tracks.keys()) - current_ids
        for tid in disappeared:
            self._tracks[tid].zone_entry.clear()
            # Keep history briefly for re-ID; prune after history maxlen expires naturally

        # --- Rule: CROWD ---
        # Count persons per zone across all current tracked objects
        zone_person_count: dict[str, list[int]] = defaultdict(list)
        for obj in tracked:
            if obj.label == "Person":
                for zone_name in active_zones.get(obj.track_id, []):
                    zone_person_count[zone_name].append(obj.track_id)

        for zone_name, ids in zone_person_count.items():
            count = len(ids)
            if count >= self._crowd_threshold:
                # Use track_id=0 as a zone-level event (not per-person)
                crowd_bbox = self._merged_bbox(
                    [self._tracks[tid].history[-1][1:3] for tid in ids if tid in self._tracks]
                )
                ev = self._maybe_fire(
                    "CROWD", 0, zone_name,
                    ActivityEvent(
                        event_type="CROWD",
                        camera_id=self.camera_id,
                        label="CROWD",
                        track_id=0,
                        zone=zone_name,
                        bbox=crowd_bbox,
                        crowd_count=count,
                    ),
                    now,
                )
                if ev:
                    events.append(ev)

        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_fire(
        self,
        event_type: str,
        track_id: int,
        zone: str,
        event: ActivityEvent,
        now: float,
    ) -> Optional[ActivityEvent]:
        """Return event only if outside cooldown window."""
        key = (event_type, track_id, zone)
        last = self._cooldown.get(key, 0.0)
        if now - last < self._activity_cooldown:
            return None
        self._cooldown[key] = now
        logger.info(
            "[%s] ACTIVITY %s | track=%d zone=%s",
            self.camera_id, event_type, track_id, zone,
        )
        return event

    @staticmethod
    def _merged_bbox(centroids: list) -> tuple[int, int, int, int]:
        """Return a bounding box that contains all the given centroids."""
        if not centroids:
            return (0, 0, 0, 0)
        xs = [c[0] for c in centroids]
        ys = [c[1] for c in centroids]
        pad = 40
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
