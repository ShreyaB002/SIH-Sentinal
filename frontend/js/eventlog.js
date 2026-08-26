/**
 * IBVAP Dashboard ? eventlog.js  (Phase 2)
 *
 * Renders incoming AI alert events into the sidebar event log.
 * Called by websocket.js with parsed event objects.
 *
 * Public API (window-level for cross-script calls):
 *   window.appendEventLog(event)  ? add a new event card
 *   window.clearEventLog()        ? empty the log
 */

'use strict';

let eventCount = 0;

const MAX_LOG_ENTRIES = 200;  // keep last N cards to avoid memory growth

/**
 * Format an ISO timestamp to a short local time string.
 * @param {string} iso
 * @returns {string}
 */
function formatTime(iso) {
  try {
    const d = new Date(iso);
    const pad = n => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch (_) {
    return '--:--:--';
  }
}

/**
 * Create an event card DOM element.
 * @param {Object} ev
 * @returns {HTMLElement}
 */
function createEventCard(ev) {
  const card = document.createElement('div');
  const isIntrusion = ev.event_type === 'INTRUSION';
  card.className = `event-card ${isIntrusion ? 'event-card--intrusion' : 'event-card--detected'}`;

  const timeStr = formatTime(ev.timestamp);
  const confStr = ev.confidence ? `${(ev.confidence * 100).toFixed(0)}%` : '';
  const zoneStr = ev.zone ? ev.zone : '';

  card.innerHTML = `
    <div class="event-card__top">
      <span class="${isIntrusion ? 'event-card__type-intrusion' : 'event-card__type-detected'}">
        ${isIntrusion ? '! INTRUSION' : 'DETECTED'}
      </span>
      <span class="event-card__time">${timeStr}</span>
    </div>
    <div class="event-card__label">${ev.label || 'Unknown'} ${confStr ? '(' + confStr + ')' : ''}</div>
    <div class="event-card__meta">${ev.camera_name || ev.camera_id} &bull; Track #${ev.track_id || 0}</div>
    ${zoneStr ? `<div class="event-card__zone">&#9655; ${zoneStr}</div>` : ''}
  `;

  return card;
}

/**
 * Append one event to the sidebar log.
 * @param {Object} ev
 */
window.appendEventLog = function(ev) {
  if (!ev || ev.event_type === 'PING' || ev.event_type === 'INFO') return;

  const body  = document.getElementById('eventLogBody');
  const empty = document.getElementById('eventLogEmpty');
  if (!body) return;

  // Hide "No events yet" placeholder
  if (empty) empty.style.display = 'none';

  // Create and prepend card
  const card = createEventCard(ev);
  body.insertBefore(card, body.firstChild);

  // Enforce max entries
  const cards = body.querySelectorAll('.event-card');
  if (cards.length > MAX_LOG_ENTRIES) {
    cards[cards.length - 1].remove();
  }

  // Update footer counter
  eventCount++;
  const counter = document.getElementById('footerEventCount');
  if (counter) counter.textContent = `Events: ${eventCount}`;
};

/**
 * Clear all event cards from the sidebar log.
 */
window.clearEventLog = function() {
  const body  = document.getElementById('eventLogBody');
  const empty = document.getElementById('eventLogEmpty');
  if (!body) return;

  body.querySelectorAll('.event-card').forEach(c => c.remove());
  if (empty) empty.style.display = '';
  eventCount = 0;
  const counter = document.getElementById('footerEventCount');
  if (counter) counter.textContent = 'Events: 0';
};
