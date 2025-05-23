import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface AgentPosition {
  x: number;
  y: number;
  id: string;
  name: string;
}

interface KitchenState {
  agents: AgentPosition[];
}

const KitchenVisualization: React.FC = () => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<string>('Disconnected');

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    const width = 800;
    const height = 600;

    svg.attr('width', width).attr('height', height);

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket('ws://localhost:8080/ws');
        
        ws.onopen = () => {
          setConnectionStatus('Connected');
          console.log('Connected to kitchen visualization server');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'kitchenState' && data.state) {
              const kitchenState: KitchenState = data.state;
              
              // Clear previous visualization
              svg.selectAll('*').remove();

              // Create visualization based on data
              svg
                .selectAll('circle')
                .data(kitchenState.agents)
                .enter()
                .append('circle')
                .attr('cx', (d: AgentPosition) => d.x)
                .attr('cy', (d: AgentPosition) => d.y)
                .attr('r', 10)
                .attr('fill', 'blue');
              
              // Add agent names
              svg
                .selectAll('text')
                .data(kitchenState.agents)
                .enter()
                .append('text')
                .attr('x', (d: AgentPosition) => d.x)
                .attr('y', (d: AgentPosition) => d.y - 15)
                .attr('text-anchor', 'middle')
                .attr('font-size', '12px')
                .text((d: AgentPosition) => d.name);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onclose = () => {
          setConnectionStatus('Disconnected');
          console.log('Disconnected from kitchen visualization server');
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
      <div style={{ marginBottom: '10px' }}>
        <strong>Connection Status:</strong> {connectionStatus}
      </div>
      <svg ref={svgRef}></svg>
    </div>
  );
};

export default KitchenVisualization;
