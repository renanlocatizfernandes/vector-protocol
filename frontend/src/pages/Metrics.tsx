import React, { useEffect, useState, useCallback } from "react";
import {
  getBotMetrics,
  getExecutionMetrics,
  getMonitoringMetrics,
  getRiskMetrics,
  type BotMetrics,
  type ExecutionMetrics,
  type MonitoringMetrics,
  type RiskMetrics
} from "../services/api";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

const COLORS = ["#4f9cff", "#10b981", "#f59e0b", "#ef4444", "#7c3aed", "#38bdf8"];

function formatNumber(n: number | undefined | null, digits = 2) {
  if (typeof n !== "number" || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

function formatDuration(seconds: number | undefined | null) {
  if (typeof seconds !== "number" || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function Metrics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [botMetrics, setBotMetrics] = useState<BotMetrics | null>(null);
  const [execMetrics, setExecMetrics] = useState<ExecutionMetrics | null>(null);
  const [monMetrics, setMonMetrics] = useState<MonitoringMetrics | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bot, exec, mon, risk] = await Promise.all([
        getBotMetrics().catch(() => null),
        getExecutionMetrics().catch(() => null),
        getMonitoringMetrics().catch(() => null),
        getRiskMetrics().catch(() => null)
      ]);
      if (bot) setBotMetrics(bot);
      if (exec) setExecMetrics(exec);
      if (mon) setMonMetrics(mon);
      if (risk) setRiskMetrics(risk);
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar métricas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
    const id = setInterval(loadAll, 10000); // Refresh every 10s
    return () => clearInterval(id);
  }, [loadAll]);

  if (loading && !botMetrics) {
    return <div className="card">Carregando métricas...</div>;
  }

  if (error) {
    return <div className="card"><div className="badge err">{error}</div></div>;
  }

  // Prepare data for charts
  const rejectionReasonsData = botMetrics ? [
    { name: "Market Filter", value: botMetrics.rejection_reasons.market_filter },
    { name: "Correlation", value: botMetrics.rejection_reasons.correlation_filter },
    { name: "Blacklist", value: botMetrics.rejection_reasons.blacklist },
    { name: "Risk Manager", value: botMetrics.rejection_reasons.risk_manager },
    { name: "Execution Failed", value: botMetrics.rejection_reasons.execution_failed }
  ].filter(d => d.value > 0) : [];

  const orderTypeData = execMetrics ? [
    { name: "LIMIT", value: execMetrics.order_type_distribution.limit },
    { name: "MARKET", value: execMetrics.order_type_distribution.market },
    { name: "ICEBERG", value: execMetrics.order_type_distribution.iceberg }
  ].filter(d => d.value > 0) : [];

  const eventTypesData = monMetrics ? [
    { name: "Trailing Stop", value: monMetrics.events.trailing_stop },
    { name: "Partial TP", value: monMetrics.events.partial_tp },
    { name: "Take Profit", value: monMetrics.events.take_profit },
    { name: "Stop Loss", value: monMetrics.events.stop_loss },
    { name: "Emergency Stop", value: monMetrics.events.emergency_stop },
    { name: "Max Loss", value: monMetrics.events.max_loss }
  ].filter(d => d.value > 0) : [];

  const latencyData = botMetrics ? [
    { name: "Scan", avg: botMetrics.latencies.avg_scan_time_sec, max: botMetrics.latencies.max_scan_time_sec },
    { name: "Signal Gen", avg: botMetrics.latencies.avg_signal_generation_time_sec, max: botMetrics.latencies.max_signal_generation_time_sec },
    { name: "Filter", avg: botMetrics.latencies.avg_filter_time_sec, max: botMetrics.latencies.max_filter_time_sec },
    { name: "Execution", avg: botMetrics.latencies.avg_execution_time_sec, max: botMetrics.latencies.max_execution_time_sec },
    { name: "Total Cycle", avg: botMetrics.latencies.avg_total_cycle_time_sec, max: botMetrics.latencies.max_total_cycle_time_sec }
  ] : [];

  return (
    <div className="grid cols-2" style={{ gap: 16 }}>
      {/* HERO */}
      <section className="hero" style={{ gridColumn: "1 / -1" }}>
        <div>
          <div className="hero-title">Métricas e Performance</div>
          <div className="hero-sub">
            Visão detalhada do desempenho dos módulos do bot em tempo real
          </div>
        </div>
        <div className="toolbar">
          <button className="btn" onClick={loadAll} disabled={loading}>
            {loading ? "Atualizando..." : "Atualizar"}
          </button>
        </div>
      </section>

      {/* BOT METRICS */}
      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>Bot Autônomo - KPIs por Ciclo</h3>
        {botMetrics ? (
          <div className="grid cols-4" style={{ gap: 12, marginTop: 12 }}>
            <div className="kpi">
              <div className="label">Total de Ciclos</div>
              <div className="value">{botMetrics.total_cycles}</div>
              <div className="sub">
                {botMetrics.cycles_with_trades} com trades • {botMetrics.cycles_without_trades} sem trades
              </div>
            </div>
            <div className="kpi">
              <div className="label">Taxa de Aprovação</div>
              <div className="value">{formatNumber(botMetrics.signals.approval_rate_pct, 1)}%</div>
              <div className="sub">
                {botMetrics.signals.total_approved} / {botMetrics.signals.total_generated} aprovados
              </div>
            </div>
            <div className="kpi">
              <div className="label">Taxa de Sucesso Execução</div>
              <div className="value">{formatNumber(botMetrics.execution.success_rate_pct, 1)}%</div>
              <div className="sub">
                {botMetrics.execution.total_successful} / {botMetrics.execution.total_attempted} executados
              </div>
            </div>
            <div className="kpi">
              <div className="label">Tempo Médio Ciclo</div>
              <div className="value">{formatDuration(botMetrics.latencies.avg_total_cycle_time_sec)}</div>
              <div className="sub">Máx: {formatDuration(botMetrics.latencies.max_total_cycle_time_sec)}</div>
            </div>
          </div>
        ) : (
          <div className="small">Sem dados disponíveis</div>
        )}
      </section>

      {/* LATENCY CHART */}
      {botMetrics && latencyData.length > 0 && (
        <section className="card">
          <h3>Latências por Fase</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={latencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" stroke="var(--muted)" />
              <YAxis stroke="var(--muted)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px"
                }}
                formatter={(value: number) => `${formatDuration(value)}`}
              />
              <Legend />
              <Bar dataKey="avg" fill="#4f9cff" name="Média" />
              <Bar dataKey="max" fill="#f59e0b" name="Máximo" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* REJECTION REASONS */}
      {botMetrics && rejectionReasonsData.length > 0 && (
        <section className="card">
          <h3>Razões de Rejeição</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={rejectionReasonsData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {rejectionReasonsData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px"
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* EXECUTION METRICS */}
      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>Executor de Ordens</h3>
        {execMetrics ? (
          <div className="grid cols-4" style={{ gap: 12, marginTop: 12 }}>
            <div className="kpi">
              <div className="label">Taxa de Sucesso</div>
              <div className="value">{formatNumber(execMetrics.success_rate * 100, 1)}%</div>
              <div className="sub">
                {execMetrics.successful_orders} / {execMetrics.total_orders} ordens
              </div>
            </div>
            <div className="kpi">
              <div className="label">Slippage Médio</div>
              <div className="value">{formatNumber(execMetrics.average_slippage_pct, 3)}%</div>
              <div className="sub">Tempo médio: {formatDuration(execMetrics.average_execution_time_sec)}</div>
            </div>
            <div className="kpi">
              <div className="label">Ratio Maker</div>
              <div className="value">{formatNumber(execMetrics.maker_taker_distribution.maker_ratio * 100, 1)}%</div>
              <div className="sub">
                {execMetrics.maker_taker_distribution.maker} maker • {execMetrics.maker_taker_distribution.taker} taker
              </div>
            </div>
            <div className="kpi">
              <div className="label">Re-quotes</div>
              <div className="value">{execMetrics.retry_metrics.re_quotes}</div>
              <div className="sub">
                {execMetrics.retry_metrics.total_retries} retries • {formatNumber(execMetrics.retry_metrics.retry_rate * 100, 1)}% taxa
              </div>
            </div>
          </div>
        ) : (
          <div className="small">Sem dados disponíveis</div>
        )}
      </section>

      {/* ORDER TYPE DISTRIBUTION */}
      {execMetrics && orderTypeData.length > 0 && (
        <section className="card">
          <h3>Distribuição de Tipos de Ordem</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={orderTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={70}
                fill="#8884d8"
                dataKey="value"
              >
                {orderTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px"
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* MONITORING METRICS */}
      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>Monitor de Posições</h3>
        {monMetrics ? (
          <div className="grid cols-4" style={{ gap: 12, marginTop: 12 }}>
            <div className="kpi">
              <div className="label">Posições Monitoradas</div>
              <div className="value">{monMetrics.total_positions_monitored}</div>
              <div className="sub">{monMetrics.positions_closed} fechadas</div>
            </div>
            <div className="kpi">
              <div className="label">Tempo Médio Hold</div>
              <div className="value">{formatDuration(monMetrics.position_stats.average_hold_time_sec)}</div>
              <div className="sub">{formatNumber(monMetrics.position_stats.average_hold_time_minutes, 1)} minutos</div>
            </div>
            <div className="kpi">
              <div className="label">MAE/MFE Tracking</div>
              <div className="value">
                {monMetrics.position_stats.positions_with_mae} / {monMetrics.position_stats.positions_with_mfe}
              </div>
              <div className="sub">MAE / MFE rastreados</div>
            </div>
            <div className="kpi">
              <div className="label">Total de Eventos</div>
              <div className="value">
                {Object.values(monMetrics.events).reduce((a, b) => a + b, 0)}
              </div>
              <div className="sub">Eventos de saída</div>
            </div>
          </div>
        ) : (
          <div className="small">Sem dados disponíveis</div>
        )}
      </section>

      {/* EVENT TYPES */}
      {monMetrics && eventTypesData.length > 0 && (
        <section className="card">
          <h3>Tipos de Eventos</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={eventTypesData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" stroke="var(--muted)" />
              <YAxis stroke="var(--muted)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--panel-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px"
                }}
              />
              <Bar dataKey="value" fill="#10b981" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* RISK METRICS */}
      <section className="card" style={{ gridColumn: "1 / -1" }}>
        <h3>Gerenciador de Risco</h3>
        {riskMetrics ? (
          <div className="grid cols-4" style={{ gap: 12, marginTop: 12 }}>
            <div className="kpi">
              <div className="label">Taxa de Aprovação</div>
              <div className="value">{formatNumber(riskMetrics.approval_rate * 100, 1)}%</div>
              <div className="sub">
                {riskMetrics.total_trades_approved} / {riskMetrics.total_trades_validated} aprovados
              </div>
            </div>
            <div className="kpi">
              <div className="label">Win Rate (Dia)</div>
              <div className="value">{formatNumber(riskMetrics.daily_stats.win_rate, 1)}%</div>
              <div className="sub">
                {riskMetrics.daily_stats.wins} wins • {riskMetrics.daily_stats.losses} losses
              </div>
            </div>
            <div className="kpi">
              <div className="label">Streaks</div>
              <div className="value">
                {riskMetrics.consecutive_wins}W / {riskMetrics.consecutive_losses}L
              </div>
              <div className="sub">Wins consecutivos / Losses consecutivos</div>
            </div>
            <div className="kpi">
              <div className="label">Fator Volatilidade</div>
              <div className="value">{formatNumber(riskMetrics.market_volatility_factor, 2)}x</div>
              <div className="sub">Ajuste dinâmico de risco</div>
            </div>
          </div>
        ) : (
          <div className="small">Sem dados disponíveis</div>
        )}
      </section>

      {/* RISK ADJUSTMENTS */}
      {riskMetrics && (
        <section className="card">
          <h3>Ajustes de Risco</h3>
          <div className="grid cols-3" style={{ gap: 12, marginTop: 12 }}>
            <div className="kpi">
              <div className="label">Aumentados</div>
              <div className="value" style={{ color: "var(--ok)" }}>
                {riskMetrics.risk_adjustments.increased}
              </div>
            </div>
            <div className="kpi">
              <div className="label">Reduzidos</div>
              <div className="value" style={{ color: "var(--warn)" }}>
                {riskMetrics.risk_adjustments.decreased}
              </div>
            </div>
            <div className="kpi">
              <div className="label">Normais</div>
              <div className="value">
                {riskMetrics.risk_adjustments.normal}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

