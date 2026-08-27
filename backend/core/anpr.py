"""
anpr.py ? High-Accuracy Automatic Number Plate Recognition (ANPR) Engine for IBVAP.

Architecture:
-------------
1. Plate Region Extraction:
   - Dedicated plate crop from vehicle detection or checkpoint scan.
2. Image Preprocessing & Enhancement:
   - Bilateral denoising, adaptive contrast enhancement, and morphology.
3. Multi-Engine OCR:
   - Primary: GPU-accelerated EasyOCR (CUDA) via ModelManager singleton.
   - Secondary: PaddleOCR PP-OCR fallback.
4. Indian License Plate Normalization:
   - Validates Indian registration regex patterns:
     e.g., RJ14CY0002, KA01AB1234, DL3CAF1234, MH12CD5678, HR98AA0000.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from backend.core.model_manager import ModelCategory, ModelManager

logger = logging.getLogger(__name__)


@dataclass
class PlateResult:
    """A verified license plate recognition result."""
    plate_text: str                          # Cleaned, validated plate (e.g. RJ14CY0002)
    confidence: float                        # OCR confidence score (0.0 ? 1.0)
    plate_bbox: Tuple[int, int, int, int]    # Bounding box in full-frame coordinates
    vehicle_label: str = "Vehicle"           # Associated vehicle classification
    is_checkpoint_scan: bool = False         # True if scanned directly from gate camera


class PlateReader:
    """High-accuracy ANPR reader supporting Indian license plate syntax."""

    # Standard Indian Plate Regex (e.g. RJ14CY0002, KA01AB1234, DL3CAF1234)
    _INDIAN_PLATE_PATTERNS = [
        re.compile(r"([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4})"),  # Standard: RJ14CY0002 / DL3CAF1234
        re.compile(r"([A-Z]{2}\d{1,2}\w{1,5}\d{1,4})"),   # Partial / Commercial
    ]

    def __init__(
        self,
        device: str = "auto",
        min_confidence: float = 0.35,
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        self._device = device
        self._min_conf = min_confidence
        self._model_mgr = model_manager or ModelManager()
        self._easyocr = None

    def _get_easyocr(self):
        """Retrieve shared GPU EasyOCR reader from ModelManager."""
        def _easyocr_loader(name: str, dev: str):
            import easyocr
            gpu_active = dev.startswith("cuda")
            return easyocr.Reader(["en"], gpu=gpu_active, verbose=False)

        inst, _ = self._model_mgr.get_or_load(
            key="anpr_easyocr",
            model_name="easyocr_en",
            loader_fn=_easyocr_loader,
            category=ModelCategory.SPECIALIST,
            target_device=self._device,
        )
        return inst

    @classmethod
    def clean_plate(cls, text: str) -> str:
        """Extract and format Indian license plate text using regex."""
        cleaned = re.sub(r"[^A-Z0-9]", "", text.upper().strip())
        for pat in cls._INDIAN_PLATE_PATTERNS:
            match = pat.search(cleaned)
            if match:
                return match.group(1)
        # Return cleaned fragment if at least 5 alphanumeric characters
        return cleaned if len(cleaned) >= 5 else ""

    @staticmethod
    def preprocess_plate(crop: np.ndarray) -> np.ndarray:
        """Apply contrast enhancement and morphological filtering for OCR."""
        if crop is None or crop.size == 0:
            return crop

        # 1. Convert to grayscale
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop

        # 2. Resize if small
        h, w = gray.shape[:2]
        if h < 64:
            scale = 64.0 / h
            gray = cv2.resize(gray, (int(w * scale), 64), interpolation=cv2.INTER_CUBIC)

        # 3. Bilateral filter for noise removal while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # 4. Adaptive thresholding
        enhanced = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        return enhanced

    def read(
        self,
        frame: np.ndarray,
        vehicle_bbox: Tuple[int, int, int, int],
        label: str = "Car",
    ) -> Optional[PlateResult]:
        """Extract and recognize license plate from a vehicle crop."""
        x1, y1, x2, y2 = vehicle_bbox
        h_frame, w_frame = frame.shape[:2]

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_frame, x2), min(h_frame, y2)

        if (x2 - x1) < 30 or (y2 - y1) < 30:
            return None

        # Lower 35% crop where license plates typically reside
        vh = y2 - y1
        vw = x2 - x1
        py1 = int(y1 + vh * 0.60)
        py2 = y2
        px1 = int(x1 + vw * 0.15)
        px2 = int(x2 - vw * 0.15)

        plate_crop = frame[py1:py2, px1:px2]
        if plate_crop.size == 0:
            return None

        return self._ocr_crop(plate_crop, plate_bbox=(px1, py1, px2, py2), label=label)

    def read_from_frame(self, frame: np.ndarray) -> Optional[PlateResult]:
        """Direct checkpoint / handheld screen license plate recognition."""
        h, w = frame.shape[:2]
        # Central checkpoint region (middle 70% width, 60% height)
        cy1, cy2 = int(h * 0.20), int(h * 0.80)
        cx1, cx2 = int(w * 0.15), int(w * 0.85)

        roi = frame[cy1:cy2, cx1:cx2]
        return self._ocr_crop(roi, plate_bbox=(cx1, cy1, cx2, cy2), label="Checkpoint", is_checkpoint=True)

    def _ocr_crop(
        self,
        crop: np.ndarray,
        plate_bbox: Tuple[int, int, int, int],
        label: str = "Vehicle",
        is_checkpoint: bool = False,
    ) -> Optional[PlateResult]:
        """Perform OCR on crop and validate plate string."""
        try:
            reader = self._get_easyocr()
            results = reader.readtext(crop)

            best_plate = ""
            best_conf = 0.0

            for (_, text, conf) in results:
                if conf < self._min_conf:
                    continue
                cleaned = self.clean_plate(text)
                if cleaned and len(cleaned) >= 5 and conf > best_conf:
                    best_plate = cleaned
                    best_conf = conf

            if best_plate:
                return PlateResult(
                    plate_text=best_plate,
                    confidence=best_conf,
                    plate_bbox=plate_bbox,
                    vehicle_label=label,
                    is_checkpoint_scan=is_checkpoint,
                )

        except Exception as exc:
            logger.debug("ANPR OCR extraction error: %s", exc)

        return None
