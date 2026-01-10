import React from 'react';
import { PositionsTable } from '../components/PositionsTable';

export const Positions: React.FC = () => {
    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <header className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                    <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
                    <h1 className="text-3xl font-bold text-gray-900">Monitor de Posições</h1>
                </div>
                <p className="text-gray-600 ml-4">Gerencie exposição, sincronize holdings e revise riscos em tempo real.</p>
            </header>

            <PositionsTable />
        </div>
    );
};

export default Positions;
