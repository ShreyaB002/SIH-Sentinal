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
        "name": "Phone Camera Feed",
        "source": "http://192.168.1.15:8080/video",
        "type": "rtsp", # or "usb" depending on OpenCV stream handling
    },
    "cam_02": {
        "name": "BOP Sector 2 (Border Road)",
        "source": str(VIDEO_DIR / "test_video.mp4"),
        "type": "file",
    },
    "cam_03": {
        "name": "BOP Sector 3 (Check Post Alpha)",
        "source": str(VIDEO_DIR / "test_video.mp4"),
        "type": "file",
    },
    "cam_04": {
        "name": "BOP Sector 4 (Fence Line)",
        "source": str(VIDEO_DIR / "test_video.mp4"),
        "type": "file",
    },
    "cam_05": {
        "name": "Check Post Bravo (Ingress)",
        "source": str(VIDEO_DIR / "test_video.mp4"),
        "type": "file",
    },
    "cam_06": {
        "name": "BOP Sector 6 (Watchtower)",
        "source": str(VIDEO_DIR / "test_video.mp4"),
        "type": "file",
    },
}

# ---------------------------------------------------------------------------
# Streaming & Frame Compression Parameters
# ---------------------------------------------------------------------------

MJPEG_FPS: int = 25
STREAM_WIDTH: int = 640
STREAM_HEIGHT: int = 360
JPEG_QUALITY: int = 65                # Optimized JPEG compression for low latency
RTSP_RECONNECT_DELAY: float = 3.0

# ---------------------------------------------------------------------------
# AI / Detection  (Phase 2)
# ---------------------------------------------------------------------------

# Set False to run Phase 1 mode (no AI, no overhead).
AI_ENABLED: bool = True

# ---------------------------------------------------------------------------
# Primary Object Detector (Phase 3 — YOLO26 & High-Accuracy Suite)
# ---------------------------------------------------------------------------
# Options: yolo26x, yolo26l, yolo26m, yolo11x, yolo11m, yolov8n
DETECTION_MODEL: str = "yolo26m.pt"
DETECTION_DEVICE: str = "auto"        # "auto", "cuda", "cpu"
DETECTION_FALLBACKS: list[str] = ["yolo26l.pt", "yolo26m.pt", "yolo11m.pt", "yolov8n.pt"]

YOLO_MODEL: str = DETECTION_MODEL
YOLO_CONFIDENCE: float = 0.28

# COCO class IDs to detect (Person, Vehicles)
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

# Run detection every frame for instant real-time tracking
DETECT_EVERY_N_FRAMES: int = 1

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
EVENT_COOLDOWN: float = 10.0
INTRUSION_MIN_CONFIDENCE: float = 0.55

# ---------------------------------------------------------------------------
# Weapons / Arms Detection (Disabled per Official SIH Border CCTV Problem Statement)
# ---------------------------------------------------------------------------

WEAPONS_ENABLED: bool = False
WEAPONS_MODEL: str = "models/threat_detector.pt"
WEAPONS_CLASSES: list[str] = []
WEAPONS_CONFIDENCE: float = 0.99
WEAPONS_ALERT_CONFIDENCE: float = 0.99

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

NIGHT_BRIGHTNESS_THRESHOLD: float = 38.0  # LAB-L mean below 38 = dark/night mode
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
# Person Re-Identification  (Phase 5 — OSNet Cross-Camera Re-ID)
# ---------------------------------------------------------------------------

REID_ENABLED: bool = True
REID_MODEL: str = "osnet_x1_0"
REID_SIMILARITY_THRESHOLD: float = 0.70    # cosine similarity threshold for match
REID_GALLERY_SIZE: int = 500              # maximum active identity gallery size
REID_EXPIRATION_SECONDS: float = 3600.0   # 1 hour TTL for gallery entries
REID_INTERVAL_FRAMES: int = 8             # extract Re-ID embedding every Nth frame

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WATCHLIST_DB_PATH = PROJECT_ROOT / "data" / "watchlist.db"
WATCHLIST_IMAGE_DIR = PROJECT_ROOT / "data" / "watchlist_images"
