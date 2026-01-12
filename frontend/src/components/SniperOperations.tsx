import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Target, TrendingUp, TrendingDown, Activity, CheckCircle, XCircle } from 'lucide-react';
import { getSniperTrades, type SniperTrade, type SniperStats } from '../services/api';
import { cn } from '@/lib/utils';

export const SniperOperations: React.FC = () => {
    const [trades, setTrades] = useState<SniperTrade[]>([]);
    const [stats, setStats] = useState<SniperStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSniperData();
        const interval = setInterval(fetchSniperData, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchSniperData = async () => {
        try {
            const response = await getSniperTrades(20);
            setTrades(response.trades);
            setStats(response.stats);
        } catch (error) {
            console.error('Erro ao carregar operações Sniper:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR', { 
            day: '2-digit', 
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <Card className="h-full">
                <CardContent className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full flex flex-col overflow-hidden">
            <CardHeader className="p-4 pb-3 border-b border-slate-200/50">
                <CardTitle className="text-base font-semibold flex items-center gap-2 text-slate-900">
                    <Target className="w-5 h-5 text-red-600" /> Operações Sniper
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-4">
                {stats && (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="bg-gradient-to-r from-red-50 to-rose-50 border border-red-200/50 rounded-xl p-3">
                            <p className="text-xs font-bold text-slate-600 uppercase">Total de Operações</p>
                            <p className="text-xl font-bold text-red-600">{stats.total_sniper_trades}</p>
                        </div>
                        <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200/50 rounded-xl p-3">
                            <p className="text-xs font-bold text-slate-600 uppercase">Lucro Total</p>
                            <p className={cn("text-xl font-bold", stats.sniper_pnl_total >= 0 ? "text-green-600" : "text-red-600")}>
                                ${stats.sniper_pnl_total.toFixed(2)}
                            </p>
                        </div>
                        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 rounded-xl p-3">
                            <p className="text-xs font-bold text-slate-600 uppercase">Taxa de Acerto</p>
                            <p className="text-xl font-bold text-blue-600">{stats.sniper_win_rate.toFixed(1)}%</p>
                        </div>
                        <div className="bg-gradient-to-r from-purple-50 to-violet-50 border border-purple-200/50 rounded-xl p-3">
                            <p className="text-xs font-bold text-slate-600 uppercase">Posições Ativas</p>
                            <p className="text-xl font-bold text-purple-600">{stats.active_sniper_positions}</p>
                        </div>
                    </div>
                )}
                
                <div className="space-y-2 max-h-[280px] overflow-y-auto">
                    <h4 className="text-sm font-bold text-slate-700 mb-2">Histórico Recente</h4>
                    {trades.length === 0 ? (
                        <div className="text-center py-8 text-slate-500 text-sm">
                            Nenhuma operação Sniper registrada
                        </div>
                    ) : (
                        trades.map((trade) => (
                            <div 
                                key={trade.id}
                                className="flex items-center justify-between p-3 rounded-lg border border-slate-200/50 bg-white hover:shadow-md transition-all"
                            >
                                <div className="flex items-center gap-3 flex-1">
                                    <div className={cn(
                                        "w-8 h-8 rounded-lg flex items-center justify-center",
                                        trade.direction === 'LONG' ? "bg-green-100" : "bg-red-100"
                                    )}>
                                        {trade.direction === 'LONG' ? (
                                            <TrendingUp className="w-4 h-4 text-green-600" />
                                        ) : (
                                            <TrendingDown className="w-4 h-4 text-red-600" />
                                        )}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-bold text-slate-900">{trade.symbol}</span>
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded-full font-medium",
                                                trade.status === 'closed' 
                                                    ? (trade.pnl && trade.pnl >= 0 
                                                        ? "bg-green-100 text-green-700" 
                                                        : "bg-red-100 text-red-700")
                                                    : "bg-blue-100 text-blue-700"
                                            )}>
                                                {trade.status === 'closed' 
                                                    ? (trade.pnl && trade.pnl >= 0 ? 'Fechada (Lucro)' : 'Fechada (Prejuízo)')
                                                    : 'Aberta'
                                                }
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-xs text-slate-600">
                                            <span>Entrada: ${trade.entry_price.toFixed(4)}</span>
                                            {trade.exit_price && <span>Saída: ${trade.exit_price.toFixed(4)}</span>}
                                            <span>Qtd: {trade.quantity}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    {trade.pnl !== undefined && (
                                        <div className={cn(
                                            "text-sm font-bold",
                                            trade.pnl >= 0 ? "text-green-600" : "text-red-600"
                                        )}>
                                            ${trade.pnl.toFixed(2)}
                                        </div>
                                    )}
                                    <div className="text-xs text-slate-500">
                                        {formatDate(trade.opened_at)}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
};
