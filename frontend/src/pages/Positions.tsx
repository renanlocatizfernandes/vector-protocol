import React from 'react';
import { PositionsTable } from '../components/PositionsTable';

export const Positions: React.FC = () => {
    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header className="space-y-2">
                <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Portfolio</span>
                <h1 className="text-3xl font-semibold text-white">Positions Monitor</h1>
                <p className="text-muted-foreground">Manage exposure, synchronize holdings, and review risk in real time.</p>
            </header>

            <PositionsTable />
        </div>
    );
};

export default Positions;
