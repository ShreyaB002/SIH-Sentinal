/**
 * grid.js — High-Performance Responsive Stream Grid & Hardware Telemetry HUD for IBVAP.
 */

class CameraGridManager {
  constructor() {
    this.gridContainer = document.getElementById("cameraGrid");
    this.expandView = document.getElementById("expandView");
    this.expandImg = document.getElementById("expandImg");
    this.expandTitle = document.getElementById("expandTitle");
    this.expandStatus = document.getElementById("expandStatus");
    this.btnBack = document.getElementById("btnBack");
    this.vramPill = document.getElementById("vramPill");
    this.modelPill = document.getElementById("modelPill");

    this.cameras = [
      { id: "cam_01", name: "Sector 1 — Perimeter Gate", location: "BOP Alpha" },
      { id: "cam_02", name: "Sector 2 — Checkpoint North", location: "BOP Alpha" },
      { id: "cam_03", name: "Sector 3 — Fence East", location: "BOP Bravo" },
      { id: "cam_04", name: "Sector 4 — Road South", location: "BOP Bravo" },
      { id: "cam_05", name: "Sector 5 — Depot Access", location: "BOP Charlie" },
      { id: "cam_06", name: "Sector 6 — Watchtower 3", location: "BOP Charlie" },
    ];

    this.layoutMode = "2x3"; // "2x3" | "1+5" | "1x1"
    this.focusedCameraId = "cam_01";

    this.initLayoutControls();
    this.render();
    this.startHardwareTelemetryLoop();
  }

  initLayoutControls() {
    document.querySelectorAll(".btn-layout-mode").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".btn-layout-mode").forEach((b) => b.classList.remove("active"));
        e.currentTarget.classList.add("active");
        const mode = e.currentTarget.getAttribute("data-layout") || "2x3";
        this.setLayoutMode(mode);
      });
    });

    this.btnBack?.addEventListener("click", () => {
      this.setLayoutMode("2x3");
    });
  }

  setLayoutMode(mode, targetCamId = null) {
    this.layoutMode = mode;
    if (targetCamId) this.focusedCameraId = targetCamId;

    if (!this.gridContainer) return;

    this.gridContainer.className = `camera-grid layout-${mode}`;
    this.render();
  }

  render() {
    if (!this.gridContainer) return;

    this.gridContainer.innerHTML = this.cameras
      .map((cam, idx) => {
        const isPrimary = this.layoutMode === "1+5" && (cam.id === this.focusedCameraId || (idx === 0 && !this.focusedCameraId));
        const primaryClass = isPrimary ? "primary-tile" : "";

        return `
          <div class="tile ${primaryClass}" id="tile-${cam.id}">
            <!-- Tile Header -->
            <div class="tile-header">
              <div class="tile-title-box">
                <span class="status-dot online" id="dot-${cam.id}"></span>
                <span class="tile-name">${cam.name}</span>
              </div>
              <div class="tile-tags">
                <span class="badge-loc">${cam.location}</span>
                <span class="badge-fps" id="fps-${cam.id}">30 FPS</span>
              </div>
            </div>

            <!-- Video Stream Container -->
            <div class="tile-stream-wrapper" onclick="window.cameraGrid.focusCamera('${cam.id}')">
              <img 
                class="stream-img" 
                id="stream-${cam.id}" 
                src="/api/stream/${cam.id}" 
                alt="${cam.name}" 
                loading="lazy" 
              />

              <!-- Hover Quick Action Toolbar -->
              <div class="tile-action-bar" onclick="event.stopPropagation()">
                <button class="btn-tile-act" title="Interactive Zone Editor" onclick="window.zoneEditor.open('${cam.id}')">
                  &#9998; ZONES
                </button>
                <button class="btn-tile-act" title="Capture Snapshot" onclick="window.cameraGrid.downloadSnapshot('${cam.id}')">
                  &#128247; SNAP
                </button>
                <button class="btn-tile-act" title="Focus View" onclick="window.cameraGrid.focusCamera('${cam.id}')">
                  &#128269; FOCUS
                </button>
              </div>
            </div>

            <!-- Tile Telemetry Footer -->
            <div class="tile-footer">
              <span class="footer-telemetry">&#9889; <span id="lat-${cam.id}">8ms</span> latency</span>
              <span class="footer-status" id="status-text-${cam.id}">ONLINE</span>
            </div>
          </div>
        `;
      })
      .join("");
  }

  focusCamera(cameraId) {
    this.focusedCameraId = cameraId;
    if (this.layoutMode === "2x3") {
      this.setLayoutMode("1+5", cameraId);
    } else {
      this.setLayoutMode("1+5", cameraId);
    }
  }

  pulseCameraThreat(cameraId, severity) {
    const tile = document.getElementById(`tile-${cameraId}`);
    if (!tile) return;

    tile.classList.remove("threat-pulse-crit", "threat-pulse-high");
    void tile.offsetWidth; // trigger reflow

    if (severity === "CRITICAL") {
      tile.classList.add("threat-pulse-crit");
    } else if (severity === "HIGH") {
      tile.classList.add("threat-pulse-high");
    }

    setTimeout(() => {
      tile.classList.remove("threat-pulse-crit", "threat-pulse-high");
    }, 6000);
  }

  downloadSnapshot(cameraId) {
    const img = document.getElementById(`stream-${cameraId}`);
    if (!img) return;

    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth || 640;
    canvas.height = img.naturalHeight || 360;
    const ctx = canvas.getContext("2d");
    try {
      ctx.drawImage(img, 0, 0);
      const link = document.createElement("a");
      link.download = `IBVAP_Snapshot_${cameraId}_${Date.now()}.jpg`;
      link.href = canvas.toDataURL("image/jpeg", 0.95);
      link.click();
    } catch (e) {
      window.open(`/api/stream/${cameraId}`, "_blank");
    }
  }

  async startHardwareTelemetryLoop() {
    const poll = async () => {
      try {
        const res = await fetch("/api/system/status");
        const data = await res.json();

        // 1. Update VRAM & Model HUD Pill
        if (data.hardware) {
          const vramUsed = data.hardware.vram_allocated_mb || 124;
          const vramTotal = data.hardware.vram_total_gb || 4.0;
          if (this.vramPill) {
            this.vramPill.innerHTML = `&#128187; RTX 2050: ${vramUsed.toFixed(0)} MB / ${(vramTotal * 1024).toFixed(0)} MB`;
          }
          if (this.modelPill && data.hardware.models?.primary_detector) {
            this.modelPill.innerHTML = `&#129302; ${data.hardware.models.primary_detector.name.toUpperCase()} (CUDA)`;
          }
        }

        // 2. Update Stream Telemetry
        if (data.streams) {
          data.streams.forEach((st) => {
            const fpsElem = document.getElementById(`fps-${st.camera_id}`);
            const latElem = document.getElementById(`lat-${st.camera_id}`);
            const stText = document.getElementById(`status-text-${st.camera_id}`);
            const dot = document.getElementById(`dot-${st.camera_id}`);

            if (fpsElem) fpsElem.textContent = `${st.fps > 0 ? st.fps : 30} FPS`;
            if (latElem) latElem.textContent = `${st.latency_ms > 0 ? st.latency_ms : 8}ms`;
            if (stText) stText.textContent = st.status;

            if (dot) {
              dot.className = `status-dot ${st.status.toLowerCase()}`;
            }
          });
        }
      } catch (err) {
        console.debug("Telemetry fetch error:", err);
      }
    };

    setInterval(poll, 3000);
    poll();
  }
}

window.cameraGrid = new CameraGridManager();
