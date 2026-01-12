import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
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
            <Card className="h-full elevated-card">
                <div className="h-full flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
            </Card>
        );
    }

    if (data.length === 0) {
        return (
            <Card className="h-full elevated-card flex items-center justify-center text-gray-500 border-dashed">
                <CardContent>
                    <p>Nenhum histórico de performance disponível.</p>
                </CardContent>
            </Card>
        );
    }

    const currentPnl = data[data.length - 1].cumulative;
    const isPositive = currentPnl >= 0;

    return (
        <Card className="h-full flex flex-col overflow-hidden elevated-card-hover">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-gray-100">
                <CardTitle className="text-base font-semibold flex items-center gap-2 text-gray-900">
                    <TrendingUp className="w-5 h-5 text-blue-600" /> Performance Total
                </CardTitle>
                <div className="flex flex-col items-end">
                    <span
                        className={cn(
                            'text-2xl font-bold tracking-tight',
                            isPositive
                                ? 'text-green-600'
                                : 'text-red-600'
                        )}
                    >
                        ${currentPnl.toFixed(2)}
                    </span>
                    <span className="text-xs text-gray-500">P&L Acumulado (Exchange)</span>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-[280px] pt-4">
                <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#6B7280"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={30}
                            style={{ fontWeight: 500 }}
                        />
                        <YAxis
                            stroke="#6B7280"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={value => `$${value.toFixed(0)}`}
                            style={{ fontWeight: 500 }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#FFFFFF',
                                borderColor: '#E5E7EB',
                                color: '#374151',
                                borderRadius: '8px',
                                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                                padding: '8px'
                            }}
                            itemStyle={{ color: '#374151', fontWeight: 600 }}
                            formatter={(value: number) => `$${value.toFixed(2)}`}
                            labelStyle={{ color: '#6B7280', fontWeight: 500 }}
                        />
                        <Line
                            type="monotone"
                            dataKey="cumulative"
                            stroke={isPositive ? '#10B981' : '#EF4444'}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 2, stroke: '#FFFFFF', fill: isPositive ? '#10B981' : '#EF4444' }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
};
