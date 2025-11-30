import React, { useEffect, useState } from "react";
import {
  getHealth,
  getBotStatus,
  getSupervisorStatus,
  supervisorEnable,
  supervisorDisable,
  supervisorToggle,
  type Health,
  type BotStatus,
  type SupervisorStatus
} from "../services/api";
import DockerStatus from "../components/DockerStatus";
import LogsViewer from "../components/LogsViewer";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Shield, Activity, Server, PlayCircle, StopCircle, RefreshCw, Terminal, Power } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Supervisor() {
  const [health, setHealth] = useState<Health | null>(null);
  const [bot, setBot] = useState<BotStatus | null>(null);
  const [sup, setSup] = useState<SupervisorStatus | null>(null);

  const [loading, setLoading] = useState(true);
  const [supLoading, setSupLoading] = useState(false);
  const [opBusy, setOpBusy] = useState(false);

  // Carrega tudo (health, bot, supervisor)
  const loadAll = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [h, b, s] = await Promise.all([
        getHealth().catch(() => null),
        getBotStatus().catch(() => null),
        getSupervisorStatus().catch(() => null)
      ]);
      if (h) setHealth(h);
      if (b) setBot(b);
      if (s) setSup(s);
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
      const s = await getSupervisorStatus();
      setSup(s);
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
            <CardTitle className="text-sm">Quando usar o Supervisor?</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <ul className="list-disc list-inside space-y-1">
              <li>Manter a API saudável automaticamente (auto-fix para falhas comuns).</li>
              <li>Garantir que o bot permaneça rodando (ensure-running).</li>
              <li>Intervir em inatividade (reinicia bot/serviço).</li>
            </ul>
            <p>
              Se preferir controle manual via UI, mantenha o Supervisor desligado. Para automação e
              resiliência, rode o Supervisor com <code>watch</code>.
            </p>
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
            <div className="mt-4">
              <h4 className="text-sm font-semibold mb-2">Notas de Operação</h4>
              <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                <li><b>--ensure-running</b> liga o “auto-start” caso o bot pare.</li>
                <li><b>--bot-dry-run</b> força iniciar em modo simulado nas intervenções.</li>
                <li><b>--inactive-mins</b> reinicia o bot se não houver atividade por X minutos.</li>
              </ul>
            </div>
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

      <Card>
        <CardHeader>
          <CardTitle>Cenários recomendados</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 border rounded-lg bg-muted/30">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <StopCircle className="h-4 w-4 text-red-500" /> Supervisor DESLIGADO
              </h4>
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                <li>Uso exploratório e controle total pela UI.</li>
                <li>Start/Stop via painel, ajustes de config por demanda.</li>
                <li>Requer atenção manual em quedas/erros.</li>
              </ul>
            </div>
            <div className="p-4 border rounded-lg bg-muted/30">
              <h4 className="font-semibold mb-2 flex items-center gap-2">
                <PlayCircle className="h-4 w-4 text-green-500" /> Supervisor LIGADO
              </h4>
              <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                <li>Ambiente always-on, com auto-fix e auto-start do bot.</li>
                <li>Mitiga falhas transitórias, reinicia serviços quando necessário.</li>
                <li>UI permanece para inspeção e ajustes finos de parâmetros.</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
