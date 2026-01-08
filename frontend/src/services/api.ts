import axios from "axios";

// Base URL: usa VITE_API_BASE se fornecido, senão proxy do Vite (dev). Com fallback automático.
const RAW_BASE = (import.meta.env as any).VITE_API_BASE;
const RAW_KEY = (import.meta.env as any).VITE_API_KEY;
const RAW_KEY_HEADER = (import.meta.env as any).VITE_API_KEY_HEADER;
const USE_ENV_BASE =
  !!RAW_BASE &&
  String(RAW_BASE).trim() !== "" &&
  String(RAW_BASE).trim() !== "undefined" &&
  String(RAW_BASE).trim() !== "null";
const API_BASE = USE_ENV_BASE ? String(RAW_BASE).trim() : "";
const API_KEY = RAW_KEY ? String(RAW_KEY).trim() : "";
const API_KEY_HEADER = RAW_KEY_HEADER ? String(RAW_KEY_HEADER).trim() : "X-API-Key";

// Axios instance com timeout menor e fallback para same-origin quando VITE_API_BASE falhar
export const http = axios.create({
  baseURL: API_BASE,
  timeout: 5000,
  headers: API_KEY ? { [API_KEY_HEADER]: API_KEY } : undefined
});

// Fallback automático: se baseURL via VITE_API_BASE falhar por timeout ou Network Error, tenta same-origin (proxy) uma única vez
http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error?.config || {};
    const isTimeout = error?.code === "ECONNABORTED" || /timeout/i.test(String(error?.message || ""));
    const isNetwork = /Network Error/i.test(String(error?.message || ""));
    const canFallback = USE_ENV_BASE && (isTimeout || isNetwork) && !(window as any).__apiFallbackDone;

    if (canFallback) {
      (window as any).__apiFallbackDone = true;
      http.defaults.baseURL = "";
      cfg.baseURL = "";
      try {
        return await http.request(cfg);
      } catch (err) {
        (window as any).__apiFallbackDone = false;
        throw err;
      }
    }
    throw error;
  }
);

// Tipos básicos
export type Health = {
  status: string;
  version: string;
  modules?: Record<string, string>;
};

export type BotStatus = {
  running: boolean;
  dry_run?: boolean;
  scan_interval?: number; // segundos
  min_score?: number;
  max_positions?: number;
  circuit_breaker_active?: boolean;
  symbols?: string[];
};

export type DailyStats = {
  total_pnl: number;
  trades_count: number;
  win_rate: number;
  best_trade?: { symbol?: string; pnl?: number };
  worst_trade?: { symbol?: string; pnl?: number };
  balance: number;
  db?: {
    total_pnl: number;
    trades_count: number;
    win_rate: number;
    best_trade?: { symbol?: string; pnl?: number };
    worst_trade?: { symbol?: string; pnl?: number };
    day_start_local?: string;
  };
  exchange?: {
    realized_pnl: number;
    fees: number;
    funding: number;
    net_realized_pnl: number;
    unrealized_pnl: number;
    net_pnl: number;
    total_wallet: number;
    available_balance: number;
    daily_start_balance?: number | null;
    wallet_change?: number | null;
    wallet_change_pct?: number | null;
    intraday_peak_balance?: number | null;
    intraday_trough_balance?: number | null;
    day_start_utc?: string;
  };
};

export type RealizedDailyPoint = {
  date: string;
  realized_pnl: number;
  fees: number;
  funding: number;
  net_pnl: number;
};

export type RealizedDailyResponse = {
  days: number;
  series: RealizedDailyPoint[];
};

