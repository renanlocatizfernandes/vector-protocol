import React, { useEffect, useState, useCallback } from 'react';
import { getBotStatus, getDailyStats, startBot, stopBot, updateBotConfig, type BotStatus as IBotStatus, type DailyStats } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Square, Settings, RefreshCw, Activity, DollarSign, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';

export const BotStatus: React.FC = () => {
    const [bot, setBot] = useState<IBotStatus | null>(null);
    const [daily, setDaily] = useState<DailyStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // Config Form
    const [scanInterval, setScanInterval] = useState<string>('');
    const [minScore, setMinScore] = useState<string>('');
    const [maxPositions, setMaxPositions] = useState<string>('');
    const [showConfig, setShowConfig] = useState(false);

    const loadData = useCallback(async () => {
        try {
            const [botData, dailyData] = await Promise.all([
                getBotStatus().catch(() => null),
                getDailyStats().catch(() => null)
            ]);

            if (botData) {
                setBot(botData);
                setScanInterval(botData.scan_interval ? String(Math.round(botData.scan_interval / 60)) : '');
                setMinScore(botData.min_score !== undefined ? String(botData.min_score) : '');
                setMaxPositions(botData.max_positions !== undefined ? String(botData.max_positions) : '');
            }
            if (dailyData) setDaily(dailyData);
        } catch (error) {
            console.error("Erro ao carregar status:", error);
        }
    }, []);

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 5000);
        return () => clearInterval(interval);
    }, [loadData]);

    const handleStart = async (dryRun: boolean) => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await startBot(dryRun);
            setMessage({ type: 'success', text: res?.message || 'Started Successfully' });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Error Starting' });
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await stopBot();
            setMessage({ type: 'success', text: res?.message || 'Stopped Successfully' });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Error Stopping' });
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateConfig = async () => {
        setLoading(true);
        setMessage(null);
        try {
            const params: any = {};
            if (scanInterval) params.scan_interval_minutes = Number(scanInterval);
            if (minScore) params.min_score = Number(minScore);
            if (maxPositions) params.max_positions = Number(maxPositions);

            const res = await updateBotConfig(params);
            setMessage({ type: 'success', text: res?.message || 'Config Updated' });
            await loadData();
            setShowConfig(false);
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Error Updating Config' });
        } finally {
            setLoading(false);
        }
    };

    const isRunning = !!bot?.running;
    const dbPnl = daily?.db?.total_pnl ?? daily?.total_pnl ?? 0;
    const dbWinRate = daily?.db?.win_rate ?? daily?.win_rate ?? 0;
    const dbTrades = daily?.db?.trades_count ?? daily?.trades_count ?? 0;
    const exRealized = daily?.exchange?.net_realized_pnl ?? 0;
    const exUnrealized = daily?.exchange?.unrealized_pnl ?? 0;
    const exFees = daily?.exchange?.fees ?? 0;
    const exFunding = daily?.exchange?.funding ?? 0;
    const exNet = daily?.exchange?.net_pnl ?? (exRealized + exUnrealized);
    const exTotalWallet = daily?.exchange?.total_wallet ?? daily?.balance ?? 0;
    const exAvailable = daily?.exchange?.available_balance ?? 0;

    return (
        <Card className="h-full relative overflow-hidden glass-card border-white/10 shadow-2xl hover:shadow-primary/5 transition-all duration-300">
            {/* Enhanced Neon Glow Background */}
            <div className="absolute -top-20 -right-20 w-40 h-40 bg-gradient-to-br from-primary/20 to-accent/10 rounded-full blur-3xl pointer-events-none animate-pulse" style={{ animationDuration: '3s' }} />
            <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-accent/10 rounded-full blur-2xl pointer-events-none" />

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 relative">
                {/* Gradient accent line */}
                <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-primary drop-shadow-[0_0_6px_rgba(42,212,198,0.4)]" />
                    <span className="bg-gradient-to-r from-white to-primary/80 bg-clip-text text-transparent font-semibold">System Status</span>
                </CardTitle>
                <div className={cn(
                    "px-3 py-1.5 rounded-full text-xs font-bold border flex items-center gap-2 shadow-lg transition-all duration-300",
                    isRunning
                        ? "bg-success/10 text-success border-success/30 shadow-success/20"
                        : "bg-danger/10 text-danger border-danger/30 shadow-danger/15"
                )}>
                    <div className={cn(
                        "w-2 h-2 rounded-full shadow-lg",
                        isRunning ? "bg-success animate-pulse shadow-success/50" : "bg-danger shadow-danger/50"
                    )} />
                    {isRunning ? 'ONLINE' : 'OFFLINE'}
                </div>
            </CardHeader>

            <CardContent className="space-y-6">
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-primary/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Daily P&L (DB)</span>
                        <span className={cn(
                            "text-2xl font-bold",
                            dbPnl >= 0 ? "text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]"
                        )}>
                            ${dbPnl.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-muted-foreground">Trades: {dbTrades}</span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-accent/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Win Rate (DB)</span>
                        <span className="text-2xl font-bold text-primary drop-shadow-[0_0_8px_rgba(42,212,198,0.3)]">
                            {dbWinRate.toFixed(1)}%
                        </span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-primary/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Realized P&L (Exchange)</span>
                        <span className={cn(
                            "text-2xl font-bold",
                            exRealized >= 0 ? "text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]"
                        )}>
                            ${exRealized.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-muted-foreground">Fees: {exFees.toFixed(2)} | Funding: {exFunding.toFixed(2)}</span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-primary/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Unrealized P&L (Exchange)</span>
                        <span className={cn(
                            "text-2xl font-bold",
                            exUnrealized >= 0 ? "text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]"
                        )}>
                            ${exUnrealized.toFixed(2)}
                        </span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-primary/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Net P&L (R+U)</span>
                        <span className={cn(
                            "text-2xl font-bold",
                            exNet >= 0 ? "text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]"
                        )}>
                            ${exNet.toFixed(2)}
                        </span>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex flex-col gap-1.5 hover:border-primary/20 transition-all duration-300 card-glow-hover">
                        <span className="text-xs text-muted-foreground uppercase tracking-wider">Wallet (Exchange)</span>
                        <span className="text-xl font-bold text-white">
                            ${exTotalWallet.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-muted-foreground">Available: ${exAvailable.toFixed(2)}</span>
                    </div>
                </div>

                <div className="flex gap-3">
                    {!isRunning ? (
                        <>
                            <Button
                                className="flex-1 bg-gradient-to-r from-primary to-accent hover:from-primary-light hover:to-accent-light shadow-lg shadow-primary/15 hover:shadow-primary/25 transition-all duration-300"
                                onClick={() => handleStart(false)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-4 w-4" /> Start Live
                            </Button>
                            <Button
                                variant="outline"
                                className="flex-1 border-primary/30 hover:bg-primary/10 hover:border-primary/50 transition-all duration-300"
                                onClick={() => handleStart(true)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-4 w-4" /> Dry Run
                            </Button>
                        </>
                    ) : (
                        <Button
                            variant="destructive"
                            className="flex-1 w-full shadow-lg shadow-danger/15 hover:shadow-danger/25 transition-all duration-300"
                            onClick={handleStop}
                            disabled={loading}
                        >
                            <Square className="mr-2 h-4 w-4 fill-current" /> Stop Engine
                        </Button>
                    )}
                </div>

                <div className="pt-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-xs text-muted-foreground hover:text-white"
                        onClick={() => setShowConfig(!showConfig)}
                    >
                        <Settings className="mr-2 h-3 w-3" />
                        {showConfig ? 'Hide Configuration' : 'Quick Configuration'}
                    </Button>

                    {showConfig && (
                        <div className="mt-4 space-y-4 p-4 rounded-lg bg-white/5 border border-white/10 animate-in slide-in-from-top-2">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Scan (min)</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-white/5 border-white/10"
                                        value={scanInterval}
                                        onChange={e => setScanInterval(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Min Score</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-white/5 border-white/10"
                                        value={minScore}
                                        onChange={e => setMinScore(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1 col-span-2">
                                    <label className="text-xs font-medium text-muted-foreground">Max Positions</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-white/5 border-white/10"
                                        value={maxPositions}
                                        onChange={e => setMaxPositions(e.target.value)}
                                    />
                                </div>
                            </div>
                            <Button size="sm" variant="secondary" className="w-full" onClick={handleUpdateConfig} disabled={loading}>
                                <RefreshCw className="mr-2 h-3 w-3" /> Save Changes
                            </Button>
                        </div>
                    )}
                </div>

                {message && (
                    <div className={cn(
                        "p-2 rounded text-xs text-center font-medium border",
                        message.type === 'success'
                            ? "bg-green-500/10 text-green-500 border-green-500/20"
                            : "bg-red-500/10 text-red-500 border-red-500/20"
                    )}>
                        {message.text}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
