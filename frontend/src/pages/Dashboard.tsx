import React from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable'; // Keeping existing for now, will refactor later
import { RealizedPnlChart } from '../components/RealizedPnlChart';
import { HealthDashboard } from '../components/HealthDashboard';

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-8 animate-fade-in">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
          <h1 className="text-3xl font-bold text-gray-900">Central de Investimentos</h1>
        </div>
        <p className="text-gray-600 ml-4">Acompanhe status, performance e posições ativas em tempo real.</p>
      </header>

      <div className="rounded-lg border border-yellow-300 bg-yellow-50 text-yellow-800 px-4 py-3 text-sm font-medium">
        Whitelist ativa: o bot monitora todas as posições, mas novas entradas são permitidas apenas para símbolos na whitelist.
      </div>

      {/* Top Section: Status & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
        {/* Left: Status & Controls */}
        <div className="flex flex-col gap-6">
          <BotStatus />
        </div>

        {/* Right: Chart */}
        <div className="lg:col-span-2 min-h-[350px]">
          <PerformanceChart />
        </div>
      </div>

      {/* Manual Trade + Realized PnL */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '0.2s' }}>
        <div className="lg:col-span-1">
          <ManualTrade />
        </div>
        <div className="lg:col-span-2 min-h-[260px]">
          <RealizedPnlChart />
        </div>
      </div>

      {/* Health Dashboard */}
      <div className="animate-slide-up" style={{ animationDelay: '0.25s' }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
          <h2 className="text-2xl font-bold text-gray-900">
            Saúde do Sistema
          </h2>
        </div>
        <HealthDashboard />
      </div>

      {/* Bottom: Positions */}
      <div className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
          <h2 className="text-2xl font-bold text-gray-900">
            Posições Ativas
          </h2>
        </div>
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard;