export type DashboardData = {
  account: {
    balance: number;
    total_wallet: number;
  };
  portfolio: any;
  open_trades: Array<{
    id: number;
    symbol: string;
    direction: string;
    entry_price: number;
    current_price?: number;
    quantity: number;
    leverage?: number;
    pnl?: number;
    pnl_percentage?: number;
    opened_at?: string;
  }>;
  exchange_positions?: Array<{
    symbol: string;
    direction: string;
    entry_price: number;
    current_price?: number;
    quantity: number;
    leverage?: number;
    pnl?: number;
    pnl_percentage?: number;
    opened_at?: string | null;
    margin_mode?: string | null;
    isolated?: boolean | null;
  }>;
  positions_source?: string;
  statistics: {
    total_trades: number;
    open_trades: number;
    closed_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    avg_win: number;
    avg_loss: number;
  };
};

export type ConfigResponse = {
  max_positions: number;
  risk_per_trade: number;
  max_portfolio_risk: number;
  default_leverage: number;
  testnet: boolean;
  symbol_whitelist?: string[];
};

// Helpers
const unwrap = <T, R = any>(res: { data: R }): R => res.data as R;

// Health e versão
export async function getHealth(): Promise<Health> {
  const res = await http.get("/health");
  return unwrap(res);
}
export async function getVersion(): Promise<any> {
  const res = await http.get("/version");
  return unwrap(res);
}

// Trading - Bot
export async function getBotStatus(): Promise<BotStatus> {
  const res = await http.get("/api/trading/bot/status");
  return unwrap(res);
}

export async function startBot(dry_run: boolean = true): Promise<any> {
  const res = await http.post("/api/trading/bot/start", null, {
    params: { dry_run }
  });
  return unwrap(res);
}

export async function stopBot(): Promise<any> {
  const res = await http.post("/api/trading/bot/stop");
  return unwrap(res);
}

export async function updateBotConfig(params: {
  scan_interval_minutes?: number;
  min_score?: number;
  max_positions?: number;
  symbols?: string;
}): Promise<any> {
  // Backend espera query params, não body
  const res = await http.put("/api/trading/bot/config", null, { params });
  return unwrap(res);
}

// Trading - Stats
export async function getDailyStats(): Promise<DailyStats> {
  const res = await http.get("/api/trading/stats/daily");
  return unwrap(res);
}

export async function getRealizedDailyStats(days: number = 7): Promise<RealizedDailyResponse> {
  const res = await http.get("/api/trading/stats/realized-daily", { params: { days } });
  return unwrap(res);
}

// Positions dashboard
export async function getPositionsDashboard(): Promise<DashboardData> {
  const res = await http.get("/api/positions/dashboard");
  return unwrap(res);
}

/**
 * Sincroniza posições entre DB e corretora.
 * - mode: "normal" | "strict" (strict aplica reconciliação forte)
 * - strict: boolean (alternativa ao mode)
 */
export async function syncPositions(params?: { mode?: "normal" | "strict"; strict?: boolean }): Promise<any> {
  const res = await http.post("/api/positions/sync", null, { params });
  return unwrap(res);
}

// Position actions
export async function closePositionExchange(symbol: string): Promise<any> {
  const res = await http.post("/api/trading/positions/close-exchange", null, { params: { symbol } });
  return unwrap(res);
}

export async function setPositionStopLoss(params: { symbol: string; stop_price?: number; stop_pct?: number }): Promise<any> {
  const res = await http.post("/api/trading/positions/stop-loss", null, { params });
  return unwrap(res);
}

export async function setPositionTakeProfit(params: { symbol: string; take_profit_price?: number; take_profit_pct?: number }): Promise<any> {
  const res = await http.post("/api/trading/positions/take-profit", null, { params });
  return unwrap(res);
}

export async function setPositionBreakeven(symbol: string): Promise<any> {
  const res = await http.post("/api/trading/positions/breakeven", null, { params: { symbol } });
  return unwrap(res);
}

export async function setPositionTrailingStop(symbol: string): Promise<any> {
  const res = await http.post("/api/trading/positions/trailing-stop", null, { params: { symbol } });
  return unwrap(res);
}

