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
import LogsViewer from "../components/LogsViewer";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Shield, Activity, Server, PlayCircle, StopCircle, RefreshCw, Terminal, Power, HeartPulse, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

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

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* HERO */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Supervisor</h1>
          <p className="text-muted-foreground">Automação para manter sua stack saudável e o bot sempre rodando.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshSup} disabled={supLoading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", supLoading && "animate-spin")} /> Atualizar
          </Button>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className={cn(buttonVariants("ghost", "sm"))}
          >
            Swagger API
          </a>
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <Badge variant={apiHealthy ? "success" : "destructive"} className="px-3 py-1 text-sm">
          API: {health?.status || "—"}
        </Badge>
        <Badge variant="outline" className="px-3 py-1 text-sm">
          v{health?.version || "—"}
        </Badge>
        <Badge variant={botRunning ? "success" : "destructive"} className="px-3 py-1 text-sm">
          Bot: {botRunning ? "Rodando" : "Parado"}
        </Badge>
        <Badge variant={supEnabled ? "success" : "destructive"} className="px-3 py-1 text-sm">
          Supervisor: {supEnabled ? "Ativado" : "Desativado"}
        </Badge>
        {supHealth && (
          <Badge variant="outline" className="px-3 py-1 text-sm">
            Restarts: {supHealth.restarts}
          </Badge>
        )}
      </div>

      <div className="flex gap-2">
        <Button variant="default" className="bg-green-600 hover:bg-green-700" disabled={opBusy} onClick={() => setSupervisor("enable")}>
          <PlayCircle className="mr-2 h-4 w-4" /> Ativar Supervisor
        </Button>
        <Button variant="destructive" disabled={opBusy} onClick={() => setSupervisor("disable")}>
          <StopCircle className="mr-2 h-4 w-4" /> Desativar Supervisor
        </Button>
        <Button variant="secondary" disabled={opBusy} onClick={() => setSupervisor("toggle")}>
          <Power className="mr-2 h-4 w-4" /> Alternar
        </Button>
      </div>

      {/* RESUMO RÁPIDO */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" /> Resumo do Sistema
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-sm text-muted-foreground">Carregando...</div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge variant={apiHealthy ? "success" : "destructive"}>
                    API: {health?.status || "—"}
                  </Badge>
                  <Badge variant="outline">v{health?.version || "—"}</Badge>
                  <Badge variant={botRunning ? "success" : "destructive"}>
                    Bot: {botRunning ? "Rodando" : "Parado"}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  Módulos: {health?.modules ? Object.keys(health.modules).join(", ") : "—"}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* NOVO: Heartbeats */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HeartPulse className="h-5 w-5 text-red-500" /> Heartbeats
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!supHealth ? (
              <div className="text-sm text-muted-foreground">Sem dados de telemetria</div>
            ) : (
              <div className="space-y-2">
                {Object.entries(supHealth.components).map(([comp, data]) => (
                  <div key={comp} className="flex justify-between items-center text-sm border-b pb-1 last:border-0">
                    <span className="capitalize">{comp.replace("_loop", "")}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{data.last_heartbeat_ago}</span>
                      <Badge variant={data.status === "ok" ? "success" : "destructive"} className="h-5 px-1">
                        {data.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* NOVO: Recursos */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-blue-500" /> Recursos
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!supHealth ? (
              <div className="text-sm text-muted-foreground">Sem dados de recursos</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>CPU Usage</span>
                    <span>{supHealth.system.cpu_percent.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all duration-500"
                      style={{ width: `${Math.min(supHealth.system.cpu_percent, 100)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>RAM Usage</span>
                    <span>{supHealth.system.memory_mb.toFixed(0)} MB</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500 transition-all duration-500"
                      style={{ width: `${Math.min((supHealth.system.memory_mb / 1024) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" /> Supervisor • Detalhes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Badge variant={supEnabled ? "success" : "destructive"}>
                Status: {supEnabled ? "Ativado" : "Desativado"}
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              Última intervenção: {fmtDate(sup?.last_intervention_at)}
            </div>
            <details className="text-sm">
              <summary className="cursor-pointer text-primary hover:underline">Últimas intervenções</summary>
              <pre className="mt-2 p-2 bg-muted rounded-md text-xs font-mono overflow-auto max-h-40">
                {(sup?.interventions_tail || []).join("\n") || "—"}
              </pre>
            </details>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Terminal className="h-4 w-4" /> Comandos Úteis
            </CardTitle>
            <CardDescription>Execute no diretório raiz do projeto</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs font-mono bg-muted p-3 rounded-md overflow-x-auto whitespace-pre-wrap text-foreground">
              {`# Preparar ambiente local (opcional)
python3 supervisor.py ensure-venv

# Subir stack Docker e checar saúde
python3 supervisor.py up

# Iniciar watchdog (recomendado em produção/dev estável)
python3 supervisor.py watch \\
  --interval 60 \\
  --inactive-mins 120 \\
  --ensure-running \\
  --bot-dry-run \\
  --start-bot

# Logs rápidos do container da API
python3 supervisor.py logs --name trading-bot-api --tail 200

# Reiniciar somente API
python3 supervisor.py restart-api --service api

# Parar stack
python3 supervisor.py down`}
            </pre>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" /> Infra • Containers e Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <DockerStatus />
              <LogsViewer />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
