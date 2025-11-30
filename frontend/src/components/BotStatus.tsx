import React, { useEffect, useState, useCallback } from 'react';
import { getBotStatus, getDailyStats, startBot, stopBot, updateBotConfig, type BotStatus as IBotStatus, type DailyStats } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Square, Settings, RefreshCw, Activity, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';

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
        const interval = setInterval(loadData, 10000);
        return () => clearInterval(interval);
    }, [loadData]);

    const handleStart = async (dryRun: boolean) => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await startBot(dryRun);
            setMessage({ type: 'success', text: res?.message || 'Bot iniciado' });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Erro ao iniciar' });
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await stopBot();
            setMessage({ type: 'success', text: res?.message || 'Bot parado' });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Erro ao parar' });
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
            setMessage({ type: 'success', text: res?.message || 'Config atualizada' });
            await loadData();
            setShowConfig(false);
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Erro ao atualizar config' });
        } finally {
            setLoading(false);
        }
    };

    const isRunning = !!bot?.running;

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Status do Bot</CardTitle>
                <Badge variant={isRunning ? "success" : "destructive"} className="flex gap-1 items-center">
                    <div className={cn("h-2 w-2 rounded-full", isRunning ? "bg-green-500 animate-pulse" : "bg-red-500")} />
                    {isRunning ? 'RODANDO' : 'PARADO'}
                </Badge>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="flex flex-col space-y-1">
                        <span className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                            <DollarSign className="h-3 w-3" /> P&L Diário
                        </span>
                        <span className={cn("text-2xl font-bold", daily && daily.total_pnl >= 0 ? "text-green-500" : "text-red-500")}>
                            ${daily ? daily.total_pnl.toFixed(2) : '—'}
                        </span>
                    </div>
                    <div className="flex flex-col space-y-1">
                        <span className="text-xs text-muted-foreground uppercase flex items-center gap-1">
                            <Activity className="h-3 w-3" /> Win Rate
                        </span>
                        <span className="text-2xl font-bold text-blue-500">
                            {daily ? daily.win_rate.toFixed(1) : '—'}%
                        </span>
                    </div>
                </div>

                <div className="flex gap-2 mb-4">
                    {!isRunning ? (
                        <>
                            <Button className="flex-1" onClick={() => handleStart(false)} disabled={loading}>
                                <Play className="mr-2 h-4 w-4" /> Start Real
                            </Button>
                            <Button variant="secondary" className="flex-1" onClick={() => handleStart(true)} disabled={loading}>
                                <Play className="mr-2 h-4 w-4" /> Dry Run
                            </Button>
                        </>
                    ) : (
                        <Button variant="destructive" className="flex-1" onClick={handleStop} disabled={loading}>
                            <Square className="mr-2 h-4 w-4 fill-current" /> Stop Bot
                        </Button>
                    )}
                </div>

                <div className="relative">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-xs text-muted-foreground"
                        onClick={() => setShowConfig(!showConfig)}
                    >
                        <Settings className="mr-2 h-3 w-3" />
                        {showConfig ? 'Ocultar Configurações' : 'Configurações Rápidas'}
                    </Button>

                    {showConfig && (
                        <div className="mt-4 space-y-4 border-t pt-4 animate-in slide-in-from-top-2">
                            <div className="grid grid-cols-3 gap-2">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium">Scan (min)</label>
                                    <input
                                        type="number"
                                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                        value={scanInterval}
                                        onChange={e => setScanInterval(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium">Min Score</label>
                                    <input
                                        type="number"
                                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                        value={minScore}
                                        onChange={e => setMinScore(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium">Max Pos</label>
                                    <input
                                        type="number"
                                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                        value={maxPositions}
                                        onChange={e => setMaxPositions(e.target.value)}
                                    />
                                </div>
                            </div>
                            <Button size="sm" variant="secondary" className="w-full" onClick={handleUpdateConfig} disabled={loading}>
                                <RefreshCw className="mr-2 h-3 w-3" /> Salvar Alterações
                            </Button>
                        </div>
                    )}
                </div>

                {message && (
                    <div className={cn(
                        "mt-4 p-2 rounded text-xs text-center font-medium",
                        message.type === 'success' ? "bg-green-500/15 text-green-500" : "bg-red-500/15 text-red-500"
                    )}>
                        {message.text}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
