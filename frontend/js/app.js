/**
 * app.js — Master Application Controller & Navigation for IBVAP Console.
 */

class AppController {
  constructor() {
    this.activeTab = "live";
    this.initNavigation();
    this.initClock();
    this.initSystemHealth();
  }

  initNavigation() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const targetTab = e.currentTarget.getAttribute("data-tab");
        this.switchTab(targetTab);
      });
    });
  }

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update Nav Buttons
    document.querySelectorAll(".nav-btn").forEach((btn) => {
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

    if (tabName === "system" && window.camerasManager) {
      window.camerasManager.render();
    } else if (tabName === "events" && window.eventLog) {
      window.eventLog.renderEventsTable();
    }
  }

  initClock() {
    const clockElem = document.getElementById("systemClock");
    const update = () => {
      if (clockElem) {
        const d = new Date();
        clockElem.textContent = d.toTimeString().split(" ")[0];
      }
    };
    setInterval(update, 1000);
    update();
  }

  async initSystemHealth() {
    const statusText = document.querySelector(".sys-status-text");
    const check = async () => {
      try {
        const res = await fetch("/api/cameras");
        if (res.ok && statusText) {
          statusText.textContent = "SYSTEM ONLINE";
        }
      } catch (e) {
        if (statusText) {
          statusText.textContent = "SYSTEM OFFLINE";
        }
      }
    };
    setInterval(check, 8000);
    check();
  }
}

window.app = new AppController();
