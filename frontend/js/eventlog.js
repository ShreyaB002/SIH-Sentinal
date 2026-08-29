/**
 * eventlog.js — Operational Incident & Alerts Controller for IBVAP.
 */

class EventLogController {
  constructor() {
    this.activeAlertsList = document.getElementById("activeAlertsList");
    this.activeAlertsCount = document.getElementById("activeAlertsCount");
    this.navAlertCount = document.getElementById("navAlertCount");
    this.eventsTableBody = document.getElementById("eventsTableBody");
    this.eventCamFilter = document.getElementById("eventCamFilter");

    // Modal elements
    this.modal = document.getElementById("incidentModal");
    this.modalHeading = document.getElementById("incModalHeading");
    this.modalCam = document.getElementById("incModalCam");
    this.modalTime = document.getElementById("incModalTime");
    this.modalSev = document.getElementById("incModalSev");
    this.modalObject = document.getElementById("incModalObject");
    this.modalDesc = document.getElementById("incModalDesc");
    this.modalImg = document.getElementById("incModalImg");
    this.btnViewCam = document.getElementById("btnIncViewCamera");
    this.btnMarkReviewed = document.getElementById("btnIncMarkReviewed");
    this.btnCloseModal = document.getElementById("btnCloseIncidentModal");

    this.events = [];
    this.activeAlerts = []; // List of unreviewed CRITICAL and WARNING incidents
    this.activeFilter = "ALL";
    this.currentIncident = null;

    this.initEvents();
  }

