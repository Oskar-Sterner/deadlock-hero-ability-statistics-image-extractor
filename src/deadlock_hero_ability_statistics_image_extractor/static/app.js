class ExtractionDashboard {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;

    this.startBtn = document.getElementById("start-btn");
    this.stopBtn = document.getElementById("stop-btn");
    this.statusIndicator = document.getElementById("status-indicator");
    this.logContent = document.getElementById("log-content");
    this.heroGrid = document.getElementById("hero-grid");

    this.initializeWebSocket();
    this.bindEvents();
  }

  initializeWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log("WebSocket disconnected");
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.initializeWebSocket();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  bindEvents() {
    this.startBtn.addEventListener("click", () => this.startExtraction());
    this.stopBtn.addEventListener("click", () => this.stopExtraction());
  }

  async startExtraction() {
    try {
      const response = await fetch("/start-extraction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const result = await response.json();

      if (result.status === "success") {
        this.updateExtractionStatus(true);
        this.addLogEntry("Extraction started...");
      } else {
        this.addLogEntry(`Error: ${result.message}`);
      }
    } catch (error) {
      this.addLogEntry(`Error starting extraction: ${error.message}`);
    }
  }

  async stopExtraction() {
    try {
      const response = await fetch("/stop-extraction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const result = await response.json();

      if (result.status === "success") {
        this.addLogEntry("Stop signal sent...");
      } else {
        this.addLogEntry(`Error: ${result.message}`);
      }
    } catch (error) {
      this.addLogEntry(`Error stopping extraction: ${error.message}`);
    }
  }

  updateExtractionStatus(running) {
    if (running) {
      this.statusIndicator.textContent = "Running";
      this.statusIndicator.className = "status running";
      this.startBtn.disabled = true;
      this.stopBtn.disabled = false;
    } else {
      this.statusIndicator.textContent = "Idle";
      this.statusIndicator.className = "status idle";
      this.startBtn.disabled = false;
      this.stopBtn.disabled = true;
    }
  }

  addLogEntry(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement("div");
    logEntry.className = "log-entry";
    logEntry.textContent = `[${timestamp}] ${message}`;

    this.logContent.appendChild(logEntry);

    requestAnimationFrame(() => {
      this.logContent.scrollTop = this.logContent.scrollHeight;
    });

    if (this.logContent.children.length > 100) {
      this.logContent.removeChild(this.logContent.firstChild);
      requestAnimationFrame(() => {
        this.logContent.scrollTop = this.logContent.scrollHeight;
      });
    }
  }

  updateHeroAbilityImage(heroId, abilityIndex, filename) {
    const heroCard = document.querySelector(`[data-hero-id="${heroId}"]`);
    if (!heroCard) return;

    const abilitySlot = heroCard.querySelector(
      `[data-ability="${abilityIndex + 1}"]`
    );
    if (!abilitySlot) return;

    const existingImage = abilitySlot.querySelector(".ability-image");
    const placeholder = abilitySlot.querySelector(".placeholder");

    if (existingImage) {
      existingImage.src = `/images/abilities/${filename}`;
    } else {
      if (placeholder) {
        placeholder.remove();
      }

      const img = document.createElement("img");
      img.src = `/images/abilities/${filename}`;
      img.alt = `Hero ${heroId} Ability ${abilityIndex + 1}`;
      img.className = "ability-image";

      img.onload = () => {
        abilitySlot.style.animation = "none";
        abilitySlot.offsetHeight;
        abilitySlot.style.animation = "pulse 0.5s ease-in-out";
      };

      abilitySlot.appendChild(img);
    }
  }

  handleMessage(data) {
    switch (data.type) {
      case "status":
        this.addLogEntry(data.message);
        break;

      case "image_update":
        this.updateHeroAbilityImage(
          data.hero_id,
          data.ability_index,
          data.filename
        );
        this.addLogEntry(
          `Updated Hero ${data.hero_id} Ability ${data.ability_index + 1}`
        );
        break;

      case "extraction_finished":
        this.updateExtractionStatus(false);
        this.addLogEntry("Extraction finished");
        break;

      default:
        console.log("Unknown message type:", data.type);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new ExtractionDashboard();
});
