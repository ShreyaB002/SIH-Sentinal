"""
test_phase2_phase3.py ? Unit Tests for Phase 2 (ModelManager) and Phase 3 (YOLO26 Detector).
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from backend.core.model_manager import ModelCategory, ModelManager
from backend.core.detector import BaseDetector, Detection, TrackedDetection, YOLO26Detector


class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.mm = ModelManager()

    def test_singleton_instance(self):
        mm2 = ModelManager()
        self.assertIs(self.mm, mm2, "ModelManager must be a true singleton.")

    def test_device_properties(self):
        self.assertIn("cuda", self.mm.device) if torch.cuda.is_available() else self.assertEqual(self.mm.device, "cpu")
        self.assertGreaterEqual(self.mm.vram_total_gb, 0.0)
        self.assertGreaterEqual(self.mm.vram_allocated_mb, 0.0)

    def test_singleton_model_caching(self):
        def dummy_loader(name, dev):
            return {"name": name, "dev": dev, "data": np.zeros((10, 10))}

        inst1, meta1 = self.mm.get_or_load("dummy_test_model", "dummy_v1", dummy_loader)
        inst2, meta2 = self.mm.get_or_load("dummy_test_model", "dummy_v1", dummy_loader)

        self.assertIs(inst1, inst2, "Loaded model instances must be shared singletons across calls.")
        self.assertEqual(meta1.name, "dummy_v1")

        status = self.mm.get_status()
        self.assertIn("dummy_test_model", status["models"])

        # Clean up
        self.assertTrue(self.mm.unload("dummy_test_model"))
        self.assertNotIn("dummy_test_model", self.mm.get_status()["models"])

    def test_fallback_chain_on_error(self):
        def failing_loader(name, dev):
            if name == "failing_primary":
                raise RuntimeError("Simulated model loading error")
            return {"name": name, "dev": dev}

        inst, meta = self.mm.get_or_load(
            key="fallback_test_model",
            model_name="failing_primary",
            loader_fn=failing_loader,
            fallback_names=["working_fallback"],
        )
        self.assertEqual(meta.name, "working_fallback")
        self.assertEqual(meta.fallback_from, "failing_primary")
        self.mm.unload("fallback_test_model")


class TestDetectorAbstraction(unittest.TestCase):
    def setUp(self):
        self.detector = YOLO26Detector(
            model_name="yolov8n.pt",
            confidence=0.25,
            device="auto",
        )
        self.dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_detector_inheritance(self):
        self.assertIsInstance(self.detector, BaseDetector)

    def test_normalized_detection_dataclass(self):
        det = Detection(
            class_id=0,
            label="Person",
            confidence=0.88,
            bbox=(100, 100, 200, 300),
            camera_id="cam_01",
        )
        self.assertEqual(det.class_name, "Person")
        self.assertEqual(det.centroid, (150, 200))
        self.assertEqual(det.width, 100)
        self.assertEqual(det.height, 200)
        self.assertEqual(det.area, 20000)

    def test_normalized_tracked_detection(self):
        td = TrackedDetection(
            class_id=2,
            label="Car",
            confidence=0.92,
            bbox=(50, 50, 150, 120),
            track_id=7,
            velocity=14.5,
            camera_id="cam_02",
        )
        self.assertEqual(td.track_id, 7)
        self.assertEqual(td.velocity, 14.5)
        self.assertEqual(td.label, "Car")

    def test_detect_and_track_execution(self):
        dets = self.detector.detect(self.dummy_frame, camera_id="cam_test")
        self.assertIsInstance(dets, list)

        tracked = self.detector.track(self.dummy_frame, camera_id="cam_test")
        self.assertIsInstance(tracked, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
