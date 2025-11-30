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
    <div className="grid" style={{ gap: 16 }}>
      {/* HERO */}
      <div className="hero" style={{ marginBottom: 8 }}>
        <div>
          <div className="hero-title">Supervisor</div>
          <div className="hero-sub">
            Automação para manter sua stack saudável e o bot sempre rodando.
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <div className={"badge " + (apiHealthy ? "ok" : "warn")}>
              <span className="dot" /> API: {health?.status || "—"}
            </div>
            <div className="badge info">v{health?.version || "—"}</div>
            <div className={"badge " + (botRunning ? "ok" : "warn")}>
              Bot: {botRunning ? "Rodando" : "Parado"}
            </div>
            <div className={"badge " + (supEnabled ? "ok" : "warn")}>
              Supervisor: {supEnabled ? "Ativado" : "Desativado"}
            </div>
          </div>
        </div>

        <div className="toolbar">
          <button className="btn success" disabled={opBusy} onClick={() => setSupervisor("enable")}>Ativar</button>
          <button className="btn destructive" disabled={opBusy} onClick={() => setSupervisor("disable")}>Desativar</button>
          <button className="btn warn" disabled={opBusy} onClick={() => setSupervisor("toggle")}>Alternar</button>
          <button className="btn ghost" disabled={supLoading} onClick={refreshSup}>Atualizar</button>
          <a className="btn ghost" href="/docs" target="_blank" rel="noreferrer">Swagger</a>
        </div>
      </div>

      {/* RESUMO RÁPIDO */}
      <div className="grid cols-2">
        <section className="card">
          <h3>Resumo</h3>
          {loading ? (
            <div className="small">Carregando...</div>
          ) : (
            <>
              <div className="row">
                <div className={"badge " + (apiHealthy ? "ok" : "warn")}>
                  API: {health?.status || "—"}
                </div>
                <div className="badge">v{health?.version || "—"}</div>
                <div className={"badge " + (botRunning ? "ok" : "warn")}>
                  Bot: {botRunning ? "Rodando" : "Parado"}
                </div>
              </div>
              <div className="small" style={{ marginTop: 8 }}>
                Módulos: {health?.modules ? Object.keys(health.modules).join(", ") : "—"}
              </div>
            </>
          )}
        </section>

        <section className="card">
          <h3>Supervisor • Detalhes</h3>
          <div className="row">
            <div className={"badge " + (supEnabled ? "ok" : "warn")}>
              Status: {supEnabled ? "Ativado" : "Desativado"}
            </div>
            <button className="btn ghost" disabled={supLoading} onClick={refreshSup}>Atualizar</button>
          </div>
          <div className="small" style={{ marginTop: 8 }}>
            Última intervenção: {fmtDate(sup?.last_intervention_at)}
          </div>
          <details style={{ marginTop: 8 }}>
            <summary>Últimas intervenções</summary>
            <pre
              className="small"
              style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}
            >
{(sup?.interventions_tail || []).join("\n") || "—"}
            </pre>
          </details>
        </section>

        <section className="card">
          <h3>Quando usar o Supervisor?</h3>
          <ul className="small">
            <li>Manter a API saudável automaticamente (auto-fix para falhas comuns).</li>
            <li>Garantir que o bot permaneça rodando (ensure-running).</li>
            <li>Intervir em inatividade (reinicia bot/serviço).</li>
          </ul>
          <p className="small">
            Se preferir controle manual via UI, mantenha o Supervisor desligado. Para automação e
            resiliência, rode o Supervisor com <code>watch</code>.
          </p>
        </section>

        <section className="card">
          <h3>Comandos Úteis</h3>
          <p className="small">Execute no diretório raiz do projeto:</p>
          <pre className="small" style={{ whiteSpace: "pre-wrap" }}>{`# Preparar ambiente local (opcional)
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
python3 supervisor.py down`}</pre>

          <h4 style={{ margin: "16px 0 8px 0" }}>Notas de Operação</h4>
          <ul className="small">
            <li><b>--ensure-running</b> liga o “auto-start” caso o bot pare.</li>
            <li><b>--bot-dry-run</b> força iniciar em modo simulado nas intervenções.</li>
            <li><b>--inactive-mins</b> reinicia o bot se não houver atividade por X minutos.</li>
          </ul>
        </section>

        <section className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Infra • Containers e Logs</h3>
          <div className="grid cols-2">
            <DockerStatus />
            <LogsViewer />
          </div>
        </section>

        <section className="card" style={{ gridColumn: "1 / -1" }}>
          <h3>Cenários recomendados</h3>
          <div className="grid cols-2">
            <div className="card">
              <h4 style={{ marginTop: 0 }}>Supervisor DESLIGADO</h4>
              <ul className="small">
                <li>Uso exploratório e controle total pela UI.</li>
                <li>Start/Stop via painel, ajustes de config por demanda.</li>
                <li>Requer atenção manual em quedas/erros.</li>
              </ul>
            </div>
            <div className="card">
              <h4 style={{ marginTop: 0 }}>Supervisor LIGADO</h4>
              <ul className="small">
                <li>Ambiente always-on, com auto-fix e auto-start do bot.</li>
                <li>Mitiga falhas transitórias, reinicia serviços quando necessário.</li>
                <li>UI permanece para inspeção e ajustes finos de parâmetros.</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
