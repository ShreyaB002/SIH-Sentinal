/**
 * IBVAP Dashboard ? websocket.js  (Phase 2)
 *
 * Connects to GET /ws/alerts and dispatches incoming AI events to:
 *   - window.triggerTileAlert(cameraId)  (grid.js)   ? tile glow
 *   - window.appendEventLog(event)       (eventlog.js) ? sidebar card
 *
 * Auto-reconnects with exponential backoff on connection loss.
 */

'use strict';

(function () {
  const WS_URL          = `ws://${location.host}/ws/alerts`;
  const MAX_BACKOFF_MS  = 30000;
  let   backoffMs       = 1000;
  let   socket          = null;

  const wsStatusEl = document.getElementById('wsStatus');

  function setWsStatus(state) {
    if (!wsStatusEl) return;
    wsStatusEl.className = 'header__ws-status';
    if (state === 'online') {
      wsStatusEl.classList.add('ws-online');
      wsStatusEl.textContent = '\u25CF LIVE';
    } else if (state === 'offline') {
      wsStatusEl.classList.add('ws-offline');
      wsStatusEl.textContent = '\u25CF OFFLINE';
    } else {
      wsStatusEl.classList.add('ws-connecting');
      wsStatusEl.textContent = '\u25CF CONNECTING';
    }
  }

  function connect() {
    setWsStatus('connecting');

    socket = new WebSocket(WS_URL);

    socket.addEventListener('open', () => {
      console.log('[IBVAP] WebSocket connected to', WS_URL);
      setWsStatus('online');
      backoffMs = 1000;  // reset backoff on success
    });

    socket.addEventListener('message', (ev) => {
      let event;
      try {
        event = JSON.parse(ev.data);
      } catch (_) {
        return;
      }

      // Handle multi-device synchronization events
      if (event && event.sync_event) {
        if (typeof window.handleSyncEvent === 'function') {
          window.handleSyncEvent(event.sync_event, event.data);
        }
        return;
      }

      // Skip keep-alive pings and info messages
      if (!event || event.event_type === 'PING' || event.event_type === 'INFO') return;

      // Dispatch to event log and camera grid
      if (window.eventLog && typeof window.eventLog.addEvent === 'function') {
        window.eventLog.addEvent(event);
      } else if (typeof window.appendEventLog === 'function') {
        window.appendEventLog(event);
      }
    });

    socket.addEventListener('close', (ev) => {
      console.warn('[IBVAP] WebSocket closed:', ev.code, ev.reason);
      setWsStatus('offline');
      scheduleReconnect();
    });

    socket.addEventListener('error', (err) => {
      console.error('[IBVAP] WebSocket error:', err);
      setWsStatus('offline');
    });
  }

  function scheduleReconnect() {
    console.log(`[IBVAP] Reconnecting WebSocket in ${backoffMs}ms...`);
    setTimeout(() => {
      backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
      connect();
    }, backoffMs);
  }

  // Initial connection
  connect();
})();
