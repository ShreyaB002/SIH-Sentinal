"""
model_manager.py ? Centralized Model Registry and VRAM Lifecycle Manager for IBVAP.

Key Architectural Guarantees:
1. SINGLETON INSTANCES: One shared loaded model instance per model key across all CCTV streams.
2. HARDWARE AWARENESS: Real-time GPU VRAM tracking on RTX 2050 (4 GB GDDR6 budget).
3. CONTROLLED FALLBACK: If a large model (e.g. yolo26x) fails or triggers CUDA OOM,
   safely clears cache, logs the event, and loads the configured fallback (yolo26l -> yolo26m -> yolov8n).
4. SPECIALIST ISOLATION: Distinguishes CORE models (detector) from SPECIALIST models (face, anpr, threat, reid).
"""

from __future__ import annotations

import gc
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch

logger = logging.getLogger(__name__)


class ModelCategory(str, Enum):
    CORE = "CORE"            # Resident in VRAM (Main Object Detector, Tracker)
    SPECIALIST = "SPECIALIST"  # Loaded on demand (Face, ANPR, Threat, ReID, Night)


@dataclass
class ModelMetadata:
    key: str
    name: str
    category: ModelCategory
    device: str
    instance: Any = None
    loaded: bool = False
    vram_mb: float = 0.0
    fallback_from: Optional[str] = None
    extra_info: Dict[str, Any] = field(default_factory=dict)


