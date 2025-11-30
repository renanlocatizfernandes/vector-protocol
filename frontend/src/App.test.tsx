import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import App from "./App";

// Mock do hook para evitar chamadas reais à API durante o teste
vi.mock("./hooks/useBotStatus", () => {
  return {
    useBotStatus: () => ({
      running: true,
      data: { running: true },
      loading: false,
      error: null
    })
  };
});

describe("App", () => {
  it("renderiza navbar, rotas básicas e rodapé", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Navbar e links
    expect(screen.getByText(/Crypto Trading Bot/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Config Bot/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Supervisor/i })).toBeInTheDocument();

    // Indicador do Bot
    expect(screen.getByText(/Bot:\s*Rodando/i)).toBeInTheDocument();

    // Rodapé com info de API
    expect(screen.getByText(/API alvo:/i)).toBeInTheDocument();
  });
});
