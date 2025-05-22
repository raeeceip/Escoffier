import React from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import AgentMonitoring from './components/AgentMonitoring';
import BenchmarkControl from './components/BenchmarkControl';
import KitchenVisualization from './components/KitchenVisualization';
import LLMPlayground from './components/LLMPlayground';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/kitchen" element={<KitchenVisualization />} />
        <Route path="/agent-monitoring" element={<AgentMonitoring />} />
        <Route path="/benchmark-control" element={<BenchmarkControl />} />
        <Route path="/llm-playground" element={<LLMPlayground />} />
        <Route path="/" element={<LLMPlayground />} />
      </Routes>
    </Router>
  );
};

export default App;
