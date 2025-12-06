import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { http } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';

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
            const response = await http.get('/api/trading/history?limit=50');
            const trades: TradeHistory[] = response.data;

            let cumulative = 0;
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

    if (loading) return (
        <Card className="h-full border-dark-700/50 bg-dark-900/20">
            <div className="h-full flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        </Card>
    );

    if (data.length === 0) {
        return (
            <Card className="h-full flex items-center justify-center text-muted-foreground border-dashed">
                <CardContent>
                    <p>No trading history available.</p>
                </CardContent>
            </Card>
        );
    }

    const currentPnl = data[data.length - 1].cumulative;
    const isPositive = currentPnl >= 0;

    return (
        <Card className="h-full flex flex-col overflow-hidden relative group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <TrendingUp className="w-24 h-24 text-primary" />
            </div>

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 z-10">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-text-muted">
                    <DollarSign className="h-4 w-4 text-primary" /> Total Performance
                </CardTitle>
                <div className="flex flex-col items-end">
                    <span className={cn("text-2xl font-bold tracking-tight", isPositive ? "text-success drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,77,77,0.3)]")}>
                        ${currentPnl.toFixed(2)}
                    </span>
                    <span className="text-xs text-muted-foreground">Cumulative PnL</span>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] pt-4 z-10">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={isPositive ? "#00ff9d" : "#ff4d4d"} stopOpacity={0.2} />
                                <stop offset="95%" stopColor={isPositive ? "#00ff9d" : "#ff4d4d"} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#a0a0a0"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={30}
                        />
                        <YAxis
                            stroke="#a0a0a0"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#12121a',
                                borderColor: '#2a2a35',
                                color: '#ffffff',
                                borderRadius: '8px',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                            }}
                            itemStyle={{ color: '#ffffff' }}
                            formatter={(value: number) => [`$${value.toFixed(2)}`, 'PnL']}
                            labelStyle={{ color: '#a0a0a0' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="cumulative"
                            stroke={isPositive ? "#00ff9d" : "#ff4d4d"}
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#colorPnl)"
                            activeDot={{ r: 6, strokeWidth: 0, fill: '#ffffff' }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
};
