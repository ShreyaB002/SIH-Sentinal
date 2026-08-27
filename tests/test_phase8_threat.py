"""
test_phase8_threat.py ? Unit Tests for Phase 8 (Weapons & Threat Detection).
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from backend.core.weapons_detector import WeaponsDetector, WeaponDetection


class TestWeaponsDetector(unittest.TestCase):
    def setUp(self):
        self.detector = WeaponsDetector(
            model_name="models/threat_detector.pt",
            confidence=0.20,
            device="auto",
        )
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_weapon_detection_dataclass(self):
        w = WeaponDetection(
            label="Gun",
            confidence=0.85,
            bbox=(50, 60, 120, 140),
        )
        self.assertEqual(w.label, "Gun")
        self.assertEqual(w.confidence, 0.85)
        self.assertEqual(w.bbox, (50, 60, 120, 140))

    def test_detector_execution_on_frame(self):
        dets = self.detector.detect(self.dummy_frame)
        self.assertIsInstance(dets, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
