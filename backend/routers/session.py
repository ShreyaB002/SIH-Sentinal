"""
session.py - REST Router for Multi-Device Session Lifecycle & Synchronization.

Endpoints
---------
POST   /api/session/create      - Register a new end-device session
POST   /api/session/heartbeat   - Ping heartbeat to maintain active session
POST   /api/session/sync        - Broadcast an action to stay in sync with peer devices
DELETE /api/session/{session_id}- Terminate a session
GET    /api/session/list        - List all active synced devices
"""

from __future__ import annotations

import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])


class CreateSessionRequest(BaseModel):
    device_name: str = "Operator_Terminal"
    role: str = "Operator"


class SyncActionRequest(BaseModel):
    session_id: str
    action: str          # "EXPAND_CAMERA" | "COLLAPSE_GRID" | "ACKNOWLEDGE_ALERT" | "WATCHLIST_CHANGED"
    payload: dict = {}


class HeartbeatRequest(BaseModel):
    session_id: str


def _get_sm(request: Request):
    mgr = request.app.state.stream_manager
    if not hasattr(mgr, "_session_manager") or mgr._session_manager is None:
        raise HTTPException(503, "Session manager not initialised")
    return mgr._session_manager


@router.post("/create")
def create_session(body: CreateSessionRequest, request: Request):
    sm = _get_sm(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    session = sm.create_session(
        device_name=body.device_name,
        ip_address=client_ip,
        role=body.role,
    )
    return {
        "status": "ok",
        "session_id": session.session_id,
        "device_name": session.device_name,
        "ip_address": session.ip_address,
        "role": session.role,
        "created_at": session.created_at,
    }


@router.post("/heartbeat")
def session_heartbeat(body: HeartbeatRequest, request: Request):
    sm = _get_sm(request)
    success = sm.heartbeat(body.session_id)
    if not success:
        raise HTTPException(404, "Session not found or expired")
    return {"status": "ok", "session_id": body.session_id}


@router.post("/sync")
def sync_device_state(body: SyncActionRequest, request: Request):
    """Broadcast an action to peer devices to keep screens synchronized."""
    sm = _get_sm(request)
    sm.update_sync_state(body.session_id, body.action, body.payload)
    return {"status": "ok", "synced_action": body.action}


@router.delete("/{session_id}")
def terminate_session(session_id: str, request: Request):
    sm = _get_sm(request)
    success = sm.terminate_session(session_id)
    if not success:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return {"status": "ok", "message": f"Session '{session_id}' terminated."}


@router.get("/list")
def list_active_sessions(request: Request):
    sm = _get_sm(request)
    return {"active_sessions": sm.list_sessions()}
