/**
 * app.js — Master Application Controller for IBVAP Border Surveillance Console.
 */

class AppController {
  constructor() {
    this.activeTab = "live";
    this.initNavigation();
    this.initClock();
    this.initSystemStatus();
  }

  initNavigation() {
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const targetTab = e.currentTarget.getAttribute("data-tab");
        this.switchTab(targetTab);
      });
    });
  }

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update Nav Tabs
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      if (btn.getAttribute("data-tab") === tabName) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // Update Tab Panes
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      if (pane.id === `tab-${tabName}`) {
        pane.classList.remove("hidden");
      } else {
        pane.classList.add("hidden");
      }
    });

    // If switching to cameras or events, trigger render
    if (tabName === "cameras" && window.camerasManager) {
      window.camerasManager.render();
    } else if (tabName === "events" && window.eventLog) {
      window.eventLog.render();
    }
  }

  initClock() {
    const clockElem = document.getElementById("consoleClock");
    const update = () => {
      if (clockElem) {
        const d = new Date();
        clockElem.textContent = d.toTimeString().split(" ")[0];
      }
    };
    setInterval(update, 1000);
    update();
  }

  async initSystemStatus() {
    const statusElem = document.getElementById("sysStatus");
    const check = async () => {
      try {
        const res = await fetch("/api/cameras");
        if (res.ok) {
          if (statusElem) {
            statusElem.innerHTML = `<span class="status-indicator online"></span> SYSTEM ONLINE`;
          }
        } else {
          if (statusElem) {
            statusElem.innerHTML = `<span class="status-indicator offline"></span> SYSTEM OFFLINE`;
          }
        }
      } catch (e) {
        if (statusElem) {
          statusElem.innerHTML = `<span class="status-indicator offline"></span> SYSTEM OFFLINE`;
        }
      }
    };
    setInterval(check, 5000);
    check();
  }
}

window.app = new AppController();
