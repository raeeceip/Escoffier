import React from 'react';
import { Route, BrowserRouter as Router, Switch } from 'react-router-dom';
import { io } from 'socket.io-client';
import AgentMonitoring from './components/AgentMonitoring';
import BenchmarkControl from './components/BenchmarkControl';
import KitchenVisualization from './components/KitchenVisualization';
import LLMPlayground from './components/LLMPlayground';

const socket = io('http://localhost:8080');

const App: React.FC = () => {
  return (
    <Router>
      <Switch>
        <Route path="/kitchen" component={KitchenVisualization} />
        <Route path="/agent-monitoring" component={AgentMonitoring} />
        <Route path="/benchmark-control" component={BenchmarkControl} />
        <Route path="/llm-playground" component={LLMPlayground} />
        <Route path="/" component={LLMPlayground} />
      </Switch>
    </Router>
  );
};

export default App;
