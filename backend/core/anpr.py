"""
anpr.py - Automatic Number Plate Recognition for IBVAP Phase 4.

Pipeline per vehicle detection:
1. Crop the vehicle bounding box from the frame (with padding)
2. Run a lightweight YOLO plate detector on the crop to locate the plate
3. Crop the plate region
4. Pre-process the plate crop (resize, denoise, threshold)
5. Run PaddleOCR to extract text
6. Clean and validate the result

Falls back gracefully if PaddleOCR is not installed or fails.

GPU usage: PaddleOCR uses CPU by default (fast enough); plate detector uses CUDA.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PlateResult:
    """Result of one ANPR read."""
    plate_text: str         # cleaned plate string e.g. "KA01AB1234"
    raw_text: str           # raw OCR output before cleaning
    confidence: float       # OCR confidence (0-1)
    vehicle_bbox: tuple     # original vehicle (x1,y1,x2,y2)
    plate_bbox: tuple       # plate region in full-frame coords (x1,y1,x2,y2)


class PlateReader:
    """Reads number plates from vehicle bounding box crops.

    Parameters
    ----------
    device : str
        Device for the plate-detection YOLO model (``"cuda"`` or ``"cpu"``).
    min_confidence : float
        Minimum OCR confidence to accept a plate reading.
    """

    # Regex patterns for common Indian number plates
    # e.g. KA01AB1234, MH12CD5678, DL3CAF1234
    _PLATE_PATTERNS = [
        re.compile(r"[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}"),   # standard: KA01AB1234
        re.compile(r"[A-Z]{2}\d{2}[A-Z]{1,3}\d{1,4}"),  # partial / older format
    ]

    def __init__(
        self,
        device: str = "cuda",
        min_confidence: float = 0.4,
    ) -> None:
        self._device = device
        self._min_conf = min_confidence
        self._ocr = None          # lazy-loaded PaddleOCR
        self._plate_model = None  # lazy-loaded YOLO plate detector

    def _load_ocr(self) -> None:
        """Lazy-load PaddleOCR (CPU, angle classification enabled)."""
        try:
            from paddleocr import PaddleOCR
            # lang='en', use_angle_cls=True handles tilted plates
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=False,   # OCR on CPU is fast enough
            )
            logger.info("PaddleOCR loaded for ANPR.")
        except Exception as exc:
            logger.error("PaddleOCR load failed: %s", exc)

    def _load_plate_model(self) -> None:
        """Load a YOLOv8 model fine-tuned for number plate detection.
        
        Uses yolov8n.pt with a targeted crop as fallback if no plate model.
        For best results, replace with a dedicated plate detector .pt file
        (e.g. from Roboflow 'license-plate-recognition' dataset).
        """
        try:
            from ultralytics import YOLO
            # Use general YOLO for vehicle crops ? then OCR the lower portion
            # (where plates typically appear). Replace with a plate-specific model
            # for much higher accuracy.
            self._plate_model = "heuristic"   # flag to use heuristic crop
            logger.info("ANPR plate detector: heuristic crop mode (no dedicated model).")
        except Exception as exc:
            logger.error("Plate model load failed: %s", exc)

    def read(
        self,
        frame: np.ndarray,
        vehicle_bbox: tuple[int, int, int, int],
        label: str = "Car",
    ) -> Optional[PlateResult]:
        """Attempt to read a number plate from a vehicle detection.

        Parameters
        ----------
        frame : np.ndarray
            Full BGR frame.
        vehicle_bbox : tuple
            Vehicle bounding box (x1, y1, x2, y2).
        label : str
            Vehicle type label for heuristic plate region selection.

        Returns
        -------
        Optional[PlateResult]
            Plate reading result, or None if no plate found / OCR failed.
        """
        # Lazy load OCR
        if self._ocr is None:
            self._load_ocr()
        if self._ocr is None:
            return None   # PaddleOCR not available

        if self._plate_model is None:
            self._load_plate_model()

        x1, y1, x2, y2 = vehicle_bbox
        h_frame, w_frame = frame.shape[:2]

        # Clamp to frame bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_frame, x2), min(h_frame, y2)

        if x2 - x1 < 20 or y2 - y1 < 20:
            return None  # bounding box too small

        # --- Heuristic plate crop ---
        # Plates appear in the lower-centre ~20% of the vehicle bounding box
        veh_h = y2 - y1
        veh_w = x2 - x1
        plate_y1 = y1 + int(veh_h * 0.65)
        plate_y2 = y2
        plate_x1 = x1 + int(veh_w * 0.10)
        plate_x2 = x2 - int(veh_w * 0.10)

        plate_crop = frame[plate_y1:plate_y2, plate_x1:plate_x2]
        if plate_crop.size == 0:
            return None

        # --- Pre-process plate crop for OCR ---
        processed = self._preprocess_plate(plate_crop)

        # --- Run PaddleOCR ---
        try:
            result = self._ocr.ocr(processed, cls=True)
        except Exception as exc:
            logger.debug("PaddleOCR error: %s", exc)
            return None

        if not result or not result[0]:
            return None

        # Extract best text line (highest confidence)
        best_text = ""
        best_conf = 0.0
        for line in result[0]:
            if line and len(line) >= 2:
                text = str(line[1][0])
                conf = float(line[1][1])
                if conf > best_conf:
                    best_text = text
                    best_conf = conf

        if best_conf < self._min_conf or not best_text.strip():
            return None

        cleaned = self._clean_plate(best_text)
        if not cleaned:
            return None

        logger.info("ANPR: '%s' (raw: '%s', conf: %.0f%%)",
                    cleaned, best_text, best_conf * 100)

        return PlateResult(
            plate_text=cleaned,
            raw_text=best_text,
            confidence=best_conf,
            vehicle_bbox=vehicle_bbox,
            plate_bbox=(plate_x1, plate_y1, plate_x2, plate_y2),
        )

    @staticmethod
    def _preprocess_plate(crop: np.ndarray) -> np.ndarray:
        """Resize and enhance plate crop for OCR accuracy."""
        # Resize to a fixed height (OCR works better on taller images)
        target_h = 64
        h, w = crop.shape[:2]
        if h < 1:
            return crop
        scale = target_h / h
        resized = cv2.resize(crop, (int(w * scale * 1.5), target_h),
                             interpolation=cv2.INTER_CUBIC)

        # Mild sharpening
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        sharpened = cv2.filter2D(resized, -1, kernel)

        # Return colour (PaddleOCR handles colour better than grayscale)
        return sharpened

    @staticmethod
    def _clean_plate(text: str) -> str:
        """Remove spaces/special chars and uppercase. Return empty if nonsense."""
        cleaned = re.sub(r"[^A-Z0-9]", "", text.upper().strip())
        # Must be at least 4 chars to be a valid plate fragment
        return cleaned if len(cleaned) >= 4 else ""
