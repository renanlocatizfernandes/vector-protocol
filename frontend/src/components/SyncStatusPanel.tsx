import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface SyncStatus {
    last_sync: string | null;
    last_sync_ago_seconds: number | null;
    auto_sync_enabled: boolean;
    divergences: Array<{
        symbol: string;
        exchange_qty: number;
        db_qty: number;
        delta: number;
    }>;
    divergence_count: number;
    status: 'ok' | 'warning';
}

export const SyncStatusPanel: React.FC = () => {
    const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

    useEffect(() => {
        // Mock data - will be replaced with real API calls in Phase 4
        const mockStatus: SyncStatus = {
            last_sync: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
            last_sync_ago_seconds: 120,
            auto_sync_enabled: true,
            divergences: [],
            divergence_count: 0,
            status: 'ok'
        };

        setSyncStatus(mockStatus);
    }, []);

    if (!syncStatus) return null;

    const formatAgo = (seconds: number | null): string => {
        if (!seconds) return 'Never';
        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} min ago`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    };

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <RefreshCw className="h-5 w-5 text-primary" />
                    Position Sync Status
                </CardTitle>
                <CardDescription>
                    Auto-sync:{' '}
                    <span className={cn(
                        "font-semibold",
                        syncStatus.auto_sync_enabled ? 'text-success' : 'text-muted-foreground'
                    )}>
                        {syncStatus.auto_sync_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-xs text-muted-foreground uppercase mb-1">Last Sync</p>
                            <p className="font-mono text-white">{formatAgo(syncStatus.last_sync_ago_seconds)}</p>
                        </div>
                        <div>
                            <p className="text-xs text-muted-foreground uppercase mb-1">Status</p>
                            <Badge variant={syncStatus.status === 'ok' ? 'default' : 'destructive'} className={cn(
                                syncStatus.status === 'ok'
                                    ? 'bg-success/15 text-success border-success/20'
                                    : 'bg-warning/15 text-warning border-warning/20'
                            )}>
                                {syncStatus.status.toUpperCase()}
                            </Badge>
                        </div>
                    </div>

                    <div>
                        <p className="text-xs text-muted-foreground uppercase mb-2">Divergences</p>
                        {syncStatus.divergences.length > 0 ? (
                            <div className="space-y-2">
                                {syncStatus.divergences.map((div, idx) => (
                                    <div key={idx} className="bg-white/5 p-2 rounded border border-warning/30">
                                        <p className="text-sm font-mono text-white">{div.symbol}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Exchange: {div.exchange_qty} | DB: {div.db_qty} | Delta: {div.delta.toFixed(4)}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-4 bg-success/5 rounded border border-success/20">
                                <p className="text-sm text-success">All positions in sync</p>
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
