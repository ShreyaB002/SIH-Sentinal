"""
CameraStream — threaded video frame reader for IBVAP.

This module provides a single :class:`CameraStream` that:

* Opens a video source (local file **or** RTSP URL) via ``cv2.VideoCapture``.
* Runs a background daemon thread that continuously reads frames and stores only
  the **latest** one, discarding older frames immediately (real-time priority).
* Exposes the latest frame through a thread-safe property.
* Handles video-file EOF by looping (simulating a continuous CCTV feed).
* Handles RTSP disconnections by attempting periodic reconnection.
* Maintains a :class:`CameraStatus` that the rest of the application can query.

Architecture note
-----------------
``CameraStream`` is the only component that ever calls ``cv2.VideoCapture``.
FastAPI endpoints and the ``StreamManager`` must **never** create their own
capture objects; they should call :meth:`CameraStream.get_frame` instead.
This ensures exactly one reader per physical (or simulated) camera source.

Future extension
----------------
Phase 2 will insert a frame-processing pipeline between the raw frame and the
callers.  The planned hook point is :meth:`CameraStream.get_frame`, which can
be extended to run detectors/trackers before returning the frame without
changing the public interface.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from backend.config import PROJECT_ROOT, RTSP_RECONNECT_DELAY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class CameraStatus(str, Enum):
    """Lifecycle status of a single camera stream."""

    CONNECTING = "CONNECTING"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


# ---------------------------------------------------------------------------
# CameraStream
# ---------------------------------------------------------------------------


class CameraStream:
    """A self-contained, threaded reader for one camera source.

    Parameters
    ----------
    camera_id:
        Unique identifier used for logging and API responses.
    name:
        Human-readable display name (e.g. "Border Camera 01").
    source:
        Video source string.  For ``type="file"`` this is a path relative to
        the project root.  For ``type="rtsp"`` this is the full RTSP URL.
    source_type:
        ``"file"`` or ``"rtsp"``.
    pipeline:
        Optional :class:`FramePipeline` instance.  When provided, raw frames
        are passed through the pipeline (detection → tracking → fence) before
        being stored in the latest-frame buffer.  ``None`` = Phase 1 mode,
        raw frames stored directly.
    """

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
        self.source_type = source_type.lower()

        # Optional AI processing pipeline (Phase 2)
        self._pipeline = pipeline

        # Resolve file paths relative to the project root so that no absolute
        # paths are baked into the configuration.
        if self.source_type == "file":
            resolved = PROJECT_ROOT / source
            self._source: str = str(resolved)
        else:
            # RTSP and other URL-based sources are used as-is.
            self._source = source

        self._status: CameraStatus = CameraStatus.CONNECTING
        self._status_lock = threading.Lock()

        # Latest frame buffer — only the most recent frame is kept.
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def status(self) -> CameraStatus:
        """Thread-safe read of the current camera status."""
        with self._status_lock:
            return self._status

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the latest decoded frame, or ``None`` if unavailable.

        Callers (e.g. the MJPEG endpoint) should handle ``None`` gracefully
        by either skipping that iteration or serving a placeholder image.

        Phase 2 hook
        ------------
        This method is the intended insertion point for the AI processing
        pipeline.  Before returning, future code will run detectors, update
        tracking state, draw bounding boxes, etc.
        """
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def start(self) -> None:
        """Start the background frame-reading thread."""
        if self._running:
            logger.warning("[%s] start() called but already running.", self.camera_id)
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop,
            name=f"cam-{self.camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] Stream thread started (source_type=%s).", self.camera_id, self.source_type)

    def stop(self) -> None:
        """Signal the background thread to stop and wait for it to exit."""
        logger.info("[%s] Stopping stream thread...", self.camera_id)
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("[%s] Stream thread stopped.", self.camera_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_status(self, status: CameraStatus) -> None:
        with self._status_lock:
            if self._status != status:
                logger.info("[%s] Status: %s → %s", self.camera_id, self._status, status)
            self._status = status

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        """Attempt to open the video source and return a capture object.

        Returns ``None`` if the source cannot be opened so that the caller
        can handle the error without raising an exception.
        """
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            cap.release()
            return None
        return cap

    # ------------------------------------------------------------------
    # Frame reading loops
    # ------------------------------------------------------------------

    def _read_loop(self) -> None:
        """Entry point for the background thread.

        Dispatches to the appropriate reading strategy based on
        ``source_type``.
        """
        if self.source_type == "file":
            self._read_loop_file()
        else:
            self._read_loop_rtsp()

    def _read_loop_file(self) -> None:
        """Read frames from a local video file, looping at EOF.

        This simulates a continuously-running CCTV camera during development.
        When the file ends, the reader seeks back to frame 0 and continues.
        """
        cap = self._open_capture()
        if cap is None:
            logger.error(
                "[%s] Cannot open file source: %s. Setting OFFLINE.",
                self.camera_id,
                self._source,
            )
            self._set_status(CameraStatus.OFFLINE)
            return

        self._set_status(CameraStatus.ONLINE)
        logger.info("[%s] File source opened: %s", self.camera_id, self._source)

        try:
            while self._running:
                ret, frame = cap.read()

                if not ret:
                    # EOF — loop back to the beginning
                    logger.debug("[%s] EOF reached, looping.", self.camera_id)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # Pass through AI pipeline if configured (Phase 2)
                if self._pipeline is not None:
                    try:
                        frame = self._pipeline.process(frame)
                    except Exception as exc:
                        logger.warning("[%s] Pipeline error: %s", self.camera_id, exc)

                with self._frame_lock:
                    self._frame = frame

        finally:
            cap.release()
            logger.info("[%s] VideoCapture released (file).", self.camera_id)

    def _read_loop_rtsp(self) -> None:
        """Read frames from an RTSP stream, reconnecting on failure.

        If the connection drops, the status is set to CONNECTING and the
        reader waits ``RTSP_RECONNECT_DELAY`` seconds before retrying.
        """
        while self._running:
            self._set_status(CameraStatus.CONNECTING)
            cap = self._open_capture()

            if cap is None:
                logger.warning(
                    "[%s] RTSP source unavailable: %s. Retrying in %.1fs.",
                    self.camera_id,
                    self._source,
                    RTSP_RECONNECT_DELAY,
                )
                self._set_status(CameraStatus.OFFLINE)
                # Wait in small increments so we can honour stop() quickly.
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
                        logger.warning("[%s] RTSP read failed, reconnecting.", self.camera_id)
                        break
                    # Pass through AI pipeline if configured (Phase 2)
                    if self._pipeline is not None:
                        try:
                            frame = self._pipeline.process(frame)
                        except Exception as exc:
                            logger.warning("[%s] Pipeline error: %s", self.camera_id, exc)
                    with self._frame_lock:
                        self._frame = frame
            finally:
                cap.release()
                logger.info("[%s] VideoCapture released (RTSP).", self.camera_id)

        self._set_status(CameraStatus.OFFLINE)
