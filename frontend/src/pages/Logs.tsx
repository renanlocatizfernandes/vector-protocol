import React from 'react';
import LogsViewer from '../components/LogsViewer';

export const Logs: React.FC = () => {
    return (
        <div className="space-y-8 animate-in fade-in duration-500 h-[calc(100vh-100px)]">
            <header className="space-y-2">
                <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Diagnostics</span>
                <h1 className="text-3xl font-semibold text-white">System Logs</h1>
                <p className="text-muted-foreground">Real-time log monitoring for all bot components.</p>
            </header>

            <LogsViewer />
        </div>
    );
};

export default Logs;
