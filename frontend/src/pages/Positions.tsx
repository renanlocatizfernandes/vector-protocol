import React from 'react';
import { PositionsTable } from '../components/PositionsTable';

export const Positions: React.FC = () => {
    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Portfolio Manager</h1>
                <p className="text-muted-foreground">Manage your active positions and open orders.</p>
            </header>

            <PositionsTable />
        </div>
    );
};

export default Positions;
