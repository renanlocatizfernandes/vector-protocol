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
    expect(screen.getByText(/Antigravity/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Configuration/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Supervisor/i })).toBeInTheDocument();

    // Indicador de Status no Sidebar (Dynamic)
    // expect(screen.getByText(/Active/i)).toBeInTheDocument();
    // expect(screen.getByText(/v4.0.0/i)).toBeInTheDocument();
  });
});
