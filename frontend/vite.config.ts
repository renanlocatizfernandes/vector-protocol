import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const API_TARGET = env.VITE_API_BASE || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      open: true,
      proxy: {
        "/api": {
          target: API_TARGET,
          changeOrigin: true
        },
        "/health": {
          target: API_TARGET,
          changeOrigin: true
        },
        "/version": {
          target: API_TARGET,
          changeOrigin: true
        },
        "/docs": {
          target: API_TARGET,
          changeOrigin: true
        }
      }
    },
    preview: {
      port: 5174
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
