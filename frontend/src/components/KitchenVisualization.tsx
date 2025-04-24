import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { io } from 'socket.io-client';

const socket = io('http://localhost:8080');

const KitchenVisualization: React.FC = () => {
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    const width = 800;
    const height = 600;

    svg.attr('width', width).attr('height', height);

    socket.on('kitchenState', (data) => {
      // Clear previous visualization
      svg.selectAll('*').remove();

      // Create visualization based on data
      svg
        .selectAll('circle')
        .data(data.agents)
        .enter()
        .append('circle')
        .attr('cx', (d) => d.x)
        .attr('cy', (d) => d.y)
        .attr('r', 10)
        .attr('fill', 'blue');
    });

    return () => {
      socket.off('kitchenState');
    };
  }, []);

  return <svg ref={svgRef}></svg>;
};

export default KitchenVisualization;
