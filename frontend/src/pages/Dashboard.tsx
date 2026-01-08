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
        <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Command Center</span>
        <h1 className="text-3xl font-semibold text-white">Trading Overview</h1>
        <p className="text-muted-foreground">Status, performance, and active exposure at a glance.</p>
      </header>

      <div className="rounded-xl border border-warning/30 bg-warning/10 text-warning px-4 py-3 text-sm">
        Whitelist enforced: the bot can monitor any open position, but new entries only execute for symbols in the whitelist.
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
        <div className="flex items-center gap-3 mb-4 pl-1">
          <div className="w-1 h-6 bg-primary rounded-full shadow-[0_0_10px_rgba(42,212,198,0.35)]" />
          <h2 className="text-xl font-semibold text-white">
            System Health
          </h2>
        </div>
        <HealthDashboard />
      </div>

      {/* Bottom: Positions */}
      <div className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
        <div className="flex items-center gap-3 mb-4 pl-1">
          <div className="w-1 h-6 bg-primary rounded-full shadow-[0_0_10px_rgba(42,212,198,0.35)]" />
          <h2 className="text-xl font-semibold text-white">
            Active Positions
          </h2>
        </div>
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard;
