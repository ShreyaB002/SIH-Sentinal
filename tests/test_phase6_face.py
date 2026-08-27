"""
test_phase6_face.py ? Unit Tests for Phase 6 (Face Recognition & Watchlist Matching).
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from backend.core.face_recognition import FaceRecognizer, FaceResult


class TestFaceRecognition(unittest.TestCase):
    def setUp(self):
        self.fr = FaceRecognizer(match_threshold=0.50, device="auto")

        # Mock 512-d normalized target embedding
        np.random.seed(42)
        target_emb = np.random.randn(512).astype(np.float32)
        target_emb /= np.linalg.norm(target_emb)

        self.watchlist = [
            {"id": "tgt_001", "name": "Target Alpha", "embedding": target_emb}
        ]
        self.fr.load_watchlist(self.watchlist)
        self.target_emb = target_emb

    def test_watchlist_match_exact(self):
        matched, name, person_id, sim = self.fr._match(self.target_emb)
        self.assertTrue(matched)
        self.assertEqual(name, "Target Alpha")
        self.assertEqual(person_id, "tgt_001")
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_watchlist_match_orthogonal_unknown(self):
        # Orthogonal / random embedding
        np.random.seed(99)
        unknown_emb = np.random.randn(512).astype(np.float32)
        unknown_emb /= np.linalg.norm(unknown_emb)

        matched, name, person_id, sim = self.fr._match(unknown_emb)
        self.assertFalse(matched)
        self.assertEqual(name, "Unknown")
        self.assertEqual(person_id, "")
        self.assertLess(sim, 0.50)

    def test_face_result_dataclass(self):
        res = FaceResult(
            matched=True,
            name="Target Alpha",
            person_id="tgt_001",
            similarity=0.88,
            bbox=(10, 20, 50, 60),
            embedding=self.target_emb,
        )
        self.assertTrue(res.matched)
        self.assertEqual(res.name, "Target Alpha")


if __name__ == "__main__":
    unittest.main(verbosity=2)