export async function cancelOpenOrders(symbol: string): Promise<any> {
  const res = await http.post("/api/positions/open-orders/cancel-all", null, { params: { symbol, dry_run: false } });
  return unwrap(res);
}

// Config global
export async function getConfig(): Promise<ConfigResponse> {
  // Usa barra final para evitar redirect 307 em alguns setups
  const res = await http.get("/api/config/");
  return unwrap(res);
}

export async function testTelegram(): Promise<any> {
  const res = await http.post("/api/trading/test/telegram");
  return unwrap(res);
}

// Mercado (básico)
export async function getSignals(min_score: number = 70): Promise<{ count: number; signals: any[]; scan_count?: number }> {
  const res = await http.get("/api/market/signals", { params: { min_score } });
  return unwrap(res);
}

// Backtest (básico)
export async function backtestQuick(days: number = 30, initial_balance: number = 5000): Promise<any> {
  const res = await http.get("/api/backtest/quick", { params: { days, initial_balance } });
  return unwrap(res);
}

export async function backtestRun(payload: {
  start_date: string;
  end_date: string;
  initial_balance: number;
  symbols?: string[] | null;
  max_positions: number;
}): Promise<any> {
  const res = await http.post("/api/backtest/run", payload);
  return unwrap(res);
}

export async function getComposeStatus(): Promise<{ ok?: boolean; items?: any[]; count?: number }> {
  const res = await http.get("/api/system/compose");
  return unwrap(res);
}

export async function getLogs(component: string = "api", tail: number = 300): Promise<{ component: string; file: string; count: number; lines: string[] }> {
  const res = await http.get("/api/system/logs", { params: { component, tail } });
  return unwrap(res);
}

// Supervisor controls
export type SupervisorStatus = {
  enabled: boolean;
  interventions_tail: string[];
  last_intervention_at?: string;
  flag_path: string;
  log_path: string;
};

export async function getSupervisorStatus(): Promise<SupervisorStatus> {
  const res = await http.get("/api/system/supervisor/status");
  return unwrap(res);
}

export async function supervisorEnable(): Promise<{ ok: boolean; enabled: boolean }> {
  const res = await http.post("/api/system/supervisor/enable");
  return unwrap(res);
}

export async function supervisorDisable(): Promise<{ ok: boolean; enabled: boolean }> {
  const res = await http.post("/api/system/supervisor/disable");
  return unwrap(res);
}

export async function supervisorToggle(): Promise<{ ok: boolean; enabled: boolean }> {
  const res = await http.post("/api/system/supervisor/toggle");
  return unwrap(res);
}

export type SupervisorHealth = {
  monitoring: boolean;
  restarts: number;
  components: Record<string, { status: string; last_heartbeat_ago: string }>;
  system: {
    cpu_percent: number;
    memory_mb: number;
  };
};

export async function getSupervisorHealth(): Promise<SupervisorHealth> {
  const res = await http.get("/api/system/supervisor/health");
  return unwrap(res);
}

// Metrics - New endpoints for module metrics
export type BotMetrics = {
  total_cycles: number;
  cycles_with_trades: number;
  cycles_without_trades: number;
  signals: {
    total_generated: number;
    total_approved: number;
    total_rejected: number;
    approval_rate_pct: number;
  };
  rejection_reasons: {
    market_filter: number;
    correlation_filter: number;
    blacklist: number;
    risk_manager: number;
    execution_failed: number;
  };
  latencies: {
    avg_scan_time_sec: number;
    max_scan_time_sec: number;
    min_scan_time_sec: number;
    avg_signal_generation_time_sec: number;
    max_signal_generation_time_sec: number;
    min_signal_generation_time_sec: number;
    avg_filter_time_sec: number;
    max_filter_time_sec: number;
    min_filter_time_sec: number;
    avg_execution_time_sec: number;
    max_execution_time_sec: number;
    min_execution_time_sec: number;
    avg_total_cycle_time_sec: number;
    max_total_cycle_time_sec: number;
    min_total_cycle_time_sec: number;
  };
  execution: {
    total_attempted: number;
    total_successful: number;
    total_failed: number;
    success_rate_pct: number;
  };
  recent_cycles: any[];
};

