import React from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable';

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Dashboard</h1>
          <p className="text-muted-foreground">Painel de controle e monitoramento em tempo real.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded border border-primary/20 font-mono">PRO v4.0</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
      <div>
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard;
