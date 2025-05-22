import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LLMPlayground from './LLMPlayground';

// Mock fetch calls
global.fetch = jest.fn().mockImplementation((url) => {
  if (url === '/api/models') {
    return Promise.resolve({
      json: () => Promise.resolve([
        { id: 'gpt4', name: 'GPT-4 Turbo', type: 'openai', maxTokens: 128000 },
        { id: 'claude3', name: 'Claude 3 Sonnet', type: 'anthropic', maxTokens: 200000 },
      ]),
    });
  } else if (url === '/api/scenarios') {
    return Promise.resolve({
      json: () => Promise.resolve([
        { id: 'busy_night', name: 'Busy Night', type: 'operational', description: 'High-volume service scenario' },
        { id: 'overstocked', name: 'Overstocked Kitchen', type: 'inventory', description: 'Managing excess inventory' },
      ]),
    });
  }
  return Promise.reject(new Error('Not found'));
});

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((error: any) => void) | null = null;
  
  constructor() {
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }
  send = jest.fn();
  close = jest.fn();
}

// @ts-ignore
global.WebSocket = MockWebSocket;

describe('LLMPlayground', () => {
  beforeEach(() => {
    // Clear mock calls between tests
    jest.clearAllMocks();
  });

  test('renders playground interface', async () => {
    render(<LLMPlayground />);
    
    // Check headings
    expect(screen.getByText('Available Models')).toBeInTheDocument();
    expect(screen.getByText('Test Scenarios')).toBeInTheDocument();
    expect(screen.getByText('Live Evaluation')).toBeInTheDocument();
    
    // Wait for models to load
    await waitFor(() => {
      expect(screen.getByText(/GPT-4 Turbo/)).toBeInTheDocument();
      expect(screen.getByText(/Claude 3 Sonnet/)).toBeInTheDocument();
    });
    
    // Wait for scenarios to load
    await waitFor(() => {
      expect(screen.getByText(/Busy Night/)).toBeInTheDocument();
      expect(screen.getByText(/Overstocked Kitchen/)).toBeInTheDocument();
    });
  });

  test('handles model and scenario selection', async () => {
    render(<LLMPlayground />);
    
    // Wait for content to load
    await waitFor(() => {
      expect(screen.getByText(/GPT-4 Turbo/)).toBeInTheDocument();
      expect(screen.getByText(/Busy Night/)).toBeInTheDocument();
    });
    
    // Select model and scenario
    fireEvent.click(screen.getByText(/GPT-4 Turbo/));
    fireEvent.click(screen.getByText(/Busy Night/));
    
    // Check that the Start Evaluation button is enabled
    const startButton = screen.getByRole('button', { name: /Start Evaluation/i });
    expect(startButton).not.toBeDisabled();
  });
}); 