export type ExecutionMetrics = {
  total_orders: number;
  successful_orders: number;
  failed_orders: number;
  success_rate: number;
  order_type_distribution: {
    limit: number;
    market: number;
    iceberg: number;
  };
  maker_taker_distribution: {
    maker: number;
    taker: number;
    maker_ratio: number;
  };
  average_slippage_pct: number;
  average_execution_time_sec: number;
  retry_metrics: {
    total_retries: number;
    re_quotes: number;
    retry_rate: number;
  };
  recent_orders: any[];
};

export type MonitoringMetrics = {
  total_positions_monitored: number;
  positions_closed: number;
  events: {
    trailing_stop: number;
    partial_tp: number;
    emergency_stop: number;
    max_loss: number;
    take_profit: number;
    stop_loss: number;
  };
  position_stats: {
    average_hold_time_sec: number;
    total_hold_time_sec: number;
    positions_with_mae: number;
    positions_with_mfe: number;
    average_hold_time_minutes: number;
  };
  recent_mae_mfe: any[];
  recent_events: any[];
};

export type RiskMetrics = {
  total_trades_validated: number;
  total_trades_approved: number;
  total_trades_rejected: number;
  rejection_reasons: Record<string, number>;
  risk_adjustments: {
    increased: number;
    decreased: number;
    normal: number;
  };
  daily_stats: {
    wins: number;
    losses: number;
    win_rate: number;
  };
  consecutive_wins: number;
  consecutive_losses: number;
  market_volatility_factor: number;
  approval_rate: number;
};

export async function getBotMetrics(): Promise<BotMetrics> {
  const res = await http.get("/api/trading/bot/metrics");
  return unwrap(res);
}

export async function getExecutionMetrics(): Promise<ExecutionMetrics> {
  const res = await http.get("/api/trading/execution/metrics");
  return unwrap(res);
}

export async function getMonitoringMetrics(): Promise<MonitoringMetrics> {
  const res = await http.get("/api/trading/monitoring/metrics");
  return unwrap(res);
}

export async function getRiskMetrics(): Promise<RiskMetrics> {
  const res = await http.get("/api/trading/risk/metrics");
  return unwrap(res);
}

export type PnlBySymbol = {
  symbol: string;
  total_trades: number;
  total_pnl: number;
  win_rate: number;
};

export async function getPnlBySymbol(): Promise<PnlBySymbol[]> {
  const res = await http.get("/api/trading/stats/pnl_by_symbol");
  return unwrap(res);
}

export type MarketTicker = {
  symbol: string;
  last_price: number;
  price_change_percent: number;
  quote_volume: number;
};

export type MarketTickersResponse = {
  count: number;
  tickers: MarketTicker[];
};

export async function getMarketTickers(limit: number = 200, quote: string = "USDT"): Promise<MarketTickersResponse> {
  const res = await http.get("/api/market/tickers", { params: { limit, quote } });
  return unwrap(res);
}

export type FearGreedPoint = {
  value: number;
  classification?: string | null;
  timestamp: number;
};

export type FearGreedResponse = {
  count: number;
  data: FearGreedPoint[];
  latest?: FearGreedPoint | null;
};

export async function getFearGreed(limit: number = 30): Promise<FearGreedResponse> {
  const res = await http.get("/api/market/fear-greed", { params: { limit } });
  return unwrap(res);
}

export interface HistoryAnalysis {
  symbol_stats: {
    symbol: string;
    total_trades: number;
    total_pnl: number;
    win_rate: number;
  }[];
  blacklist_recommendations: string[];
  binance_pnl_24h: {
    net_pnl: number;
    gross_pnl: number;
    fees: number;
    funding: number;
  };
}

