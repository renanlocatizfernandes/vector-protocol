import React from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable';
import { RealizedPnlChart } from '../components/RealizedPnlChart';
import { HealthDashboard } from '../components/HealthDashboard';
import { SniperOperations } from '../components/SniperOperations';
import { TrendingUp, ShieldCheck, Activity, Zap, AlertCircle, Target, TrendingDown, DollarSign, Coins, BarChart3, AlertTriangle } from 'lucide-react';

export const Dashboard: React.FC = () => {
  return (
    <div className="h-screen overflow-y-auto animate-fade-in">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* 🎯 Hero Section */}
        <header className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-6 shadow-xl shadow-blue-500/30">
          <div className="relative flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">
                Central de Investimentos
              </h1>
              <p className="text-lg text-blue-100 font-medium mt-1">
                Acompanhe status, performance e posições em tempo real
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

        {/* ⚠️ Warning Banner */}
        <div className="relative overflow-hidden rounded-xl border-2 border-amber-300 bg-gradient-to-r from-amber-50 to-yellow-50 px-6 py-4 shadow-lg shadow-amber-500/10">
          <div className="relative z-10 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/30 flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-white" />
            </div>
            <p className="text-sm font-bold text-amber-900">
              <span className="text-amber-600">Whitelist ativa:</span> o bot monitora todas as posições, mas novas entradas são permitidas apenas para símbolos na whitelist.
            </p>
          </div>
        </div>

        {/* 📊 Quick Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="stat-card stat-card-primary">
            <div className="flex items-center justify-between mb-3">
              <DollarSign className="w-5 h-5 text-blue-600" />
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">P&L Hoje</p>
            <p className="text-2xl font-bold text-green-600">+$1,234.56</p>
          </div>
          <div className="stat-card stat-card-success">
            <div className="flex items-center justify-between mb-3">
              <Target className="w-5 h-5 text-green-600" />
              <Activity className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Trades Hoje</p>
            <p className="text-2xl font-bold text-slate-900">24</p>
          </div>
          <div className="stat-card stat-card-purple">
            <div className="flex items-center justify-between mb-3">
              <BarChart3 className="w-5 h-5 text-purple-600" />
              <Coins className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Win Rate</p>
            <p className="text-2xl font-bold text-purple-600">78.5%</p>
          </div>
          <div className="stat-card stat-card-danger">
            <div className="flex items-center justify-between mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <TrendingDown className="w-5 h-5 text-slate-600" />
            </div>
            <p className="text-xs font-bold text-slate-600 uppercase">Perda Máx</p>
            <p className="text-2xl font-bold text-red-600">-$45.20</p>
          </div>
        </div>

        {/* 🎯 Sniper Operations */}
        <div className="glass-card-hover">
          <SniperOperations />
        </div>

        {/* 📈 Charts Section */}
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
                  <p className="text-xs text-slate-500 font-medium">Histórico Completo</p>
                </div>
              </div>
            </div>
            <div className="chart-body">
              <RealizedPnlChart />
            </div>
          </div>
        </div>

        {/* ⚙️ Bot Controls */}
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
                    <p className="text-xs text-slate-500 font-medium">Execute operações</p>
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

        {/* 📊 Positions Table */}
        <div className="glass-card-hover overflow-hidden">
          <div className="p-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-blue-50/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Posições Ativas</h3>
                <p className="text-xs text-slate-500 font-medium">Visualize e gerencie suas operações</p>
              </div>
            </div>
          </div>
          <div className="p-6">
            <PositionsTable />
          </div>
        </div>

        {/* 🏥 Health Dashboard - MOVED TO BOTTOM */}
        <div className="glass-card-hover">
          <div className="p-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-blue-50/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Saúde do Sistema</h3>
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
