import React from 'react';
import { ManualTrade } from '../components/ManualTrade';
import { PerformanceChart } from '../components/PerformanceChart';
import { BotStatus } from '../components/BotStatus';
import { PositionsTable } from '../components/PositionsTable'; // Keeping existing for now, will refactor later

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-700">

      {/* Top Section: Status & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Status & Controls */}
        <div className="flex flex-col gap-6">
          <BotStatus />
        </div>

        {/* Right: Chart */}
        <div className="lg:col-span-2 min-h-[350px]">
          <PerformanceChart />
        </div>
      </div>

      {/* Manual Trade Section - Possibly move to a dialog or keep here? Keeping here for now */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ManualTrade />
        </div>
      </div>

      {/* Bottom: Positions */}
      <div>
        <h2 className="text-xl font-bold mb-4 text-white pl-1 border-l-4 border-primary">Active Positions</h2>
        <PositionsTable />
      </div>
    </div>
  );
};

export default Dashboard;
