import React, { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const socket = io('http://localhost:8080');

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

  useEffect(() => {
    socket.on('agentStatus', (data) => {
      setAgents(data);
    });

    socket.on('agentLogs', (data) => {
      setLogs(data);
    });

    return () => {
      socket.off('agentStatus');
      socket.off('agentLogs');
    };
  }, []);

  return (
    <div>
      <h1>Agent Monitoring</h1>
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
