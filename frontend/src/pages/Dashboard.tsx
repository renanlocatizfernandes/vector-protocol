import React from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable';

export const Dashboard: React.FC = () => {
  return (
    <div className="container py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-blue-400 flex items-center gap-3">
            Crypto Bot
            <span className="text-xs bg-blue-900/30 text-blue-300 px-2 py-1 rounded border border-blue-900/50">PRO v4.0</span>
          </h1>
          <p className="text-secondary mt-1">Painel de Controle & Performance</p>
        </div>
        <div className="flex gap-4">
          {/* Future: Notifications or User Profile */}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Coluna Esquerda: Status e Manual */}
        <div className="flex flex-col gap-6">
          <BotStatus />
          <ManualTrade />
        </div>

        {/* Coluna Direita (Larga): Gráfico */}
        <div className="lg:col-span-2 min-h-[400px]">
          <PerformanceChart />
        </div>
      </div>

      {/* Posições (Full Width) */}
      <div className="mb-8">
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard;