export async function getHistoryAnalysis(): Promise<HistoryAnalysis> {
  const res = await http.get("/api/trading/history/analysis");
  return unwrap(res);
}

// ========================================
// PHASE 2-4: Health Monitoring & PnL
// ========================================

// Cumulative PnL (Phase 2)
export interface CumulativePnlPoint {
  date: string;
  net_pnl: number;
  cumulative: number;
  realized: number;
  fees: number;
  funding: number;
}

export interface CumulativePnlResponse {
  series: CumulativePnlPoint[];
}

export async function getCumulativePnl(days: number = 30): Promise<CumulativePnlResponse> {
  const res = await http.get(`/api/trading/stats/cumulative-pnl`, { params: { days } });
  return unwrap(res);
}

// Error Monitoring (Phase 4)
export interface ErrorLog {
  timestamp: number;
  component: string;
  level: string;
  message: string;
  traceback?: string;
}

export interface ErrorsResponse {
  errors: ErrorLog[];
  count: number;
  limit: number;
  filters: { component?: string; level?: string };
}

export async function getRecentErrors(limit: number = 50, component?: string, level?: string): Promise<ErrorsResponse> {
  const params: any = { limit };
  if (component) params.component = component;
  if (level) params.level = level;
  const res = await http.get("/api/system/errors/recent", { params });
  return unwrap(res);
}

export interface ErrorRateResponse {
  hourly: Array<{ hour: string; count: number }>;
  total: number;
  average_per_hour: number;
}

export async function getErrorRate(component?: string, hours: number = 24): Promise<ErrorRateResponse> {
  const params: any = { hours };
  if (component) params.component = component;
  const res = await http.get("/api/system/errors/rate", { params });
  return unwrap(res);
}

export interface ErrorSummary {
  by_component: Record<string, number>;
  by_level: Record<string, number>;
  total: number;
}

export async function getErrorSummary(): Promise<ErrorSummary> {
  const res = await http.get("/api/system/errors/summary");
  return unwrap(res);
}

// Latency Monitoring (Phase 4)
export interface LatencyStats {
  last_cycle: {
    scan?: number;
    signal?: number;
    execution?: number;
    total?: number;
  };
  sla_status: string;
  sla_threshold: number;
  timestamp: string;
}

export async function getLatencyStats(): Promise<LatencyStats> {
  const res = await http.get("/api/system/latency");
  return unwrap(res);
}

// Sync Status (Phase 4)
export interface SyncStatus {
  last_sync: string | null;
  last_sync_ago_seconds: number | null;
  auto_sync_enabled: boolean;
  auto_sync_interval_minutes: number;
  divergences: Array<{
    symbol: string;
    exchange_qty: number;
    db_qty: number;
    delta: number;
  }>;
  divergence_count: number;
  status: string;
  db_positions_count: number;
  exchange_positions_count: number;
}

export async function getSyncStatus(): Promise<SyncStatus> {
  const res = await http.get("/api/positions/sync/status");
  return unwrap(res);
}

// Market Conditions (Phase 4)
export interface MarketConditions {
  high_funding: Array<{
    symbol: string;
    funding_rate: number;
    funding_rate_pct: number;
    next_funding_time?: number;
    mark_price: number;
  }>;
  trending_symbols: Array<{
    symbol: string;
    price_change_pct: number;
    volume: number;
    volume_usd: string;
    price: number;
    direction: string;
  }>;
  volatility_index: number;
  timestamp: string;
}

export async function getMarketConditions(): Promise<MarketConditions> {
  const res = await http.get("/api/system/market/conditions");
  return unwrap(res);
}

// Utils
export function toMinutes(seconds?: number): number {
  if (!seconds && seconds !== 0) return 0;
  return Math.round((seconds as number) / 60);
}
export function toSeconds(minutes?: number): number {
  if (!minutes && minutes !== 0) return 0;
  return Math.round((minutes as number) * 60);
}
