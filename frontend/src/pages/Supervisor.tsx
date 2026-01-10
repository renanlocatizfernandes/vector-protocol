import React, { useEffect, useState } from "react";
import {
  getHealth,
  getBotStatus,
  getSupervisorStatus,
  getSupervisorHealth,
  supervisorEnable,
  supervisorDisable,
  supervisorToggle,
  type Health,
  type BotStatus,
  type SupervisorStatus,
  type SupervisorHealth
} from "../services/api";
import DockerStatus from "../components/DockerStatus";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Shield, Activity, Server, PlayCircle, StopCircle, RefreshCw, Terminal, Power, HeartPulse, Cpu, Zap, Archive } from "lucide-react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

export default function Supervisor() {
  const [health, setHealth] = useState<Health | null>(null);
  const [bot, setBot] = useState<BotStatus | null>(null);
  const [sup, setSup] = useState<SupervisorStatus | null>(null);
  const [supHealth, setSupHealth] = useState<SupervisorHealth | null>(null);

  const [loading, setLoading] = useState(true);
  const [supLoading, setSupLoading] = useState(false);
  const [opBusy, setOpBusy] = useState(false);

  // Carrega tudo (health, bot, supervisor)
  const loadAll = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [h, b, s, sh] = await Promise.all([
        getHealth().catch(() => null),
        getBotStatus().catch(() => null),
        getSupervisorStatus().catch(() => null),
        getSupervisorHealth().catch(() => null)
      ]);
      if (h) setHealth(h);
      if (b) setBot(b);
      if (s) setSup(s);
      if (sh) setSupHealth(sh);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  // Polling leve para manter status atualizados
  useEffect(() => {
    const id = setInterval(() => loadAll(true), 5000);
    return () => clearInterval(id);
  }, []);

  // Supervisor handlers
  const refreshSup = async () => {
    setSupLoading(true);
    try {
      const [s, sh] = await Promise.all([
        getSupervisorStatus(),
        getSupervisorHealth().catch(() => null)
      ]);
      setSup(s);
      if (sh) setSupHealth(sh);
    } finally {
      setSupLoading(false);
    }
  };

  const setSupervisor = async (action: "enable" | "disable" | "toggle") => {
    setOpBusy(true);
    try {
      if (action === "enable") await supervisorEnable();
      else if (action === "disable") await supervisorDisable();
      else await supervisorToggle();
      await refreshSup();
    } finally {
      setOpBusy(false);
    }
  };

  const fmtDate = (iso?: string) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const apiHealthy = health?.status === "healthy";
  const botRunning = !!bot?.running;
  const supEnabled = !!sup?.enabled;

  if (loading && !health) {
    return <div className="animate-pulse h-96 bg-gray-50 rounded-xl" />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* HERO */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
            <h1 className="text-3xl font-bold text-gray-900">Supervisor do Sistema</h1>
          </div>
          <p className="text-gray-600 ml-4">Monitoramento automático de saúde e gerenciamento de processos.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={refreshSup} disabled={supLoading} className="border-gray-200 hover:bg-gray-50">
            <RefreshCw className={cn("mr-2 h-4 w-4", supLoading && "animate-spin")} /> Refresh
          </Button>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "text-muted-foreground hover:text-gray-900")}
          >
            Swagger API
          </a>
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <Badge variant="outline" className={cn("px-3 py-1 text-sm border-gray-200", apiHealthy ? "text-green-600 bg-success/10" : "text-red-600 bg-danger/10")}>
          <Activity className="w-3 h-3 mr-2" /> API: {health?.status || "—"}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 text-sm border-gray-200 text-muted-foreground">
          v{health?.version || "—"}
        </Badge>
        <Badge variant="outline" className={cn("px-3 py-1 text-sm border-gray-200", botRunning ? "text-green-600 bg-success/10" : "text-muted-foreground")}>
          <Zap className="w-3 h-3 mr-2" /> Bot: {botRunning ? "Running" : "Stopped"}
        </Badge>
        <Badge variant="outline" className={cn("px-3 py-1 text-sm border-gray-200", supEnabled ? "text-primary bg-primary/10" : "text-muted-foreground")}>
          <Shield className="w-3 h-3 mr-2" /> Supervisor: {supEnabled ? "Active" : "Disabled"}
        </Badge>
        {supHealth && (
          <Badge variant="outline" className="px-3 py-1 text-sm border-gray-200 text-muted-foreground">
            Restarts: {supHealth.restarts}
          </Badge>
        )}
      </div>

      <div className="flex gap-3">
        <Button
          className="bg-primary hover:bg-primary/90 text-dark-950 shadow-[0_0_18px_rgba(42,212,198,0.35)]"
          disabled={opBusy}
          onClick={() => setSupervisor("enable")}
        >
          <PlayCircle className="mr-2 h-4 w-4" /> Enable Supervisor
        </Button>
        <Button
          variant="destructive"
          className="shadow-[0_0_15px_rgba(239,68,68,0.4)]"
          disabled={opBusy}
          onClick={() => setSupervisor("disable")}
        >
          <StopCircle className="mr-2 h-4 w-4" /> Disable Supervisor
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Heartbeats */}
        <Card className="elevated-card border-primary/20 bg-gray-50">
          <CardHeader className="pb-4 border-b border-gray-200">
            <CardTitle className="flex items-center gap-2 text-gray-900">
              <HeartPulse className="h-5 w-5 text-red-600 animate-pulse" /> Component Health
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {!supHealth ? (
              <div className="text-sm text-muted-foreground flex flex-col items-center justify-center h-32 opacity-50">
                <Activity className="w-8 h-8 mb-2" />
                No telemetry data
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(supHealth.components).map(([comp, data]) => (
                  <div key={comp} className="flex justify-between items-center text-sm p-2 rounded-lg bg-gray-50 border border-gray-200">
                    <span className="capitalize font-medium text-gray-900">{comp.replace("_loop", "")}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground">{data.last_heartbeat_ago}</span>
                      <div className={cn("h-2 w-2 rounded-full", data.status === "ok" ? "bg-success shadow-[0_0_8px_rgba(43,212,165,0.6)]" : "bg-danger")} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Resources */}
        <Card className="elevated-card border-gray-200 bg-gray-50">
          <CardHeader className="pb-4 border-b border-gray-200">
            <CardTitle className="flex items-center gap-2 text-gray-900">
              <Cpu className="h-5 w-5 text-primary" /> System Resources
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {!supHealth ? (
              <div className="text-sm text-muted-foreground flex flex-col items-center justify-center h-32 opacity-50">
                <Activity className="w-8 h-8 mb-2" />
                No resource data
              </div>
            ) : (
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">CPU Load</span>
                    <span className="font-mono text-gray-900">{supHealth.system.cpu_percent.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-gray-50 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary/80 shadow-[0_0_10px_rgba(42,212,198,0.4)] transition-all duration-500"
                      style={{ width: `${Math.min(supHealth.system.cpu_percent, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Memory Usage</span>
                    <span className="font-mono text-gray-900">{supHealth.system.memory_mb.toFixed(0)} MB</span>
                  </div>
                  <div className="h-2 bg-gray-50 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent/80 shadow-[0_0_10px_rgba(245,159,58,0.4)] transition-all duration-500"
                      style={{ width: `${Math.min((supHealth.system.memory_mb / 1024) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts / Interventions */}
        <Card className="elevated-card border-gray-200 bg-gray-50">
          <CardHeader className="pb-4 border-b border-gray-200">
            <CardTitle className="flex items-center gap-2 text-gray-900">
              <Shield className="h-5 w-5 text-warning" /> Interventions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Last Intervention:</span>
                <span className="font-mono text-gray-900">{fmtDate(sup?.last_intervention_at)}</span>
              </div>

              <div className="bg-dark-950 rounded-lg border border-gray-200 p-3 h-32 overflow-y-auto">
                <ul className="text-xs font-mono space-y-1 text-muted-foreground">
                  {(sup?.interventions_tail || []).length > 0 ? (
                    (sup?.interventions_tail || []).map((line, i) => (
                      <li key={i} className="border-b border-gray-200 pb-1 last:border-0">{line}</li>
                    ))
                  ) : (
                    <li className="italic opacity-50 text-center py-8">No recent interventions</li>
                  )}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Docker Status */}
      <Card className="elevated-card border-gray-200 bg-gray-50">
        <CardHeader className="border-b border-gray-200 pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-gray-900">
              <Server className="h-5 w-5 text-muted-foreground" /> Infrastructure Status
            </CardTitle>
            <Link to="/logs">
              <Button variant="ghost" size="sm" className="text-xs">
                <Archive className="mr-2 w-3 h-3" /> View System Logs
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <DockerStatus />
        </CardContent>
      </Card>

    </div>
  );
}
