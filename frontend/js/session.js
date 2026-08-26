/**
 * IBVAP Dashboard ? session.js
 * Real-time Multi-Device Session Management and Screen State Synchronization.
 */

'use strict';

let currentSessionId = null;
let isRemoteAction = false;

async function initSession() {
  const deviceName = `${navigator.userAgentData?.platform || 'Terminal'}_${Math.floor(Math.random() * 1000)}`;
  try {
    const res = await fetch('/api/session/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_name: deviceName, role: 'Operator' }),
    });
    if (res.ok) {
      const data = await res.json();
      currentSessionId = data.session_id;
      console.log(`[IBVAP Session] Registered session: ${currentSessionId}`);
      updateDeviceCount();
      startHeartbeat();
    }
  } catch (err) {
    console.warn('[IBVAP Session] Failed to register session:', err);
  }
}

function startHeartbeat() {
  setInterval(async () => {
    if (!currentSessionId) return;
    try {
      await fetch('/api/session/heartbeat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSessionId }),
      });
      updateDeviceCount();
    } catch (_) {}
  }, 20000);
}

async function updateDeviceCount() {
  try {
    const res = await fetch('/api/session/list');
    if (res.ok) {
      const data = await res.json();
      const count = data.active_sessions?.length || 1;
      const badge = document.getElementById('sessionSyncBadge');
      if (badge) {
        badge.textContent = `?? ${count} DEVICE${count > 1 ? 'S' : ''} SYNCED`;
        badge.style.color = count > 1 ? 'var(--green)' : 'var(--text-sec)';
      }
    }
  } catch (_) {}
}

window.broadcastDeviceAction = async function(action, payload = {}) {
  if (isRemoteAction || !currentSessionId) return;
  try {
    await fetch('/api/session/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: currentSessionId,
        action: action,
        payload: payload,
      }),
    });
  } catch (err) {
    console.warn('[IBVAP Session] Broadcast error:', err);
  }
};

window.handleSyncEvent = function(syncEvent, data) {
  if (!data || (data.by && data.by === currentSessionId)) return;

  isRemoteAction = true;
  try {
    if (syncEvent === 'SYNC_EXPAND_CAMERA' && data.camera_id) {
      console.log(`[IBVAP Sync] Remote device expanded camera: ${data.camera_id}`);
      if (typeof window.expandCamera === 'function') {
        window.expandCamera(data.camera_id);
      }
    } else if (syncEvent === 'SYNC_COLLAPSE_GRID') {
      console.log('[IBVAP Sync] Remote device returned to grid.');
      if (typeof window.collapseToGrid === 'function') {
        window.collapseToGrid();
      }
    } else if (syncEvent === 'SYNC_WATCHLIST_UPDATE') {
      console.log('[IBVAP Sync] Watchlist update from remote device.');
      if (typeof window.renderWatchlist === 'function') {
        window.renderWatchlist();
      }
    } else if (syncEvent === 'DEVICE_CONNECTED' || syncEvent === 'DEVICE_DISCONNECTED') {
      updateDeviceCount();
    }
  } finally {
    setTimeout(() => { isRemoteAction = false; }, 300);
  }
};

window.addEventListener('beforeunload', () => {
  if (currentSessionId) {
    navigator.sendBeacon(`/api/session/${currentSessionId}`, JSON.stringify({}));
  }
});

document.addEventListener('DOMContentLoaded', initSession);
