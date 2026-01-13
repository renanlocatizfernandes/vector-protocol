import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Target, TrendingUp, TrendingDown } from 'lucide-react';
import { getDailyStats, getPositionsDashboard, type DashboardData, type DailyStats } from '../services/api';
import { cn } from '@/lib/utils';

type ExchangePosition = NonNullable<DashboardData['exchange_positions']>[number];

export const SniperOperations: React.FC = () => {
    const [positions, setPositions] = useState<ExchangePosition[]>([]);
    const [daily, setDaily] = useState<DailyStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchExchangeData();
        const interval = setInterval(fetchExchangeData, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchExchangeData = async () => {
        try {
            const [dashboard, dailyStats] = await Promise.all([
                getPositionsDashboard().catch(() => null),
                getDailyStats().catch(() => null)
            ]);
            setPositions(dashboard?.exchange_positions ?? []);
            if (dailyStats) setDaily(dailyStats);
        } catch (error) {
            console.error('Erro ao carregar operacoes da exchange:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString?: string | null) => {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const exRealized = daily?.exchange?.net_realized_pnl ?? null;
    const exFees = daily?.exchange?.fees ?? null;
    const exFunding = daily?.exchange?.funding ?? null;
    const feesFundingValue = exFees === null || exFunding === null ? null : exFees + exFunding;
    const formatMoney = (value: number | null) =>
        value === null ? '--' : `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
    const unrealizedTotal = positions.reduce((sum, pos) => sum + (pos.pnl ?? 0), 0);

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
                    <Target className="w-5 h-5 text-red-600" /> Operacoes Exchange
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-4">
                <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gradient-to-r from-red-50 to-rose-50 border border-red-200/50 rounded-xl p-3">
                        <p className="text-xs font-bold text-slate-600 uppercase">Posicoes Ativas</p>
                        <p className="text-xl font-bold text-red-600">{positions.length}</p>
                    </div>
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200/50 rounded-xl p-3">
                        <p className="text-xs font-bold text-slate-600 uppercase">Nao Realizado</p>
                        <p className={cn("text-xl font-bold", unrealizedTotal >= 0 ? "text-green-600" : "text-red-600")}>
                            {formatMoney(unrealizedTotal)}
                        </p>
                    </div>
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 rounded-xl p-3">
                        <p className="text-xs font-bold text-slate-600 uppercase">Realizado (24h)</p>
                        <p className={cn("text-xl font-bold", (exRealized ?? 0) >= 0 ? "text-blue-600" : "text-red-600")}>
                            {formatMoney(exRealized)}
                        </p>
                    </div>
                    <div className="bg-gradient-to-r from-purple-50 to-violet-50 border border-purple-200/50 rounded-xl p-3">
                        <p className="text-xs font-bold text-slate-600 uppercase">Fees + Funding (24h)</p>
                        <p className={cn("text-xl font-bold", (feesFundingValue ?? 0) >= 0 ? "text-purple-600" : "text-red-600")}>
                            {formatMoney(feesFundingValue)}
                        </p>
                    </div>
                </div>

                <div className="space-y-2 max-h-[280px] overflow-y-auto">
                    <h4 className="text-sm font-bold text-slate-700 mb-2">Posicoes Abertas (Exchange)</h4>
                    {positions.length === 0 ? (
                        <div className="text-center py-8 text-slate-500 text-sm">
                            Nenhuma posicao aberta na exchange
                        </div>
                    ) : (
                        positions.map((pos, index) => (
                            <div
                                key={`${pos.symbol}-${index}`}
                                className="flex items-center justify-between p-3 rounded-lg border border-slate-200/50 bg-white hover:shadow-md transition-all"
                            >
                                <div className="flex items-center gap-3 flex-1">
                                    <div className={cn(
                                        "w-8 h-8 rounded-lg flex items-center justify-center",
                                        pos.direction === 'LONG' ? "bg-green-100" : "bg-red-100"
                                    )}>
                                        {pos.direction === 'LONG' ? (
                                            <TrendingUp className="w-4 h-4 text-green-600" />
                                        ) : (
                                            <TrendingDown className="w-4 h-4 text-red-600" />
                                        )}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-bold text-slate-900">{pos.symbol}</span>
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded-full font-medium",
                                                (pos.pnl ?? 0) >= 0
                                                    ? "bg-green-100 text-green-700"
                                                    : "bg-red-100 text-red-700"
                                            )}>
                                                {(pos.pnl ?? 0) >= 0 ? 'Lucro' : 'Prejuizo'}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-xs text-slate-600">
                                            <span>Entrada: ${pos.entry_price.toFixed(4)}</span>
                                            {pos.current_price && <span>Atual: ${pos.current_price.toFixed(4)}</span>}
                                            <span>Qtd: {pos.quantity}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    {pos.pnl !== undefined && (
                                        <div className={cn(
                                            "text-sm font-bold",
                                            pos.pnl >= 0 ? "text-green-600" : "text-red-600"
                                        )}>
                                            ${pos.pnl.toFixed(2)}
                                        </div>
                                    )}
                                    <div className="text-xs text-slate-500">
                                        {formatDate(pos.opened_at ?? null)}
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
