"""
IBVAP ? FastAPI application entry point (Phase 2).

Changes from Phase 1
---------------------
* StreamManager.start_all() now receives the running asyncio event loop
  so the EventManager can call_soon_threadsafe() from camera threads.
* WebSocket router (/ws/alerts) registered.
* Events router (/api/events) registered.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import APP_TITLE, APP_VERSION
from backend.core.stream_manager import StreamManager
from backend.routers.video import router as video_router
from backend.routers.ws import router as ws_router
from backend.routers.events import router as events_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("IBVAP starting up (Phase 2)...")
    loop = asyncio.get_running_loop()
    manager = StreamManager()
    manager.start_all(loop=loop)
    app.state.stream_manager = manager
    logger.info("IBVAP ready. Dashboard: http://127.0.0.1:8000/")

    yield

    logger.info("IBVAP shutting down...")
    manager.stop_all()
    logger.info("IBVAP shutdown complete.")


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Phase 2: AI analytics pipeline ? YOLO detection, ByteTrack tracking, "
        "virtual fence intrusion detection, WebSocket alerts, SQLite event log."
    ),
    lifespan=lifespan,
)

# API routes
app.include_router(video_router, prefix="/api", tags=["video"])
app.include_router(events_router, prefix="/api", tags=["events"])
app.include_router(ws_router, tags=["alerts"])

# Serve frontend
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend directory not found: %s", _FRONTEND_DIR)
