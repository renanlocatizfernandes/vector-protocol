import React, { useEffect, useState } from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable';
import { RealizedPnlChart } from '../components/RealizedPnlChart';
import { TradeHistory } from '../components/TradeHistory';
import { HealthDashboard } from '../components/HealthDashboard';
import { SniperOperations } from '../components/SniperOperations';
import { TrendingUp, ShieldCheck, Activity, Zap, AlertCircle, Target, TrendingDown, DollarSign, Coins, BarChart3, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getDatabaseConfig, updateDatabaseConfig, getDailyStats, type DailyStats } from '../services/api';

export const Dashboard: React.FC = () => {
  const [whitelistStrict, setWhitelistStrict] = useState<boolean | null>(null);
  const [whitelistBusy, setWhitelistBusy] = useState(false);
  const [dailyStats, setDailyStats] = useState<DailyStats | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const wl = await getDatabaseConfig('SCANNER_STRICT_WHITELIST');
        if (wl && typeof wl.value === 'boolean') {
          setWhitelistStrict(wl.value);
        } else {
          setWhitelistStrict(false);
        }
      } catch {
        setWhitelistStrict(false);
      }
    })();
  }, []);

  useEffect(() => {
    let active = true;
    const loadStats = async () => {
      try {
        const stats = await getDailyStats();
        if (active) setDailyStats(stats);
      } catch {
        if (active) setDailyStats(null);
      }
    };
    loadStats();
    const timer = setInterval(loadStats, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const onToggleWhitelist = async () => {
    if (whitelistStrict === null) return;
    setWhitelistBusy(true);
    try {
      const nextValue = !whitelistStrict;
      await updateDatabaseConfig(
        'SCANNER_STRICT_WHITELIST',
        nextValue,
        'Toggle whitelist strict mode'
      );
      setWhitelistStrict(nextValue);
    } finally {
      setWhitelistBusy(false);
    }
  };

  const exDaily = dailyStats?.exchange?.daily_net_pnl ?? null;
  const exRealized = dailyStats?.exchange?.net_realized_pnl ?? null;
  const exFees = dailyStats?.exchange?.fees ?? null;
  const exFunding = dailyStats?.exchange?.funding ?? null;
  const exUnrealized = dailyStats?.exchange?.unrealized_pnl ?? null;
  const formatMoney = (value: number | null) =>
    value === null ? "--" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
  const dailyPnlText = formatMoney(exDaily);
  const realizedText = formatMoney(exRealized);
  const feesFundingValue = exFees === null || exFunding === null ? null : exFees + exFunding;
  const feesFundingText =
    feesFundingValue === null ? "--" : `${feesFundingValue >= 0 ? "+" : ""}${feesFundingValue.toFixed(2)}`;
  const unrealizedText = formatMoney(exUnrealized);

  return (
    <div className="h-screen overflow-y-auto animate-fade-in">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/*  Hero Section */}
        <header className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-6 shadow-xl shadow-blue-500/30">
          <div className="relative flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">
                Central de Investimentos
              </h1>
              <p className="text-lg text-blue-100 font-medium mt-1">
                Acompanhe status, performance e posicoes em tempo real
              </p>
            </div>
            <div className="flex gap-3">
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/20 backdrop-blur-sm border border-white/30">
                <Zap className="w-4 h-4 text-white" />
                <span className="text-sm font-bold text-white">Tempo Real</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/20 backdrop-blur-sm border border-white/30">
                <Activity className="w-4 h-4 text-white" />
                <span className="text-sm font-bold text-white">Ativo 24/7</span>
              </div>
            </div>
          </div>
        </header>

        {/*  Warning Banner */}
        <div className="relative overflow-hidden rounded-xl border-2 border-amber-300 bg-gradient-to-r from-amber-50 to-yellow-50 px-6 py-4 shadow-lg shadow-amber-500/10">
          <div className="relative z-10 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/30 flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-1 flex-col gap-2">
              <p className="text-sm font-bold text-amber-900">
                {whitelistStrict
                  ? "Whitelist ativa: o bot monitora todas as posicoes, mas novas entradas so executam para simbolos na whitelist."
                  : "Whitelist desativada: o bot pode abrir novas entradas para qualquer simbolo permitido pelo scanner."}
              </p>
              <div>
                <Button
                  type="button"
                  size="sm"
                  variant={whitelistStrict ? "destructive" : "outline"}
                  onClick={onToggleWhitelist}
                  disabled={whitelistBusy || whitelistStrict === null}
                >
                  {whitelistStrict ? "Desativar whitelist" : "Ativar whitelist"}
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/*  Quick Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="stat-card stat-card-primary">
            <div className="flex items-center justify-between mb-3">
              <DollarSign className="w-5 h-5 text-blue-600" />
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">P&L Hoje (Exchange)</p>
            <p
              className={`text-2xl font-bold ${exDaily === null ? "text-slate-500" : exDaily >= 0 ? "text-green-600" : "text-red-600"
                }`}
            >
              {dailyPnlText}
            </p>
          </div>
          <div className="stat-card stat-card-success">
            <div className="flex items-center justify-between mb-3">
              <Target className="w-5 h-5 text-green-600" />
              <Activity className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Realizado (24h)</p>
            <p
              className={`text-2xl font-bold ${exRealized === null ? "text-slate-500" : exRealized >= 0 ? "text-green-600" : "text-red-600"
                }`}
            >
              {realizedText}
            </p>
          </div>
          <div className="stat-card stat-card-purple">
            <div className="flex items-center justify-between mb-3">
              <BarChart3 className="w-5 h-5 text-purple-600" />
              <Coins className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Fees + Funding (24h)</p>
            <p
              className={`text-2xl font-bold ${feesFundingValue === null ? "text-slate-500" : feesFundingValue >= 0 ? "text-green-600" : "text-red-600"
                }`}
            >
              {feesFundingText}
            </p>
          </div>
          <div className="stat-card stat-card-danger">
            <div className="flex items-center justify-between mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <TrendingDown className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Nao Realizado</p>
            <p
              className={`text-2xl font-bold ${exUnrealized === null ? "text-slate-500" : exUnrealized >= 0 ? "text-green-600" : "text-red-600"
                }`}
            >
              {unrealizedText}
            </p>
          </div>
        </div>

        {/*  Sniper Operations */}
        <div className="glass-card-hover">
          <SniperOperations />
        </div>

        {/*  Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="chart-container">
            <div className="chart-header">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Performance</h3>
                  <p className="text-xs text-slate-500 font-medium">P&L em Tempo Real</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full pulse-dot" />
                <span className="text-xs font-bold text-green-600">Live</span>
              </div>
            </div>
            <div className="chart-body">
              <PerformanceChart />
            </div>
          </div>

          <div className="chart-container">
            <div className="chart-header">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-600 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/30">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">P&L Realizado</h3>
                  <p className="text-xs text-slate-500 font-medium">Historico Completo</p>
                </div>
              </div>
            </div>
            <div className="chart-body">
              <RealizedPnlChart />
            </div>
          </div>
        </div>

        {/*  Bot Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="glass-card h-full">
              <div className="p-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-purple-50/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                    <Activity className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">Trade Manual</h3>
                    <p className="text-xs text-slate-500 font-medium">Execute operacoes</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <ManualTrade />
              </div>
            </div>
          </div>
          <div className="lg:col-span-2">
            <div className="glass-card h-full">
              <div className="p-6 border-b border-slate-200/50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                    <ShieldCheck className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">Status do Sistema</h3>
                    <p className="text-xs text-slate-500 font-medium">Controle e monitoramento</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <BotStatus />
              </div>
            </div>
          </div>
        </div>

        {/*  Positions Table */}
        <div className="glass-card-hover overflow-hidden">
          <div className="p-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-blue-50/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Posicoes Ativas</h3>
                <p className="text-xs text-slate-500 font-medium">Visualize e gerencie suas operacoes</p>
              </div>
            </div>
          </div>
          <div className="p-6">
            <PositionsTable />
          </div>
        </div>

        {/*  Trade History */}
        <div className="glass-card-hover overflow-hidden">
          <TradeHistory />
        </div>

        {/*  Health Dashboard - MOVED TO BOTTOM */}
        <div className="glass-card-hover">
          <div className="p-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-blue-50/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Saude do Sistema</h3>
                <p className="text-xs text-slate-500 font-medium">Monitoramento de componentes</p>
              </div>
            </div>
          </div>
          <div className="p-6">
            <HealthDashboard />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
