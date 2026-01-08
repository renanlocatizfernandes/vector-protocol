import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LatencyStats {
    last_cycle: {
        scan: number;
        signal: number;
        execution: number;
        total: number;
    };
    hourly_average: {
        scan: number;
        signal: number;
        execution: number;
        total: number;
    };
    sla_status: 'ok' | 'warning';
}

export const LatencyPanel: React.FC = () => {
    const [latency, setLatency] = useState<LatencyStats | null>(null);

    useEffect(() => {
        // Mock data - will be replaced with real API calls in Phase 4
        const mockLatency: LatencyStats = {
            last_cycle: {
                scan: 1.2,
                signal: 0.8,
                execution: 0.5,
                total: 2.5
            },
            hourly_average: {
                scan: 1.1,
                signal: 0.9,
                execution: 0.6,
                total: 2.6
            },
            sla_status: 'ok'
        };

        setLatency(mockLatency);
    }, []);

    if (!latency) return null;

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Performance & Latency
                </CardTitle>
                <CardDescription>
                    SLA Status:{' '}
                    <span className={cn(
                        "font-semibold",
                        latency.sla_status === 'ok' ? 'text-success' : 'text-warning'
                    )}>
                        {latency.sla_status.toUpperCase()}
                    </span>
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <h4 className="text-xs text-muted-foreground uppercase mb-2">Last Cycle</h4>
                            <div className="space-y-1">
                                <div className="flex justify-between text-sm">
                                    <span>Scan:</span>
                                    <span className="font-mono text-white">{latency.last_cycle.scan.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span>Signal:</span>
                                    <span className="font-mono text-white">{latency.last_cycle.signal.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span>Execution:</span>
                                    <span className="font-mono text-white">{latency.last_cycle.execution.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm font-semibold border-t border-white/10 pt-1 mt-1">
                                    <span>Total:</span>
                                    <span className={cn(
                                        "font-mono",
                                        latency.last_cycle.total < 5 ? 'text-success' : 'text-warning'
                                    )}>
                                        {latency.last_cycle.total.toFixed(2)}s
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div>
                            <h4 className="text-xs text-muted-foreground uppercase mb-2">Hourly Avg</h4>
                            <div className="space-y-1">
                                <div className="flex justify-between text-sm">
                                    <span>Scan:</span>
                                    <span className="font-mono text-white">{latency.hourly_average.scan.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span>Signal:</span>
                                    <span className="font-mono text-white">{latency.hourly_average.signal.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span>Execution:</span>
                                    <span className="font-mono text-white">{latency.hourly_average.execution.toFixed(2)}s</span>
                                </div>
                                <div className="flex justify-between text-sm font-semibold border-t border-white/10 pt-1 mt-1">
                                    <span>Total:</span>
                                    <span className={cn(
                                        "font-mono",
                                        latency.hourly_average.total < 5 ? 'text-success' : 'text-warning'
                                    )}>
                                        {latency.hourly_average.total.toFixed(2)}s
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
