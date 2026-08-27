"""
test_phase9_night.py ? Unit Tests for Phase 9 (Low-Light & Night Processing).
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from backend.core.night import LowLightProcessor, NightEnhancer


class TestLowLightProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = LowLightProcessor(
            mode="clahe",
            brightness_threshold=40.0,
            clip_limit=3.0,
            denoise=False,
        )

        # Bright daylight frame (L ~ 180)
        self.bright_frame = np.full((360, 640, 3), 180, dtype=np.uint8)

        # Dark night frame (L ~ 20)
        self.dark_frame = np.full((360, 640, 3), 20, dtype=np.uint8)

    def test_daylight_bypass(self):
        out_frame, is_night = self.processor.process(self.bright_frame)
        self.assertFalse(is_night)
        # Should be identical array
        np.testing.assert_array_equal(out_frame, self.bright_frame)

    def test_low_light_enhancement(self):
        out_frame, is_night = self.processor.process(self.dark_frame)
        self.assertTrue(is_night)
        self.assertEqual(out_frame.shape, self.dark_frame.shape)

    def test_badge_drawing(self):
        annotated = LowLightProcessor.draw_night_indicator(self.dark_frame.copy())
        self.assertEqual(annotated.shape, self.dark_frame.shape)


if __name__ == "__main__":
    unittest.main(verbosity=2)
