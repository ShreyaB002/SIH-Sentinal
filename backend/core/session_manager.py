"""
session_manager.py - Real-Time Multi-Device Session & State Synchronization Manager for IBVAP.

Features
--------
1. Session Lifecycle:
   - Create session on device connect (assigns session_id, device_name, device_ip).
   - Heartbeat / keepalive tracking (auto-terminates stale sessions after timeout).
   - Explicit termination on logout / tab close.

2. State Synchronization Across Connected End Devices:
   - Broadcasts user actions (Camera Expand, Alert Acknowledge, Watchlist Sync, Grid Layout)
     to all active peer sessions so both end devices operate in lockstep.
   - Maintains a shared C2 operational state (active alert acknowledgments, selected camera).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_TIMEOUT_SECONDS = 45.0  # Expire if no heartbeat received


@dataclass
class DeviceSession:
    """Represents an active connected control room / mobile device session."""
    session_id: str
    device_name: str
    ip_address: str
    created_at: str
    last_heartbeat: float = field(default_factory=time.monotonic)
    active_camera: Optional[str] = None
    role: str = "Operator"   # "Operator" | "Commander" | "Viewer"


class SessionManager:
    """Manages active device sessions and real-time state synchronization."""

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop
        self._sessions: dict[str, DeviceSession] = {}
        self._queues: dict[str, asyncio.Queue] = {}   # session_id -> WebSocket queue
        self._shared_state: dict = {
            "expanded_camera": None,
            "acknowledged_events": set(),
            "active_alert_level": "NORMAL",
        }
        logger.info("SessionManager initialised for multi-device synchronization.")

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        device_name: str = "Control_Station",
        ip_address: str = "127.0.0.1",
        role: str = "Operator",
    ) -> DeviceSession:
        """Create and register a new device session."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        session = DeviceSession(
            session_id=session_id,
            device_name=device_name,
            ip_address=ip_address,
            created_at=now_iso,
            role=role,
        )
        self._sessions[session_id] = session
        q = asyncio.Queue(maxsize=128)
        self._queues[session_id] = q

        logger.info("Session CREATED: %s (%s @ %s) [%d active sessions]",
                    session_id, device_name, ip_address, len(self._sessions))

        # Notify peers about new device
        self.broadcast_sync("DEVICE_CONNECTED", {
            "session_id": session_id,
            "device_name": device_name,
            "total_active": len(self._sessions),
        }, exclude_session=session_id)

        return session

    def register_queue(self, session_id: str) -> asyncio.Queue:
        """Get or create the WebSocket message queue for this session."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=128)
        return self._queues[session_id]

    def heartbeat(self, session_id: str) -> bool:
        """Refresh session heartbeat. Returns False if session not found."""
        if session_id in self._sessions:
            self._sessions[session_id].last_heartbeat = time.monotonic()
            return True
        return False

    def terminate_session(self, session_id: str) -> bool:
        """Terminate and clean up an active session."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            self._queues.pop(session_id, None)

            logger.info("Session TERMINATED: %s (%s) [%d active sessions remaining]",
                        session_id, session.device_name, len(self._sessions))

            # Broadcast device disconnect to peer devices
            self.broadcast_sync("DEVICE_DISCONNECTED", {
                "session_id": session_id,
                "device_name": session.device_name,
                "total_active": len(self._sessions),
            })
            return True
        return False

    def list_sessions(self) -> list[dict]:
        """Return metadata for all active sessions."""
        self._cleanup_stale()
        return [
            {
                "session_id": s.session_id,
                "device_name": s.device_name,
                "ip_address": s.ip_address,
                "created_at": s.created_at,
                "role": s.role,
                "active_camera": s.active_camera,
            }
            for s in self._sessions.values()
        ]

    # ------------------------------------------------------------------
    # State Synchronization across End Devices
    # ------------------------------------------------------------------

    def update_sync_state(self, session_id: str, action: str, payload: dict) -> None:
        """Apply state change from one device and broadcast to all peer devices."""
        self.heartbeat(session_id)

        if action == "EXPAND_CAMERA":
            cam_id = payload.get("camera_id")
            self._shared_state["expanded_camera"] = cam_id
            if session_id in self._sessions:
                self._sessions[session_id].active_camera = cam_id
            self.broadcast_sync("SYNC_EXPAND_CAMERA", {"camera_id": cam_id, "by": session_id}, exclude_session=session_id)

        elif action == "COLLAPSE_GRID":
            self._shared_state["expanded_camera"] = None
            if session_id in self._sessions:
                self._sessions[session_id].active_camera = None
            self.broadcast_sync("SYNC_COLLAPSE_GRID", {"by": session_id}, exclude_session=session_id)

        elif action == "ACKNOWLEDGE_ALERT":
            event_id = payload.get("event_id")
            if event_id:
                self._shared_state["acknowledged_events"].add(str(event_id))
            self.broadcast_sync("SYNC_ALERT_ACK", {"event_id": event_id, "by": session_id})

        elif action == "WATCHLIST_CHANGED":
            self.broadcast_sync("SYNC_WATCHLIST_UPDATE", {"message": "Watchlist modified", "by": session_id})

    def broadcast_sync(self, event_type: str, data: dict, exclude_session: Optional[str] = None) -> None:
        """Broadcast a synchronization event to all connected sessions."""
        if not self._loop or self._loop.is_closed():
            return

        msg = json.dumps({
            "sync_event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })

        for sid, q in list(self._queues.items()):
            if sid == exclude_session:
                continue
            try:
                self._loop.call_soon_threadsafe(q.put_nowait, msg)
            except Exception:
                pass

    def _cleanup_stale(self) -> None:
        """Clean up sessions that have timed out."""
        now = time.monotonic()
        stale = [
            sid for sid, s in self._sessions.items()
            if now - s.last_heartbeat > SESSION_TIMEOUT_SECONDS
        ]
        for sid in stale:
            self.terminate_session(sid)
