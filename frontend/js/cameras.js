/**
 * cameras.js — Camera Management & Perimeter Tool Launcher for IBVAP.
 */

class CamerasManagementController {
  constructor() {
    this.gridList = document.getElementById("camerasGridList");
    this.btnWatchlist = document.getElementById("btnOpenWatchlistModal");
    this.btnANPR = document.getElementById("btnOpenANPRModal");

    this.cameras = [
      { id: "cam_01", name: "Perimeter Gate", type: "RTSP / IP", status: "ONLINE" },
      { id: "cam_02", name: "Checkpoint North", type: "RTSP / IP", status: "ONLINE" },
      { id: "cam_03", name: "Fence East", type: "RTSP / IP", status: "ONLINE" },
      { id: "cam_04", name: "Road South", type: "RTSP / IP", status: "ONLINE" },
      { id: "cam_05", name: "Depot Access", type: "RTSP / IP", status: "ONLINE" },
      { id: "cam_06", name: "Watchtower 3", type: "RTSP / IP", status: "ONLINE" },
    ];

    this.initEvents();
  }

  initEvents() {
    this.btnWatchlist?.addEventListener("click", () => {
      document.getElementById("watchlistModal")?.classList.remove("hidden");
      if (typeof window.renderWatchlist === "function") {
        window.renderWatchlist();
      }
    });

    this.btnANPR?.addEventListener("click", () => {
      window.anprLog?.open();
    });
  }

  render() {
    if (!this.gridList) return;

    this.gridList.innerHTML = this.cameras
      .map((cam) => {
        return `
          <div class="camera-card">
            <div class="cam-card-head">
              <span class="cam-card-title">CAM ${cam.id.replace("cam_", "")} — ${cam.name}</span>
              <span class="status-indicator online"></span>
            </div>
            <div style="font-size:11px;color:var(--text-sec);">
              Source: ${cam.type} &bull; Status: <strong style="color:var(--status-online)">ONLINE</strong>
            </div>
            <div class="cam-card-actions">
              <button class="btn-console" onclick="window.camerasManager.openFeed('${cam.id}')">VIEW FEED</button>
              <button class="btn-console" onclick="window.zoneEditor.open('${cam.id}')">&#9998; CONFIGURE ZONES</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  openFeed(cameraId) {
    window.app?.switchTab("live");
    window.cameraGrid?.openSingleView(cameraId);
  }
}

window.camerasManager = new CamerasManagementController();
