"""
detector.py ? High-Accuracy Object Detector Abstraction & YOLO26 Engine for IBVAP.

Architecture:
-------------
BaseDetector (ABC)
    ??? YOLO26Detector (Ultralytics YOLO26 / YOLOv8 / YOLO11 with ModelManager Singleton)
    ??? FutureDetector (Extension point for custom on-premise architectures)

Guarantees:
1. Normalizes all raw framework predictions into standardized project Detection objects.
2. Uses ModelManager singleton so all camera streams share one GPU model instance.
3. Automatically applies graceful fallback if high-VRAM models (e.g. yolo26x) exceed hardware limits.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.core.model_manager import ModelCategory, ModelManager

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A standardized object detection result independent of underlying AI model."""
    class_id: int
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2) in pixel coordinates
    camera_id: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def class_name(self) -> str:
        return self.label

    @property
    def centroid(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def width(self) -> int:
        return max(0, self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> int:
        return max(0, self.bbox[3] - self.bbox[1])

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class TrackedDetection(Detection):
    """Detection enriched with persistent tracker ID and motion parameters."""
    track_id: int = 0
    velocity: float = 0.0             # centroid pixel displacement / frame


class BaseDetector(ABC):
    """Abstract Base Class for all object detectors in IBVAP."""

    @abstractmethod
    def detect(self, frame: np.ndarray, camera_id: str = "") -> List[Detection]:
        """Execute detection on a single BGR frame."""
        pass

    @abstractmethod
    def track(
        self,
        frame: np.ndarray,
        camera_id: str = "",
        tracker_cfg: str = "bytetrack.yaml",
        persist: bool = True,
    ) -> List[TrackedDetection]:
        """Execute detection and ByteTrack tracking on a single BGR frame."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured primary model identifier."""
        pass

    @property
    @abstractmethod
    def active_model_name(self) -> str:
        """Currently active loaded model (considering fallbacks)."""
        pass

    @property
    @abstractmethod
    def device(self) -> str:
        """Execution device ('cuda' or 'cpu')."""
        pass


class YOLO26Detector(BaseDetector):
    """YOLO26 & Ultralytics family high-accuracy detector.

    Supports configurable model selection (yolo26x, yolo26l, yolo26m, yolov8n)
    backed by the centralized ModelManager singleton.
    """

    def __init__(
        self,
        model_name: str = "yolo26m.pt",
        confidence: float = 0.28,
        class_ids: Optional[List[int]] = None,
        device: str = "auto",
        fallback_models: Optional[List[str]] = None,
        label_overrides: Optional[Dict[int, str]] = None,
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        self._requested_model_name = self._normalize_model_name(model_name)
        self._confidence = confidence
        self._class_ids = class_ids
        self._device_pref = device
        self._label_overrides = label_overrides or {
            0: "Person",
            2: "Car",
            3: "Motorcycle",
            5: "Bus",
            7: "Truck",
        }

        # Build fallback list
        fallbacks = fallback_models or [
            "yolo26l.pt",
            "yolo26m.pt",
            "yolo11m.pt",
            "yolov8n.pt",
        ]
        self._fallbacks = [
            self._normalize_model_name(f)
            for f in fallbacks
            if self._normalize_model_name(f) != self._requested_model_name
        ]

        self._model_mgr = model_manager or ModelManager()
        self._active_model_name = self._requested_model_name
        self._resolved_device = "cpu"

        logger.info(
            "YOLO26Detector configured: model=%s (fallbacks=%s) device=%s conf=%.2f",
            self._requested_model_name,
            self._fallbacks,
            self._device_pref,
            self._confidence,
        )

    @staticmethod
    def _normalize_model_name(name: str) -> str:
        name = name.strip()
        if not name.endswith(".pt") and not name.endswith(".onnx") and not name.endswith(".engine"):
            name = f"{name}.pt"
        return name

    def _get_model(self) -> Any:
        """Retrieve the shared YOLO singleton from ModelManager."""
        def _loader(m_name: str, dev: str) -> Any:
            from ultralytics import YOLO
            m = YOLO(m_name)
            m.to(dev)
            return m

        model_inst, meta = self._model_mgr.get_or_load(
            key="primary_detector",
            model_name=self._requested_model_name,
            loader_fn=_loader,
            category=ModelCategory.CORE,
            fallback_names=self._fallbacks,
            target_device=self._device_pref,
        )
        self._active_model_name = meta.name
        self._resolved_device = meta.device
        return model_inst

    @property
    def model_name(self) -> str:
        return self._requested_model_name

    @property
    def active_model_name(self) -> str:
        return self._active_model_name

    @property
    def device(self) -> str:
        return self._resolved_device

    def detect(self, frame: np.ndarray, camera_id: str = "") -> List[Detection]:
        """Execute inference and return standardized Detection objects."""
        try:
            model = self._get_model()
            results = model.predict(
                source=frame,
                conf=self._confidence,
                classes=self._class_ids,
                device=self._resolved_device,
                verbose=False,
            )
        except Exception as exc:
            logger.warning("[%s] Detection inference error: %s", camera_id or "Detector", exc)
            return []

        detections: List[Detection] = []
        ts = time.time()
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = self._label_overrides.get(
                    cls_id,
                    r.names.get(cls_id, str(cls_id)),
                )
                detections.append(
                    Detection(
                        class_id=cls_id,
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        camera_id=camera_id,
                        timestamp=ts,
                    )
                )
        return detections

    def track(
        self,
        frame: np.ndarray,
        camera_id: str = "",
        tracker_cfg: str = "bytetrack.yaml",
        persist: bool = True,
    ) -> List[TrackedDetection]:
        """Execute detection and ByteTrack tracking in a single GPU forward pass."""
        try:
            model = self._get_model()
            try:
                results = model.track(
                    source=frame,
                    conf=self._confidence,
                    classes=self._class_ids,
                    device=self._resolved_device,
                    tracker=tracker_cfg,
                    persist=persist,
                    verbose=False,
                )
            except Exception as trk_err:
                # Fallback to Hungarian botsort tracker if bytetrack has solver issues
                logger.debug("[%s] ByteTrack fallback to BoTSORT: %s", camera_id, trk_err)
                results = model.track(
                    source=frame,
                    conf=self._confidence,
                    classes=self._class_ids,
                    device=self._resolved_device,
                    tracker="botsort.yaml",
                    persist=persist,
                    verbose=False,
                )
        except Exception as exc:
            logger.warning("[%s] Tracking inference error: %s", camera_id or "Detector", exc)
            return []

        tracked: List[TrackedDetection] = []
        ts = time.time()
        for r in results:
            if r.boxes is None:
                continue
            for i, box in enumerate(r.boxes):
                track_id = int(box.id[0]) if box.id is not None else (i + 1)
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = self._label_overrides.get(
                    cls_id,
                    r.names.get(cls_id, str(cls_id)),
                )
                tracked.append(
                    TrackedDetection(
                        class_id=cls_id,
                        label=label,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        track_id=track_id,
                        camera_id=camera_id,
                        timestamp=ts,
                    )
                )
        return tracked


# Backward-compatibility alias
Detector = YOLO26Detector
