import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface TradeHistory {
    id: number;
    closed_at: string;
    pnl: number;
    symbol: string;
}

export const PerformanceChart: React.FC = () => {
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHistory();
        const interval = setInterval(fetchHistory, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchHistory = async () => {
        try {
            const response = await axios.get(`${API_URL}/api/trading/history?limit=50`);
            const trades: TradeHistory[] = response.data;

            // Processar dados para acumulado
            let cumulative = 0;
            // Ordenar por data (antigo -> novo) para acumular
            const sorted = [...trades].sort((a, b) => new Date(a.closed_at).getTime() - new Date(b.closed_at).getTime());

            const chartData = sorted.map(t => {
                cumulative += t.pnl;
                return {
                    date: new Date(t.closed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    pnl: t.pnl,
                    cumulative: cumulative,
                    symbol: t.symbol
                };
            });

            setData(chartData);
        } catch (error) {
            console.error("Erro ao carregar histórico:", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="animate-pulse h-64 bg-muted rounded-lg"></div>;

    if (data.length === 0) {
        return (
            <Card className="h-full flex items-center justify-center text-muted-foreground">
                <CardContent>
                    <p>Sem dados de histórico ainda.</p>
                </CardContent>
            </Card>
        );
    }

    const isPositive = data.length > 0 && data[data.length - 1].cumulative >= 0;

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-500" /> Performance (PnL Acumulado)
                </CardTitle>
                <span className={cn("text-xl font-bold", isPositive ? "text-green-500" : "text-red-500")}>
                    ${data[data.length - 1].cumulative.toFixed(2)}
                </span>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] pt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={isPositive ? "#22c55e" : "#ef4444"} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="hsl(var(--muted-foreground))"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="hsl(var(--muted-foreground))"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: 'hsl(var(--popover))', borderColor: 'hsl(var(--border))', color: 'hsl(var(--popover-foreground))' }}
                            itemStyle={{ color: 'hsl(var(--foreground))' }}
                            formatter={(value: number) => [`$${value.toFixed(2)}`, 'Acumulado']}
                            labelStyle={{ color: 'hsl(var(--muted-foreground))' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="cumulative"
                            stroke={isPositive ? "#22c55e" : "#ef4444"}
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorPnl)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
};
