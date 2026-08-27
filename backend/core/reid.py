"""
reid.py ? OSNet Cross-Camera Person Re-Identification (Re-ID) Engine for IBVAP.

Architecture:
-------------
1. OSNetExtractor:
   - Takes BGR person crop (x1, y1, x2, y2)
   - Preprocesses into (256, 128) normalized tensor
   - Computes L2-normalized 512-dimensional embedding vector
   - Backed by ModelManager singleton (category: SPECIALIST)

2. ReIDManager / Cross-Camera Gallery:
   - Maintains rolling gallery of active person embeddings across all CCTV streams
   - Matches incoming track embeddings against gallery using Cosine Similarity
   - Detects cross-camera transitions (e.g. cam_01 Track #17 -> cam_04 Track #42)
   - Prunes expired embeddings after configurable TTL
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from backend.core.model_manager import ModelCategory, ModelManager
from backend.core.reid_model import OSNet, build_osnet

logger = logging.getLogger(__name__)


@dataclass
class ReIDEntry:
    """Stored embedding entry for an active person in the surveillance zone."""
    global_person_id: int
    embedding: np.ndarray             # 512-d float32 L2-normalized vector
    camera_id: str
    local_track_id: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReIDMatchResult:
    """Result of cross-camera person matching."""
    global_person_id: int
    similarity: float
    is_new_registration: bool
    origin_camera_id: str = ""
    origin_track_id: int = 0
    matched: bool = False


class OSNetExtractor:
    """Extracts 512-dimensional identity embeddings from person crops using OSNet."""

    def __init__(
        self,
        device: str = "auto",
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        self._model_mgr = model_manager or ModelManager()
        self._device_pref = device

    def _get_model(self) -> Tuple[OSNet, str]:
        """Lazy load shared OSNet instance via ModelManager."""
        def _loader(m_name: str, dev: str) -> OSNet:
            model = build_osnet(feature_dim=512)
            model.to(dev)
            return model

        inst, meta = self._model_mgr.get_or_load(
            key="person_reid_osnet",
            model_name="osnet_x1_0",
            loader_fn=_loader,
            category=ModelCategory.SPECIALIST,
            target_device=self._device_pref,
        )
        return inst, meta.device

    def extract(self, person_crop: np.ndarray) -> Optional[np.ndarray]:
        """Extract 512-d normalized embedding from a BGR person crop.

        Parameters
        ----------
        person_crop : np.ndarray
            BGR image slice of a detected person.

        Returns
        -------
        Optional[np.ndarray]
            (512,) float32 normalized embedding vector, or None if invalid crop.
        """
        if person_crop is None or person_crop.size == 0:
            return None

        h, w = person_crop.shape[:2]
        if h < 32 or w < 16:
            return None

        try:
            # 1. Resize to standard Re-ID dimensions (256 height x 128 width)
            resized = cv2.resize(person_crop, (128, 256), interpolation=cv2.INTER_LINEAR)

            # 2. Convert BGR to RGB and normalize to [0, 1]
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

            # 3. Standard ImageNet mean & std normalization
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            norm = (rgb - mean) / std

            # 4. HWC -> CHW -> NCHW tensor
            tensor = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0)

            model, dev = self._get_model()
            tensor = tensor.to(dev)

            with torch.no_grad():
                features = model(tensor)
                embedding = features.squeeze(0).cpu().numpy().astype(np.float32)

            return embedding

        except Exception as exc:
            logger.warning("OSNet Re-ID embedding extraction error: %s", exc)
            return None


class ReIDManager:
    """Global Cross-Camera Person Gallery and Re-Identification Coordinator."""

    _instance: Optional["ReIDManager"] = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(ReIDManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        similarity_threshold: float = 0.70,
        max_gallery_size: int = 500,
        expiration_seconds: float = 3600.0,
        device: str = "auto",
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self._threshold = similarity_threshold
        self._max_gallery_size = max_gallery_size
        self._expiration_seconds = expiration_seconds
        self._extractor = OSNetExtractor(device=device)

        self._gallery: List[ReIDEntry] = []
        self._next_global_id = 1
        self._lock = threading.Lock()
        self._initialized = True

        logger.info(
            "ReIDManager initialized. Sim Threshold: %.2f | Max Gallery: %d",
            self._threshold,
            self._max_gallery_size,
        )

    def match_or_register(
        self,
        person_crop: np.ndarray,
        camera_id: str,
        local_track_id: int,
    ) -> Optional[ReIDMatchResult]:
        """Extract embedding from person crop, match against active gallery or register."""
        embedding = self._extractor.extract(person_crop)
        if embedding is None:
            return None

        now = time.time()
        with self._lock:
            self._cleanup_expired(now)

            best_sim = 0.0
            best_entry: Optional[ReIDEntry] = None

            # Compare against all gallery entries
            for entry in self._gallery:
                # Cosine similarity between two unit vectors = dot product
                sim = float(np.dot(embedding, entry.embedding))
                if sim > best_sim:
                    best_sim = sim
                    best_entry = entry

            # Check if match exceeds confidence threshold
            if best_entry is not None and best_sim >= self._threshold:
                # Matched existing global person identity!
                matched_gid = best_entry.global_person_id
                # Append updated embedding to smooth variations
                self._gallery.append(
                    ReIDEntry(
                        global_person_id=matched_gid,
                        embedding=embedding,
                        camera_id=camera_id,
                        local_track_id=local_track_id,
                        timestamp=now,
                    )
                )
                logger.info(
                    "Re-ID MATCH: [%s #%d] -> Global Person #%d (Sim: %.1f%%, Origin: %s #%d)",
                    camera_id,
                    local_track_id,
                    matched_gid,
                    best_sim * 100.0,
                    best_entry.camera_id,
                    best_entry.local_track_id,
                )
                return ReIDMatchResult(
                    global_person_id=matched_gid,
                    similarity=best_sim,
                    is_new_registration=False,
                    origin_camera_id=best_entry.camera_id,
                    origin_track_id=best_entry.local_track_id,
                    matched=True,
                )
            else:
                # New person identity registration
                new_gid = self._next_global_id
                self._next_global_id += 1

                self._gallery.append(
                    ReIDEntry(
                        global_person_id=new_gid,
                        embedding=embedding,
                        camera_id=camera_id,
                        local_track_id=local_track_id,
                        timestamp=now,
                    )
                )
                # Enforce gallery cap
                if len(self._gallery) > self._max_gallery_size:
                    self._gallery.pop(0)

                return ReIDMatchResult(
                    global_person_id=new_gid,
                    similarity=best_sim,
                    is_new_registration=True,
                    origin_camera_id=camera_id,
                    origin_track_id=local_track_id,
                    matched=False,
                )

    def _cleanup_expired(self, now: float) -> None:
        """Prune gallery entries older than expiration_seconds."""
        cutoff = now - self._expiration_seconds
        self._gallery = [e for e in self._gallery if e.timestamp >= cutoff]

    def clear(self) -> None:
        """Clear all active gallery identities."""
        with self._lock:
            self._gallery.clear()
            self._next_global_id = 1
