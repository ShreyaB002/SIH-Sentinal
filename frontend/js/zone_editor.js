/**
 * zone_editor.js — In-Browser Interactive Polygon Zone Drawer & Editor for IBVAP.
 * Allows operators to draw and edit virtual fence boundaries directly on the live camera stream.
 */

class ZoneEditor {
  constructor() {
    this.modal = document.getElementById("zoneEditorModal");
    this.canvas = document.getElementById("zoneCanvas");
    this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
    this.img = document.getElementById("zoneStreamImg");
    this.cameraSelect = document.getElementById("zoneCameraSelect");
    this.zoneNameInput = document.getElementById("zoneNameInput");
    this.statusElem = document.getElementById("zoneStatus");

    this.activeCameraId = "cam_01";
    this.points = []; // current polygon vertices [(x, y), ...]
    this.zones = [];  // list of existing zones [{name: "", polygon: []}]

    this.initEvents();
  }

  initEvents() {
    if (!this.canvas) return;

    // Canvas click to add vertex
    this.canvas.addEventListener("click", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;

      const x = Math.round((e.clientX - rect.left) * scaleX);
      const y = Math.round((e.clientY - rect.top) * scaleY);

      this.points.push([x, y]);
      this.render();
    });

    document.getElementById("btnOpenZoneEditor")?.addEventListener("click", () => this.open("cam_01"));
    document.getElementById("btnCloseZoneEditor")?.addEventListener("click", () => this.close());
    document.getElementById("btnClearZonePoints")?.addEventListener("click", () => {
      this.points = [];
      this.render();
    });
    document.getElementById("btnSaveZone")?.addEventListener("click", () => this.saveCurrentZone());
    document.getElementById("btnResetZones")?.addEventListener("click", () => this.resetZones());

    this.cameraSelect?.addEventListener("change", (e) => {
      this.open(e.target.value);
    });
  }

  async open(cameraId) {
    this.activeCameraId = cameraId;
    if (this.cameraSelect) this.cameraSelect.value = cameraId;

    this.modal.classList.remove("hidden");
    this.points = [];

    // Set preview feed source
    if (this.img) {
      this.img.src = `/api/stream/${cameraId}`;
    }

    // Fetch existing zones
    try {
      const res = await fetch(`/api/zones/${cameraId}`);
      const data = await res.json();
      this.zones = data.zones || [];
      if (this.zones.length > 0 && this.zones[0].polygon) {
        this.points = [...this.zones[0].polygon];
      }
    } catch (err) {
      console.warn("Could not fetch zones:", err);
      this.zones = [];
    }

    this.render();
  }

  close() {
    this.modal.classList.add("hidden");
    if (this.img) this.img.src = "";
  }

  render() {
    if (!this.ctx) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.clearRect(0, 0, w, h);

    // Draw existing points & lines
    if (this.points.length === 0) return;

    this.ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
    this.ctx.strokeStyle = "#ef4444";
    this.ctx.lineWidth = 2.5;

    this.ctx.beginPath();
    this.ctx.moveTo(this.points[0][0], this.points[0][1]);
    for (let i = 1; i < this.points.length; i++) {
      this.ctx.lineTo(this.points[i][0], this.points[i][1]);
    }
    if (this.points.length >= 3) {
      this.ctx.closePath();
      this.ctx.fill();
    }
    this.ctx.stroke();

    // Draw handles on vertices
    this.points.forEach(([x, y], idx) => {
      this.ctx.fillStyle = "#ffffff";
      this.ctx.beginPath();
      this.ctx.arc(x, y, 5, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.strokeStyle = "#ef4444";
      this.ctx.stroke();

      this.ctx.fillStyle = "#e2e8f0";
      this.ctx.font = "10px sans-serif";
      this.ctx.fillText(`P${idx + 1}`, x + 7, y - 5);
    });
  }

  async saveCurrentZone() {
    if (this.points.length < 3) {
      this.setStatus("Please place at least 3 vertices for a polygon zone.", "red");
      return;
    }

    const zoneName = this.zoneNameInput?.value?.trim() || "Restricted Zone A";
    const payload = {
      zones: [
        {
          name: zoneName,
          polygon: this.points,
        },
      ],
    };

    try {
      this.setStatus("Saving zone to live pipeline...", "amber");
      const res = await fetch(`/api/zones/${this.activeCameraId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.status === "success") {
        this.setStatus(`Zone '${zoneName}' updated live!`, "green");
      } else {
        this.setStatus("Error saving zone: " + data.message, "red");
      }
    } catch (err) {
      this.setStatus("Save failed: " + err.message, "red");
    }
  }

  async resetZones() {
    this.points = [
      [80, 80],
      [560, 80],
      [560, 280],
      [80, 280],
    ];
    this.render();
    await this.saveCurrentZone();
  }

  setStatus(msg, color) {
    if (!this.statusElem) return;
    this.statusElem.textContent = msg;
    this.statusElem.style.color = color === "green" ? "#22c55e" : color === "amber" ? "#f59e0b" : "#ef4444";
  }
}

window.zoneEditor = new ZoneEditor();
