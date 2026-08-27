"""
test_phase7_anpr.py ? Unit Tests for Phase 7 (ANPR & Indian Plate Normalization).
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from backend.core.anpr import PlateReader, PlateResult


class TestANPR(unittest.TestCase):
    def test_indian_plate_cleaning_and_validation(self):
        test_cases = [
            ("RJ 14 CY 0002", "RJ14CY0002"),
            ("KA-01-AB-1234", "KA01AB1234"),
            ("DL3CAF1234", "DL3CAF1234"),
            ("hr 98 aa 0000", "HR98AA0000"),
            ("MH 12 CD 5678", "MH12CD5678"),
            ("Invalid-12", ""),
        ]
        for raw, expected in test_cases:
            cleaned = PlateReader.clean_plate(raw)
            if expected:
                self.assertEqual(cleaned, expected, f"Failed on raw input: {raw}")
            else:
                self.assertNotEqual(cleaned, "Invalid-12")

    def test_plate_preprocessing(self):
        crop = np.zeros((40, 100, 3), dtype=np.uint8)
        enhanced = PlateReader.preprocess_plate(crop)
        self.assertIsNotNone(enhanced)
        self.assertEqual(len(enhanced.shape), 2)  # Grayscale
        self.assertGreaterEqual(enhanced.shape[0], 64)  # Resized height >= 64

    def test_plate_result_dataclass(self):
        res = PlateResult(
            plate_text="RJ14CY0002",
            confidence=0.89,
            plate_bbox=(100, 200, 300, 260),
            vehicle_label="Car",
            is_checkpoint_scan=False,
        )
        self.assertEqual(res.plate_text, "RJ14CY0002")
        self.assertEqual(res.vehicle_label, "Car")
        self.assertFalse(res.is_checkpoint_scan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
