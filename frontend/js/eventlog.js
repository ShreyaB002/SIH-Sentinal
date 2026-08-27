/**
 * eventlog.js — Real-Time Tactical Incident Feed & Audio Chime Engine for IBVAP.
 */

class EventLogManager {
  constructor() {
    this.sidebar = document.getElementById("sidebar");
    this.body = document.getElementById("eventLogBody");
    this.emptyMsg = document.getElementById("eventLogEmpty");
    this.mainContent = document.getElementById("mainContent");
    this.btnToggle = document.getElementById("btnToggleLog");
    this.btnClear = document.getElementById("btnClearLog");
    this.btnAudioToggle = document.getElementById("btnAudioToggle");
    this.unreadBadge = document.getElementById("unreadAlertBadge");

    this.audioEnabled = true;
    this.audioCtx = null;
    this.events = [];
    this.activeFilter = "ALL";
    this.unreadCount = 0;

    this.initEvents();
    this.initAudioContext();
  }

  initEvents() {
    this.btnToggle?.addEventListener("click", () => this.toggleSidebar());
    this.btnClear?.addEventListener("click", () => this.clearLog());
    this.btnAudioToggle?.addEventListener("click", () => this.toggleAudio());

    // Severity filter pill clicks
    document.querySelectorAll(".sev-pill").forEach((pill) => {
      pill.addEventListener("click", (e) => {
        document.querySelectorAll(".sev-pill").forEach((p) => p.classList.remove("active"));
        e.target.classList.add("active");
        this.activeFilter = e.target.getAttribute("data-sev") || "ALL";
        this.render();
      });
    });
  }

  initAudioContext() {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    } catch (e) {
      console.warn("Web Audio API not supported.");
    }
  }

  playTacticalChime(severity) {
    if (!this.audioEnabled || !this.audioCtx) return;
    try {
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }

      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      const now = this.audioCtx.currentTime;

      if (severity === "CRITICAL") {
        // High-urgency double beep
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.setValueAtTime(1100, now + 0.1);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (severity === "HIGH") {
        // Warning chime
        osc.type = "triangle";
        osc.frequency.setValueAtTime(587.33, now);
        osc.frequency.setValueAtTime(783.99, now + 0.15);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
      } else {
        // Subtle notification
        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      }
    } catch (err) {
      console.debug("Audio play error:", err);
    }
  }

  toggleAudio() {
    this.audioEnabled = !this.audioEnabled;
    if (this.btnAudioToggle) {
      this.btnAudioToggle.innerHTML = this.audioEnabled ? "&#128266; AUDIO ON" : "&#128263; MUTED";
      this.btnAudioToggle.style.color = this.audioEnabled ? "var(--green)" : "var(--text-sec)";
    }
    if (this.audioEnabled && this.audioCtx && this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
  }

  toggleSidebar(forceState) {
    const isHidden = this.sidebar?.classList.contains("hidden");
    const open = forceState !== undefined ? forceState : isHidden;

    if (open) {
      this.sidebar?.classList.remove("hidden");
      this.mainContent?.classList.add("sidebar-open");
      this.unreadCount = 0;
      this.updateUnreadBadge();
    } else {
      this.sidebar?.classList.add("hidden");
      this.mainContent?.classList.remove("sidebar-open");
    }
  }

  addEvent(eventData) {
    const eventType = (eventData.event_type || eventData.type || "ACTIVITY").toUpperCase();
    const severity = this.determineSeverity(eventType, eventData);

    const record = {
      id: "EVT-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
      type: eventType,
      severity: severity,
      camera_id: eventData.camera_id || "cam_01",
      label: eventData.label || eventData.event_type || "Threat",
      confidence: eventData.confidence || 0.85,
      timestamp: eventData.timestamp || Date.now() / 1000,
      details: eventData.details || {},
      acknowledged: false,
    };

    this.events.unshift(record);
    if (this.events.length > 200) this.events.pop();

    if (this.sidebar?.classList.contains("hidden")) {
      this.unreadCount++;
      this.updateUnreadBadge();
    }

    // Play tactical auditory chime
    this.playTacticalChime(severity);

    // Trigger visual pulse on camera tile
    window.cameraGrid?.pulseCameraThreat(record.camera_id, severity);

    this.render();
  }

  determineSeverity(type, data) {
    if (type.includes("WEAPON") || type.includes("ARMED") || type.includes("GUN") || type.includes("WATCHLIST")) {
      return "CRITICAL";
    }
    if (type.includes("FENCE") || type.includes("INTRUSION") || type.includes("REID") || type.includes("RUNNING")) {
      return "HIGH";
    }
    if (type.includes("LOITER") || type.includes("CROWD") || type.includes("PLATE")) {
      return "MEDIUM";
    }
    return "LOW";
  }

  updateUnreadBadge() {
    if (!this.unreadBadge) return;
    if (this.unreadCount > 0) {
      this.unreadBadge.textContent = this.unreadCount > 99 ? "99+" : this.unreadCount;
      this.unreadBadge.classList.remove("hidden");
    } else {
      this.unreadBadge.classList.add("hidden");
    }
  }

  acknowledge(eventId) {
    const item = this.events.find((e) => e.id === eventId);
    if (item) {
      item.acknowledged = true;
      this.render();
    }
  }

  render() {
    if (!this.body) return;

    const filtered = this.events.filter((e) => {
      if (this.activeFilter === "ALL") return true;
      return e.severity === this.activeFilter;
    });

    if (filtered.length === 0) {
      this.body.innerHTML = `
        <div class="event-log-empty">
          ${this.events.length === 0 ? "No security incidents logged yet. AI models active..." : "No events match current filter (" + this.activeFilter + ")."}
        </div>
      `;
      return;
    }

    this.body.innerHTML = filtered
      .map((ev) => {
        const timeStr = new Date(ev.timestamp * 1000).toLocaleTimeString();
        const confPercent = Math.round((ev.confidence || 0.85) * 100);
        const sevClass = `sev-${ev.severity.toLowerCase()}`;
        const ackClass = ev.acknowledged ? "ack-done" : "";

        let desc = `${ev.label} detected on ${ev.camera_id}`;
        if (ev.type.includes("FENCE")) desc = `Boundary intrusion into ${ev.details.zone || "Restricted Zone"}`;
        if (ev.type.includes("WEAPON")) desc = `Weapon threat (${ev.label}) detected!`;
        if (ev.type.includes("FACE")) desc = `Watchlist Target '${ev.details.name || ev.label}' identified!`;
        if (ev.type.includes("PLATE")) desc = `License plate [${ev.details.plate || ev.label}] logged`;
        if (ev.type.includes("REID")) desc = `Cross-camera suspect Re-ID match!`;

        return `
          <div class="incident-card ${sevClass} ${ackClass}" id="${ev.id}">
            <div class="inc-header">
              <span class="inc-badge ${sevClass}">${ev.severity}</span>
              <span class="inc-type">${ev.type}</span>
              <span class="inc-time">${timeStr}</span>
            </div>
            <div class="inc-desc">${desc}</div>
            <div class="inc-meta">
              <span>&#128249; ${ev.camera_id}</span>
              <span>&#127919; ${confPercent}% Conf</span>
              ${
                !ev.acknowledged
                  ? `<button class="btn-ack" onclick="window.eventLog.acknowledge('${ev.id}')">&#10003; ACKNOWLEDGE</button>`
                  : `<span class="ack-tag">&#10003; ACKNOWLEDGED</span>`
              }
            </div>
          </div>
        `;
      })
      .join("");
  }

  clearLog() {
    this.events = [];
    this.render();
  }
}

window.eventLog = new EventLogManager();
