import "@testing-library/jest-dom";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Limpa o DOM após cada teste para evitar vazamento de estado
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia (não disponível no JSDOM)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // Deprecated
    removeListener: () => {}, // Deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock global fetch para testes
global.fetch = async (url: string | URL | Request) => {
  const urlString = typeof url === 'string' ? url : url.toString();

  // Mock responses para diferentes endpoints
  const mockResponses: Record<string, any> = {
    '/api/trading/stats/daily': {
      total_pnl: 0,
      trades_count: 0,
      win_rate: 0,
      balance: 10000,
      db: { realized_pnl: 0, net_pnl: 0 },
      exchange: { realized_pnl: 0, daily_net_pnl: 0 }
    },
    '/api/trading/history': [],
    '/api/positions/dashboard': {
      positions: [],
      summary: { total_positions: 0, total_pnl: 0 }
    },
    '/api/trading/bot/status': {
      running: true,
      dry_run: false,
      symbols: []
    }
  };

  // Encontra o mock response baseado na URL
  const matchedKey = Object.keys(mockResponses).find(key => urlString.includes(key));
  const data = matchedKey ? mockResponses[matchedKey] : {};

  return Promise.resolve(new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  }));
};
