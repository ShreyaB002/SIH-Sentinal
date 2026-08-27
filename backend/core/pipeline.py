"""
pipeline.py - Per-camera AI processing pipeline (IBVAP Phase 4 - COMPLETE).

Full Phase 4 processing chain per frame:
-----------------------------------------
raw frame
  -> NightEnhancer (CLAHE if low-light)
  -> [every N] YOLOv8 track (person/vehicle, ByteTrack, CUDA)
  -> [every N] WeaponsDetector (YOLO-World-L, CUDA)
  -> VirtualFence check (intrusion)
  -> ActivityAnalyzer (loitering, running, crowd)
  -> [per Person] FaceRecognizer (InsightFace, CUDA)
  -> [per Vehicle] PlateReader (PaddleOCR, CPU)
  -> Annotate all overlays + alert banners
  -> EventManager.receive_* (all event types)
  -> return annotated frame to MJPEG encoder
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np

from backend.config import (
    AI_ENABLED,
    ACTIVITY_COOLDOWN,
    BBOX_COLORS,
    CROWD_THRESHOLD,
    DETECT_EVERY_N_FRAMES,
    LABEL_OVERRIDES,
    LOITER_SECONDS,
    NIGHT_BRIGHTNESS_THRESHOLD,
    NIGHT_CLAHE_CLIP,
    NIGHT_DENOISE,
    RUNNING_SPEED,
    WEAPONS_CLASSES,
    WEAPONS_CONFIDENCE,
    WEAPONS_ENABLED,
    WEAPONS_MODEL,
    YOLO_CLASSES,
    YOLO_CONFIDENCE,
    ZONES,
)
from backend.core.activity import ActivityAnalyzer, ActivityEvent
from backend.core.anpr import PlateReader, PlateResult
from backend.core.face_recognition import FaceRecognizer, FaceResult
from backend.core.fence import VirtualFence
from backend.core.night import NightEnhancer
from backend.core.tracker import TrackedObject, Tracker
from backend.core.weapons_detector import WeaponsDetector, WeaponDetection

if TYPE_CHECKING:
    from backend.core.event_manager import EventManager

logger = logging.getLogger(__name__)

# Annotation BGR colors
_C_WEAPON    = (0,   0,   255)
_C_LOITER    = (0,   165, 255)
_C_RUNNING   = (255, 200, 0)
_C_CROWD     = (255, 0,   200)
_C_INTRUSION = (0,   60,  220)
_C_FACE_MATCH= (0,   220, 80)
_C_FACE_UNK  = (0,   140, 255)
_C_PLATE     = (255, 255, 0)
_C_NIGHT     = (180, 100, 40)


class FramePipeline:
    """Full Phase 4 per-camera AI pipeline."""

    def __init__(
        self,
        camera_id: str,
        event_manager: "EventManager",
        face_recognizer: Optional[FaceRecognizer] = None,
    ) -> None:
        self.camera_id = camera_id
        self._event_manager = event_manager
        self._frame_count = 0
        self._device = "cuda"

        # Night enhancer with calibrated thresholds
        self._night = NightEnhancer(
            brightness_threshold=NIGHT_BRIGHTNESS_THRESHOLD,
            clip_limit=NIGHT_CLAHE_CLIP,
            denoise=NIGHT_DENOISE,
        )

        # Per-pipeline YOLO tracker
        self._tracker_model = None

        # Weapons detector (YOLO-World-L, CUDA)
        self._weapons: Optional[WeaponsDetector] = None
        if WEAPONS_ENABLED:
            self._weapons = WeaponsDetector(
                model_name=WEAPONS_MODEL,
                classes=WEAPONS_CLASSES,
                confidence=WEAPONS_CONFIDENCE,
                device=self._device,
            )

        # Virtual fence zones
        zones_cfg = ZONES.get(camera_id, [])
        self._fence = VirtualFence(camera_id=camera_id, zones=zones_cfg)

        # Activity analyzer
        self._activity = ActivityAnalyzer(
            camera_id=camera_id,
            loiter_seconds=LOITER_SECONDS,
            running_speed=RUNNING_SPEED,
            crowd_threshold=CROWD_THRESHOLD,
        )

        # Shared face recognizer (one instance across all cameras for watchlist sync)
        self._face_recognizer = face_recognizer

        # ANPR (per-pipeline, lazy-loaded)
        self._plate_reader: Optional[PlateReader] = None

        # Detection cache & live 30 FPS overlay data
        self._last_tracked: list[TrackedObject] = []
        self._last_weapons: list[WeaponDetection] = []
        self._latest_overlay_data = None
        self._overlay_lock = threading.Lock()

        logger.info("[%s] FramePipeline Phase 4 ready (device=%s)", camera_id, self._device)

    def set_face_recognizer(self, fr: FaceRecognizer) -> None:
        """Update face recognizer (called when watchlist changes)."""
        self._face_recognizer = fr

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Run full pipeline. Called from CameraStream background thread."""
        if not AI_ENABLED:
            return frame

        self._frame_count += 1
        run_detection = (self._frame_count % DETECT_EVERY_N_FRAMES == 0)

        # --- Night enhancement ---
        try:
            enhanced, is_night = self._night.process(frame)
        except Exception:
            enhanced, is_night = frame, False

        # --- Detection & Tracking ---
        if run_detection:
            try:
                tracked = self._run_tracking(enhanced)
                self._last_tracked = tracked
            except Exception as trk_err:
                logger.warning("[%s] Tracking error: %s", self.camera_id, trk_err)
                tracked = self._last_tracked

            try:
                weapons = self._weapons.detect(enhanced) if self._weapons else []
                self._last_weapons = weapons
            except Exception as wpn_err:
                logger.warning("[%s] Weapons detector error: %s", self.camera_id, wpn_err)
                weapons = self._last_weapons
        else:
            tracked = self._last_tracked
            weapons = self._last_weapons
            enhanced = frame

        # --- Virtual fence ---
        try:
            fence_events = self._fence.check(tracked)
        except Exception:
            fence_events = []

        # --- Active zones mapping ---
        active_zones: dict[int, list[str]] = {}
        for fe in fence_events:
            active_zones.setdefault(fe.track_id, []).append(fe.zone_name)

        # --- Activity analysis ---
        try:
            activity_events = self._activity.analyze(tracked, active_zones)
        except Exception:
            activity_events = []

        # --- Face recognition (per Person) ---
        face_results: list[FaceResult] = []
        if self._face_recognizer and (self._frame_count % 4 == 0):
            for obj in tracked:
                if obj.label == "Person":
                    try:
                        crop, offset = self._crop_person(enhanced, obj.bbox)
                        if crop is not None:
                            faces = self._face_recognizer.recognize(crop, offset)
                            face_results.extend(faces)
                    except Exception as fr_err:
                        logger.debug("[%s] Face recognition error: %s", self.camera_id, fr_err)

        # --- ANPR ---
        plate_results: list[PlateResult] = []
        if run_detection:
            try:
                for obj in tracked:
                    if obj.label in ("Car", "Truck", "Bus", "Motorcycle"):
                        pr = self._get_plate_reader().read(enhanced, obj.bbox, obj.label)
                        if pr:
                            plate_results.append(pr)
                if not plate_results and (self._frame_count % 4 == 0):
                    pr_direct = self._get_plate_reader().read_from_frame(enhanced)
                    if pr_direct:
                        plate_results.append(pr_direct)
            except Exception as anpr_err:
                logger.debug("[%s] ANPR error: %s", self.camera_id, anpr_err)

        # --- Emit events ---
        try:
            if fence_events:
                self._event_manager.receive(fence_events)
            for w in weapons:
                self._event_manager.receive_weapon(self.camera_id, w)
            for a in activity_events:
                self._event_manager.receive_activity(a)
            for f in face_results:
                self._event_manager.receive_face(self.camera_id, f)
            for p in plate_results:
                self._event_manager.receive_plate(self.camera_id, p)
            if is_night and run_detection and tracked:
                self._event_manager.receive_night_movement(self.camera_id, len(tracked))
        except Exception as evt_err:
            logger.debug("[%s] Event emit error: %s", self.camera_id, evt_err)

        # --- Cache latest overlays for live 30 FPS rendering ---
        with self._overlay_lock:
            self._latest_overlay_data = (
                tracked, fence_events, weapons, activity_events,
                face_results, plate_results, is_night
            )

        # --- Annotate ---
        annotated = self._annotate(
            frame.copy(), tracked, fence_events,
            weapons, activity_events, face_results, plate_results, is_night
        )
        return annotated

    def annotate_live_frame(self, frame: np.ndarray) -> np.ndarray:
        """Instantly composites latest AI detection overlays onto the live moving frame (<0.5ms)."""
        with self._overlay_lock:
            if self._latest_overlay_data is None:
                return self._fence.draw_zones(frame, set())
            (tracked, fence_events, weapons, activity_events,
             face_results, plate_results, is_night) = self._latest_overlay_data

        return self._annotate(
            frame, tracked, fence_events,
            weapons, activity_events, face_results, plate_results, is_night
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_tracking(self, frame: np.ndarray) -> list[TrackedObject]:
        try:
            if self._tracker_model is None:
                from ultralytics import YOLO
                self._tracker_model = YOLO("yolov8n.pt")
                self._tracker_model.to(self._device)
                logger.info("[%s] Tracker model loaded on %s.", self.camera_id, self._device)

            try:
                results = self._tracker_model.track(
                    source=frame, conf=YOLO_CONFIDENCE,
                    classes=YOLO_CLASSES, device=self._device,
                    persist=True, tracker="bytetrack.yaml", verbose=False,
                )
            except Exception as trk_err:
                # Fallback to botsort if bytetrack has solver issues
                results = self._tracker_model.track(
                    source=frame, conf=YOLO_CONFIDENCE,
                    classes=YOLO_CLASSES, device=self._device,
                    persist=True, tracker="botsort.yaml", verbose=False,
                )
            return Tracker.from_track_results(results, LABEL_OVERRIDES)
        except Exception as exc:
            logger.warning("[%s] Tracking error: %s", self.camera_id, exc)
            return []

    def _get_plate_reader(self) -> PlateReader:
        if self._plate_reader is None:
            self._plate_reader = PlateReader(device=self._device)
        return self._plate_reader

    @staticmethod
    def _crop_person(frame: np.ndarray, bbox: tuple) -> tuple:
        """Return (crop, (x1_offset, y1_offset)) for a person bbox."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = max(0,bbox[0]), max(0,bbox[1]), min(w,bbox[2]), min(h,bbox[3])
        if x2 - x1 < 20 or y2 - y1 < 20:
            return None, None
        return frame[y1:y2, x1:x2].copy(), (x1, y1)

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def _annotate(self, frame, tracked, fence_events, weapons,
                  activity_events, face_results, plate_results, is_night):
        intruder_ids = {fe.track_id for fe in fence_events}
        loiterer_ids = {ae.track_id for ae in activity_events if ae.event_type == "LOITERING"}
        runner_ids   = {ae.track_id for ae in activity_events if ae.event_type == "RUNNING"}

        # Draw fence zones
        self._fence.draw_zones(frame, {fe.zone_name for fe in fence_events})

        # Night mode badge
        if is_night:
            NightEnhancer.draw_night_indicator(frame)

        # Draw tracked objects
        for obj in tracked:
            x1, y1, x2, y2 = obj.bbox
            if obj.track_id in loiterer_ids:    color, thick = _C_LOITER, 3
            elif obj.track_id in runner_ids:    color, thick = _C_RUNNING, 3
            elif obj.track_id in intruder_ids:  color, thick = _C_INTRUSION, 3
            else:
                color = BBOX_COLORS.get(obj.label, BBOX_COLORS["Unknown"])
                thick = 2
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, thick)
            tag = f"{obj.label} #{obj.track_id} {obj.confidence:.0%}"
            self._draw_label(frame, tag, x1, y1, color)

        # Weapons (thick red)
        for w in weapons:
            x1,y1,x2,y2 = w.bbox
            cv2.rectangle(frame, (x1-2,y1-2), (x2+2,y2+2), _C_WEAPON, 4)
            self._draw_label(frame, f"!WEAPON:{w.label} {w.confidence:.0%}", x1, y1, _C_WEAPON, scale=0.55, thick=2)

        # Faces
        for f in face_results:
            x1,y1,x2,y2 = f.bbox
            color = _C_FACE_MATCH if f.matched else _C_FACE_UNK
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            tag = f"MATCH:{f.name} {f.similarity:.0%}" if f.matched else "UNKNOWN FACE"
            self._draw_label(frame, tag, x1, y1, color)

        # Plates
        for p in plate_results:
            px1,py1,px2,py2 = p.plate_bbox
            cv2.rectangle(frame, (px1,py1), (px2,py2), _C_PLATE, 2)
            self._draw_label(frame, f"PLATE:{p.plate_text}", px1, py2+2, _C_PLATE, top=False)

        # Alert banners
        h, w_px = frame.shape[:2]
        banners = []
        if weapons:
            banners.append((f"!! WEAPON: {weapons[0].label.upper()}", _C_WEAPON))
        if any(f.matched for f in face_results):
            m = next(f for f in face_results if f.matched)
            banners.append((f"!! WATCHLIST MATCH: {m.name}", _C_FACE_MATCH))
        if [ae for ae in activity_events if ae.event_type=="CROWD"]:
            ae = next(a for a in activity_events if a.event_type=="CROWD")
            banners.append((f"! CROWD: {ae.crowd_count} PERSONS in {ae.zone}", _C_CROWD))
        if fence_events:
            banners.append((f"! INTRUSION: {fence_events[0].label} in {fence_events[0].zone_name}", _C_INTRUSION))
        if [ae for ae in activity_events if ae.event_type=="LOITERING"]:
            ae = next(a for a in activity_events if a.event_type=="LOITERING")
            banners.append((f"! LOITERING {ae.duration_seconds:.0f}s in {ae.zone}", _C_LOITER))
        if plate_results:
            banners.append((f"PLATE: {plate_results[0].plate_text}", _C_PLATE))
        if is_night and tracked:
            banners.append(("[ NIGHT MOVEMENT ]", _C_NIGHT))

        for i, (text, color) in enumerate(banners[:4]):
            y0 = h - 36*(i+1)
            dim = tuple(max(0,c-80) for c in color)
            cv2.rectangle(frame, (0,y0), (w_px,y0+32), dim, -1)
            cv2.putText(frame, text, (8,y0+22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def _draw_label(frame, text, x, y, color, scale=0.45, thick=1, top=True):
        (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        h, w = frame.shape[:2]
        x = max(2, min(w - tw - 6, x))
        if top:
            if y - th - bl - 6 < 0:
                box_y1 = y
                box_y2 = min(h, y + th + bl + 6)
                text_y = y + th + 2
            else:
                box_y1 = max(0, y - th - bl - 6)
                box_y2 = y
                text_y = y - bl - 2
            cv2.rectangle(frame, (x, box_y1), (x + tw + 6, box_y2), color, -1)
            cv2.putText(frame, text, (x + 3, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thick, cv2.LINE_AA)
        else:
            y2 = min(h - 2, y + th + bl + 6)
            cv2.rectangle(frame, (x, y), (x + tw + 6, y2), color, -1)
            cv2.putText(frame, text, (x + 3, min(h - 4, y + th + 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thick, cv2.LINE_AA)
