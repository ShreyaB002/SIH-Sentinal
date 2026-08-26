/**
 * IBVAP Dashboard ? watchlist.js (Phase 4)
 * Handles Watchlist Modal (view, upload face, delete).
 */

'use strict';

const WATCHLIST_API = '/api/watchlist';

async function fetchWatchlist() {
  try {
    const res = await fetch(WATCHLIST_API);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('[IBVAP] Failed to fetch watchlist:', err);
    return [];
  }
}

async function renderWatchlist() {
  const listEl = document.getElementById('watchlistItems');
  if (!listEl) return;

  const entries = await fetchWatchlist();
  if (entries.length === 0) {
    listEl.innerHTML = '<div style="color:var(--text-dim);padding:12px;font-size:12px;">No watchlist targets registered. Upload a face photo below.</div>';
    return;
  }

  listEl.innerHTML = entries.map(e => `
    <div class="watchlist-entry" style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px;background:#0d1a2a;border:1px solid var(--border);border-radius:4px;margin-bottom:6px;">
      <div>
        <div style="font-weight:600;color:var(--text-pri);font-size:13px;">${e.name}</div>
        <div style="font-size:10px;color:var(--text-dim);">ID: ${e.id} &bull; ${new Date(e.added_at).toLocaleString()}</div>
      </div>
      <button onclick="deleteWatchlistEntry('${e.id}')" style="background:#7f1d1d;border:none;color:#fff;padding:4px 8px;border-radius:3px;cursor:pointer;font-size:11px;">Delete</button>
    </div>
  `).join('');
}

window.deleteWatchlistEntry = async function(id) {
  if (!confirm('Remove this person from the watchlist?')) return;
  try {
    const res = await fetch(`${WATCHLIST_API}/${id}`, { method: 'DELETE' });
    if (res.ok) {
      renderWatchlist();
    } else {
      alert('Failed to delete entry');
    }
  } catch (err) {
    alert('Error deleting entry: ' + err.message);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const btnWatchlist = document.getElementById('btnToggleWatchlist');
  const modal = document.getElementById('watchlistModal');
  const btnClose = document.getElementById('btnCloseWatchlist');
  const form = document.getElementById('watchlistForm');
  const statusMsg = document.getElementById('watchlistStatus');

  if (btnWatchlist && modal) {
    btnWatchlist.addEventListener('click', () => {
      modal.classList.toggle('hidden');
      if (!modal.classList.contains('hidden')) {
        renderWatchlist();
      }
    });
  }

  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nameInput = document.getElementById('wlName');
      const fileInput = document.getElementById('wlImage');
      if (!nameInput || !fileInput || !fileInput.files[0]) return;

      const formData = new FormData();
      formData.append('name', nameInput.value.trim());
      formData.append('image', fileInput.files[0]);

      if (statusMsg) {
        statusMsg.textContent = 'Registering face embedding...';
        statusMsg.style.color = 'var(--amber)';
      }

      try {
        const res = await fetch(`${WATCHLIST_API}/add`, {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        if (res.ok) {
          if (statusMsg) {
            statusMsg.textContent = `Success! '${data.name}' registered to Watchlist.`;
            statusMsg.style.color = 'var(--green)';
          }
          form.reset();
          renderWatchlist();
        } else {
          if (statusMsg) {
            statusMsg.textContent = data.detail || 'Registration failed.';
            statusMsg.style.color = 'var(--red)';
          }
        }
      } catch (err) {
        if (statusMsg) {
          statusMsg.textContent = 'Error: ' + err.message;
          statusMsg.style.color = 'var(--red)';
        }
      }
    });
  }
});
