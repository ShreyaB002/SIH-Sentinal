# IBVAP Architecture — Phase 1

## 1. System Overview

```
                VIDEO SOURCE
                     │
           ┌─────────┴─────────┐
           │                   │
      Video File             RTSP
      (current)           (future)
           │                   │
           └─────────┬─────────┘
                     ↓
               CameraStream
             (background thread)
                     ↓
               Latest Frame
             (thread-safe buffer)
                     ↓
               StreamManager
               (owns all streams)
                     ↓
                  FastAPI
               (async HTTP)
                     ↓
               MJPEG stream
               (HTTP boundary)
                     ↓
                Dashboard
              (browser <img>)
```

---

## 2. Component Descriptions

### `CameraStream` (`backend/core/camera_stream.py`)

The fundamental building block of IBVAP's video ingestion layer.

**Design principles:**
- One `CameraStream` instance per camera source.
- One dedicated `threading.Thread` per stream — never the async event loop.
- Stores only the **latest** frame; older frames are discarded immediately.
- Thread-safe frame access via `threading.Lock`.
- Completely source-agnostic from the perspective of callers (they only call `get_frame()`).

**File source behaviour:**
```
open VideoCapture(path)
    ↓
read() → frame available?
    ├── YES → store as latest frame → read next
    └── NO (EOF) → seek to frame 0 → continue
```

**RTSP source behaviour:**
```
open VideoCapture(rtsp://...)
    ├── success → mark ONLINE → read loop
    └── failure → mark OFFLINE → wait → retry
```

**State machine:**
```
CONNECTING → ONLINE   (source opened successfully)
ONLINE     → OFFLINE  (read failure on RTSP)
OFFLINE    → CONNECTING (reconnect attempt)
```

### `StreamManager` (`backend/core/stream_manager.py`)

Owns and coordinates all `CameraStream` objects.

```
StreamManager
    ├── CameraStream cam_01
    ├── CameraStream cam_02
    ├── CameraStream cam_03
    ├── CameraStream cam_04
    ├── CameraStream cam_05
    └── CameraStream cam_06
```

**Public interface:**
- `start_all()` — create and start all configured streams
- `stop_all()` — stop all streams cleanly
- `get_frame(camera_id)` — get latest frame for a camera
- `get_statuses()` — return status list for the API

### FastAPI Application (`backend/main.py`)

- Uses `lifespan` context manager for startup/shutdown.
- Creates `StreamManager` and attaches it to `app.state`.
- Camera threads are started in `lifespan` → `startup`, stopped in `lifespan` → `shutdown`.
- API threads never interact with `cv2.VideoCapture` directly.
- Frontend served as `StaticFiles` at `/`.

### MJPEG Router (`backend/routers/video.py`)

- `GET /api/stream/{camera_id}` → `multipart/x-mixed-replace` response.
- Each boundary part contains a JPEG-encoded frame.
- Frame rate limited to `MJPEG_FPS` (configurable in `config.py`).
- Browser disconnection detected via `request.is_disconnected()`.
- JPEG encoding offloaded to `asyncio.get_event_loop().run_in_executor()` to avoid blocking the event loop.

### Frontend (`frontend/`)

- Pure HTML + CSS + Vanilla JavaScript (no framework, no build step).
- `grid.js` polls `GET /api/cameras` every 5 seconds for status updates.
- MJPEG feeds displayed via `<img src="/api/stream/{id}">` — browser handles the multipart stream natively.
- Tile click → expand to full view.
- "Back to Grid" → restore 3×2 grid.
- Updates status indicators in place without re-requesting streams.

---

## 3. Threading Model

```
Main Thread (Python / Uvicorn)
│
├── asyncio event loop (FastAPI)
│   ├── MJPEG generator coroutine (cam_01)
│   ├── MJPEG generator coroutine (cam_02)
│   └── ...
│
├── camera thread: cam_01 (daemon)
├── camera thread: cam_02 (daemon)
├── camera thread: cam_03 (daemon)
├── camera thread: cam_04 (daemon)
├── camera thread: cam_05 (daemon)
└── camera thread: cam_06 (daemon)
```

Camera threads are daemon threads, so they automatically exit when the main process exits, even if `stop_all()` is not called (though proper cleanup is always attempted).

---

## 4. Frame Flow

```
cv2.VideoCapture.read()
        ↓
raw BGR frame (numpy array)
        ↓
threading.Lock.acquire()
        ↓
self._frame = frame          ← only latest stored
        ↓
threading.Lock.release()

                    ...

MJPEG endpoint
        ↓
stream.get_frame()
        ↓
threading.Lock.acquire()
        ↓
frame.copy()                 ← caller gets a safe copy
        ↓
threading.Lock.release()
        ↓
cv2.imencode('.jpg', frame)  ← JPEG encoding (executor thread)
        ↓
multipart boundary response
        ↓
browser
```

---

## 5. Configuration (`backend/config.py`)

All camera definitions and tunable parameters live in `config.py`.

```python
CAMERAS = {
    "cam_01": {"name": "...", "source": "...", "type": "file|rtsp"},
}

MJPEG_FPS = 25
JPEG_QUALITY = 80
RTSP_RECONNECT_DELAY = 3.0
```

Switching from development (video file) to production (RTSP) requires only a change to `CAMERAS["cam_01"]["source"]` and `CAMERAS["cam_01"]["type"]`.

---

## 6. Phase 2 Extension Points

Phase 2 will insert an AI pipeline between the raw frame and the MJPEG encoder:

```python
# CameraStream.get_frame() — Phase 2 extension

def get_frame(self):
    with self._frame_lock:
        raw = self._frame.copy()

    # ---- Phase 2 insertion point ----
    annotated = self._pipeline.process(raw)
    # ---------------------------------

    return annotated
```

The `_pipeline` will wrap:
- YOLO detector
- Object tracker
- Virtual fence checker
- Bounding box renderer

From the MJPEG endpoint's perspective, `get_frame()` still returns a numpy array — no changes needed at the API layer.

**WebSocket events** (Phase 3) will be emitted from the `EventManager` independently of the MJPEG stream:

```
CameraStream
      ↓
Frame Pipeline (Phase 2)
      ↓
EventManager (Phase 3)
      ├── WebSocket → Dashboard (alert glow)
      └── Database → Event log
```

---

## 7. API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cameras` | GET | Camera list + statuses |
| `/api/stream/{id}` | GET | MJPEG live stream |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc UI |
| `/` | GET | Dashboard |

---

## 8. Deployment (Development)

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

For production (Phase 3+), consider:
- `--workers 1` (camera threads are shared state — do not fork)
- Nginx reverse proxy for TLS termination
- Systemd service for automatic restart
