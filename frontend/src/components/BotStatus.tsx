import React, { useEffect, useState, useCallback } from 'react';
import { getBotStatus, getDailyStats, startBot, stopBot, updateBotConfig, type BotStatus as IBotStatus, type DailyStats } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Play, Square, Settings, RefreshCw, Activity, DollarSign, Cpu, Zap, TrendingUp, TrendingDown, Wallet, Coins } from 'lucide-react';
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
    const exDaily = daily?.exchange?.daily_net_pnl ?? 0;
    const exRealized = daily?.exchange?.net_realized_pnl ?? 0;
    const exUnrealized = daily?.exchange?.unrealized_pnl ?? 0;
    const exFees = daily?.exchange?.fees ?? 0;
    const exFunding = daily?.exchange?.funding ?? 0;
    const exNet = daily?.exchange?.net_pnl ?? (exRealized + exUnrealized);
    const exTotalWallet = daily?.exchange?.total_wallet ?? 0;
    const exAvailable = daily?.exchange?.available_balance ?? 0;

    return (
        <Card className="h-full glass-card-hover overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 border-b border-slate-200/50 bg-gradient-to-r from-white/50 to-blue-50/50">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className={cn(
                            "w-12 h-12 rounded-xl flex items-center justify-center shadow-lg transition-all duration-300",
                            isRunning 
                                ? "bg-gradient-to-br from-green-500 to-emerald-600 shadow-green-500/30 pulse-glow" 
                                : "bg-gradient-to-br from-red-500 to-rose-600 shadow-red-500/30"
                        )}>
                            <Activity className="w-6 h-6 text-white" />
                        </div>
                        <div className={cn(
                            "absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white transition-all duration-300",
                            isRunning ? "bg-green-500 pulse-dot" : "bg-red-500"
                        )} />
                    </div>
                    <div>
                        <CardTitle className="text-lg font-bold text-slate-900">Status do Sistema</CardTitle>
                        <p className="text-xs text-slate-500 font-medium mt-0.5">Monitoramento em Tempo Real</p>
                    </div>
                </div>
                <Badge
                    className={cn(
                        "px-4 py-2 font-bold text-sm border shadow-md transition-all duration-300",
                        isRunning
                            ? "bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 border-green-300 shadow-green-500/20"
                            : "bg-gradient-to-r from-red-100 to-rose-100 text-red-700 border-red-300 shadow-red-500/20"
                    )}
                >
                    <span className="flex items-center gap-2">
                        <span className={cn(
                            "w-2 h-2 rounded-full transition-all duration-300",
                            isRunning ? "bg-green-500 pulse-glow" : "bg-red-500"
                        )} />
                        <Zap className={cn("w-4 h-4", isRunning ? "text-green-600" : "text-red-600")} />
                        {isRunning ? 'ATIVO' : 'OFFLINE'}
                    </span>
                </Badge>
            </CardHeader>

            <CardContent className="space-y-6 p-6">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* P&L Diario */}
                    <div className={cn(
                        "stat-card relative overflow-hidden group",
                        exDaily >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <DollarSign className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">P&L Diario (HOJE)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                {exDaily >= 0 ? (
                                    <TrendingUp className="w-5 h-5 text-green-600" />
                                ) : (
                                    <TrendingDown className="w-5 h-5 text-red-600" />
                                )}
                                <span className={cn(
                                    "text-2xl font-bold",
                                    exDaily >= 0 ? "text-green-700" : "text-red-700"
                                )}>
                                    ${exDaily.toFixed(2)}
                                </span>
                            </div>
                            <span className="text-xs text-slate-600 font-semibold mt-1 block flex items-center gap-1.5">
                                <Coins className="w-3 h-3" />
                                Fonte: Exchange
                            </span>
                        </div>
                    </div>

                    {/* Win Rate */}
                    <div className="stat-card stat-card-primary relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <Activity className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Fees + Funding (24h)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                                    <span className="text-white font-bold text-lg">{(exFees + exFunding).toFixed(2)}</span>
                                </div>
                                <span className="text-lg font-black text-gradient-blue ml-1">
                                    {exFees.toFixed(2)} | {exFunding.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Realizado */}
                    <div className={cn(
                        "stat-card relative overflow-hidden group",
                        exRealized >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <Wallet className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Realizado</span>
                            </div>
                            <div className={cn(
                                "text-2xl font-bold",
                                exRealized >= 0 ? "text-green-700" : "text-red-700"
                            )}>
                                ${exRealized.toFixed(2)}
                            </div>
                            <span className="text-xs text-slate-600 font-semibold mt-1 block">
                                Fees: {exFees.toFixed(2)} | Funding: {exFunding.toFixed(2)}
                            </span>
                        </div>
                    </div>

                    {/* Nao Realizado */}
                    <div className={cn(
                        "stat-card relative overflow-hidden group",
                        exUnrealized >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <TrendingUp className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Nao Realizado</span>
                            </div>
                            <div className={cn(
                                "text-2xl font-bold",
                                exUnrealized >= 0 ? "text-green-700" : "text-red-700"
                            )}>
                                ${exUnrealized.toFixed(2)}
                            </div>
                        </div>
                    </div>

                    {/* P&L Liquido */}
                    <div className={cn(
                        "stat-card stat-card-primary relative overflow-hidden group",
                        exNet >= 0 ? "stat-card-success" : "stat-card-danger"
                    )}>
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <DollarSign className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">P&L Liquido</span>
                            </div>
                            <div className={cn(
                                "text-2xl font-bold",
                                exNet >= 0 ? "text-green-700" : "text-red-700"
                            )}>
                                ${exNet.toFixed(2)}
                            </div>
                            <span className="text-xs text-slate-600 font-semibold mt-1 block">
                                (R+U)
                            </span>
                        </div>
                    </div>

                    {/* Carteira */}
                    <div className="stat-card stat-card-purple relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-transparent to-white/50 rounded-bl-full opacity-50" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-2">
                                <Wallet className="w-4 h-4 text-slate-700" />
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Carteira</span>
                            </div>
                            <div className="text-2xl font-black text-gradient-purple">
                                ${exTotalWallet.toFixed(2)}
                            </div>
                            <span className="text-xs text-slate-600 font-semibold mt-1 block">
                                Disponivel: ${exAvailable.toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Control Buttons */}
                <div className="flex gap-3">
                    {!isRunning ? (
                        <>
                            <Button
                                className="flex-1 btn-primary h-12 text-base"
                                onClick={() => handleStart(false)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-5 w-5" /> Iniciar Bot
                            </Button>
                            <Button
                                variant="outline"
                                className="flex-1 h-12 text-base border-2 border-slate-200 hover:border-purple-300 hover:bg-purple-50/50 transition-all duration-300"
                                onClick={() => handleStart(true)}
                                disabled={loading}
                            >
                                <Play className="mr-2 h-5 w-5" /> Modo Teste
                            </Button>
                        </>
                    ) : (
                        <Button
                            variant="destructive"
                            className="flex-1 w-full h-12 text-base btn-danger"
                            onClick={handleStop}
                            disabled={loading}
                        >
                            <Square className="mr-2 h-5 w-5 fill-current" /> Parar Bot
                        </Button>
                    )}
                </div>

                {/* Configuration Toggle */}
                <div className="pt-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-sm font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 transition-all duration-300"
                        onClick={() => setShowConfig(!showConfig)}
                    >
                        <Settings className="mr-2 h-4 w-4" />
                        {showConfig ? 'Ocultar Configuracao' : 'Configuracao Rapida'}
                    </Button>

                    {/* Configuration Panel */}
                    {showConfig && (
                        <div className="mt-4 space-y-4 p-5 rounded-2xl bg-gradient-to-br from-slate-50 to-blue-50/50 border border-slate-200/50 shadow-lg animate-in slide-in-from-top-2">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Intervalo (min)</label>
                                    <Input
                                        type="number"
                                        className="input-modern"
                                        value={scanInterval}
                                        onChange={e => setScanInterval(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Score Minimo</label>
                                    <Input
                                        type="number"
                                        className="input-modern"
                                        value={minScore}
                                        onChange={e => setMinScore(e.target.value)}
                                    />
                                </div>
                                <div className="space-y-2 col-span-2">
                                    <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Posicoes Max</label>
                                    <Input
                                        type="number"
                                        className="input-modern"
                                        value={maxPositions}
                                        onChange={e => setMaxPositions(e.target.value)}
                                    />
                                </div>
                            </div>
                            <Button 
                                size="sm" 
                                className="w-full btn-purple h-11 text-base"
                                onClick={handleUpdateConfig} 
                                disabled={loading}
                            >
                                <RefreshCw className="mr-2 h-4 w-4" /> Salvar Alteracoes
                            </Button>
                        </div>
                    )}
                </div>

                {/* Message Alert */}
                {message && (
                    <div className={cn(
                        "p-4 rounded-xl text-sm text-center font-bold border-2 animate-bounce-in shadow-lg",
                        message.type === 'success'
                            ? "bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 border-green-300 shadow-green-500/20"
                            : "bg-gradient-to-r from-red-100 to-rose-100 text-red-700 border-red-300 shadow-red-500/20"
                    )}>
                        {message.text}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
