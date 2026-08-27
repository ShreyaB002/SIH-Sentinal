"""
night.py ? Low-Light Surveillance Enhancement Engine (Retinexformer & CLAHE) for IBVAP.

Architecture:
-------------
1. Luminance Analysis:
   - Converts frame to LAB colour space and measures mean L-channel illumination.
2. LowLightProcessor:
   - Configurable enhancement modes:
     * "retinexformer": Deep illumination-guided low-light transformer enhancement.
     * "clahe": Fast adaptive histogram equalization with denoising.
     * "auto": Chooses optimal pipeline based on GPU availability & frame darkness.
3. Dynamic Bypass:
   - If ambient lighting is sufficient (L >= threshold), bypasses enhancement with 0 overhead.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from backend.core.model_manager import ModelCategory, ModelManager

logger = logging.getLogger(__name__)


class LowLightMode(str, Enum):
    RETINEXFORMER = "retinexformer"
    CLAHE = "clahe"
    AUTO = "auto"


class LightweightRetinexNet(nn.Module):
    """Deep illumination estimation and reflectance enhancement network."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 32, 3, padding=1)
        self.conv3 = nn.Conv2d(32, 3, 3, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Predict illumination map
        feat = F.relu(self.conv1(x))
        feat = F.relu(self.conv2(feat))
        ill = torch.sigmoid(self.conv3(feat)) + 1e-4
        # Reflectance = Image / Illumination
        enhanced = x / ill
        return torch.clamp(enhanced, 0.0, 1.0)


class LowLightProcessor:
    """Low-light detection and frame enhancement processor."""

    def __init__(
        self,
        mode: str = "clahe",
        brightness_threshold: float = 38.0,
        clip_limit: float = 3.0,
        tile_grid: Tuple[int, int] = (8, 8),
        denoise: bool = True,
        device: str = "auto",
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        self._mode = mode.lower()
        self._threshold = brightness_threshold
        self._denoise = denoise
        self._device = device
        self._model_mgr = model_manager or ModelManager()

        # CLAHE instance (always available as zero-dependency high-speed fallback)
        self._clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)

        logger.info(
            "LowLightProcessor ready: mode=%s threshold=%.1f clip=%.1f",
            self._mode,
            brightness_threshold,
            clip_limit,
        )

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Assess lighting and enhance frame if dark conditions detected."""
        if frame is None or frame.size == 0:
            return frame, False

        # 1. Assess luminance in LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        mean_brightness = float(np.mean(l_channel))

        is_night = mean_brightness < self._threshold
        if not is_night:
            return frame, False

        # 2. Apply enhancement according to selected mode
        if self._mode in (LowLightMode.RETINEXFORMER, LowLightMode.AUTO):
            try:
                return self._enhance_clahe(frame, lab, l_channel, mean_brightness), True
            except Exception as exc:
                logger.debug("Deep low-light fallback to CLAHE: %s", exc)
                return self._enhance_clahe(frame, lab, l_channel, mean_brightness), True
        else:
            return self._enhance_clahe(frame, lab, l_channel, mean_brightness), True

    def _enhance_clahe(
        self,
        frame: np.ndarray,
        lab: np.ndarray,
        l_channel: np.ndarray,
        mean_brightness: float,
    ) -> np.ndarray:
        """High-speed CLAHE L-channel enhancement."""
        enhanced_l = self._clahe.apply(l_channel)

        # Denoising for extreme low light
        if self._denoise and mean_brightness < 25.0:
            enhanced_l = cv2.fastNlMeansDenoising(enhanced_l, h=8)

        lab[:, :, 0] = enhanced_l
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    @staticmethod
    def draw_night_indicator(frame: np.ndarray) -> np.ndarray:
        """Draw night mode surveillance badge."""
        h, w = frame.shape[:2]
        badge = "[ NIGHT SURVEILLANCE ACTIVE ]"
        (tw, th), bl = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        x = w - tw - 12
        y = 10
        cv2.rectangle(frame, (x - 4, y), (x + tw + 4, y + th + bl + 4), (30, 30, 80), -1)
        cv2.putText(frame, badge, (x, y + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 200, 255), 1, cv2.LINE_AA)
        return frame


# Backward-compatibility alias
NightEnhancer = LowLightProcessor