class ModelManager:
    """Thread-safe centralized AI model registry and GPU memory manager."""

    _instance: Optional["ModelManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, default_device: str = "auto") -> None:
        if getattr(self, "_initialized", False):
            return

        self._default_device_pref = default_device.lower()
        self._device = self._resolve_device(self._default_device_pref)
        self._models: Dict[str, ModelMetadata] = {}
        self._model_locks: Dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()
        self._initialized = True

        logger.info(
            "ModelManager initialized. Target Device: %s | Total GPU VRAM: %.2f GB",
            self.device_name,
            self.vram_total_gb,
        )

    # ------------------------------------------------------------------
    # Hardware & Device Resolution
    # ------------------------------------------------------------------

    def _resolve_device(self, pref: str) -> str:
        if pref in ("cuda", "gpu"):
            return "cuda" if torch.cuda.is_available() else "cpu"
        elif pref == "cpu":
            return "cpu"
        # "auto"
        return "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def device(self) -> str:
        return self._device

    @property
    def is_cuda(self) -> bool:
        return self._device.startswith("cuda") and torch.cuda.is_available()

    @property
    def device_name(self) -> str:
        if self.is_cuda:
            try:
                return f"cuda:0 ({torch.cuda.get_device_name(0)})"
            except Exception:
                return "cuda"
        return "cpu"

    @property
    def vram_total_gb(self) -> float:
        if self.is_cuda:
            try:
                return torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except Exception:
                return 0.0
        return 0.0

    @property
    def vram_allocated_mb(self) -> float:
        if self.is_cuda:
            try:
                return torch.cuda.memory_allocated(0) / (1024**2)
            except Exception:
                return 0.0
        return 0.0

    @property
    def vram_reserved_mb(self) -> float:
        if self.is_cuda:
            try:
                return torch.cuda.memory_reserved(0) / (1024**2)
            except Exception:
                return 0.0
        return 0.0

    # ------------------------------------------------------------------
    # Singleton Model Retrieval & Lifecycle
    # ------------------------------------------------------------------

    def get_or_load(
        self,
        key: str,
        model_name: str,
        loader_fn: Callable[[str, str], Any],
        category: ModelCategory = ModelCategory.CORE,
        fallback_names: Optional[List[str]] = None,
        target_device: Optional[str] = None,
        **extra_kwargs,
    ) -> Tuple[Any, ModelMetadata]:
        """Retrieve a shared model singleton, loading it lazily if not present."""
        with self._registry_lock:
            if key not in self._model_locks:
                self._model_locks[key] = threading.Lock()
            model_lock = self._model_locks[key]

        with model_lock:
            # Check if already loaded
            if key in self._models and self._models[key].loaded:
                return self._models[key].instance, self._models[key]

            device = self._resolve_device(target_device or self._default_device_pref)
            candidates = [model_name] + (fallback_names or [])
            vram_before = self.vram_allocated_mb

            instance = None
            used_name = model_name
            fallback_from = None

            for idx, candidate in enumerate(candidates):
                try:
                    logger.info("[%s] Loading model: %s on %s...", key, candidate, device)
                    instance = loader_fn(candidate, device, **extra_kwargs)
                    used_name = candidate
                    if idx > 0:
                        fallback_from = candidates[0]
                        logger.warning(
                            "[%s] Primary model '%s' failed or OOM. Fallback active: '%s'",
                            key,
                            candidates[0],
                            used_name,
                        )
                    break
                except (torch.cuda.OutOfMemoryError, RuntimeError, Exception) as exc:
                    is_oom = isinstance(exc, torch.cuda.OutOfMemoryError) or "out of memory" in str(exc).lower()
                    logger.warning(
                        "[%s] Failed to load candidate '%s' on %s (OOM=%s): %s",
                        key,
                        candidate,
                        device,
                        is_oom,
                        exc,
                    )
                    self.clear_gpu_cache()

                    if idx == len(candidates) - 1:
                        # If all GPU candidates failed, try CPU fallback as last resort
                        if device != "cpu":
                            logger.warning("[%s] Attempting final CPU fallback for '%s'...", key, candidate)
                            try:
                                instance = loader_fn(candidate, "cpu", **extra_kwargs)
                                used_name = candidate
                                device = "cpu"
                                fallback_from = candidates[0]
                                break
                            except Exception as cpu_exc:
                                logger.error("[%s] CPU fallback failed: %s", key, cpu_exc)

            if instance is None:
                raise RuntimeError(
                    f"ModelManager: Unable to load model '{key}' from candidates {candidates}."
                )

            vram_after = self.vram_allocated_mb
            vram_delta = max(0.0, vram_after - vram_before)

            meta = ModelMetadata(
                key=key,
                name=used_name,
                category=category,
                device=device,
                instance=instance,
                loaded=True,
                vram_mb=vram_delta,
                fallback_from=fallback_from,
                extra_info=extra_kwargs,
            )

            with self._registry_lock:
                self._models[key] = meta

            logger.info(
                "[%s] Model ready: %s (Device: %s | VRAM: ~%.1f MB)",
                key,
                used_name,
                device,
                vram_delta,
            )
            return instance, meta

    def unload(self, key: str) -> bool:
        """Unload a model from memory and release GPU cache."""
        with self._registry_lock:
            if key not in self._models or not self._models[key].loaded:
                return False
            meta = self._models[key]

        lock = self._model_locks.get(key, threading.Lock())
        with lock:
            logger.info("[%s] Unloading model %s (%s)...", key, meta.name, meta.device)
            meta.instance = None
            meta.loaded = False
            meta.vram_mb = 0.0

            with self._registry_lock:
                self._models.pop(key, None)

            self.clear_gpu_cache()
            return True

    def clear_gpu_cache(self) -> None:
        """Run garbage collection and empty PyTorch CUDA cache."""
        gc.collect()
        if self.is_cuda:
            try:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Diagnostics & Status Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of all registered models and VRAM utilization."""
        with self._registry_lock:
            models_info = {}
            for key, meta in self._models.items():
                models_info[key] = {
                    "name": meta.name,
                    "category": meta.category.value,
                    "device": meta.device,
                    "loaded": meta.loaded,
                    "vram_mb": round(meta.vram_mb, 1),
                    "fallback_from": meta.fallback_from,
                }

        return {
            "device": self.device_name,
            "vram_total_gb": round(self.vram_total_gb, 2),
            "vram_allocated_mb": round(self.vram_allocated_mb, 1),
            "vram_reserved_mb": round(self.vram_reserved_mb, 1),
            "models_count": len(models_info),
            "models": models_info,
        }
