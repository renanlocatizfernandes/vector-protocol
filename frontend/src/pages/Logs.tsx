import React from 'react';
import LogsViewer from '../components/LogsViewer';

export const Logs: React.FC = () => {
    return (
        <div className="space-y-6 animate-in fade-in duration-500 h-[calc(100vh-100px)]">
            <header className="mb-2">
                <h1 className="text-3xl font-bold tracking-tight text-white">System Diagnostics</h1>
                <p className="text-muted-foreground">Real-time log monitoring for all bot components.</p>
            </header>

            <LogsViewer />
        </div>
    );
};

export default Logs;
