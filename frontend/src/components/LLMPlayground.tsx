import React, { useEffect, useRef, useState } from 'react';
import './LLMPlayground.css';

interface Model {
  id: string;
  name: string;
  type: string;
  maxTokens: number;
}

interface Scenario {
  id: string;
  name: string;
  type: string;
  description: string;
}

interface MetricData {
  [key: string]: number | string;
}

interface EvaluationResult {
  model: string;
  scenario: string;
  metrics: MetricData;
  events?: any[];
}

const LLMPlayground: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MetricData | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load models and scenarios
    fetchModels();
    fetchScenarios();

    // Setup WebSocket
    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    // Scroll to bottom of logs
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const setupWebSocket = () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = () => {
      appendLog('Connected to server');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as EvaluationResult;
        if (data.metrics) {
          setMetrics(data.metrics);
        }
        appendLog(JSON.stringify(data, null, 2));
      } catch (error) {
        appendLog(`Error parsing message: ${error}`);
      }
    };

    ws.onclose = () => {
      appendLog('Disconnected from server');
    };

    ws.onerror = (error) => {
      appendLog(`WebSocket error: ${error.type}`);
    };

    wsRef.current = ws;
  };

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/models');
      const data = await response.json();
      setModels(data);
    } catch (error) {
      appendLog(`Failed to load models: ${error}`);
    }
  };

  const fetchScenarios = async () => {
    try {
      const response = await fetch('/api/scenarios');
      const data = await response.json();
      setScenarios(data);
    } catch (error) {
      appendLog(`Failed to load scenarios: ${error}`);
    }
  };

  const appendLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [...prevLogs, `[${timestamp}] ${message}`]);
  };

  const formatMetricName = (name: string) => {
    return name
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const startEvaluation = () => {
    if (!selectedModel || !selectedScenario || !wsRef.current) {
      appendLog('Please select both a model and a scenario');
      return;
    }

    const request = {
      model: selectedModel,
      scenario: selectedScenario,
    };

    wsRef.current.send(JSON.stringify(request));
    appendLog(`Starting evaluation with model ${selectedModel} and scenario ${selectedScenario}`);
    setMetrics(null);
  };

  return (
    <div className="playground-container">
      <div className="models-panel">
        <h2>Available Models</h2>
        <div className="model-list">
          {models.map(model => (
            <div 
              key={model.id}
              className={`model-item ${selectedModel === model.id ? 'selected' : ''}`}
              onClick={() => setSelectedModel(model.id)}
            >
              {model.name} ({model.type})
            </div>
          ))}
        </div>
        <div className="button-container">
          <button 
            className="evaluation-button"
            disabled={!selectedModel || !selectedScenario}
            onClick={startEvaluation}
          >
            Start Evaluation
          </button>
        </div>
      </div>

      <div className="scenario-panel">
        <h2>Test Scenarios</h2>
        <div className="scenario-list">
          {scenarios.map(scenario => (
            <div 
              key={scenario.id}
              className={`scenario-item ${selectedScenario === scenario.id ? 'selected' : ''}`}
              onClick={() => setSelectedScenario(scenario.id)}
            >
              {scenario.name} ({scenario.type})
              <div className="scenario-description">{scenario.description}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="evaluation-panel">
        <h2>Live Evaluation</h2>
        <div className="metrics-display">
          {metrics ? (
            Object.entries(metrics).map(([key, value]) => (
              <div key={key} className="metric-card">
                <div className="metric-title">{formatMetricName(key)}</div>
                <div className="metric-value">
                  {typeof value === 'number' ? value.toFixed(2) : value}
                </div>
              </div>
            ))
          ) : (
            <div className="no-metrics">No metrics available</div>
          )}
        </div>
        <div className="log-output">
          {logs.map((log, index) => (
            <div key={index} className="log-entry">{log}</div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};

export default LLMPlayground; 