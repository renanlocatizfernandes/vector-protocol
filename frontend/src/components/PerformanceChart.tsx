import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getRealizedDailyStats, type RealizedDailyPoint } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';

type ChartRow = {
    date: string;
    net_pnl: number;
    realized_pnl: number;
    cumulative: number;
};

export const PerformanceChart: React.FC = () => {
    const [data, setData] = useState<ChartRow[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSeries();
        const interval = setInterval(fetchSeries, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchSeries = async () => {
        try {
            const response = await getRealizedDailyStats(30);
            const series: RealizedDailyPoint[] = response.series || [];

            let cumulative = 0;
            const chartData = series
                .slice()
                .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
                .map(point => {
                    cumulative += point.net_pnl || 0;
                    const parsedDate = new Date(point.date);
                    return {
                        date: parsedDate.toLocaleDateString([], { month: 'short', day: '2-digit' }),
                        net_pnl: point.net_pnl || 0,
                        realized_pnl: point.realized_pnl || 0,
                        cumulative
                    };
                });

            setData(chartData);
        } catch (error) {
            console.error('Erro ao carregar performance acumulada:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card className="h-full border-white/10 bg-white/5">
                <div className="h-full flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
            </Card>
        );
    }

    if (data.length === 0) {
        return (
            <Card className="h-full flex items-center justify-center text-muted-foreground border-dashed border-white/10">
                <CardContent>
                    <p>Nenhum histórico de performance disponível.</p>
                </CardContent>
            </Card>
        );
    }

    const currentPnl = data[data.length - 1].cumulative;
    const isPositive = currentPnl >= 0;

    return (
        <Card className="h-full flex flex-col overflow-hidden relative group glass-card border-white/10">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <TrendingUp className="w-24 h-24 text-primary" />
            </div>

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 z-10">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                    <DollarSign className="h-4 w-4 text-primary" /> Total Performance
                </CardTitle>
                <div className="flex flex-col items-end">
                    <span
                        className={cn(
                            'text-2xl font-bold tracking-tight',
                            isPositive
                                ? 'text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]'
                                : 'text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]'
                        )}
                    >
                        ${currentPnl.toFixed(2)}
                    </span>
                    <span className="text-xs text-muted-foreground">Cumulative PnL (Exchange)</span>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-[300px] pt-4 z-10">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop
                                    offset="5%"
                                    stopColor={isPositive ? '#2bd4a5' : '#ff5a5f'}
                                    stopOpacity={0.2}
                                />
                                <stop
                                    offset="95%"
                                    stopColor={isPositive ? '#2bd4a5' : '#ff5a5f'}
                                    stopOpacity={0}
                                />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#9aa3b2"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={30}
                        />
                        <YAxis
                            stroke="#9aa3b2"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={value => `$${value.toFixed(0)}`}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#111827',
                                borderColor: '#1f2937',
                                color: '#ffffff',
                                borderRadius: '8px',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                            }}
                            itemStyle={{ color: '#ffffff' }}
                            formatter={(value: number, name: string) => [`$${value.toFixed(2)}`, name]}
                            labelStyle={{ color: '#9aa3b2' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="cumulative"
                            stroke={isPositive ? '#2bd4a5' : '#ff5a5f'}
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
