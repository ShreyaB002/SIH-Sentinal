"""
IBVAP ? Intelligent Border Video Analytics Platform
Camera and application configuration.

Phase 2 adds: YOLO detection, ByteTrack tracking, virtual fence zones,
event management, WebSocket alerts, and SQLite event logging.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
VIDEO_DIR: Path = PROJECT_ROOT / "data" / "videos"
DB_PATH: Path = PROJECT_ROOT / "data" / "events.db"

# ---------------------------------------------------------------------------
# Camera definitions
# ---------------------------------------------------------------------------
#
# type = "file"  ? local video file (loops at EOF)
# type = "rtsp"  ? RTSP/HTTP stream (reconnects on failure)
#
# To switch to a real camera:
#   "source": "rtsp://user:pass@192.168.1.x:554/stream",
#   "type":   "rtsp",

CAMERAS: dict[str, dict] = {
    "cam_01": {
        "name": "Camera 01",
        "source": "http://192.0.0.4:8080/video",
        "type": "rtsp",
    },
    "cam_02": {
        "name": "Camera 02",
        "source": "http://192.168.1.8:8080/video",
        "type": "rtsp",
    },
    "cam_03": {
        "name": "Camera 03",
        "source": "http://192.168.1.6:8080/video",
        "type": "rtsp",
    },
    "cam_04": {
        "name": "Camera 04",
        "source": "http://192.168.1.9:8080/video",
        "type": "rtsp",
    },
    "cam_05": {
        "name": "Camera 05",
        "source": "http://192.168.1.10:8080/video",
        "type": "rtsp",
    },
    "cam_06": {
        "name": "Camera 06",
        "source": "http://192.168.1.11:8080/video",
        "type": "rtsp",
    },
}

# ---------------------------------------------------------------------------
# Streaming parameters
# ---------------------------------------------------------------------------

MJPEG_FPS: int = 25
JPEG_QUALITY: int = 80
RTSP_RECONNECT_DELAY: float = 3.0

# ---------------------------------------------------------------------------
# AI / Detection  (Phase 2)
# ---------------------------------------------------------------------------

# Set False to run Phase 1 mode (no AI, no overhead).
AI_ENABLED: bool = True

# YOLOv8 model name ? downloaded automatically on first run into models/
# Options by speed/accuracy: yolov8n (nano) < yolov8s < yolov8m < yolov8l
YOLO_MODEL: str = "yolov8n.pt"

# Minimum confidence to keep a detection (0.0?1.0)
YOLO_CONFIDENCE: float = 0.45

# COCO class IDs to detect. Uncomment/add as needed.
# Full list: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml
YOLO_CLASSES: list[int] = [
    0,   # person
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
]

# Friendly label overrides (COCO default names are fine, but customise here)
LABEL_OVERRIDES: dict[int, str] = {
    0: "Person",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
}

# Run detection every Nth frame (1 = every frame, 3 = every 3rd frame).
# Higher values reduce GPU load; annotations persist between detections.
DETECT_EVERY_N_FRAMES: int = 2

# Bounding box colours per label (BGR)
BBOX_COLORS: dict[str, tuple] = {
    "Person":     (0,   200, 0),    # green
    "Car":        (200, 100, 0),    # blue
    "Motorcycle": (0,   165, 255),  # orange
    "Bus":        (128, 0,   128),  # purple
    "Truck":      (0,   0,   200),  # red
    "Unknown":    (150, 150, 150),  # grey
}

# ---------------------------------------------------------------------------
# Virtual fence zones  (Phase 2)
# ---------------------------------------------------------------------------
#
# Each entry is a list of named polygon zones for that camera.
# Coordinates are pixel (x, y) in the camera's native resolution.
# Use a tool like https://www.image-map.net/ or the IBVAP zone editor
# (Phase 3) to draw polygons.
#
# TIP: For the synthetic test video (640x360), the example zones below
#      cover meaningful areas of the frame so you will see alerts.

ZONES: dict[str, list[dict]] = {
    "cam_01": [
        {
            "name": "Zone A",
            "polygon": [(80, 80), (560, 80), (560, 280), (80, 280)],
        },
    ],
    "cam_02": [
        {
            "name": "Zone A",
            "polygon": [(80, 80), (560, 80), (560, 280), (80, 280)],
        },
    ],
    "cam_03": [
        {
            "name": "Entry Point",
            "polygon": [(100, 100), (540, 100), (540, 380), (100, 380)],
        },
    ],
    "cam_04": [
        {
            "name": "Zone A",
            "polygon": [(80, 80), (560, 80), (560, 280), (80, 280)],
        },
    ],
    "cam_05": [
        {
            "name": "Zone A",
            "polygon": [(80, 80), (560, 80), (560, 280), (80, 280)],
        },
    ],
    "cam_06": [
        {
            "name": "Zone A",
            "polygon": [(80, 80), (560, 80), (560, 280), (80, 280)],
        },
    ],
}

# ---------------------------------------------------------------------------
# Event manager  (Phase 2)
# ---------------------------------------------------------------------------

# Suppress repeat alerts for the same (camera, track_id, zone) within this
# many seconds. Prevents alert flooding for a person standing in a zone.
EVENT_COOLDOWN: float = 5.0

# ---------------------------------------------------------------------------
# Weapons Detection  (Phase 3)
# ---------------------------------------------------------------------------

WEAPONS_ENABLED: bool = True
WEAPONS_MODEL: str = "yolov8l-worldv2.pt"  # large = best accuracy on GPU
WEAPONS_CLASSES: list[str] = [
    "handgun", "pistol", "revolver",
    "rifle", "assault rifle", "shotgun",
    "knife", "machete", "blade", "grenade",
]
WEAPONS_CONFIDENCE: float = 0.28  # lower than YOLO — open-vocab models score lower

# ---------------------------------------------------------------------------
# Suspicious Activity  (Phase 3)
# ---------------------------------------------------------------------------

LOITER_SECONDS: float = 5.0      # demo-friendly; use 30-60s in production
RUNNING_SPEED: float = 22.0      # centroid px/frame above this = running
CROWD_THRESHOLD: int = 3         # persons in zone at once before CROWD fires
ACTIVITY_COOLDOWN: float = 15.0  # seconds between repeated activity alerts

# ---------------------------------------------------------------------------
# API / Server
# ---------------------------------------------------------------------------

APP_TITLE: str = "IBVAP — Intelligent Border Video Analytics Platform"
APP_VERSION: str = "3.0.0-phase3"

# ---------------------------------------------------------------------------
# Night Detection  (Phase 4)
# ---------------------------------------------------------------------------

NIGHT_BRIGHTNESS_THRESHOLD: float = 80.0  # LAB-L mean below this = night
NIGHT_CLAHE_CLIP: float = 3.0
NIGHT_DENOISE: bool = True

# ---------------------------------------------------------------------------
# Face Recognition  (Phase 4)
# ---------------------------------------------------------------------------

FRS_ENABLED: bool = True
FRS_MODEL: str = "buffalo_l"               # InsightFace large model
FRS_DET_SIZE: tuple = (640, 640)
FRS_MATCH_THRESHOLD: float = 0.40         # cosine similarity threshold

# ---------------------------------------------------------------------------
# ANPR  (Phase 4)
# ---------------------------------------------------------------------------

ANPR_ENABLED: bool = True
ANPR_MIN_CONFIDENCE: float = 0.40         # minimum OCR confidence to accept plate

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WATCHLIST_DB_PATH = PROJECT_ROOT / "data" / "watchlist.db"
WATCHLIST_IMAGE_DIR = PROJECT_ROOT / "data" / "watchlist_images"
