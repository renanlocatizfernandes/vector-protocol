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
        <Card className="h-full elevated-card-hover">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-gray-100">
                <CardTitle className="text-base font-semibold flex items-center gap-2 text-gray-900">
                    <Activity className="w-5 h-5 text-blue-600" />
                    Status do Sistema
                </CardTitle>
                <Badge
                    className={cn(
                        "px-3 py-1.5 font-bold",
                        isRunning
                            ? "bg-green-100 text-green-700 border-green-200"
                            : "bg-red-100 text-red-700 border-red-200"
                    )}
                >
                    <span className="flex items-center gap-2">
                        <span className={cn(
                            "w-1.5 h-1.5 rounded-full",
                            isRunning ? "bg-green-500" : "bg-red-500"
                        )} />
                        {isRunning ? 'ATIVO' : 'OFFLINE'}
                    </span>
                </Badge>
            </CardHeader>

            <CardContent className="space-y-6">
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className={cn(
                        "stat-card",
                        dbPnl >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">P&L Diário (DB)</span>
                        <span className={cn(
                            "text-2xl font-bold mt-1 block",
                            dbPnl >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                            ${dbPnl.toFixed(2)}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">Trades: {dbTrades}</span>
                    </div>
                    <div className="stat-card">
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Win Rate (DB)</span>
                        <span className="text-2xl font-bold text-blue-600 mt-1 block">
                            {dbWinRate.toFixed(1)}%
                        </span>
                    </div>
                    <div className={cn(
                        "stat-card",
                        exRealized >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Realizado (Exchange)</span>
                        <span className={cn(
                            "text-2xl font-bold mt-1 block",
                            exRealized >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                            ${exRealized.toFixed(2)}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">Fees: {exFees.toFixed(2)} | Funding: {exFunding.toFixed(2)}</span>
                    </div>
                    <div className={cn(
                        "stat-card",
                        exUnrealized >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Não Realizado (Exchange)</span>
                        <span className={cn(
                            "text-2xl font-bold mt-1 block",
                            exUnrealized >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                            ${exUnrealized.toFixed(2)}
                        </span>
                    </div>
                    <div className={cn(
                        "stat-card",
                        exNet >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">P&L Líquido (R+U)</span>
                        <span className={cn(
                            "text-2xl font-bold mt-1 block",
                            exNet >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                            ${exNet.toFixed(2)}
                        </span>
                    </div>
                    <div className="stat-card">
                        <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Carteira (Exchange)</span>
                        <span className="text-xl font-bold text-gray-900 mt-1 block">
                            ${exTotalWallet.toFixed(2)}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">Disponível: ${exAvailable.toFixed(2)}</span>
                    </div>
                </div>

                <div className="flex gap-3">
                    {!isRunning ? (
                        <>
                            <Button
                                className="flex-1 bg-gradient-to-r from-blue-600 to-green-600 hover:from-blue-700 hover:to-green-700 text-white font-semibold shadow-md hover:shadow-lg"
                                onClick={() => handleStart(false)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-4 w-4" /> Iniciar Bot
                            </Button>
                            <Button
                                variant="outline"
                                className="flex-1"
                                onClick={() => handleStart(true)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-4 w-4" /> Modo Teste
                            </Button>
                        </>
                    ) : (
                        <Button
                            variant="destructive"
                            className="flex-1 w-full"
                            onClick={handleStop}
                            disabled={loading}
                        >
                            <Square className="mr-2 h-4 w-4 fill-current" /> Parar Bot
                        </Button>
                    )}
                </div>

                <div className="pt-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-xs"
                        onClick={() => setShowConfig(!showConfig)}
                    >
                        <Settings className="mr-2 h-3 w-3" />
                        {showConfig ? 'Ocultar Configuração' : 'Configuração Rápida'}
                    </Button>

                    {showConfig && (
                        <div className="mt-4 space-y-4 p-4 rounded-lg bg-gray-50 border border-gray-200 animate-in slide-in-from-top-2">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-gray-700">Intervalo (min)</label>
                                    <Input
                                        type="number"
                                        className="h-8"
                                        value={scanInterval}
                                        onChange={e => setScanInterval(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-medium text-gray-700">Score Mínimo</label>
                                    <Input
                                        type="number"
                                        className="h-8"
                                        value={minScore}
                                        onChange={e => setMinScore(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-1 col-span-2">
                                    <label className="text-xs font-medium text-gray-700">Posições Máx</label>
                                    <Input
                                        type="number"
                                        className="h-8"
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
                        "p-3 rounded-lg text-sm text-center font-medium border",
                        message.type === 'success'
                            ? "bg-green-100 text-green-700 border-green-200"
                            : "bg-red-100 text-red-700 border-red-200"
                    )}>
                        {message.text}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
