"""
test_phase5_reid.py ? Unit Tests for Phase 5 (OSNet Person Re-Identification).
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from backend.core.reid import OSNetExtractor, ReIDManager, ReIDMatchResult


class TestPersonReID(unittest.TestCase):
    def setUp(self):
        self.reid_mgr = ReIDManager(
            similarity_threshold=0.92,
            max_gallery_size=10,
            expiration_seconds=2.0,
            device="auto",
        )
        self.reid_mgr.clear()

        # Synthetic person crop (200 height x 100 width, BGR)
        # Person A (Blue shirt, dark pants)
        self.person_a_crop = np.zeros((200, 100, 3), dtype=np.uint8)
        self.person_a_crop[:100, :] = [220, 50, 50]   # Blue top
        self.person_a_crop[100:, :] = [30, 30, 30]    # Dark bottom

        # Person B (Red shirt, yellow pants)
        self.person_b_crop = np.zeros((200, 100, 3), dtype=np.uint8)
        self.person_b_crop[:100, :] = [50, 50, 220]   # Red top
        self.person_b_crop[100:, :] = [50, 220, 220]  # Yellow bottom

    def test_osnet_extractor_embedding_properties(self):
        extractor = OSNetExtractor(device="auto")
        emb = extractor.extract(self.person_a_crop)

        self.assertIsNotNone(emb)
        self.assertEqual(emb.shape, (512,))
        self.assertEqual(emb.dtype, np.float32)
        # L2 norm must be 1.0 (unit vector)
        norm = np.linalg.norm(emb)
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_cross_camera_person_matching(self):
        # 1. Camera 01 detects Person A for the first time
        res_cam01 = self.reid_mgr.match_or_register(
            person_crop=self.person_a_crop,
            camera_id="cam_01",
            local_track_id=17,
        )
        self.assertIsNotNone(res_cam01)
        self.assertTrue(res_cam01.is_new_registration)
        self.assertFalse(res_cam01.matched)
        global_id_a = res_cam01.global_person_id
        self.assertEqual(global_id_a, 1)

        # 2. Camera 04 detects the SAME Person A with slight noise
        person_a_cam04 = self.person_a_crop.copy()
        # Add slight compression / brightness variation
        person_a_cam04 = np.clip(person_a_cam04.astype(np.int32) + 5, 0, 255).astype(np.uint8)

        res_cam04 = self.reid_mgr.match_or_register(
            person_crop=person_a_cam04,
            camera_id="cam_04",
            local_track_id=42,
        )
        self.assertIsNotNone(res_cam04)
        self.assertTrue(res_cam04.matched, f"Must match Person A. Sim was {res_cam04.similarity:.2f}")
        self.assertEqual(res_cam04.global_person_id, global_id_a)
        self.assertEqual(res_cam04.origin_camera_id, "cam_01")
        self.assertEqual(res_cam04.origin_track_id, 17)
        self.assertGreaterEqual(res_cam04.similarity, 0.70)

        # 3. Camera 02 detects DIFFERENT Person B
        res_cam02 = self.reid_mgr.match_or_register(
            person_crop=self.person_b_crop,
            camera_id="cam_02",
            local_track_id=5,
        )
        self.assertIsNotNone(res_cam02)
        self.assertTrue(res_cam02.is_new_registration)
        self.assertNotEqual(res_cam02.global_person_id, global_id_a)

    def test_gallery_expiration(self):
        # Register Person A at t0
        self.reid_mgr.match_or_register(self.person_a_crop, "cam_01", 1)
        self.assertEqual(len(self.reid_mgr._gallery), 1)

        # Fast forward time by simulating expiration cleanup
        t_future = time.time() + 5.0
        self.reid_mgr._cleanup_expired(t_future)
        self.assertEqual(len(self.reid_mgr._gallery), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
