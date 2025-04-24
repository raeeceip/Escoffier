import React, { useState } from 'react';
import axios from 'axios';

const BenchmarkControl: React.FC = () => {
  const [sessionName, setSessionName] = useState('');
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [scenario, setScenario] = useState('');

  const handleSessionCreation = () => {
    // Implement session creation logic
    console.log('Session Created:', sessionName);
  };

  const handleModelUpload = async () => {
    if (modelFile) {
      const formData = new FormData();
      formData.append('model', modelFile);

      try {
        const response = await axios.post('/upload-model', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        console.log('Model Uploaded:', response.data);
      } catch (error) {
        console.error('Error uploading model:', error);
      }
    }
  };

  const handleScenarioExecution = () => {
    // Implement scenario execution logic
    console.log('Scenario Executed:', scenario);
  };

  return (
    <div>
      <h1>Benchmark Control</h1>
      <div>
        <h2>Session Creation</h2>
        <input
          type="text"
          value={sessionName}
          onChange={(e) => setSessionName(e.target.value)}
          placeholder="Session Name"
        />
        <button onClick={handleSessionCreation}>Create Session</button>
      </div>
      <div>
        <h2>Model Uploading</h2>
        <input
          type="file"
          onChange={(e) => setModelFile(e.target.files ? e.target.files[0] : null)}
        />
        <button onClick={handleModelUpload}>Upload Model</button>
      </div>
      <div>
        <h2>Scenario Configuration</h2>
        <textarea
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          placeholder="Scenario Configuration"
        />
        <button onClick={handleScenarioExecution}>Execute Scenario</button>
      </div>
    </div>
  );
};

export default BenchmarkControl;
