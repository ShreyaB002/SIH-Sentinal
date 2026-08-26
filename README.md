# IBVAP — Intelligent Border Video Analytics Platform

**Phase 1: Video Ingestion and Monitoring Foundation**

> SIH Problem: AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure

---

## Overview

IBVAP is a prototype surveillance platform that ingests video from IP CCTV cameras and applies AI-powered analytics.  
**Phase 1** establishes the video ingestion pipeline and a six-camera command-and-control dashboard.  
AI detection, tracking, and event systems are planned for Phase 2 and beyond.

---

## Phase 1 Scope

| Feature | Status |
|---------|--------|
| Local video file simulation of CCTV feed | ✅ Implemented |
| RTSP-ready architecture | ✅ Designed (switchable via config) |
| Background threaded frame reader per camera | ✅ Implemented |
| MJPEG HTTP streaming | ✅ Implemented |
| Six-camera dashboard | ✅ Implemented |
| Camera status API (`/api/cameras`) | ✅ Implemented |
| Expand-on-click tile interaction | ✅ Implemented |
| OFFLINE resilience (one bad camera won't crash others) | ✅ Implemented |
| YOLO / object detection | ⏳ Phase 2 |
| Face recognition / ANPR | ⏳ Phase 2 |
| Virtual fence intrusion detection | ⏳ Phase 2 |
| WebSocket event alerts | ⏳ Phase 3 |
| Database event logging | ⏳ Phase 3 |

---

## Project Structure

```
ibvap/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, startup/shutdown lifecycle
│   ├── config.py        # Camera definitions and app settings
│   ├── core/
│   │   ├── __init__.py
│   │   ├── camera_stream.py   # Threaded frame reader (CameraStream)
│   │   └── stream_manager.py  # Manages all CameraStream instances
│   └── routers/
│       ├── __init__.py
│       └── video.py     # /api/stream/{id} and /api/cameras
│
├── data/
│   └── videos/
│       └── test_cctv.mp4   ← Place your test video here
│
├── frontend/
│   ├── index.html       # Six-camera C2 dashboard
│   ├── css/
│   │   └── dashboard.css
│   └── js/
│       └── grid.js
│
├── docs/
│   └── architecture.md
│
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Create a virtual environment

```bash
cd ibvap
python -m venv .venv
```

**Windows:**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Test Video Setup

IBVAP does **not** include a test video file (copyright / size reasons).

Place any `.mp4` video file here:

```
ibvap/data/videos/test_cctv.mp4
```

You can use any video. Suggestions:

- Download a free stock video from [Pexels](https://www.pexels.com/videos/) or [Pixabay](https://pixabay.com/videos/).
- Use `ffmpeg` to record a short clip from your own camera.
- Download a public CCTV sample from academic datasets.

> **The file must be named `test_cctv.mp4`** (or update `config.py` to match your filename).

---

## Running the Application

```bash
# From the ibvap/ directory, with .venv activated
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser:

```
http://localhost:8000/
```

---

## Camera Configuration

Edit `backend/config.py` to define cameras.

### Current (development — video file)

```python
CAMERAS = {
    "cam_01": {
        "name": "Camera 01",
        "source": "data/videos/test_cctv.mp4",
        "type": "file",
    },
}
```

### Future (production — real RTSP camera)

```python
CAMERAS = {
    "cam_01": {
        "name": "Border Camera 01",
        "source": "rtsp://username:password@192.168.1.50:554/stream",
        "type": "rtsp",
    },
}
```

No changes to the pipeline code are required when switching between file and RTSP sources.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cameras` | List cameras and their statuses |
| `GET` | `/api/stream/{camera_id}` | MJPEG live stream for a camera |
| `GET` | `/docs` | FastAPI Swagger UI |
| `GET` | `/` | Dashboard (served as static HTML) |

### Example: Camera status

```
GET /api/cameras

[
    {"id": "cam_01", "name": "Camera 01", "status": "ONLINE"},
    {"id": "cam_02", "name": "Camera 02", "status": "OFFLINE"}
]
```

### Example: MJPEG stream

Embed directly in HTML:

```html
<img src="/api/stream/cam_01" />
```

---

## Dashboard Usage

- The main view shows **six camera tiles** in a 3×2 grid.
- Each tile shows:
  - Camera name
  - Live MJPEG feed (or OFFLINE placeholder)
  - Status indicator (● ONLINE / ● OFFLINE / ● CONNECTING)
- **Click any tile** to expand that camera to full view.
- Click **← Back to Grid** to return to the six-camera grid.

---

## Known Limitations (Phase 1)

- No AI analytics (detection, tracking, recognition).
- No WebSocket alerts.
- No database logging.
- No authentication.
- MJPEG is less bandwidth-efficient than H.264/HLS but simpler for prototyping.
- Multiple browser clients for the same camera will each receive the MJPEG stream independently (acceptable for Phase 1).

---

## What Phase 2 Should Implement

1. **YOLO integration** — object detection on each frame.
2. **Object tracking** — assign consistent IDs across frames.
3. **Specialized modules** — face recognition, ANPR, virtual fence.
4. **Event manager** — classify and record detected events.
5. **WebSocket server** — push events to connected dashboard clients.
6. **Alert UI** — camera tile glow/pulse on event detection.
7. **SQLite / PostgreSQL logging** — persistent event records.
8. **Event log sidebar** — scrollable real-time event feed in dashboard.
