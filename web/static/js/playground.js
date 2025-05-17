class PlaygroundUI {
    constructor() {
        this.ws = new WebSocket(`ws://${window.location.host}/ws`);
        this.selectedModel = null;
        this.selectedScenario = null;
        this.setupWebSocket();
        this.loadModels();
        this.loadScenarios();
        this.setupEventListeners();
    }

    setupWebSocket() {
        this.ws.onopen = () => {
            console.log('WebSocket connection established');
            this.appendLog('Connected to server');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateMetrics(data);
            this.appendLog(JSON.stringify(data, null, 2));
        };

        this.ws.onclose = () => {
            console.log('WebSocket connection closed');
            this.appendLog('Disconnected from server');
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.appendLog('Error: ' + error.message);
        };
    }

    async loadModels() {
        try {
            const response = await fetch("/api/models");
            const models = await response.json();
            this.renderModels(models);
        } catch (error) {
            console.error("Error loading models:", error);
            this.appendLog("Failed to load models: " + error.message);
        }
    }

    async loadScenarios() {
        try {
            const response = await fetch("/api/scenarios");
            const scenarios = await response.json();
            this.renderScenarios(scenarios);
        } catch (error) {
            console.error("Error loading scenarios:", error);
            this.appendLog("Failed to load scenarios: " + error.message);
        }
    }

    renderModels(models) {
        const modelList = document.getElementById("model-list");
        modelList.innerHTML = '';

        models.forEach(model => {
            const modelItem = document.createElement("div");
            modelItem.className = "model-item";
            modelItem.textContent = `${model.name} (${model.type})`;
            modelItem.dataset.modelId = model.id;
            
            modelItem.addEventListener("click", () => {
                document.querySelectorAll(".model-item").forEach(item => {
                    item.classList.remove("selected");
                });
                modelItem.classList.add("selected");
                this.selectedModel = model.id;
                this.checkStartEnabled();
            });
            
            modelList.appendChild(modelItem);
        });

        // Add start evaluation button
        const buttonContainer = document.createElement("div");
        buttonContainer.style.marginTop = "20px";
        buttonContainer.style.textAlign = "center";
        
        const startButton = document.createElement("button");
        startButton.className = "evaluation-button";
        startButton.id = "start-evaluation";
        startButton.textContent = "Start Evaluation";
        startButton.disabled = true;
        
        buttonContainer.appendChild(startButton);
        modelList.appendChild(buttonContainer);
    }

    renderScenarios(scenarios) {
        const scenarioList = document.getElementById("scenario-list");
        scenarioList.innerHTML = '';

        scenarios.forEach(scenario => {
            const scenarioItem = document.createElement("div");
            scenarioItem.className = "scenario-item";
            scenarioItem.textContent = `${scenario.name} (${scenario.type})`;
            scenarioItem.dataset.scenarioId = scenario.id;
            
            scenarioItem.addEventListener("click", () => {
                document.querySelectorAll(".scenario-item").forEach(item => {
                    item.classList.remove("selected");
                });
                scenarioItem.classList.add("selected");
                this.selectedScenario = scenario.id;
                this.checkStartEnabled();
            });
            
            scenarioList.appendChild(scenarioItem);
        });
    }

    checkStartEnabled() {
        const startButton = document.getElementById("start-evaluation");
        if (this.selectedModel && this.selectedScenario) {
            startButton.disabled = false;
        } else {
            startButton.disabled = true;
        }
    }

    setupEventListeners() {
        document.addEventListener("DOMContentLoaded", () => {
            document.body.addEventListener("click", (event) => {
                if (event.target.id === "start-evaluation") {
                    this.startEvaluation();
                }
            });
        });
    }

    startEvaluation() {
        if (!this.selectedModel || !this.selectedScenario) {
            this.appendLog("Please select both a model and a scenario");
            return;
        }

        const request = {
            model: this.selectedModel,
            scenario: this.selectedScenario,
        };

        this.ws.send(JSON.stringify(request));
        this.appendLog(`Starting evaluation with model ${this.selectedModel} and scenario ${this.selectedScenario}`);
        
        // Clear previous metrics
        document.getElementById("metrics-display").innerHTML = '';
    }

    updateMetrics(data) {
        const metricsDisplay = document.getElementById("metrics-display");

        // Create metrics cards
        if (data.metrics) {
            metricsDisplay.innerHTML = '';
            
            Object.entries(data.metrics).forEach(([key, value]) => {
                const metricCard = document.createElement("div");
                metricCard.className = "metric-card";
                
                const metricTitle = document.createElement("div");
                metricTitle.className = "metric-title";
                metricTitle.textContent = this.formatMetricName(key);
                
                const metricValue = document.createElement("div");
                metricValue.className = "metric-value";
                metricValue.textContent = typeof value === 'number' ? value.toFixed(2) : value;
                
                metricCard.appendChild(metricTitle);
                metricCard.appendChild(metricValue);
                metricsDisplay.appendChild(metricCard);
            });
        }
    }

    formatMetricName(name) {
        return name
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    appendLog(message) {
        const logOutput = document.getElementById("log-output");
        const logEntry = document.createElement("div");
        
        const timestamp = new Date().toLocaleTimeString();
        logEntry.textContent = `[${timestamp}] ${message}`;
        
        logOutput.appendChild(logEntry);
        logOutput.scrollTop = logOutput.scrollHeight;
    }
}

// Initialize the UI
document.addEventListener("DOMContentLoaded", () => {
    window.playgroundUI = new PlaygroundUI();
}); 