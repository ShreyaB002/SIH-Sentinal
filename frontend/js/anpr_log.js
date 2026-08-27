/**
 * anpr_log.js — ANPR License Plate Log & Vehicle Checkpoint Manager for IBVAP.
 */

class ANPRLogManager {
  constructor() {
    this.modal = document.getElementById("anprModal");
    this.tableBody = document.getElementById("anprTableBody");
    this.searchInput = document.getElementById("anprSearchInput");
    this.records = [];

    this.initEvents();
  }

  initEvents() {
    document.getElementById("btnToggleANPR")?.addEventListener("click", () => this.open());
    document.getElementById("btnCloseANPR")?.addEventListener("click", () => this.close());
    document.getElementById("btnRefreshANPR")?.addEventListener("click", () => this.loadPlates());
    document.getElementById("btnExportANPRCSV")?.addEventListener("click", () => this.exportCSV());

    this.searchInput?.addEventListener("input", () => this.render());
  }

  async open() {
    this.modal?.classList.remove("hidden");
    await this.loadPlates();
  }

  close() {
    this.modal?.classList.add("hidden");
  }

  async loadPlates() {
    if (!this.tableBody) return;
    this.tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-sec);padding:20px;">Fetching license plate records...</td></tr>`;

    try {
      const res = await fetch("/api/plates");
      this.records = await res.json();
      this.render();
    } catch (err) {
      this.tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--red);padding:20px;">Failed to load records: ${err.message}</td></tr>`;
    }
  }

  render() {
    if (!this.tableBody) return;
    const query = this.searchInput?.value?.trim().toUpperCase() || "";
    const filtered = this.records.filter((r) => !query || r.plate_text.toUpperCase().includes(query) || r.camera_id.toUpperCase().includes(query));

    if (filtered.length === 0) {
      this.tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-sec);padding:20px;">No matching license plates logged yet.</td></tr>`;
      return;
    }

    this.tableBody.innerHTML = filtered
      .map((r) => {
        const timeStr = r.timestamp ? new Date(r.timestamp * 1000).toLocaleTimeString() : "--:--:--";
        const confPercent = Math.round((r.confidence || 0.85) * 100);
        return `
          <tr style="border-bottom:1px solid var(--border);">
            <td style="padding:8px 12px;font-family:monospace;font-weight:700;color:var(--green);font-size:13px;letter-spacing:1px;">
              &#128663; ${r.plate_text}
            </td>
            <td style="padding:8px 12px;color:var(--text-pri);">${r.vehicle_type || "Vehicle"}</td>
            <td style="padding:8px 12px;color:var(--text-sec);font-size:12px;">${r.camera_id}</td>
            <td style="padding:8px 12px;">
              <span style="background:rgba(34,197,94,0.15);color:var(--green);padding:2px 6px;border-radius:3px;font-size:11px;font-weight:600;">
                ${confPercent}%
              </span>
            </td>
            <td style="padding:8px 12px;color:var(--text-sec);font-size:12px;">${timeStr}</td>
          </tr>
        `;
      })
      .join("");
  }

  exportCSV() {
    if (this.records.length === 0) {
      alert("No records to export.");
      return;
    }

    const headers = ["Plate Text", "Vehicle Type", "Camera", "Confidence", "Timestamp"];
    const rows = this.records.map((r) => [
      `"${r.plate_text}"`,
      `"${r.vehicle_type || "Vehicle"}"`,
      `"${r.camera_id}"`,
      `"${r.confidence || 0.85}"`,
      `"${new Date((r.timestamp || Date.now() / 1000) * 1000).toISOString()}"`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `ibvap_anpr_plates_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

window.anprLog = new ANPRLogManager();
