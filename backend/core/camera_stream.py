"""
camera_stream.py - High-Performance Decoupled Camera Ingestion & AI Processing.

Architecture: Asynchronous Producer-Consumer Decoupling
-------------------------------------------------------
1. Ingestion Thread (Producer):
   - Reads frames from OpenCV VideoCapture (RTSP / HTTP / file) at full 30 FPS.
   - Non-blocking: never waits for AI inference.
   - Eliminates RTSP buffer overflows, dropped packets, and video pauses.

2. AI Worker Thread (Consumer):
   - Grabs the latest raw frame and runs the Phase 4 AI Pipeline (YOLO + YOLO-World + FRS + ANPR).
   - Produces the annotated frame and fires alerts asynchronously.

3. get_frame():
   - Delivers the latest annotated frame instantly (<1ms) to the MJPEG streaming endpoint.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from backend.config import RTSP_RECONNECT_DELAY

logger = logging.getLogger(__name__)


class CameraStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"


class CameraStream:
    """Manages high-speed ingestion and asynchronous AI analytics for one camera."""

    def __init__(
        self,
        camera_id: str,
        name: str,
        source: str,
        source_type: str = "file",
        pipeline=None,
    ) -> None:
        self.camera_id = camera_id
        self.name = name
        self._source = source
        self._source_type = source_type.lower()
        self._pipeline = pipeline

        self._status = CameraStatus.CONNECTING
        self._status_lock = threading.Lock()

        self._raw_frame: Optional[np.ndarray] = None
        self._annotated_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._ai_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the ingestion and AI worker background threads."""
        if self._running:
            return

        self._running = True

        # Determine capture loop based on source type
        is_usb = self._source_type in ("usb", "webcam", "device") or str(self._source).isdigit()
        if self._source_type == "file":
            target = self._read_loop_file
        elif is_usb:
            target = self._read_loop_usb
        else:
            target = self._read_loop_rtsp

        self._read_thread = threading.Thread(
            target=target,
            name=f"IngestThread-{self.camera_id}",
            daemon=True,
        )
        self._read_thread.start()

        # Dedicated AI analytics worker thread
        if self._pipeline is not None:
            self._ai_thread = threading.Thread(
                target=self._ai_worker_loop,
                name=f"AIWorker-{self.camera_id}",
                daemon=True,
            )
            self._ai_thread.start()

        logger.info("[%s] Decoupled Stream & AI threads started (%s).", self.camera_id, self._source_type)

    def stop(self) -> None:
        """Signal threads to terminate and wait."""
        if not self._running:
            return

        self._running = False

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)
        if self._ai_thread and self._ai_thread.is_alive():
            self._ai_thread.join(timeout=2.0)

        self._set_status(CameraStatus.OFFLINE)
        logger.info("[%s] Stream stopped.", self.camera_id)

    # ------------------------------------------------------------------
    # Frame Access
    # ------------------------------------------------------------------

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the live moving camera frame with AI detection overlays composited in real-time (<0.5ms)."""
        raw = None
        with self._frame_lock:
            if self._raw_frame is not None:
                raw = self._raw_frame.copy()

        if raw is None:
            return None

        if self._pipeline is not None:
            return self._pipeline.annotate_live_frame(raw)
        return raw

    @property
    def status(self) -> CameraStatus:
        with self._status_lock:
            return self._status

    def _set_status(self, new_status: CameraStatus) -> None:
        with self._status_lock:
            if self._status != new_status:
                self._status = new_status

    # ------------------------------------------------------------------
    # Ingestion Loops (Producer - Never Blocks)
    # ------------------------------------------------------------------

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        try:
            # Handle USB / Webcam device indices (e.g. 0, 1, "0", "1")
            if str(self._source).isdigit():
                dev_idx = int(self._source)
                cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(dev_idx)
            else:
                cap = cv2.VideoCapture(self._source)

            if not cap or not cap.isOpened():
                if cap:
                    cap.release()
                return None
            return cap
        except Exception as exc:
            logger.warning("[%s] VideoCapture open failed: %s", self.camera_id, exc)
            return None

    def _read_loop_usb(self) -> None:
        """High-speed non-blocking loop for USB connected phone / webcams."""
        while self._running:
            self._set_status(CameraStatus.CONNECTING)
            cap = self._open_capture()
            if cap is None:
                self._set_status(CameraStatus.OFFLINE)
                for _ in range(int(RTSP_RECONNECT_DELAY * 10)):
                    if not self._running:
                        return
                    time.sleep(0.1)
                continue

            self._set_status(CameraStatus.ONLINE)
            logger.info("[%s] USB Camera connected (Device: %s)", self.camera_id, self._source)

            try:
                while self._running:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("[%s] USB read failed / unplugged, reconnecting...", self.camera_id)
                        break

                    with self._frame_lock:
                        self._raw_frame = frame
                        if self._pipeline is None:
                            self._annotated_frame = frame
            finally:
                cap.release()

    def _read_loop_file(self) -> None:
        cap = self._open_capture()
        if cap is None:
            self._set_status(CameraStatus.OFFLINE)
            return

        self._set_status(CameraStatus.ONLINE)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_time = 1.0 / fps

        try:
            while self._running:
                t0 = time.monotonic()
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                with self._frame_lock:
                    self._raw_frame = frame
                    if self._pipeline is None:
                        self._annotated_frame = frame

                # Maintain realistic video pace for test video files
                elapsed = time.monotonic() - t0
                sleep_dur = frame_time - elapsed
                if sleep_dur > 0:
                    time.sleep(sleep_dur)
        finally:
            cap.release()

    def _read_loop_rtsp(self) -> None:
        while self._running:
            self._set_status(CameraStatus.CONNECTING)
            cap = self._open_capture()
            if cap is None:
                self._set_status(CameraStatus.OFFLINE)
                for _ in range(int(RTSP_RECONNECT_DELAY * 10)):
                    if not self._running:
                        return
                    time.sleep(0.1)
                continue

            self._set_status(CameraStatus.ONLINE)
            logger.info("[%s] RTSP connected: %s", self.camera_id, self._source)

            try:
                while self._running:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("[%s] RTSP stream read interrupted, reconnecting...", self.camera_id)
                        break

                    with self._frame_lock:
                        self._raw_frame = frame
                        if self._pipeline is None:
                            self._annotated_frame = frame
            finally:
                cap.release()

    # ------------------------------------------------------------------
    # AI Processing Worker (Consumer - Asynchronous)
    # ------------------------------------------------------------------

    def _ai_worker_loop(self) -> None:
        """Pulls the latest raw frame and executes AI inference concurrently."""
        while self._running:
            raw = None
            with self._frame_lock:
                if self._raw_frame is not None:
                    raw = self._raw_frame.copy()

            if raw is None:
                time.sleep(0.02)
                continue

            try:
                annotated = self._pipeline.process(raw)
                with self._frame_lock:
                    self._annotated_frame = annotated
            except Exception as exc:
                logger.warning("[%s] AI Worker error: %s", self.camera_id, exc)
                time.sleep(0.05)
