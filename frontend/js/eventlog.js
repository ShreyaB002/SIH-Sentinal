/**
 * eventlog.js — Operational Active Alerts Panel & Forensic Incident Log.
 */

class EventLogController {
  constructor() {
    this.alertsContainer = document.getElementById("activeAlertsContainer");
    this.alertsBadge = document.getElementById("activeAlertsBadge");
    this.sidebarBadge = document.getElementById("sidebarEventBadge");
    this.eventsTableBody = document.getElementById("eventsTableBody");
    this.eventCamFilter = document.getElementById("eventCamFilter");
    this.btnViewAll = document.getElementById("btnViewAllEvents");

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
    this.activeAlerts = [];
    this.activeFilter = "ALL";
    this.currentIncident = null;

    this.camNames = {
      cam_01: "Perimeter Gate",
      cam_02: "Checkpoint North",
      cam_03: "Fence East",
      cam_04: "Road South",
      cam_05: "Depot Access",
      cam_06: "Watchtower 3",
    };

    this.initEvents();
  }

  initEvents() {
    // Filter pills on events page
    document.querySelectorAll(".filter-pill").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".filter-pill").forEach((b) => b.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.activeFilter = e.currentTarget.getAttribute("data-sev") || "ALL";
        this.renderEventsTable();
      });
    });

    this.eventCamFilter?.addEventListener("change", () => this.renderEventsTable());
    document.getElementById("btnExportEventsCSV")?.addEventListener("click", () => this.exportCSV());

    // View all events shortcut
    this.btnViewAll?.addEventListener("click", () => {
      window.app?.switchTab("events");
    });

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
      confidence: rawEvent.confidence || 0.88,
      timestamp: rawEvent.timestamp || Date.now() / 1000,
      details: rawEvent.details || {},
      reviewed: false,
    };

    this.events.unshift(record);
    if (this.events.length > 500) this.events.pop();

    if (severity === "CRITICAL" || severity === "WARNING") {
      this.activeAlerts.unshift(record);
      if (this.activeAlerts.length > 20) this.activeAlerts.pop();

      const bannerText = this.formatEventBrief(record).toUpperCase();
      window.cameraGrid?.setCameraAlert(record.camera_id, severity, bannerText);
    }

    this.updateActiveAlertsSidebar();
    this.renderEventsTable();
  }

  classifySeverity(type, data) {
    if (type.includes("FENCE") || type.includes("INTRUSION") || type.includes("WATCHLIST")) {
      return "CRITICAL";
    }
    if (type.includes("VEHICLE") || type.includes("PLATE") || type.includes("LOITER") || type.includes("RUNNING") || type.includes("CROWD") || type.includes("REID")) {
      return "WARNING";
    }
    return "INFO";
  }

  formatEventBrief(ev) {
    if (ev.type.includes("FENCE") || ev.type.includes("INTRUSION")) return "Intrusion Detected";
    if (ev.type.includes("WATCHLIST") || ev.type.includes("FACE")) return `Watchlist: ${ev.details.name || ev.label}`;
    if (ev.type.includes("VEHICLE") || ev.type.includes("PLATE")) return "Vehicle Detected";
    if (ev.type.includes("LOITER")) return "Loitering Detected";
    if (ev.type.includes("RUNNING")) return "Rapid Movement";
    if (ev.type.includes("CROWD")) return "Crowd Detected";
    return ev.type;
  }

  updateActiveAlertsSidebar() {
    if (!this.alertsContainer || !this.alertsBadge) return;

    this.alertsBadge.textContent = this.activeAlerts.length;
    if (this.sidebarBadge) {
      if (this.activeAlerts.length > 0) {
        this.sidebarBadge.textContent = this.activeAlerts.length;
        this.sidebarBadge.classList.remove("hidden");
      } else {
        this.sidebarBadge.classList.add("hidden");
      }
    }

    if (this.activeAlerts.length === 0) {
      this.alertsContainer.innerHTML = `
        <div class="empty-alerts-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <p>No active incidents.<br />All sectors secure.</p>
        </div>
      `;
      return;
    }

    this.alertsContainer.innerHTML = this.activeAlerts
      .map((ev) => {
        const timeStr = new Date(ev.timestamp * 1000).toTimeString().split(" ")[0];
        const brief = this.formatEventBrief(ev);
        const camLabel = `CAM ${ev.camera_id.replace("cam_", "")} &nbsp;${this.camNames[ev.camera_id] || ""}`;
        const sevClass = ev.severity.toLowerCase();

        return `
          <div class="active-alert-card ${sevClass}" onclick="window.eventLog.openIncidentDetail('${ev.id}')">
            <div class="alert-card-top">
              <span class="alert-type-title ${sevClass}">
                <svg class="alert-card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                ${brief}
              </span>
            </div>
            <div class="alert-card-bottom">
              <span class="alert-cam-name">${camLabel}</span>
              <span class="alert-timestamp">${timeStr}</span>
            </div>
          </div>
        `;
      })
      .join("");
  }

  dismissActiveAlert(incidentId) {
    this.activeAlerts = this.activeAlerts.filter((a) => a.id !== incidentId);
    this.updateActiveAlertsSidebar();
  }

  openIncidentDetail(incidentId) {
    const inc = this.events.find((e) => e.id === incidentId);
    if (!inc || !this.modal) return;

    this.currentIncident = inc;
    const timeStr = new Date(inc.timestamp * 1000).toTimeString().split(" ")[0];
    const brief = this.formatEventBrief(inc);

    if (this.modalHeading) this.modalHeading.textContent = `INCIDENT REVIEW — ${brief.toUpperCase()}`;
    if (this.modalCam) this.modalCam.textContent = `CAM ${inc.camera_id.replace("cam_", "")} — ${this.camNames[inc.camera_id] || inc.camera_id}`;
    if (this.modalTime) this.modalTime.textContent = timeStr;
    if (this.modalSev) {
      this.modalSev.textContent = inc.severity;
      this.modalSev.className = `sev-tag ${inc.severity.toLowerCase()}`;
    }
    if (this.modalObject) this.modalObject.textContent = inc.label;

    let desc = `${inc.label} incident detected on sector ${inc.camera_id}.`;
    if (inc.details.zone) desc = `Object breached '${inc.details.zone}' virtual perimeter.`;
    if (inc.details.plate) desc = `License plate [${inc.details.plate}] identified at checkpoint.`;
    if (inc.details.name) desc = `Face match against target watchlist '${inc.details.name}'.`;
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

  renderEventsTable() {
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
          <td colspan="6" style="text-align:center;color:var(--text-sec);padding:28px;">
            No events recorded for current filter (${this.activeFilter}).
          </td>
        </tr>
      `;
      return;
    }

    this.eventsTableBody.innerHTML = filtered
      .map((ev) => {
        const timeStr = new Date(ev.timestamp * 1000).toTimeString().split(" ")[0];
        const brief = this.formatEventBrief(ev);

        return `
          <tr onclick="window.eventLog.openIncidentDetail('${ev.id}')" style="cursor:pointer;">
            <td style="font-family:var(--font-mono);color:var(--text-sec);">${timeStr}</td>
            <td>
              <span class="sev-tag ${ev.severity.toLowerCase()}">${ev.severity}</span>
            </td>
            <td style="font-weight:700;">${brief}</td>
            <td style="color:var(--text-sec);">CAM ${ev.camera_id.replace("cam_", "")} — ${this.camNames[ev.camera_id] || ""}</td>
            <td style="color:var(--text-pri);">${ev.details.zone || ev.details.plate || ev.details.name || ev.label}</td>
            <td style="text-align:right;">
              <button class="btn-clean" onclick="event.stopPropagation(); window.eventLog.openIncidentDetail('${ev.id}')">REVIEW</button>
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

    const headers = ["Timestamp", "Severity", "Event Type", "Camera", "Details", "Confidence"];
    const rows = this.events.map((e) => [
      `"${new Date(e.timestamp * 1000).toISOString()}"`,
      `"${e.severity}"`,
      `"${e.type}"`,
      `"${e.camera_id}"`,
      `"${e.details.zone || e.details.plate || e.details.name || e.label}"`,
      `"${e.confidence}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = `IBVAP_Surveillance_Log_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

window.eventLog = new EventLogController();
