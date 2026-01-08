import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getLatencyStats, LatencyStats } from '@/services/api';

export const LatencyPanel: React.FC = () => {
    const [latency, setLatency] = useState<LatencyStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await getLatencyStats();
                setLatency(data);
            } catch (err) {
                console.error('Failed to fetch latency data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const slaColor = latency?.sla_status === 'ok' ? 'text-success' : latency?.sla_status === 'warning' ? 'text-yellow-400' : 'text-danger';

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Bot Latency
                </CardTitle>
                <CardDescription>
                    Cycle performance • SLA: {latency?.sla_threshold || 5}s
                </CardDescription>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="text-center py-8 text-muted-foreground">Loading...</div>
                ) : latency?.last_cycle && Object.keys(latency.last_cycle).length > 0 ? (
                    <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-white/5 p-3 rounded-lg">
                                <div className="text-xs text-muted-foreground">Scan</div>
                                <div className="text-lg font-semibold text-primary">
                                    {latency.last_cycle.scan?.toFixed(2) || '0.00'}s
                                </div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg">
                                <div className="text-xs text-muted-foreground">Signal</div>
                                <div className="text-lg font-semibold text-primary">
                                    {latency.last_cycle.signal?.toFixed(2) || '0.00'}s
                                </div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg">
                                <div className="text-xs text-muted-foreground">Execution</div>
                                <div className="text-lg font-semibold text-primary">
                                    {latency.last_cycle.execution?.toFixed(2) || '0.00'}s
                                </div>
                            </div>
                            <div className="bg-white/5 p-3 rounded-lg">
                                <div className="text-xs text-muted-foreground">Total</div>
                                <div className={cn("text-lg font-semibold", slaColor)}>
                                    {latency.last_cycle.total?.toFixed(2) || '0.00'}s
                                </div>
                            </div>
                        </div>
                        <div className={cn(
                            "text-sm text-center py-2 rounded",
                            latency.sla_status === 'ok' ? 'bg-success/10 text-success' :
                            latency.sla_status === 'warning' ? 'bg-yellow-400/10 text-yellow-400' :
                            'bg-danger/10 text-danger'
                        )}>
                            SLA Status: {latency.sla_status.toUpperCase()}
                        </div>
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground">
                        <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>No cycle data yet</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
