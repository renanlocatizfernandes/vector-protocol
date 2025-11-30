import React from "react";
import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ConfigBot from "./pages/ConfigBot";
import Supervisor from "./pages/Supervisor";
import Metrics from "./pages/Metrics";
import { Layout } from "./components/Layout";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/config" element={<ConfigBot />} />
        <Route path="/supervisor" element={<Supervisor />} />
        <Route path="/logs" element={<div className="p-4">Logs Viewer (Coming Soon)</div>} />
      </Routes>
    </Layout>
  );
}

