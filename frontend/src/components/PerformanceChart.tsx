import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import axios from 'axios';

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

    if (loading) return <div className="animate-pulse h-64 bg-gray-800 rounded-lg"></div>;

    if (data.length === 0) {
        return (
            <div className="card h-full flex items-center justify-center text-secondary">
                <p>Sem dados de histórico ainda.</p>
            </div>
        );
    }

    const isPositive = data.length > 0 && data[data.length - 1].cumulative >= 0;

    return (
        <div className="card h-full flex flex-col">
            <h2 className="text-lg font-semibold mb-4 flex items-center justify-between">
                <span className="flex items-center gap-2"><span className="text-blue">📈</span> Performance (PnL Acumulado)</span>
                <span className={`text-xl font-bold ${isPositive ? 'text-success' : 'text-danger'}`}>
                    ${data[data.length - 1].cumulative.toFixed(2)}
                </span>
            </h2>

            <div className="flex-1 min-h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={isPositive ? "#81c995" : "#f28b82"} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={isPositive ? "#81c995" : "#f28b82"} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#3c4043" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#9aa0a6"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#9aa0a6"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `$${value}`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#292a2d', borderColor: '#3c4043', color: '#e8eaed' }}
                            itemStyle={{ color: '#e8eaed' }}
                            formatter={(value: number) => [`$${value.toFixed(2)}`, 'Acumulado']}
                            labelStyle={{ color: '#9aa0a6' }}
                        />
                        <Area
                            type="monotone"
                            dataKey="cumulative"
                            stroke={isPositive ? "#81c995" : "#f28b82"}
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorPnl)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
