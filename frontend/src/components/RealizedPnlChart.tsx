import React, { useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getRealizedDailyStats, type RealizedDailyPoint } from '../services/api';
import { cn } from '@/lib/utils';

export const RealizedPnlChart: React.FC = () => {
    const [data, setData] = useState<RealizedDailyPoint[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        const fetchData = async () => {
            try {
                const res = await getRealizedDailyStats(7);
                if (mounted) setData(res.series || []);
            } catch (error) {
                console.error('Erro ao carregar PnL diário:', error);
            } finally {
                if (mounted) setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    const total = useMemo(() => {
        return data.reduce((acc, cur) => acc + (cur.net_pnl || 0), 0);
    }, [data]);

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
                    <p>No realized PnL data.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full flex flex-col overflow-hidden relative group glass-card border-white/10">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 z-10">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                    Realized PnL (Exchange)
                </CardTitle>
                <div className="flex flex-col items-end">
                    <span className={cn(
                        "text-2xl font-bold tracking-tight",
                        total >= 0 ? "text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]" : "text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]"
                    )}>
                        ${total.toFixed(2)}
                    </span>
                    <span className="text-xs text-muted-foreground">Last 7 days</span>
                </div>
            </CardHeader>
            <CardContent className="flex-1 min-h-[280px] pt-4 z-10">
                <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                        <XAxis
                            dataKey="date"
                            stroke="#9aa3b2"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={10}
                        />
                        <YAxis
                            stroke="#9aa3b2"
                            fontSize={11}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `$${value}`}
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
                            formatter={(value: number) => [`$${value.toFixed(2)}`, 'Net PnL']}
                            labelStyle={{ color: '#9aa3b2' }}
                        />
                        <Bar dataKey="net_pnl" radius={[6, 6, 0, 0]}>
                            {data.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.net_pnl >= 0 ? '#2bd4a5' : '#ff5a5f'}
                                    fillOpacity={0.7}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
};
