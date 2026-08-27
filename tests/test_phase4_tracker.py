"""
test_phase4_tracker.py ? Unit Tests for Phase 4 (ByteTrack & Motion Kinematics).
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.detector import TrackedDetection
from backend.core.tracker import ByteTracker, TrackedObject


class TestByteTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = ByteTracker(camera_id="cam_01", max_history=10, track_buffer_seconds=1.0)

    def test_single_frame_entry(self):
        t0 = 1000.0
        tds = [
            TrackedDetection(
                class_id=0,
                label="Person",
                confidence=0.90,
                bbox=(100, 100, 200, 300),
                track_id=1,
                camera_id="cam_01",
                timestamp=t0,
            )
        ]
        objs = self.tracker.update_from_tracked_detections(tds, current_time=t0)
        self.assertEqual(len(objs), 1)
        obj = objs[0]
        self.assertEqual(obj.track_id, 1)
        self.assertEqual(obj.entry_time, t0)
        self.assertEqual(obj.dwell_time, 0.0)
        self.assertEqual(len(obj.trajectory), 1)
        self.assertEqual(obj.centroid, (150, 200))
        self.assertEqual(obj.velocity, 0.0)

    def test_trajectory_and_velocity_estimation(self):
        t0 = 1000.0
        # Frame 1: centroid at (150, 200)
        tds_1 = [
            TrackedDetection(
                class_id=0,
                label="Person",
                confidence=0.90,
                bbox=(100, 100, 200, 300),
                track_id=1,
                camera_id="cam_01",
                timestamp=t0,
            )
        ]
        self.tracker.update_from_tracked_detections(tds_1, current_time=t0)

        # Frame 2: centroid moved to (180, 240) (dx=30, dy=40 -> dist=50)
        t1 = 1001.0
        tds_2 = [
            TrackedDetection(
                class_id=0,
                label="Person",
                confidence=0.92,
                bbox=(130, 140, 230, 340),
                track_id=1,
                camera_id="cam_01",
                timestamp=t1,
            )
        ]
        objs = self.tracker.update_from_tracked_detections(tds_2, current_time=t1)
        self.assertEqual(len(objs), 1)
        obj = objs[0]

        self.assertEqual(obj.entry_time, t0)
        self.assertEqual(obj.last_seen_time, t1)
        self.assertEqual(obj.dwell_time, 1.0)
        self.assertEqual(len(obj.trajectory), 2)
        self.assertEqual(obj.trajectory[0], (150, 200))
        self.assertEqual(obj.trajectory[1], (180, 240))
        self.assertAlmostEqual(obj.velocity, 50.0, delta=1.0)

    def test_stale_track_cleanup(self):
        t0 = 1000.0
        tds_1 = [
            TrackedDetection(
                class_id=0,
                label="Person",
                confidence=0.90,
                bbox=(100, 100, 200, 300),
                track_id=1,
                camera_id="cam_01",
                timestamp=t0,
            )
        ]
        self.tracker.update_from_tracked_detections(tds_1, current_time=t0)

        # 3 seconds later, a different object appears (track_id=2)
        t2 = 1003.0
        tds_2 = [
            TrackedDetection(
                class_id=2,
                label="Car",
                confidence=0.85,
                bbox=(400, 400, 500, 500),
                track_id=2,
                camera_id="cam_01",
                timestamp=t2,
            )
        ]
        objs = self.tracker.update_from_tracked_detections(tds_2, current_time=t2)
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].track_id, 2)

        # Track 1 should have been purged from internal memory
        self.assertNotIn(1, self.tracker._entry_times)
        self.assertIn(2, self.tracker._entry_times)


if __name__ == "__main__":
    unittest.main(verbosity=2)
