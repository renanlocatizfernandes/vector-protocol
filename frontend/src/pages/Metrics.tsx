import React, { useEffect, useState, useCallback } from "react";
import {
  getBotMetrics,
  getExecutionMetrics,
  getMonitoringMetrics,
  getRiskMetrics,
  getPnlBySymbol,
  getHistoryAnalysis,
  type BotMetrics,
  type ExecutionMetrics,
  type MonitoringMetrics,
  type RiskMetrics,
  type PnlBySymbol,
  type HistoryAnalysis
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Activity,
  RefreshCw,
  Zap,
  Shield,
  Clock,
  BarChart3,
  Target,
  AlertTriangle,
  TrendingUp,

  TrendingDown,
  History,
  Wallet,
  Ban
} from "lucide-react";

const COLORS = ["#2ad4c6", "#f59f3a", "#4fc3f7", "#2bd4a5", "#ff5a5f", "#9aa3b2"];

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

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-popover border border-border rounded-lg shadow-lg p-3 text-sm">
        <p className="font-semibold mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2" style={{ color: entry.color }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span>{entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function Metrics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [botMetrics, setBotMetrics] = useState<BotMetrics | null>(null);
  const [execMetrics, setExecMetrics] = useState<ExecutionMetrics | null>(null);
  const [monMetrics, setMonMetrics] = useState<MonitoringMetrics | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);

  const [pnlBySymbol, setPnlBySymbol] = useState<PnlBySymbol[]>([]);
  const [historyAnalysis, setHistoryAnalysis] = useState<HistoryAnalysis | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bot, exec, mon, risk, pnl, history] = await Promise.all([
        getBotMetrics().catch(() => null),
        getExecutionMetrics().catch(() => null),
        getMonitoringMetrics().catch(() => null),
        getRiskMetrics().catch(() => null),
        getPnlBySymbol().catch(() => []),
        getHistoryAnalysis().catch(() => null)
      ]);
      if (bot) setBotMetrics(bot);
      if (exec) setExecMetrics(exec);
      if (mon) setMonMetrics(mon);
      if (risk) setRiskMetrics(risk);
      if (pnl) setPnlBySymbol(pnl);
      if (history) setHistoryAnalysis(history);
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
    { name: "Signal", avg: botMetrics.latencies.avg_signal_generation_time_sec, max: botMetrics.latencies.max_signal_generation_time_sec },
    { name: "Filter", avg: botMetrics.latencies.avg_filter_time_sec, max: botMetrics.latencies.max_filter_time_sec },
    { name: "Exec", avg: botMetrics.latencies.avg_execution_time_sec, max: botMetrics.latencies.max_execution_time_sec },
    { name: "Total", avg: botMetrics.latencies.avg_total_cycle_time_sec, max: botMetrics.latencies.max_total_cycle_time_sec }
  ] : [];

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-destructive/10 text-destructive p-4 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Analytics</span>
          <h1 className="text-3xl font-semibold text-white mt-2">Metrics & Performance</h1>
          <p className="text-muted-foreground mt-1">Monitoramento em tempo real dos KPIs e saúde do sistema.</p>
        </div>
        <Button onClick={loadAll} disabled={loading} variant="outline" className="gap-2">
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Atualizando..." : "Atualizar"}
        </Button>
      </div>



      {/* HISTORY ANALYSIS SECTION */}
      {
        historyAnalysis && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* REALIZED PNL CARD */}
            <Card className="glass-card border-primary/20 bg-white/5">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Wallet className="w-5 h-5 text-success" />
                  PnL Realizado (24h)
                </CardTitle>
                <CardDescription>Dados oficiais da Binance (com taxas)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Lucro Líquido</p>
                    <div className={`text-3xl font-bold ${historyAnalysis.binance_pnl_24h.net_pnl >= 0 ? "text-success" : "text-danger"}`}>
                      {historyAnalysis.binance_pnl_24h.net_pnl >= 0 ? "+" : ""}{formatNumber(historyAnalysis.binance_pnl_24h.net_pnl)} USDT
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="p-2 bg-white/5 rounded border">
                      <p className="text-muted-foreground">Bruto</p>
                      <p className="font-semibold">{formatNumber(historyAnalysis.binance_pnl_24h.gross_pnl)}</p>
                    </div>
                    <div className="p-2 bg-white/5 rounded border">
                      <p className="text-muted-foreground">Taxas</p>
                      <p className="font-semibold text-red-400">{formatNumber(historyAnalysis.binance_pnl_24h.fees)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* BLACKLIST RECOMMENDATIONS */}
            <Card className="md:col-span-2 border-accent/20">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Ban className="w-5 h-5 text-accent" />
                  Recomendações de Bloqueio
                </CardTitle>
                <CardDescription>Símbolos com baixa performance sugeridos para blacklist</CardDescription>
              </CardHeader>
              <CardContent>
                {historyAnalysis.blacklist_recommendations.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {historyAnalysis.blacklist_recommendations.map(symbol => (
                      <Badge key={symbol} variant="destructive" className="text-sm py-1 px-3">
                        {symbol}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-success bg-success/10 p-3 rounded-lg">
                    <Shield className="w-4 h-4" />
                    <span className="font-medium">Nenhuma recomendação de bloqueio no momento.</span>
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-4">
                  * Baseado em Win Rate &lt; 30% e PnL negativo nos últimos 7 dias.
                </p>
              </CardContent>
            </Card>
          </div>
        )
      }

      {/* BOT METRICS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              Bot Autônomo
            </CardTitle>
            <CardDescription>Performance dos ciclos de decisão</CardDescription>
          </CardHeader>
          <CardContent>
            {botMetrics ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-muted-foreground">Ciclos Totais</p>
                  <div className="text-2xl font-bold">{botMetrics.total_cycles}</div>
                  <p className="text-xs text-muted-foreground">
                    {botMetrics.cycles_with_trades} trades • {botMetrics.cycles_without_trades} idle
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-muted-foreground">Taxa Aprovação</p>
                  <div className="text-2xl font-bold text-success">
                    {formatNumber(botMetrics.signals.approval_rate_pct, 1)}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {botMetrics.signals.total_approved}/{botMetrics.signals.total_generated} sinais
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-muted-foreground">Sucesso Execução</p>
                  <div className="text-2xl font-bold text-primary">
                    {formatNumber(botMetrics.execution.success_rate_pct, 1)}%
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {botMetrics.execution.total_successful}/{botMetrics.execution.total_attempted} ordens
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-muted-foreground">Tempo Ciclo</p>
                  <div className="text-2xl font-bold">
                    {formatDuration(botMetrics.latencies.avg_total_cycle_time_sec)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Máx: {formatDuration(botMetrics.latencies.max_total_cycle_time_sec)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">Carregando dados...</div>
            )}
          </CardContent>
        </Card>

        {/* LATENCY CHART */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-accent" />
              Latências
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[200px]">
            {botMetrics && latencyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latencyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                  <Bar dataKey="avg" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Média" />
                  <Bar dataKey="max" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Máximo" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Sem dados de latência
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* REJECTION REASONS */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Razões de Rejeição</CardTitle>
          </CardHeader>
          <CardContent className="h-[250px]">
            {botMetrics && rejectionReasonsData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={rejectionReasonsData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {rejectionReasonsData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Sem rejeições registradas
              </div>
            )}
          </CardContent>
        </Card>

        {/* ORDER TYPES */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Distribuição de Ordens</CardTitle>
          </CardHeader>
          <CardContent className="h-[250px]">
            {execMetrics && orderTypeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={orderTypeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {orderTypeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Sem ordens executadas
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* EXECUTION & RISK GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* EXECUTION METRICS */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-accent" />
              Execução
            </CardTitle>
          </CardHeader>
          <CardContent>
            {execMetrics ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Slippage Médio</p>
                  <div className="text-xl font-bold text-foreground">
                    {formatNumber(execMetrics.average_slippage_pct, 3)}%
                  </div>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Maker Ratio</p>
                  <div className="text-xl font-bold text-foreground">
                    {formatNumber(execMetrics.maker_taker_distribution.maker_ratio * 100, 1)}%
                  </div>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Re-quotes</p>
                  <div className="text-xl font-bold text-foreground">
                    {execMetrics.retry_metrics.re_quotes}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {execMetrics.retry_metrics.total_retries} retries
                  </p>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-sm text-muted-foreground mb-1">Tempo Médio</p>
                  <div className="text-xl font-bold text-foreground">
                    {formatDuration(execMetrics.average_execution_time_sec)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">Carregando...</div>
            )}
          </CardContent>
        </Card>

        {/* RISK METRICS */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-danger" />
              Gerenciamento de Risco
            </CardTitle>
          </CardHeader>
          <CardContent>
            {riskMetrics ? (
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Win Rate (Dia)</p>
                    <div className="text-xl font-bold mt-1">
                      {formatNumber(riskMetrics.daily_stats.win_rate, 1)}%
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {riskMetrics.daily_stats.wins}W - {riskMetrics.daily_stats.losses}L
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Streak Atual</p>
                    <div className="text-xl font-bold mt-1 flex justify-center gap-2">
                      <span className="text-success">{riskMetrics.consecutive_wins}W</span>
                      <span className="text-muted-foreground">/</span>
                      <span className="text-danger">{riskMetrics.consecutive_losses}L</span>
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Volatilidade</p>
                    <div className="text-xl font-bold mt-1">
                      {formatNumber(riskMetrics.market_volatility_factor, 2)}x
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <p className="text-sm font-medium mb-3">Ajustes Dinâmicos de Risco</p>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="flex flex-col items-center p-2 bg-success/10 rounded border border-success/20">
                      <span className="text-success font-bold">{riskMetrics.risk_adjustments.increased}</span>
                      <span className="text-xs text-muted-foreground">Aumentados</span>
                    </div>
                    <div className="flex flex-col items-center p-2 bg-danger/10 rounded border border-danger/20">
                      <span className="text-danger font-bold">{riskMetrics.risk_adjustments.decreased}</span>
                      <span className="text-xs text-muted-foreground">Reduzidos</span>
                    </div>
                    <div className="flex flex-col items-center p-2 bg-white/5 rounded border border-white/10">
                      <span className="font-bold">{riskMetrics.risk_adjustments.normal}</span>
                      <span className="text-xs text-muted-foreground">Normais</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">Carregando...</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* MONITORING EVENTS */}
      {
        monMetrics && eventTypesData.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                Eventos de Monitoramento
              </CardTitle>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={eventTypesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                  <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} name="Ocorrências" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )
      }

      {/* PNL BY SYMBOL TABLE */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            Performance por Símbolo
          </CardTitle>
          <CardDescription>Lucro/Prejuízo acumulado por par de moeda</CardDescription>
        </CardHeader>
        <CardContent>
          {pnlBySymbol.length > 0 ? (
            <div className="max-h-[400px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Símbolo</TableHead>
                    <TableHead className="text-right">Trades</TableHead>
                    <TableHead className="text-right">Win Rate</TableHead>
                    <TableHead className="text-right">PnL (USDT)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pnlBySymbol.map((item) => (
                    <TableRow key={item.symbol}>
                      <TableCell className="font-medium">{item.symbol}</TableCell>
                      <TableCell className="text-right">{item.total_trades}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant={item.win_rate >= 50 ? "default" : "destructive"}>
                          {item.win_rate.toFixed(1)}%
                        </Badge>
                      </TableCell>
                      <TableCell className={`text-right font-bold ${item.total_pnl >= 0 ? "text-success" : "text-danger"}`}>
                        {item.total_pnl > 0 ? "+" : ""}{item.total_pnl.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Nenhum trade fechado ainda para exibir estatísticas por símbolo.
            </div>
          )}
        </CardContent>
      </Card>
    </div >
  );
}
