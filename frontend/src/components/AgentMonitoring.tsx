import React, { useEffect, useState, useRef } from 'react';

interface Agent {
  id: string;
  name: string;
  role: string;
  state: string;
}

interface Log {
  timestamp: string;
  agentName: string;
  message: string;
}

const AgentMonitoring: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<string>('Disconnected');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const ws = new WebSocket('ws://localhost:8080/ws');
        
        ws.onopen = () => {
          setConnectionStatus('Connected');
          console.log('Connected to agent monitoring server');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'agentStatus') {
              setAgents(data.agents || []);
            } else if (data.type === 'agentLogs') {
              setLogs(data.logs || []);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onclose = () => {
          setConnectionStatus('Disconnected');
          console.log('Disconnected from agent monitoring server');
          // Attempt to reconnect after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = () => {
          setConnectionStatus('Error');
          console.error('WebSocket error occurred');
        };

        wsRef.current = ws;
      } catch (error) {
        console.error('Failed to establish WebSocket connection:', error);
        setConnectionStatus('Error');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div>
      <h1>Agent Monitoring</h1>
      <div style={{ marginBottom: '10px' }}>
        <strong>Connection Status:</strong> {connectionStatus}
      </div>
      <div>
        <h2>Agent Status Dashboard</h2>
        <ul>
          {agents.map((agent) => (
            <li key={agent.id}>
              {agent.name} - {agent.role} - {agent.state}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h2>Communication Logs</h2>
        <ul>
          {logs.map((log, index) => (
            <li key={index}>
              {log.timestamp} - {log.agentName}: {log.message}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default AgentMonitoring;
