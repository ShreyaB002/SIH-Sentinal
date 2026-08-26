/**
 * IBVAP Dashboard ? grid.js  (Phase 2)
 *
 * Phase 2 additions:
 *   - triggerTileAlert(cameraId)  ? called by websocket.js on AI event
 *   - updateCameraCount() exposed for footer counter
 */

'use strict';

const API_BASE         = '';
const CAMERAS_ENDPOINT = `${API_BASE}/api/cameras`;
const STREAM_BASE      = `${API_BASE}/api/stream`;
const POLL_INTERVAL_MS = 5000;

let cameras = [];
let expandedCameraId = null;

// ---------------------------------------------------------------------------
// Clock
// ---------------------------------------------------------------------------
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const el = document.getElementById('clock');
  if (el) el.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}
setInterval(updateClock, 1000);
updateClock();

// ---------------------------------------------------------------------------
// Sidebar toggle
// ---------------------------------------------------------------------------
document.getElementById('btnToggleLog').addEventListener('click', () => {
  const sidebar = document.getElementById('sidebar');
  const main    = document.getElementById('mainContent');
  sidebar.classList.toggle('hidden');
  main.classList.toggle('sidebar-open');
});

document.getElementById('btnClearLog').addEventListener('click', () => {
  window.clearEventLog && window.clearEventLog();
});

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
async function fetchCameras() {
  try {
    const res = await fetch(CAMERAS_ENDPOINT);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[IBVAP] Could not fetch cameras:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Tile rendering
// ---------------------------------------------------------------------------
function createTile(cam) {
  const tile = document.createElement('div');
  tile.className = 'tile';
  tile.dataset.camId = cam.id;
  tile.dataset.status = cam.status;
  tile.setAttribute('role', 'button');
  tile.setAttribute('tabindex', '0');
  tile.setAttribute('aria-label', `Expand ${cam.name}`);

  const isOnline     = cam.status === 'ONLINE';
  const isConnecting = cam.status === 'CONNECTING';
  const statusClass  = isOnline ? 'online' : (isConnecting ? 'connecting' : 'offline');

  tile.innerHTML = `
    <span class="tile__label">${cam.name.toUpperCase()}</span>
    <span class="tile__expand-icon" aria-hidden="true">&#x26F6;</span>
    <div class="tile__feed">
      ${isOnline || isConnecting
        ? `<img class="tile__img" src="${STREAM_BASE}/${cam.id}" alt="${cam.name} feed" />`
        : `<div class="tile__offline">
             <span class="tile__offline-icon">&#9632;</span>
             <span class="tile__offline-text">OFFLINE</span>
           </div>`
      }
    </div>
    <div class="tile__status-bar">
      <span class="status-dot status-dot--${statusClass}"></span>
      <span class="status-text--${statusClass}">${cam.status}</span>
      <span style="margin-left:auto;color:var(--text-dim);font-size:10px;letter-spacing:1px;">${cam.id.toUpperCase()}</span>
    </div>
  `;

  tile.addEventListener('click',   () => expandCamera(cam.id));
  tile.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') expandCamera(cam.id); });
  return tile;
}

function renderGrid(newCameras) {
  const grid = document.getElementById('cameraGrid');
  if (!grid) return;

  const existingTiles = grid.querySelectorAll('.tile');
  if (existingTiles.length !== newCameras.length) {
    grid.innerHTML = '';
    newCameras.forEach(cam => grid.appendChild(createTile(cam)));
    return;
  }

  newCameras.forEach((cam, i) => {
    const tile      = existingTiles[i];
    const oldStatus = tile.dataset.status;
    if (oldStatus === cam.status) return;
    tile.dataset.status = cam.status;

    const isOnline     = cam.status === 'ONLINE';
    const isConnecting = cam.status === 'CONNECTING';
    const cls          = isOnline ? 'online' : (isConnecting ? 'connecting' : 'offline');

    const dot  = tile.querySelector('.status-dot');
    const text = tile.querySelector('[class^="status-text"]');
    if (dot)  dot.className  = `status-dot status-dot--${cls}`;
    if (text) { text.className = `status-text--${cls}`; text.textContent = cam.status; }

    const feed = tile.querySelector('.tile__feed');
    if (feed) {
      const img         = feed.querySelector('.tile__img');
      const placeholder = feed.querySelector('.tile__offline');
      if ((isOnline || isConnecting) && !img) {
        feed.innerHTML = `<img class="tile__img" src="${STREAM_BASE}/${cam.id}" alt="${cam.name} feed" />`;
      } else if (!isOnline && !isConnecting && !placeholder) {
        feed.innerHTML = `<div class="tile__offline">
          <span class="tile__offline-icon">&#9632;</span>
          <span class="tile__offline-text">OFFLINE</span>
        </div>`;
      }
    }
  });
}

// ---------------------------------------------------------------------------
// PHASE 2 ? Alert glow trigger
// Called by websocket.js when an AI event arrives for a camera
// ---------------------------------------------------------------------------
window.triggerTileAlert = function(cameraId) {
  const tile = document.querySelector(`.tile[data-cam-id="${cameraId}"]`);
  if (!tile) return;

  // Remove class first (in case it's already glowing) then re-add
  tile.classList.remove('tile--alert');
  void tile.offsetWidth;   // force reflow to restart animation
  tile.classList.add('tile--alert');

  // Auto-remove after animation completes (6 cycles x 0.5s = 3s)
  setTimeout(() => tile.classList.remove('tile--alert'), 3100);
};

// ---------------------------------------------------------------------------
// Expand / collapse
// ---------------------------------------------------------------------------
function expandCamera(cameraId) {
  const cam = cameras.find(c => c.id === cameraId);
  if (!cam) return;
  expandedCameraId = cameraId;

  const expandTitle  = document.getElementById('expandTitle');
  const expandStatus = document.getElementById('expandStatus');
  const expandImg    = document.getElementById('expandImg');

  if (expandTitle) expandTitle.textContent = cam.name.toUpperCase();
  if (expandStatus) {
    const isOnline     = cam.status === 'ONLINE';
    const isConnecting = cam.status === 'CONNECTING';
    expandStatus.className  = `expand-status status-text--${isOnline ? 'online' : isConnecting ? 'connecting' : 'offline'}`;
    expandStatus.textContent = `\u25CF ${cam.status}`;
  }
  if (expandImg) {
    if (cam.status === 'ONLINE' || cam.status === 'CONNECTING') {
      expandImg.src = `${STREAM_BASE}/${cam.id}`;
      expandImg.style.display = '';
    } else {
      expandImg.src = '';
      expandImg.style.display = 'none';
    }
  }

  document.getElementById('gridView').classList.add('hidden');
  document.getElementById('expandView').classList.remove('hidden');

  if (typeof window.broadcastDeviceAction === 'function') {
    window.broadcastDeviceAction('EXPAND_CAMERA', { camera_id: cameraId });
  }
}

function collapseToGrid() {
  expandedCameraId = null;
  const expandImg = document.getElementById('expandImg');
  if (expandImg) expandImg.src = '';
  document.getElementById('expandView').classList.add('hidden');
  document.getElementById('gridView').classList.remove('hidden');

  if (typeof window.broadcastDeviceAction === 'function') {
    window.broadcastDeviceAction('COLLAPSE_GRID');
  }
}

window.expandCamera = expandCamera;
window.collapseToGrid = collapseToGrid;

document.getElementById('btnBack').addEventListener('click', collapseToGrid);

// ---------------------------------------------------------------------------
// Status polling
// ---------------------------------------------------------------------------
async function refreshCameras() {
  const data = await fetchCameras();
  if (!data) return;
  cameras = data;

  if (expandedCameraId === null) {
    renderGrid(cameras);
  } else {
    const cam = cameras.find(c => c.id === expandedCameraId);
    const expandStatus = document.getElementById('expandStatus');
    if (cam && expandStatus) {
      const isOnline     = cam.status === 'ONLINE';
      const isConnecting = cam.status === 'CONNECTING';
      expandStatus.className  = `expand-status status-text--${isOnline ? 'online' : isConnecting ? 'connecting' : 'offline'}`;
      expandStatus.textContent = `\u25CF ${cam.status}`;
    }
  }
}

(async () => {
  await refreshCameras();
  setInterval(refreshCameras, POLL_INTERVAL_MS);
})();
