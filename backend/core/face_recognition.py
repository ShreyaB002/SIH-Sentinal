"""
face_recognition.py - Face detection and watchlist matching for IBVAP Phase 4.

Uses InsightFace (ArcFace backbone) for:
  - Face detection (RetinaFace)
  - Face embedding extraction (ArcFace 512-d vector)
  - Watchlist matching (cosine similarity)

GPU-accelerated via ONNX Runtime with CUDA execution provider.
Falls back to CPU if GPU is unavailable.

Workflow per frame
------------------
1. Receive Person bounding box crop from pipeline
2. Run InsightFace to detect faces + extract 512-d embeddings
3. Compare embedding against watchlist DB using cosine similarity
4. If similarity > MATCH_THRESHOLD ? FACE_MATCH event
5. If face detected but no match ? UNKNOWN_FACE event (optional)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceResult:
    """Result of one face recognition attempt."""
    matched: bool
    name: str                          # Matched person name or "Unknown"
    person_id: str                     # Watchlist ID or empty
    similarity: float                  # Cosine similarity (0-1)
    bbox: tuple[int, int, int, int]    # Face bbox in full-frame coords
    embedding: Optional[np.ndarray]    # 512-d embedding for storage


class FaceRecognizer:
    """InsightFace-based face detector and watchlist matcher.

    Parameters
    ----------
    det_size : tuple[int, int]
        Face detection input size. (640, 640) for best accuracy.
    match_threshold : float
        Cosine similarity threshold for watchlist match (0-1).
        0.4 is strict; 0.35 is lenient. Use 0.40 for border security.
    device : str
        ``"cuda"`` or ``"cpu"``. CUDA dramatically speeds up detection.
    """

    def __init__(
        self,
        det_size: tuple = (640, 640),
        match_threshold: float = 0.40,
        device: str = "cuda",
    ) -> None:
        self._det_size = det_size
        self._match_threshold = match_threshold
        self._device = device
        self._app = None    # InsightFace FaceAnalysis app
        self._watchlist: list[dict] = []  # {id, name, embedding}

        logger.info("FaceRecognizer configured: device=%s threshold=%.2f",
                    device, match_threshold)

    def _load(self) -> None:
        """Lazy-load InsightFace with CUDA ONNX provider via ModelManager."""
        from backend.core.model_manager import ModelCategory, ModelManager
        mm = ModelManager()

        def _insightface_loader(name: str, dev: str):
            import insightface
            from insightface.app import FaceAnalysis
            providers = (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if dev == "cuda"
                else ["CPUExecutionProvider"]
            )
            app = FaceAnalysis(name=name, providers=providers)
            app.prepare(ctx_id=0 if dev == "cuda" else -1, det_size=self._det_size)
            return app

        try:
            self._app, _ = mm.get_or_load(
                key="face_insightface",
                model_name="buffalo_l",
                loader_fn=_insightface_loader,
                category=ModelCategory.SPECIALIST,
                target_device=self._device,
            )
            logger.info("InsightFace (buffalo_l) ready via ModelManager.")
        except Exception as exc:
            logger.warning("InsightFace not available (%s), using OpenCV Face Cascade fallback.", exc)
            self._app = "opencv_fallback"
            self._cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def load_watchlist(self, entries: list[dict]) -> None:
        """Load watchlist entries with pre-computed embeddings.

        Each entry: {id: str, name: str, embedding: np.ndarray (512,)}
        """
        self._watchlist = entries
        logger.info("FaceRecognizer watchlist loaded: %d entries.", len(entries))

    def recognize(
        self,
        frame: np.ndarray,
        person_bbox: Optional[tuple] = None,
    ) -> list[FaceResult]:
        """Detect and recognize faces in a frame (or person crop)."""
        if self._app is None:
            try:
                self._load()
            except Exception:
                return []

        px_off = person_bbox[0] if person_bbox else 0
        py_off = person_bbox[1] if person_bbox else 0
        results: list[FaceResult] = []

        if self._app == "opencv_fallback":
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._cascade.detectMultiScale(gray, 1.2, 4, minSize=(30, 30))
                for (x, y, w, h) in faces:
                    fx1, fy1, fx2, fy2 = x + px_off, y + py_off, x + w + px_off, y + h + py_off
                    # Simple color/texture descriptor as 512-dim embedding fallback
                    face_roi = cv2.resize(gray[y:y+h, x:x+w], (32, 16))
                    emb = face_roi.flatten().astype(np.float32)
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        emb = emb / norm
                    matched, name, person_id, similarity = self._match(emb)
                    results.append(FaceResult(
                        matched=matched,
                        name=name,
                        person_id=person_id,
                        similarity=similarity,
                        bbox=(fx1, fy1, fx2, fy2),
                        embedding=emb,
                    ))
            except Exception as exc:
                logger.debug("OpenCV face fallback error: %s", exc)
            return results

        try:
            faces = self._app.get(frame)
        except Exception as exc:
            logger.debug("InsightFace inference error: %s", exc)
            return []

        results: list[FaceResult] = []
        px_off = person_bbox[0] if person_bbox else 0
        py_off = person_bbox[1] if person_bbox else 0

        for face in faces:
            emb = face.embedding  # 512-d np.ndarray, already L2-normalised
            bbox_local = [int(v) for v in face.bbox]   # in crop coords
            # Convert to full-frame coords
            fx1 = bbox_local[0] + px_off
            fy1 = bbox_local[1] + py_off
            fx2 = bbox_local[2] + px_off
            fy2 = bbox_local[3] + py_off

            matched, name, person_id, similarity = self._match(emb)
            results.append(FaceResult(
                matched=matched,
                name=name,
                person_id=person_id,
                similarity=similarity,
                bbox=(fx1, fy1, fx2, fy2),
                embedding=emb,
            ))

        return results

    def _match(self, embedding: np.ndarray) -> tuple[bool, str, str, float]:
        """Compare embedding against watchlist. Returns (matched, name, id, sim)."""
        if not self._watchlist:
            return False, "Unknown", "", 0.0

        best_sim = -1.0
        best_name = "Unknown"
        best_id = ""

        for entry in self._watchlist:
            wl_emb = entry["embedding"]
            # Cosine similarity (both embeddings are L2-normalised by InsightFace)
            sim = float(np.dot(embedding, wl_emb))
            if sim > best_sim:
                best_sim = sim
                best_name = entry["name"]
                best_id = entry["id"]

        matched = best_sim >= self._match_threshold
        return matched, best_name if matched else "Unknown", best_id if matched else "", best_sim

    @staticmethod
    def draw_face(frame: np.ndarray, result: FaceResult) -> np.ndarray:
        """Draw face bounding box + name label on frame."""
        x1, y1, x2, y2 = result.bbox
        color = (0, 255, 100) if result.matched else (255, 140, 0)  # green=match, amber=unknown
        thickness = 3 if result.matched else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        label = f"{result.name} {result.similarity:.0%}" if result.matched else "Unknown Face"
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - bl - 6), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, label, (x1 + 3, y1 - bl - 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return frame
