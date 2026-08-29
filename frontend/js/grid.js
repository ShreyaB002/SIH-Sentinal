/**
 * grid.js — Clean 2x3 Surveillance Camera Grid Controller for IBVAP.
 */

class CameraGridController {
  constructor() {
    this.gridContainer = document.getElementById("cameraMatrix");
    this.singleView = document.getElementById("singleCameraView");
    this.singleImg = document.getElementById("singleCamImg");
    this.singleTitle = document.getElementById("singleCamTitle");
    this.btnBack = document.getElementById("btnBackToGrid");

    this.cameras = [
      { id: "cam_01", name: "PERIMETER GATE" },
      { id: "cam_02", name: "CHECKPOINT NORTH" },
      { id: "cam_03", name: "FENCE EAST" },
      { id: "cam_04", name: "ROAD SOUTH" },
      { id: "cam_05", name: "DEPOT ACCESS" },
      { id: "cam_06", name: "WATCHTOWER 3" },
    ];

    this.cameraAlerts = {}; // cam_01 -> { sev, text, timer }

    this.initEvents();
    this.render();
  }

  initEvents() {
    this.btnBack?.addEventListener("click", () => {
      this.closeSingleView();
    });
  }

  render() {
    if (!this.gridContainer) return;

    this.gridContainer.innerHTML = this.cameras
      .map((cam) => {
        const activeAlert = this.cameraAlerts[cam.id];
        const tileClass = activeAlert
          ? activeAlert.sev === "CRITICAL"
            ? "cam-tile tile-critical"
            : "cam-tile tile-warning"
          : "cam-tile";

        return `
          <div class="${tileClass}" id="tile-${cam.id}" onclick="window.cameraGrid.openSingleView('${cam.id}')">
            <div class="cam-tile-header">
              <span class="cam-id-name">CAM ${cam.id.replace("cam_", "")} — ${cam.name}</span>
              <div class="cam-status-box">
                <span class="status-indicator online" id="dot-${cam.id}"></span>
                <span>LIVE</span>
              </div>
            </div>
            <div class="cam-stream-wrapper">
              <img 
                class="stream-video-img" 
                id="stream-${cam.id}" 
                src="/api/stream/${cam.id}" 
                alt="${cam.name}" 
                loading="lazy" 
              />
              ${
                activeAlert
                  ? `<div class="cam-event-banner sev-${activeAlert.sev.toLowerCase()}">
                       <span>${activeAlert.sev === "CRITICAL" ? "🚨" : "⚠"} ${activeAlert.text}</span>
                     </div>`
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");
  }

  openSingleView(cameraId) {
    const cam = this.cameras.find((c) => c.id === cameraId) || { id: cameraId, name: "CAMERA" };
    if (!this.singleView || !this.gridContainer) return;

    this.gridContainer.classList.add("hidden");
    this.singleView.classList.remove("hidden");

    if (this.singleTitle) {
      this.singleTitle.textContent = `CAM ${cam.id.replace("cam_", "")} — ${cam.name}`;
    }
    if (this.singleImg) {
      this.singleImg.src = `/api/stream/${cam.id}`;
    }
  }

  closeSingleView() {
    if (!this.singleView || !this.gridContainer) return;

    this.singleView.classList.add("hidden");
    this.gridContainer.classList.remove("hidden");

    if (this.singleImg) {
      this.singleImg.src = "";
    }
  }

  setCameraAlert(cameraId, severity, text) {
    if (this.cameraAlerts[cameraId]?.timer) {
      clearTimeout(this.cameraAlerts[cameraId].timer);
    }

    const timer = setTimeout(() => {
      delete this.cameraAlerts[cameraId];
      this.render();
    }, 8000);

    this.cameraAlerts[cameraId] = { sev: severity, text: text, timer: timer };
    this.render();
  }
}

window.cameraGrid = new CameraGridController();
