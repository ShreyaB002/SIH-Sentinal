# IBVAP — Intelligent Border Video Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%2012.4-orange.svg)](https://pytorch.org/)
[![Ultralytics](https://img.shields.io/badge/Ultralytics-YOLO26%20%2F%20YOLOv8-yellow.svg)](https://docs.ultralytics.com/)
[![SIH](https://img.shields.io/badge/SIH-Border%20Surveillance-red.svg)](#)

> **AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure**

---

## 🎯 Problem Overview

Border security forces deploy CCTV cameras at **Border Out Posts (BOPs), check posts, border roads, and strategic perimeters**. However, conventional CCTV systems only offer passive video recording and require continuous, exhausting human observation. 

Advanced capabilities such as **Facial Recognition Systems (FRS), Automatic Number Plate Recognition (ANPR), intrusion detection, and object tracking** traditionally demand costly, specialized edge cameras and proprietary hardware.

### 🛡️ The Solution: IBVAP
**IBVAP** is an entirely software-defined surveillance platform that transforms **existing legacy IP cameras (RTSP/HTTP)** into an intelligent surveillance network without requiring hardware upgrades. It runs on standard edge/server hardware with GPU acceleration, delivering actionable, real-time intelligence for control room operators.

---

## 🚀 Specialist-Model Architecture & Capabilities

| Surveillance Capability | Specialist Model / Engine | Architecture & Description |
| :--- | :--- | :--- |
| **Centralized Model Registry** | `ModelManager` Singleton | Shared GPU singleton per model across all 6 streams with VRAM tracking & auto-fallback. |
| **Object Detection & Classification** | `YOLO26` / `YOLOv8` Abstraction | High-accuracy detection for Persons, Cars, Trucks, Buses, and Motorcycles. |
| **Multi-Object Tracking & Kinematics** | `ByteTrack` Kinematics Engine | Persistent IDs, centroid trajectory history, entry/exit timestamps, and velocity estimation. |
| **Cross-Camera Person Re-ID** | `OSNet` (512-d Embedding) | Identifies same suspect across different cameras (`cam_01 Track #17` $\rightarrow$ `cam_04 Track #42`). |
| **Facial Recognition System (FRS)** | `InsightFace` (ArcFace `buffalo_l`) | 512-d facial embedding extraction with cosine similarity matching against target watchlist. |
| **Target Watchlist Management** | Integrated Web UI + SQLite | Control room personnel can upload suspect face photos and names directly via browser. |
| **Automatic Number Plate Recognition** | GPU `EasyOCR` + `PP-OCR` + Regex | Localizes vehicle plates, normalizes Indian registration syntax (`RJ14CY0002`), and checkpoint scan. |
| **Weapons & Threat Detection** | Fine-Tuned Threat Model + YOLO-World | Dedicated detection of firearms (pistols, rifles) and melee weapons (knives, explosives). |
| **Low-Light / Night Enhancement** | `LowLightProcessor` (Retinex / CLAHE) | Luminance assessment in LAB space and adaptive enhancement for dark scenes. |
| **Virtual Fence Intrusion** | Point-in-Polygon Engine | Polygon exclusion zones per camera; triggers alarms upon boundary breaches. |
| **Suspicious Activity (Loitering & Speed)** | Dwell-Time & Velocity Monitor | Flags individuals lingering in zones (>5s) or running at high velocity (>22 px/frame). |
| **Event Correlation & Risk Engine** | `EventCorrelationEngine` | Multi-signal synthesis (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with explainable evidence trails. |
| **Camera Health Telemetry** | `CameraStream` Health Monitor | Tracks FPS, frame age, latency, reconnect counters, and operational drop events. |
| **Real-Time C2 Dashboard** | Responsive Matrix + WebSockets | 6-camera live grid with instant red threat pulsing, visual overlays, and WebSocket alert feed. |
| **Audit & Forensic Logging** | Relational SQLite (`events.db`) | Complete incident history with timestamps, confidence scores, bounding boxes, and camera IDs. |

---

## ??? System Architecture

```
                       EXISTING BORDER CCTV (RTSP / HTTP / IP CAMERAS)
                                              ?
                                              ?
                                 [ CameraStream Threadpool ]
                                              ?
                                              ?
                                 [ FrameProcessing Pipeline ]
                                              ?
            ?????????????????????????????????????????????????????????????????????
            ?                                                                   ?
            ?                                                                   ?
   [ Night Vision Enhancer ]                                           [ Day/Standard Feed ]
   (LAB L-channel CLAHE)                                                        ?
            ?                                                                   ?
            ?????????????????????????????????????????????????????????????????????
                                              ?
                                              ?
                                   [ YOLOv8 + ByteTrack ]
                                 (People & Vehicle Tracking)
                                              ?
                    ?????????????????????????????????????????????????????
                    ?                         ?                         ?
                    ?                         ?                         ?
             [ Virtual Fence ]       [ Weapons Detector ]      [ Activity Analyzer ]
             (Point-in-Polygon)      (YOLO-World Large)        (Loitering / Speed / Crowd)
                    ?                         ?                         ?
                    ?????????????????????????????????????????????????????
                                              ?
                                              ?
                                  [ Sub-Crop Analyzers ]
                                    ??? Person Crop  ? [ FaceRecognizer (FRS) ]
                                    ??? Vehicle Crop ? [ PlateReader (ANPR) ]
                                              ?
                                              ?
                                 [ Unified Frame Annotator ]
                               (Boxes, Zones, Badges, Banners)
                                              ?
                                              ?
                                    [ EventManager Hub ]
                                              ?
                           ???????????????????????????????????????
                           ?                                     ?
                [ SQLite Audit Store ]                 [ WebSocket Dispatcher ]
                (data/events.db)                       (ws://localhost:8000/ws/alerts)
                                                                 ?
                                                                 ?
                                                    [ C2 Operations Dashboard ]
                                                    - 6-Camera Live Matrix Grid
                                                    - Real-Time Alert Log Sidebar
                                                    - FRS Watchlist Management Modal
                                                    - Pulsing Red Threat Indicators
```

---

## ?? Hardware & Software Requirements

* **OS:** Windows 10/11 or Ubuntu 20.04/22.04 LTS
* **Python:** 3.10 or 3.11
* **GPU:** NVIDIA GPU with CUDA support (e.g., RTX 2050 / RTX 3060+ recommended for real-time 6-stream inference)
* **Cameras:** Any standard RTSP / HTTP IP surveillance camera or video files

---

## ? Quickstart Guide

### 1. Clone Repository
```bash
git clone https://github.com/ShreyaB002/SIH-Sentinal.git
cd SIH-Sentinal
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install insightface onnxruntime paddleocr paddlepaddle python-multipart
```

### 4. Configure Cameras (Optional)
Edit `backend/config.py` to add your live IP camera stream URLs (RTSP/HTTP):
```python
CAMERAS = {
    "cam_01": {"name": "BOP North Perimeter", "source": "rtsp://192.168.1.50:554/live", "type": "rtsp"},
    "cam_02": {"name": "Check Post Road", "source": "http://192.168.1.6:8080/video", "type": "rtsp"},
    # ... up to 6+ cameras
}
```

### 5. Launch the Platform
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open your browser and navigate to **`http://localhost:8000/`**.

---

## ?? API & Integration Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web Operations Command & Control Dashboard |
| `GET` | `/api/cameras` | Status of all configured camera streams (ONLINE, CONNECTING, OFFLINE) |
| `GET` | `/api/stream/{camera_id}` | Live MJPEG video stream with real-time AI bounding boxes and overlays |
| `GET` | `/api/events` | Query stored security events from SQLite (?camera_id=, ?limit=) |
| `GET` | `/api/watchlist` | List all registered target faces in the FRS watchlist |
| `POST` | `/api/watchlist/add` | Register a new target face (Multipart Form: name + image file) |
| `DELETE`| `/api/watchlist/{id}` | Remove a target from the watchlist |
| `WS` | `/ws/alerts` | Real-time bi-directional WebSocket feed broadcasting security alerts |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation |

---

## ?? Directory Structure

```
SIH-Sentinal/
??? backend/
?   ??? config.py                 # Platform settings, camera definitions & thresholds
?   ??? main.py                   # FastAPI application entry point & router mounting
?   ??? core/
?   ?   ??? activity.py           # Loitering, running & crowd formation behavioral rules
?   ?   ??? anpr.py               # Automatic Number Plate Recognition (PaddleOCR)
?   ?   ??? camera_stream.py      # Threaded frame ingestion & auto-reconnect logic
?   ?   ??? database.py           # Thread-safe SQLite event store wrapper
?   ?   ??? detector.py           # YOLOv8 object detection wrapper
?   ?   ??? face_recognition.py   # InsightFace ArcFace biometric face recognizer
?   ?   ??? fence.py              # Point-in-Polygon virtual fence tripwire engine
?   ?   ??? night.py              # CLAHE adaptive low-light night enhancer
?   ?   ??? pipeline.py           # Per-camera master AI orchestration pipeline
?   ?   ??? stream_manager.py     # Stream supervisor & lifecycle manager
?   ?   ??? tracker.py            # ByteTrack object tracking wrapper
?   ?   ??? watchlist.py          # Watchlist SQLite vector store
?   ?   ??? weapons_detector.py   # YOLO-World open-vocabulary threat detector
?   ??? routers/
?       ??? events.py             # Event query REST endpoints
?       ??? video.py              # Camera status & MJPEG streaming endpoints
?       ??? watchlist.py          # Watchlist CRUD REST endpoints
?       ??? ws.py                 # Real-time WebSocket alert push router
??? frontend/
?   ??? index.html                # C2 Command & Control operational dashboard
?   ??? css/
?   ?   ??? dashboard.css         # Dark tactical theme, tile glows & sidebar styling
?   ??? js/
?       ??? eventlog.js           # Real-time alert card renderer & event manager
?       ??? grid.js               # Multi-camera matrix renderer & status polling
?       ??? watchlist.js          # Target face registration & modal manager
?       ??? websocket.js          # Auto-reconnecting WebSocket client
??? data/
?   ??? events.db                 # SQLite database for forensic event logging
?   ??? videos/
?       ??? test_cctv.mp4         # Sample video stream for offline demonstration
??? requirements.txt              # Core project dependencies
??? README.md                     # Project documentation & SIH overview
```

---

## ??? License & Submission Notice
Developed for the **Smart India Hackathon (SIH)**.  
*Problem Statement: AI-Based Intelligent Video Analytics Platform for Border Surveillance using Existing CCTV Infrastructure.*
