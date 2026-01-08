import React from 'react';
import { ErrorsPanel } from './ErrorsPanel';
import { LatencyPanel } from './LatencyPanel';
import { SyncStatusPanel } from './SyncStatusPanel';
import { MarketConditionsPanel } from './MarketConditionsPanel';

export const HealthDashboard: React.FC = () => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ErrorsPanel />
            <LatencyPanel />
            <SyncStatusPanel />
            <MarketConditionsPanel />
        </div>
    );
};
