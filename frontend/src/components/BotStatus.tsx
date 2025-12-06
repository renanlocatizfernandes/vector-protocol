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

    return (
        <Card className="h-full relative overflow-hidden">
            {/* Neon Glow Background */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-primary" /> System Status
                </CardTitle>
                <div className={cn(
                    "px-2 py-1 rounded-md text-xs font-bold border flex items-center gap-2",
                    isRunning
                        ? "bg-green-500/10 text-green-500 border-green-500/20"
                        : "bg-red-500/10 text-red-500 border-red-500/20"
                )}>
                    <div className={cn("w-2 h-2 rounded-full", isRunning ? "bg-green-500 animate-pulse" : "bg-red-500")} />
                    {isRunning ? 'ONLINE' : 'OFFLINE'}
                </div>
            </CardHeader>

            <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-dark-800/50 border border-dark-700/50 flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Daily P&L</span>
                        <span className={cn("text-xl font-bold", daily && daily.total_pnl >= 0 ? "text-success" : "text-danger")}>
                            ${daily ? daily.total_pnl.toFixed(2) : '0.00'}
                        </span>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-800/50 border border-dark-700/50 flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Win Rate</span>
                        <span className="text-xl font-bold text-primary">
                            {daily ? daily.win_rate.toFixed(1) : '0.0'}%
                        </span>
                    </div>
                </div>

                <div className="flex gap-3">
                    {!isRunning ? (
                        <>
                            <Button className="flex-1" onClick={() => handleStart(false)} disabled={loading}>
                                <Play className="mr-2 h-4 w-4" /> Start Live
                            </Button>
                            <Button variant="outline" className="flex-1" onClick={() => handleStart(true)} disabled={loading}>
                                <Play className="mr-2 h-4 w-4" /> Dry Run
                            </Button>
                        </>
                    ) : (
                        <Button variant="destructive" className="flex-1 w-full" onClick={handleStop} disabled={loading}>
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
                        <div className="mt-4 space-y-4 p-4 rounded-lg bg-dark-950/50 border border-dark-700/50 animate-in slide-in-from-top-2">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Scan (min)</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-dark-900 border-dark-700"
                                        value={scanInterval}
                                        onChange={e => setScanInterval(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-muted-foreground">Min Score</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-dark-900 border-dark-700"
                                        value={minScore}
                                        onChange={e => setMinScore(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1 col-span-2">
                                    <label className="text-xs font-medium text-muted-foreground">Max Positions</label>
                                    <Input
                                        type="number"
                                        className="h-8 bg-dark-900 border-dark-700"
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