  initEvents() {
    document.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.activeFilter = e.currentTarget.getAttribute("data-sev") || "ALL";
        this.render();
      });
    });

    this.eventCamFilter?.addEventListener("change", () => this.render());
    document.getElementById("btnClearActiveAlerts")?.addEventListener("click", () => this.clearActiveAlerts());
    document.getElementById("btnExportEventsCSV")?.addEventListener("click", () => this.exportCSV());

    // Modal actions
    this.btnCloseModal?.addEventListener("click", () => this.closeModal());
    this.btnViewCam?.addEventListener("click", () => {
      if (this.currentIncident?.camera_id) {
        this.closeModal();
        window.app?.switchTab("live");
        window.cameraGrid?.openSingleView(this.currentIncident.camera_id);
      }
    });

    this.btnMarkReviewed?.addEventListener("click", () => {
      if (this.currentIncident) {
        this.dismissActiveAlert(this.currentIncident.id);
        this.closeModal();
      }
    });
  }

  addEvent(rawEvent) {
    const eventType = (rawEvent.event_type || rawEvent.type || "ACTIVITY").toUpperCase();
    const severity = this.classifySeverity(eventType, rawEvent);

    const record = {
      id: "INC-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
      type: eventType,
      severity: severity,
      camera_id: rawEvent.camera_id || "cam_01",
      label: rawEvent.label || rawEvent.event_type || "Activity",
      confidence: rawEvent.confidence || 0.85,
      timestamp: rawEvent.timestamp || Date.now() / 1000,
      details: rawEvent.details || {},
      reviewed: false,
    };

    this.events.unshift(record);
    if (this.events.length > 500) this.events.pop();

    // If Critical or Warning, add to active alerts & highlight camera
    if (severity === "CRITICAL" || severity === "WARNING") {
      this.activeAlerts.unshift(record);
      if (this.activeAlerts.length > 20) this.activeAlerts.pop();

      const bannerText = this.formatEventBrief(record);
      window.cameraGrid?.setCameraAlert(record.camera_id, severity, bannerText);
    }

    this.updateActiveAlertsUI();
    this.render();
  }

  classifySeverity(type, data) {
    if (type.includes("FENCE") || type.includes("INTRUSION") || type.includes("WEAPON") || type.includes("ARMED") || type.includes("WATCHLIST")) {
      return "CRITICAL";
    }
    if (type.includes("LOITER") || type.includes("RUNNING") || type.includes("CROWD") || type.includes("REID")) {
      return "WARNING";
    }
    return "INFO";
  }

  formatEventBrief(ev) {
    if (ev.type.includes("FENCE") || ev.type.includes("INTRUSION")) return "INTRUSION DETECTED";
    if (ev.type.includes("WEAPON") || ev.type.includes("ARMED")) return `WEAPON: ${ev.label.toUpperCase()}`;
    if (ev.type.includes("WATCHLIST") || ev.type.includes("FACE")) return `WATCHLIST: ${ev.details.name || ev.label}`;
    if (ev.type.includes("LOITER")) return "LOITERING DETECTED";
    if (ev.type.includes("RUNNING")) return "RAPID MOVEMENT";
    if (ev.type.includes("CROWD")) return "CROWD FORMATION";
    if (ev.type.includes("PLATE")) return `VEHICLE: ${ev.details.plate || ev.label}`;
    return ev.type;
  }

  updateActiveAlertsUI() {
    if (!this.activeAlertsList || !this.activeAlertsCount) return;

    this.activeAlertsCount.textContent = this.activeAlerts.length;
    if (this.navAlertCount) {
      if (this.activeAlerts.length > 0) {
        this.navAlertCount.textContent = this.activeAlerts.length;
        this.navAlertCount.classList.remove("hidden");
      } else {
        this.navAlertCount.classList.add("hidden");
      }
    }

    if (this.activeAlerts.length === 0) {
      this.activeAlertsList.innerHTML = `<div class="no-alerts-msg">No active security alerts. All sectors normal.</div>`;
      return;
    }

    this.activeAlertsList.innerHTML = this.activeAlerts
      .map((ev) => {
        const timeStr = new Date(ev.timestamp * 1000).toLocaleTimeString();
        const icon = ev.severity === "CRITICAL" ? "🚨" : "⚠";
        const brief = this.formatEventBrief(ev);

        return `
          <div class="active-alert-item sev-${ev.severity.toLowerCase()}" onclick="window.eventLog.openIncidentDetail('${ev.id}')">
            <div class="alert-left">
              <span class="alert-sev-tag sev-${ev.severity.toLowerCase()}">${icon} ${ev.severity}</span>
              <span class="alert-text"><strong>${brief}</strong> — ${ev.camera_id.toUpperCase()}</span>
            </div>
            <span class="alert-time">${timeStr}</span>
          </div>
        `;
      })
      .join("");
  }

  clearActiveAlerts() {
    this.activeAlerts = [];
    this.updateActiveAlertsUI();
  }

  dismissActiveAlert(incidentId) {
    this.activeAlerts = this.activeAlerts.filter((a) => a.id !== incidentId);
    this.updateActiveAlertsUI();
  }

  openIncidentDetail(incidentId) {
    const inc = this.events.find((e) => e.id === incidentId);
    if (!inc || !this.modal) return;

    this.currentIncident = inc;
    const timeStr = new Date(inc.timestamp * 1000).toLocaleTimeString();
    const brief = this.formatEventBrief(inc);

    if (this.modalHeading) this.modalHeading.textContent = `${inc.severity === "CRITICAL" ? "🚨 " : "⚠ "}${brief}`;
    if (this.modalCam) this.modalCam.textContent = inc.camera_id.toUpperCase();
    if (this.modalTime) this.modalTime.textContent = timeStr;
    if (this.modalSev) {
      this.modalSev.textContent = inc.severity;
      this.modalSev.style.color = inc.severity === "CRITICAL" ? "var(--sev-critical)" : inc.severity === "WARNING" ? "var(--sev-warning)" : "var(--sev-info)";
    }
    if (this.modalObject) this.modalObject.textContent = inc.label;

    let desc = `${inc.label} event triggered on ${inc.camera_id}.`;
    if (inc.details.zone) desc = `Object crossed virtual boundary into '${inc.details.zone}'.`;
    if (inc.details.plate) desc = `Vehicle license plate [${inc.details.plate}] recorded.`;
    if (inc.details.name) desc = `Face match against watchlist suspect '${inc.details.name}'.`;
    if (this.modalDesc) this.modalDesc.textContent = desc;

    if (this.modalImg) {
      this.modalImg.src = `/api/stream/${inc.camera_id}`;
    }

    this.modal.classList.remove("hidden");
  }

  closeModal() {
    if (this.modal) this.modal.classList.add("hidden");
    if (this.modalImg) this.modalImg.src = "";
    this.currentIncident = null;
  }

  render() {
    if (!this.eventsTableBody) return;

    const camFilter = this.eventCamFilter?.value || "ALL";
    const filtered = this.events.filter((e) => {
      const matchSev = this.activeFilter === "ALL" || e.severity === this.activeFilter;
      const matchCam = camFilter === "ALL" || e.camera_id === camFilter;
      return matchSev && matchCam;
    });

    if (filtered.length === 0) {
      this.eventsTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center;color:var(--text-sec);padding:24px;">
            No events match current filter (${this.activeFilter}).
          </td>
        </tr>
      `;
      return;
    }

    this.eventsTableBody.innerHTML = filtered
      .map((ev) => {
        const timeStr = new Date(ev.timestamp * 1000).toLocaleTimeString();
        const brief = this.formatEventBrief(ev);
        const icon = ev.severity === "CRITICAL" ? "🚨" : ev.severity === "WARNING" ? "⚠" : "ℹ";

        return `
          <tr onclick="window.eventLog.openIncidentDetail('${ev.id}')" style="cursor:pointer;">
            <td style="font-family:monospace;color:var(--text-sec);">${timeStr}</td>
            <td>
              <span class="alert-sev-tag sev-${ev.severity.toLowerCase()}">${icon} ${ev.severity}</span>
            </td>
            <td style="font-weight:700;">${brief}</td>
            <td style="color:var(--text-sec);">${ev.camera_id.toUpperCase()}</td>
            <td style="color:var(--text-pri);">${ev.details.zone || ev.details.plate || ev.details.name || ev.label}</td>
            <td style="text-align:right;">
              <button class="btn-console-small" onclick="event.stopPropagation(); window.eventLog.openIncidentDetail('${ev.id}')">REVIEW</button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  exportCSV() {
    if (this.events.length === 0) {
      alert("No events to export.");
      return;
    }

    const headers = ["Timestamp", "Severity", "Event Type", "Camera", "Label", "Confidence"];
    const rows = this.events.map((e) => [
      `"${new Date(e.timestamp * 1000).toISOString()}"`,
      `"${e.severity}"`,
      `"${e.type}"`,
      `"${e.camera_id}"`,
      `"${e.label}"`,
      `"${e.confidence}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = `IBVAP_Events_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

window.eventLog = new EventLogController();
