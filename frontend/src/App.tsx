import React from "react";
import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ConfigBot from "./pages/ConfigBot";
import Supervisor from "./pages/Supervisor";
import Positions from "./pages/Positions";
import Logs from "./pages/Logs";
import Metrics from "./pages/Metrics";
import Markets from "./pages/Markets";
import { Layout } from "./components/Layout";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/positions" element={<Positions />} />
        <Route path="/config" element={<ConfigBot />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/markets" element={<Markets />} />
        <Route path="/supervisor" element={<Supervisor />} />
        <Route path="/logs" element={<Logs />} />
      </Routes>
    </Layout>
  );
}
