"""
test_phase10_behavior.py ? Unit Tests for Phase 10 (Behavior Analytics & Virtual Fence).
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.activity import ActivityAnalyzer, ActivityEvent
from backend.core.fence import VirtualFence, FenceEvent
from backend.core.tracker import TrackedObject


class TestBehaviorAnalytics(unittest.TestCase):
    def setUp(self):
        # 1. Virtual Fence setup: Polygon [(100, 100), (300, 100), (300, 300), (100, 300)]
        self.fence = VirtualFence(
            camera_id="cam_01",
            zones=[
                {
                    "name": "Restricted Zone",
                    "polygon": [(100, 100), (300, 100), (300, 300), (100, 300)],
                }
            ],
        )

        # 2. Activity Analyzer setup
        self.activity = ActivityAnalyzer(
            camera_id="cam_01",
            loiter_seconds=1.0,
            running_speed=20.0,
            crowd_threshold=3,
        )

    def test_virtual_fence_intrusion(self):
        # Object inside polygon (centroid at (200, 200))
        inside_obj = TrackedObject(
            track_id=1,
            class_id=0,
            label="Person",
            confidence=0.90,
            bbox=(150, 150, 250, 250),
        )
        # Object outside polygon (centroid at (500, 500))
        outside_obj = TrackedObject(
            track_id=2,
            class_id=0,
            label="Person",
            confidence=0.90,
            bbox=(450, 450, 550, 550),
        )

        events = self.fence.check([inside_obj, outside_obj])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].track_id, 1)
        self.assertEqual(events[0].zone_name, "Restricted Zone")

    def test_running_speed_detection(self):
        # Frame 1: Person at (100, 100)
        obj_f1 = TrackedObject(
            track_id=10,
            class_id=0,
            label="Person",
            confidence=0.90,
            bbox=(80, 80, 120, 120),
        )
        self.activity.analyze([obj_f1], active_zones={})

        # Frame 2: Person sprinted to (160, 180) (dx=60, dy=80 -> dist=100px > 20px)
        obj_f2 = TrackedObject(
            track_id=10,
            class_id=0,
            label="Person",
            confidence=0.92,
            bbox=(140, 160, 180, 200),
        )
        events = self.activity.analyze([obj_f2], active_zones={})
        running_evts = [e for e in events if e.event_type == "RUNNING"]
        self.assertEqual(len(running_evts), 1)
        self.assertEqual(running_evts[0].track_id, 10)
        self.assertGreaterEqual(running_evts[0].speed, 20.0)

    def test_crowd_formation_detection(self):
        # 3 persons in Restricted Zone simultaneously
        p1 = TrackedObject(1, 0, "Person", 0.9, (120, 120, 160, 160))
        p2 = TrackedObject(2, 0, "Person", 0.9, (140, 140, 180, 180))
        p3 = TrackedObject(3, 0, "Person", 0.9, (160, 160, 200, 200))

        active_zones = {1: ["Restricted Zone"], 2: ["Restricted Zone"], 3: ["Restricted Zone"]}
        events = self.activity.analyze([p1, p2, p3], active_zones=active_zones)
        crowd_evts = [e for e in events if e.event_type == "CROWD"]
        self.assertEqual(len(crowd_evts), 1)
        self.assertEqual(crowd_evts[0].crowd_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
