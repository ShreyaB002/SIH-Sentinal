/**
 * grid.js — Clean 2x3 Surveillance Matrix Controller matching official mock.
 */

class CameraGridController {
  constructor() {
    this.gridContainer = document.getElementById("cameraGrid");
    this.singleView = document.getElementById("singleStreamView");
    this.singleImg = document.getElementById("singleStreamImg");
    this.singleTitle = document.getElementById("singleStreamTitle");
    this.btnBack = document.getElementById("btnBackToGrid");

    this.cameras = [
      { id: "cam_01", name: "Perimeter Gate" },
      { id: "cam_02", name: "Checkpoint North" },
      { id: "cam_03", name: "Fence East" },
      { id: "cam_04", name: "Road South" },
      { id: "cam_05", name: "Depot Access" },
      { id: "cam_06", name: "Watchtower 3" },
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
        const num = cam.id.replace("cam_", "");
        const activeAlert = this.cameraAlerts[cam.id];
        
        let alertClass = "";
        if (activeAlert) {
          alertClass = activeAlert.sev === "CRITICAL" ? "alert-critical" : "alert-warning";
        }

        return `
          <div class="cam-tile ${alertClass}" id="tile-${cam.id}" onclick="window.cameraGrid.openSingleView('${cam.id}')">
            <div class="cam-tile-head">
              <div class="cam-title-left">
                <span class="cam-status-dot"></span>
                <span class="cam-name-text">CAM ${num} &nbsp;${cam.name}</span>
              </div>
              <button class="cam-opts-btn" onclick="event.stopPropagation(); window.zoneEditor.open('${cam.id}')">&#8942;</button>
            </div>
            
            <div class="cam-video-box">
              <img 
                class="cam-feed-img" 
                id="feed-${cam.id}" 
                src="/api/stream/${cam.id}" 
                alt="${cam.name}" 
                loading="lazy" 
              />
              <div class="cam-tile-bottom">
                <div class="cam-live-indicator">
                  <span class="cam-live-dot"></span>
                  <span>LIVE</span>
                </div>
                ${
                  activeAlert
                    ? `<div class="cam-alert-pill ${activeAlert.sev === "CRITICAL" ? "critical" : "warning"}">
                         <span>&#9888; ${activeAlert.text}</span>
                       </div>`
                    : ""
                }
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  openSingleView(cameraId) {
    const cam = this.cameras.find((c) => c.id === cameraId) || { id: cameraId, name: "Camera" };
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
    }, 10000);

    this.cameraAlerts[cameraId] = { sev: severity, text: text, timer: timer };
    this.render();
  }
}

window.cameraGrid = new CameraGridController();
