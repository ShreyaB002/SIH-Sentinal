"""
detector.py ? YOLOv8 inference wrapper for IBVAP.

Wraps Ultralytics YOLOv8 to provide a clean, reusable detection interface.
One shared Detector instance is created at startup and used by all
FramePipeline objects (thread-safe for inference).

GPU is used automatically when available; falls back to CPU gracefully.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single object detection result."""
    class_id: int
    label: str
    confidence: float
    # Bounding box in pixel coords: (x1, y1, x2, y2)
    bbox: tuple[int, int, int, int]


class Detector:
    """YOLOv8 detector shared across all camera pipelines.

    Parameters
    ----------
    model_name:
        YOLOv8 model variant, e.g. ``"yolov8n.pt"``. Downloaded automatically
        on first use into the current working directory (or ultralytics cache).
    confidence:
        Minimum detection confidence threshold.
    class_ids:
        List of COCO class IDs to detect. ``None`` means detect all classes.
    device:
        PyTorch device string (``"cuda"``, ``"cpu"``). ``None`` = auto-select.
    label_overrides:
        Optional mapping of class_id ? custom display label.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence: float = 0.45,
        class_ids: Optional[list[int]] = None,
        device: Optional[str] = None,
        label_overrides: Optional[dict[int, str]] = None,
    ) -> None:
        self._confidence = confidence
        self._class_ids = class_ids
        self._label_overrides = label_overrides or {}
        self._model = None  # lazy-loaded on first call

        # Resolve device
        if device is None:
            try:
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self._device = "cpu"
        else:
            self._device = device

        self._model_name = model_name
        logger.info("Detector configured: model=%s device=%s conf=%.2f",
                    model_name, self._device, confidence)

    def _load_model(self) -> None:
        """Lazy-load the YOLO model on first inference call."""
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_name)
            self._model.to(self._device)
            logger.info("YOLO model loaded on %s: %s", self._device, self._model_name)
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            raise

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a single BGR frame.

        Parameters
        ----------
        frame:
            OpenCV BGR image as a numpy array.

        Returns
        -------
        list[Detection]
            Filtered detections above the confidence threshold.
            Empty list if the model is not loaded or inference fails.
        """
        if self._model is None:
            try:
                self._load_model()
            except Exception:
                return []

        try:
            results = self._model.predict(
                source=frame,
                conf=self._confidence,
                classes=self._class_ids,
                device=self._device,
                verbose=False,
            )
        except Exception as exc:
            logger.warning("YOLO inference error: %s", exc)
            return []

        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = self._label_overrides.get(
                    cls_id,
                    result.names.get(cls_id, str(cls_id)),
                )
                detections.append(
                    Detection(
                        class_id=cls_id,
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                    )
                )

        return detections
