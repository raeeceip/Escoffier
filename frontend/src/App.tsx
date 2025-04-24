import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import KitchenVisualization from './components/KitchenVisualization';
import AgentMonitoring from './components/AgentMonitoring';
import BenchmarkControl from './components/BenchmarkControl';
import { io } from 'socket.io-client';

const socket = io('http://localhost:8080');

const App: React.FC = () => {
  return (
    <Router>
      <Switch>
        <Route path="/kitchen" component={KitchenVisualization} />
        <Route path="/agent-monitoring" component={AgentMonitoring} />
        <Route path="/benchmark-control" component={BenchmarkControl} />
      </Switch>
    </Router>
  );
};

export default App;
