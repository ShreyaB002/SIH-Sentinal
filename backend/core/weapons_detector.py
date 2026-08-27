"""
weapons_detector.py - YOLO-World based weapons/threat detector for IBVAP Phase 3.

Uses YOLO-World (open-vocabulary) to detect weapons and threats using plain
English text prompts. No custom training required.

Model: yolov8l-worldv2.pt (large, best accuracy)
Auto-downloaded on first run (~200 MB).

Each FramePipeline gets its own WeaponsDetector instance with its own model
so GPU memory and state are isolated per camera.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WeaponDetection:
    """A single weapon/threat detection result."""
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]   # (x1, y1, x2, y2)


class WeaponsDetector:
    """YOLO-World open-vocabulary weapons detector.

    Parameters
    ----------
    model_name : str
        YOLO-World model variant. ``yolov8l-worldv2.pt`` recommended for
        best accuracy on GPU.
    classes : list[str]
        Plain-English class names to detect, e.g.
        ``["handgun", "pistol", "rifle", "knife", "machete"]``.
    confidence : float
        Detection confidence threshold (0.0-1.0).  Lower than standard YOLO
        (~0.25-0.35) because open-vocab models are naturally less confident.
    device : str
        PyTorch device (``"cuda"`` or ``"cpu"``).
    """

    def __init__(
        self,
        model_name: str = "yolov8l-worldv2.pt",
        classes: Optional[list[str]] = None,
        confidence: float = 0.30,
        device: str = "cuda",
    ) -> None:
        self._model_name = model_name
        self._classes = classes or [
            "handgun", "pistol", "revolver",
            "rifle", "assault rifle", "shotgun",
            "knife", "machete", "blade",
        ]
        self._confidence = confidence
        self._device = device
        self._model = None   # lazy-loaded on first detect() call

        logger.info(
            "WeaponsDetector configured: model=%s device=%s conf=%.2f classes=%s",
            model_name, device, confidence, self._classes,
        )

    def _get_model(self):
        """Lazy-load the threat model via ModelManager singleton."""
        from backend.core.model_manager import ModelCategory, ModelManager
        mm = ModelManager()

        def _threat_loader(m_name: str, dev: str):
            from ultralytics import YOLO
            m = YOLO(m_name)
            if hasattr(m, "set_classes") and "world" in str(m_name).lower():
                m.set_classes(self._classes)
            m.to(dev)
            return m

        inst, meta = mm.get_or_load(
            key="threat_detector",
            model_name=self._model_name,
            loader_fn=_threat_loader,
            category=ModelCategory.SPECIALIST,
            target_device=self._device,
        )
        if hasattr(inst, "names") and isinstance(inst.names, dict) and "world" not in str(self._model_name).lower():
            self._names = inst.names
        else:
            self._names = None
        return inst, meta.device

    def detect(self, frame: np.ndarray) -> list[WeaponDetection]:
        """Run weapons detection on a single BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            OpenCV BGR image.

        Returns
        -------
        list[WeaponDetection]
            All detected weapons/threats above the confidence threshold.
            Empty list if none found or model unavailable.
        """
        try:
            model, dev = self._get_model()
            results = model.predict(
                source=frame,
                conf=self._confidence,
                device=dev,
                imgsz=640,
                verbose=False,
            )
        except Exception as exc:
            logger.warning("WeaponsDetector inference error: %s", exc)
            return []

        detections: list[WeaponDetection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                if self._names and isinstance(self._names, dict):
                    label = self._names.get(cls_id, "Weapon")
                elif cls_id < len(self._classes):
                    label = self._classes[cls_id]
                else:
                    label = "Weapon"

                detections.append(
                    WeaponDetection(label=label, confidence=conf, bbox=(x1, y1, x2, y2))
                )

        if detections:
            logger.info(
                "WEAPON DETECTED: %s",
                [(d.label, f"{d.confidence:.0%}") for d in detections],
            )

        return detections
