import React, { useEffect, useState } from "react";
import {
  getConfig,
  getBotStatus,
  updateBotConfig,
  testTelegram,
  type ConfigResponse,
  type BotStatus
} from "../services/api";

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label>{label}</label>
      {children}
    </div>
  );
}

export default function ConfigBot() {
  const [loading, setLoading] = useState(true);
  const [cfg, setCfg] = useState<ConfigResponse | null>(null);
  const [bot, setBot] = useState<BotStatus | null>(null);

  const [scanIntervalMin, setScanIntervalMin] = useState<number | "">("");
  const [minScore, setMinScore] = useState<number | "">("");
  const [maxPositions, setMaxPositions] = useState<number | "">("");

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [c, b] = await Promise.all([
          getConfig().catch(() => null),
          getBotStatus().catch(() => null),
        ]);
        if (c) setCfg(c);
        if (b) {
          setBot(b);
          setScanIntervalMin(b?.scan_interval ? Math.round((b.scan_interval as number) / 60) : "");
          setMinScore(typeof b?.min_score === "number" ? (b.min_score as number) : "");
          setMaxPositions(typeof b?.max_positions === "number" ? (b.max_positions as number) : "");
        }
      } catch {
        setMsg({ kind: "err", text: "Falha ao carregar configuração" });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const onSave = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const params: Record<string, number> = {};
      if (scanIntervalMin !== "" && !Number.isNaN(Number(scanIntervalMin))) params.scan_interval_minutes = Number(scanIntervalMin);
      if (minScore !== "" && !Number.isNaN(Number(minScore))) params.min_score = Number(minScore);
      if (maxPositions !== "" && !Number.isNaN(Number(maxPositions))) params.max_positions = Number(maxPositions);

      const res = await updateBotConfig(params);
      setMsg({ kind: "ok", text: res?.message || "Config atualizada" });
      const b = await getBotStatus().catch(() => null);
      if (b) setBot(b);
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.message || "Erro ao salvar" });
    } finally {
      setBusy(false);
    }
  };

  const onTestTelegram = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await testTelegram();
      setMsg({ kind: "ok", text: res?.message || "Telegram OK" });
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.message || "Erro ao enviar teste" });
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="card">Carregando...</div>;
  }

  const runningBadge = (
    <span className={"badge " + (bot?.running ? "ok" : "warn")}>
      <span className="dot" />
      {bot?.running ? "Rodando" : "Parado"}
    </span>
  );

  return (
    <div className="grid cols-2">
      {/* HERO */}
      <section className="hero" style={{ gridColumn: "1 / -1" }}>
        <div>
          <div className="hero-title">Configuração do Bot</div>
          <div className="hero-sub">
            Ajuste as principais variáveis de execução em runtime. As mudanças aplicam sem reiniciar o serviço.
          </div>
        </div>
        <div className="toolbar">
          {runningBadge}
          <button className="btn ghost" onClick={onTestTelegram} disabled={busy}>
            Testar Telegram
          </button>
        </div>
      </section>

      {/* Painel de Configurações do backend */}
      <section className="card">
        <h3>Configurações Globais</h3>
        <div className="row small">
          <div className="badge">MAX_POSITIONS: {cfg?.max_positions ?? "—"}</div>
          <div className="badge">RISK_PER_TRADE: {cfg?.risk_per_trade ?? "—"}</div>
          <div className="badge">MAX_PORTFOLIO_RISK: {cfg?.max_portfolio_risk ?? "—"}</div>
          <div className="badge">DEFAULT_LEVERAGE: {cfg?.default_leverage ?? "—"}</div>
          <div className="badge">TESTNET: {String(cfg?.testnet ?? "—")}</div>
        </div>
        <p className="small" style={{ marginTop: 8 }}>
          Valores acima vêm do backend (pydantic-settings). Ajustes finos do loop do bot são aplicados na seção ao lado.
        </p>
      </section>

      {/* Form runtime refinado */}
      <section className="card">
        <h3>Config do Bot (runtime)</h3>
        <div className="row small" style={{ marginBottom: 8 }}>
          <div className="badge">dry_run: {String(bot?.dry_run ?? "—")}</div>
          <div className="badge">min_score: {String(bot?.min_score ?? "—")}</div>
          <div className="badge">max_positions: {String(bot?.max_positions ?? "—")}</div>
          <div className="badge">scan: {bot?.scan_interval ? Math.round((bot?.scan_interval as number) / 60) + "m" : "—"}</div>
        </div>

        <div className="form-row">
          <Field label="Scan interval (min)">
            <input
              type="number"
              min={1}
              value={scanIntervalMin}
              onChange={(e) => setScanIntervalMin(e.target.value === "" ? "" : Number(e.target.value))}
            />
          </Field>
          <Field label="Min score">
            <input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(e.target.value === "" ? "" : Number(e.target.value))}
            />
          </Field>
          <Field label="Max positions">
            <input
              type="number"
              min={1}
              value={maxPositions}
              onChange={(e) => setMaxPositions(e.target.value === "" ? "" : Number(e.target.value))}
            />
          </Field>
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn primary" onClick={onSave} disabled={busy}>
            Salvar
          </button>
          {msg && (
            <div className={"badge " + (msg.kind === "ok" ? "ok" : "err")}>
              {msg.text}
            </div>
          )}
        </div>
      </section>

      {/* Notas */}
      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>Notas</h3>
        <ul className="small">
          <li>PUT /api/trading/bot/config aplica em runtime (não altera .env).</li>
          <li>Mantenha TESTNET=True até validar a estratégia; depois troque para produção com cautela.</li>
          <li>Use a página Supervisor para resiliência extra via watchdog.</li>
        </ul>
      </section>
    </div>
  );
}
