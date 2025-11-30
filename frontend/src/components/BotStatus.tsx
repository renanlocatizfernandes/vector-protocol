import React, { useEffect, useState, useCallback } from 'react';
import { getBotStatus, getDailyStats, startBot, stopBot, updateBotConfig, type BotStatus as IBotStatus, type DailyStats } from '../services/api';

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
        <div className="card flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                    <span className="text-blue">🤖</span> Status do Bot
                </h2>
                <span className={`badge ${isRunning ? 'badge-success' : 'badge-warning'}`}>
                    <span className={`w-2 h-2 rounded-full mr-2 ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></span>
                    {isRunning ? 'RODANDO' : 'PARADO'}
                </span>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-tertiary p-3 rounded">
                    <div className="text-secondary text-xs uppercase">P&L Diário</div>
                    <div className={`text-lg font-bold ${daily && daily.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                        ${daily ? daily.total_pnl.toFixed(2) : '—'}
                    </div>
                </div>
                <div className="bg-tertiary p-3 rounded">
                    <div className="text-secondary text-xs uppercase">Win Rate</div>
                    <div className="text-lg font-bold text-blue">
                        {daily ? daily.win_rate.toFixed(1) : '—'}%
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div className="flex gap-2 mt-2">
                {!isRunning ? (
                    <>
                        <button className="btn btn-primary flex-1" onClick={() => handleStart(false)} disabled={loading}>
                            Start Real
                        </button>
                        <button className="btn btn-secondary flex-1" onClick={() => handleStart(true)} disabled={loading}>
                            Dry Run
                        </button>
                    </>
                ) : (
                    <button className="btn btn-danger flex-1" onClick={handleStop} disabled={loading}>
                        Stop Bot
                    </button>
                )}
            </div>

            {/* Config Toggle */}
            <button
                className="text-xs text-secondary hover:text-primary text-center mt-2 underline"
                onClick={() => setShowConfig(!showConfig)}
            >
                {showConfig ? 'Ocultar Configurações' : 'Mostrar Configurações'}
            </button>

            {/* Config Form */}
            {showConfig && (
                <div className="bg-tertiary p-3 rounded mt-2 flex flex-col gap-3 animate-fade-in">
                    <div className="grid grid-cols-3 gap-2">
                        <div>
                            <label className="label">Scan (min)</label>
                            <input type="number" className="input p-1 text-sm" value={scanInterval} onChange={e => setScanInterval(e.target.value)} />
                        </div>
                        <div>
                            <label className="label">Min Score</label>
                            <input type="number" className="input p-1 text-sm" value={minScore} onChange={e => setMinScore(e.target.value)} />
                        </div>
                        <div>
                            <label className="label">Max Pos</label>
                            <input type="number" className="input p-1 text-sm" value={maxPositions} onChange={e => setMaxPositions(e.target.value)} />
                        </div>
                    </div>
                    <button className="btn btn-secondary text-xs w-full" onClick={handleUpdateConfig} disabled={loading}>
                        Salvar Alterações
                    </button>
                </div>
            )}

            {message && (
                <div className={`p-2 rounded text-xs text-center ${message.type === 'success' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}`}>
                    {message.text}
                </div>
            )}
        </div>
    );
};
