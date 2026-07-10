import { render, screen } from '@testing-library/react';
import { expect, test, vi, beforeAll } from 'vitest';
import App from './App';

// Mock global fetch and WebSocket before tests run
beforeAll(() => {
  (globalThis as any).fetch = vi.fn().mockImplementation(() => 
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ access_token: "dummy_token", username: "citizen_john" })
    } as any)
  );

  // Mock WebSocket
  class MockWebSocket {
    url: string;
    onopen: (() => void) | null = null;
    onmessage: ((e: { data: string }) => void) | null = null;
    onclose: (() => void) | null = null;
    
    constructor(url: string) {
      this.url = url;
      // Simulate connection opening in a next tick
      setTimeout(() => {
        if (this.onopen) this.onopen();
      }, 0);
    }
    
    close() {}
  }
  
  (globalThis as any).WebSocket = MockWebSocket as any;
});

test('renders RakshaNet title and logo', async () => {
  render(<App />);
  
  // Verify main branding title is present
  const titleElements = screen.getAllByText(/RakshaNet/i);
  expect(titleElements.length).toBeGreaterThanOrEqual(1);
  expect(titleElements[0]).toBeInTheDocument();
  
  // Verify target role label is present
  const selectLabel = screen.getByText(/Access Role:/i);
  expect(selectLabel).toBeInTheDocument();
});
