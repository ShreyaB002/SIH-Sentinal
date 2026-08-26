/**
 * IBVAP Dashboard ? eventlog.js (Phase 4 Complete)
 *
 * Renders incoming AI alert events into the sidebar event log.
 * Handles all event types:
 *   - INTRUSION, WEAPON, LOITERING, RUNNING, CROWD
 *   - FACE_MATCH, PLATE_DETECTED, NIGHT_MOVEMENT, DETECTED
 */

'use strict';

let eventCount = 0;
const MAX_LOG_ENTRIES = 200;

function formatTime(iso) {
  try {
    const d = new Date(iso || Date.now());
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch (_) {
    return '--:--:--';
  }
}

function getCardClass(type) {
  switch (type) {
    case 'WEAPON':         return 'event-card--weapon';
    case 'FACE_MATCH':     return 'event-card--facematch';
    case 'LOITERING':      return 'event-card--loitering';
    case 'RUNNING':        return 'event-card--running';
    case 'CROWD':          return 'event-card--crowd';
    case 'INTRUSION':      return 'event-card--intrusion';
    case 'PLATE_DETECTED': return 'event-card--plate';
    case 'NIGHT_MOVEMENT': return 'event-card--night';
    default:               return 'event-card--detected';
  }
}

function getTypeTag(type) {
  switch (type) {
    case 'WEAPON':         return '<span class="event-card__type-weapon">!! WEAPON</span>';
    case 'FACE_MATCH':     return '<span class="event-card__type-facematch">!! FRS MATCH</span>';
    case 'LOITERING':      return '<span class="event-card__type-loitering">LOITERING</span>';
    case 'RUNNING':        return '<span class="event-card__type-running">RUNNING</span>';
    case 'CROWD':          return '<span class="event-card__type-crowd">CROWD</span>';
    case 'INTRUSION':      return '<span class="event-card__type-intrusion">! INTRUSION</span>';
    case 'PLATE_DETECTED': return '<span class="event-card__type-plate">ANPR PLATE</span>';
    case 'NIGHT_MOVEMENT': return '<span class="event-card__type-night">NIGHT MOVE</span>';
    default:               return '<span class="event-card__type-detected">DETECTED</span>';
  }
}

function formatExtra(ev) {
  if (ev.event_type === 'LOITERING' && ev.duration_seconds)
    return `Duration: ${ev.duration_seconds}s`;
  if (ev.event_type === 'RUNNING' && ev.speed)
    return `Speed: ${ev.speed} px/frame`;
  if (ev.event_type === 'CROWD' && ev.crowd_count)
    return `${ev.crowd_count} persons detected`;
  if (ev.event_type === 'PLATE_DETECTED' && ev.plate_text)
    return `Plate: <strong>${ev.plate_text}</strong> (${(ev.confidence * 100).toFixed(0)}%)`;
  if (ev.event_type === 'FACE_MATCH' && ev.person_name)
    return `Watchlist: <strong>${ev.person_name}</strong> (${(ev.confidence * 100).toFixed(0)}% match)`;
  if (ev.event_type === 'NIGHT_MOVEMENT' && ev.object_count)
    return `${ev.object_count} objects in low-light`;
  if (ev.confidence && ev.event_type !== 'CROWD')
    return `Confidence: ${(ev.confidence * 100).toFixed(0)}%`;
  return '';
}

function createEventCard(ev) {
  const card = document.createElement('div');
  card.className = `event-card ${getCardClass(ev.event_type)}`;

  const timeStr = formatTime(ev.timestamp);
  const extraStr = formatExtra(ev);

  card.innerHTML = `
    <div class="event-card__top">
      ${getTypeTag(ev.event_type)}
      <span class="event-card__time">${timeStr}</span>
    </div>
    <div class="event-card__label">${ev.label || 'Unknown'}</div>
    <div class="event-card__meta">${ev.camera_name || ev.camera_id} ${ev.track_id ? '&bull; Track #' + ev.track_id : ''}</div>
    ${ev.zone ? `<div class="event-card__zone">&#9655; ${ev.zone}</div>` : ''}
    ${extraStr ? `<div class="event-card__meta" style="color:var(--text-pri)">${extraStr}</div>` : ''}
  `;
  return card;
}

window.appendEventLog = function(ev) {
  if (!ev || ev.event_type === 'PING' || ev.event_type === 'INFO') return;

  const body = document.getElementById('eventLogBody');
  const empty = document.getElementById('eventLogEmpty');
  if (!body) return;
  if (empty) empty.style.display = 'none';

  const card = createEventCard(ev);
  body.insertBefore(card, body.firstChild);

  const cards = body.querySelectorAll('.event-card');
  if (cards.length > MAX_LOG_ENTRIES) {
    cards[cards.length - 1].remove();
  }

  // Trigger tile alert/glow
  if (ev.camera_id) {
    if (ev.event_type === 'WEAPON' || ev.event_type === 'FACE_MATCH') {
      const tile = document.querySelector(`.tile[data-cam-id="${ev.camera_id}"]`);
      if (tile) {
        tile.classList.remove('tile--weapon');
        void tile.offsetWidth;
        tile.classList.add('tile--weapon');
        setTimeout(() => tile.classList.remove('tile--weapon'), 3200);
      }
    } else if (typeof window.triggerTileAlert === 'function') {
      window.triggerTileAlert(ev.camera_id);
    }
  }

  eventCount++;
  const counter = document.getElementById('footerEventCount');
  if (counter) counter.textContent = `Events: ${eventCount}`;
};

window.clearEventLog = function() {
  const body = document.getElementById('eventLogBody');
  const empty = document.getElementById('eventLogEmpty');
  if (!body) return;

  body.querySelectorAll('.event-card').forEach(c => c.remove());
  if (empty) empty.style.display = '';
  eventCount = 0;
  const counter = document.getElementById('footerEventCount');
  if (counter) counter.textContent = 'Events: 0';
};
