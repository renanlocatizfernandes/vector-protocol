import React from 'react';
import LogsViewer from '../components/LogsViewer';

export const Logs: React.FC = () => {
    return (
        <div className="space-y-8 animate-in fade-in duration-500 h-[calc(100vh-100px)]">
            <header className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                    <div className="w-1 h-8 bg-gradient-to-b from-blue-600 to-green-600 rounded-full" />
                    <h1 className="text-3xl font-bold text-gray-900">Logs do Sistema</h1>
                </div>
                <p className="text-gray-600 ml-4">Monitoramento de logs em tempo real para todos os componentes do bot.</p>
            </header>

            <LogsViewer />
        </div>
    );
};

export default Logs;
