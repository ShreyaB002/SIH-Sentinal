"""
night.py - Night-time detection and frame enhancement for IBVAP Phase 4.

Detects low-light / night conditions by measuring mean frame brightness,
then enhances the frame using CLAHE (Contrast Limited Adaptive Histogram
Equalization) before passing it to the YOLO pipeline.

This means the existing YOLO models work in the dark without any retraining.

Algorithm
---------
1. Convert frame to LAB colour space
2. Measure mean L (luminance) channel value (0-255)
3. If L_mean < NIGHT_BRIGHTNESS_THRESHOLD ? it is night
4. Apply CLAHE to the L channel only ? merge back to BGR
5. Optionally apply slight denoising for very dark scenes
6. Return enhanced frame + is_night flag

The enhanced frame is used for ALL subsequent detection (YOLO, weapons, ANPR,
face recognition) ? no changes needed in those modules.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class NightEnhancer:
    """Detects low-light conditions and enhances frames for better detection.

    Parameters
    ----------
    brightness_threshold : float
        Mean LAB-L value below which the frame is treated as night (0-255).
        Default 80 works well for typical CCTV in low light.
    clip_limit : float
        CLAHE clip limit. Higher = more contrast. 3.0 is a good balance.
    tile_grid : tuple[int, int]
        CLAHE tile grid size. (8, 8) is standard.
    denoise : bool
        Apply fast non-local means denoising on very dark frames (L < 40).
        Slightly slower but removes CCTV noise in extreme darkness.
    """

    def __init__(
        self,
        brightness_threshold: float = 80.0,
        clip_limit: float = 3.0,
        tile_grid: tuple = (8, 8),
        denoise: bool = True,
    ) -> None:
        self._threshold = brightness_threshold
        self._denoise = denoise
        self._clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        logger.info("NightEnhancer ready (threshold=%.0f, clahe_clip=%.1f)",
                    brightness_threshold, clip_limit)

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, bool]:
        """Enhance frame if night-time conditions detected.

        Parameters
        ----------
        frame : np.ndarray
            Raw BGR frame from camera.

        Returns
        -------
        tuple[np.ndarray, bool]
            (processed_frame, is_night)
            processed_frame is enhanced if night, otherwise unchanged.
            is_night is True if low-light was detected.
        """
        # Convert to LAB to measure luminance independently of colour
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        mean_brightness = float(np.mean(l_channel))

        is_night = mean_brightness < self._threshold

        if not is_night:
            return frame, False

        # Apply CLAHE to L channel only
        enhanced_l = self._clahe.apply(l_channel)

        # Optional denoising for extremely dark frames
        if self._denoise and mean_brightness < 40:
            enhanced_l = cv2.fastNlMeansDenoising(enhanced_l, h=10)

        lab[:, :, 0] = enhanced_l
        enhanced_bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr, True

    @staticmethod
    def draw_night_indicator(frame: np.ndarray) -> np.ndarray:
        """Draw a small NIGHT MODE indicator badge on the frame."""
        h, w = frame.shape[:2]
        badge = "[ NIGHT MODE ]"
        (tw, th), bl = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        # Top-right corner
        x = w - tw - 12
        y = 10
        cv2.rectangle(frame, (x - 4, y), (x + tw + 4, y + th + bl + 4),
                      (30, 30, 80), -1)
        cv2.putText(frame, badge, (x, y + th + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 200, 255), 1, cv2.LINE_AA)
        return frame
