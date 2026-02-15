class ExtractionDashboard {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;

    this.startBtn = document.getElementById("start-btn");
    this.stopBtn = document.getElementById("stop-btn");
    this.statusIndicator = document.getElementById("status-indicator");
    this.logContainer = document.getElementById("log-container");
    this.logContent = document.getElementById("log-content");
    this.heroGrid = document.getElementById("hero-grid");
    this.itemList = document.getElementById("item-list");
    this.itemEmptyState = document.getElementById("item-empty-state");
    this.extractModeAbilityControl =
      document.getElementById("extract-mode-ability") ||
      document.getElementById("extract-abilities");
    this.extractModeItemsControl =
      document.getElementById("extract-mode-items") ||
      document.getElementById("extract-items");
    this.extractionModeControls = Array.from(
      document.querySelectorAll('input[name="extract-mode"]')
    );

    if (
      this.extractionModeControls.length === 0 &&
      this.extractModeAbilityControl &&
      this.extractModeItemsControl
    ) {
      this.extractionModeControls = [
        this.extractModeAbilityControl,
        this.extractModeItemsControl,
      ];
    }

    this.initializeWebSocket();
    this.bindEvents();
  }

  upsertItemTooltip(itemId, itemName, filename) {
    if (!this.itemList || !filename) {
      return;
    }

    if (this.itemEmptyState) {
      this.itemEmptyState.style.display = "none";
    }

    const normalizedItemId = String(itemId ?? "");
    const existingByFilename = this.itemList.querySelector(
      `a[href="/images/items/${filename}"]`
    );
    const existingByItemId = normalizedItemId
      ? this.itemList.querySelector(`li[data-item-id="${normalizedItemId}"]`)
      : null;
    const existingItem = existingByFilename?.closest("li") || existingByItemId;

    const itemLink = document.createElement("a");
    itemLink.href = `/images/items/${filename}`;
    itemLink.target = "_blank";
    itemLink.rel = "noopener";

    const previewImage = document.createElement("img");
    previewImage.src = `/images/items/${filename}`;
    previewImage.alt = filename;
    previewImage.className = "item-image-preview";
    previewImage.loading = "lazy";

    const filenameLabel = document.createElement("span");
    filenameLabel.className = "item-filename";
    filenameLabel.textContent = filename;

    itemLink.appendChild(previewImage);
    itemLink.appendChild(filenameLabel);

    if (existingItem) {
      existingItem.setAttribute("data-item-id", normalizedItemId);
      existingItem.className = "item-card";
      existingItem.innerHTML = "";
      existingItem.appendChild(itemLink);
      return;
    }

    const itemRow = document.createElement("li");
    itemRow.className = "item-card";
    itemRow.setAttribute("data-item-id", normalizedItemId);
    itemRow.setAttribute("title", itemName || "");
    itemRow.appendChild(itemLink);
    this.itemList.prepend(itemRow);
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
    if (!this.startBtn || !this.stopBtn) {
      return;
    }

    this.startBtn.addEventListener("click", () => this.startExtraction());
    this.stopBtn.addEventListener("click", () => this.stopExtraction());
  }

  getSelectedExtractionMode() {
    const checkedModeControl = document.querySelector(
      'input[name="extract-mode"]:checked'
    );
    if (checkedModeControl) {
      return checkedModeControl.value === "items" ? "items" : "ability";
    }

    if (this.extractModeItemsControl?.checked) {
      return "items";
    }

    return "ability";
  }

  async startExtraction() {
    try {
      const extractionMode = this.getSelectedExtractionMode();

      const response = await fetch("/start-extraction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          extraction_mode: extractionMode,
        }),
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
    if (!this.statusIndicator || !this.startBtn || !this.stopBtn) {
      return;
    }

    if (running) {
      this.statusIndicator.textContent = "Running";
      this.statusIndicator.className = "status running";
      this.startBtn.disabled = true;
      this.stopBtn.disabled = false;
      this.extractionModeControls.forEach((control) => {
        control.disabled = true;
      });
    } else {
      this.statusIndicator.textContent = "Idle";
      this.statusIndicator.className = "status idle";
      this.startBtn.disabled = false;
      this.stopBtn.disabled = true;
      this.extractionModeControls.forEach((control) => {
        control.disabled = false;
      });
    }
  }

  addLogEntry(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement("div");
    logEntry.className = "log-entry";
    logEntry.textContent = `[${timestamp}] ${message}`;

    this.logContent.appendChild(logEntry);

    requestAnimationFrame(() => {
      this.logContainer.scrollTop = this.logContainer.scrollHeight;
    });

    if (this.logContent.children.length > 100) {
      this.logContent.removeChild(this.logContent.firstChild);
      requestAnimationFrame(() => {
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
      });
    }
  }

  updateHeroAbilityImage(heroId, abilityIndex, filename) {
    const heroCard = document.querySelector(`[data-hero-id="${heroId}"]`);
    if (!heroCard) return;

    const abilitySlot = heroCard.querySelector(
      `[data-ability="${abilityIndex}"]`
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
      img.alt = `Hero ${heroId} Ability ${abilityIndex}`;
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
          `Updated Hero ${data.hero_id} Ability ${data.ability_index}`
        );
        break;

      case "item_update":
        this.upsertItemTooltip(data.item_id, data.item_name, data.filename);
        this.addLogEntry(
          `Updated item ${data.item_name} (${data.item_id})`
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
