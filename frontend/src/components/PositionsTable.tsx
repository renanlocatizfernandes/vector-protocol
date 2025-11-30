import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { getPositionsDashboard, syncPositions, type DashboardData } from '../services/api';

export const PositionsTable: React.FC = () => {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(false);
    const [agg, setAgg] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const loadData = useCallback(async () => {
        try {
            const res = await getPositionsDashboard();
            setData(res);
        } catch (error) {
            console.error("Erro ao carregar posições:", error);
        }
    }, []);

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 5000); // Atualização mais frequente para posições
        return () => clearInterval(interval);
    }, [loadData]);

    const handleSync = async (strict: boolean) => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await syncPositions(strict ? { mode: 'strict' } : undefined);
            setMessage({ type: 'success', text: `Sincronização concluída` });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Erro ao sincronizar' });
        } finally {
            setLoading(false);
        }
    };

    const aggRows = useMemo(() => {
        if (!data?.open_trades?.length) return [];
        const map = new Map<string, any>();

        for (const t of data.open_trades) {
            const key = t.symbol;
            if (!map.has(key)) {
                map.set(key, {
                    symbol: key,
                    netQty: 0,
                    wPriceSum: 0,
                    wSum: 0,
                    pnlSum: 0,
                    pnlPctWsum: 0,
                    earliest: t.opened_at
                });
            }
            const g = map.get(key);
            const qty = Number(t.quantity);
            const isShort = t.direction.includes('SHORT');
            const signed = (isShort ? -1 : 1) * qty;

            g.netQty += signed;
            g.wPriceSum += Number(t.entry_price) * qty;
            g.wSum += qty;
            g.pnlSum += Number(t.pnl || 0);
            if (t.pnl_percentage) g.pnlPctWsum += t.pnl_percentage * qty;
        }

        return Array.from(map.values()).map(g => ({
            id: g.symbol,
            symbol: g.symbol,
            direction: g.netQty > 0 ? 'LONG' : 'SHORT',
            entry_price: g.wSum > 0 ? g.wPriceSum / g.wSum : 0,
            quantity: Math.abs(g.netQty),
            pnl: g.pnlSum,
            pnl_percentage: g.wSum > 0 ? g.pnlPctWsum / g.wSum : 0,
            opened_at: g.earliest
        }));
    }, [data?.open_trades]);

    const rows = agg ? aggRows : (data?.open_trades || []);

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Posições Abertas</h3>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={agg}
                            onChange={e => setAgg(e.target.checked)}
                            className="rounded border-gray-600 bg-gray-700 text-blue-500"
                        />
                        Agrupar por Símbolo
                    </label>
                    <div className="flex gap-2">
                        <button className="btn btn-secondary text-xs" onClick={() => handleSync(false)} disabled={loading}>
                            Sync
                        </button>
                        <button className="btn btn-secondary text-xs" onClick={() => handleSync(true)} disabled={loading}>
                            Sync (Strict)
                        </button>
                    </div>
                </div>
            </div>

            {message && (
                <div className={`mb-4 p-2 rounded text-sm ${message.type === 'success' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}`}>
                    {message.text}
                </div>
            )}

            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Símbolo</th>
                            <th>Direção</th>
                            <th>Entrada</th>
                            <th>Qtd</th>
                            <th>PNL (USDT)</th>
                            <th>PNL %</th>
                            <th>Aberto em</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.length > 0 ? (
                            rows.map((row: any) => (
                                <tr key={row.id}>
                                    <td className="font-mono font-bold">{row.symbol}</td>
                                    <td>
                                        <span className={`badge ${row.direction === 'LONG' ? 'badge-success' : 'badge-danger'}`}>
                                            {row.direction}
                                        </span>
                                    </td>
                                    <td className="font-mono">{Number(row.entry_price).toFixed(4)}</td>
                                    <td className="font-mono">{Number(row.quantity).toFixed(4)}</td>
                                    <td className={`font-mono font-bold ${row.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                                        {row.pnl ? row.pnl.toFixed(2) : '—'}
                                    </td>
                                    <td className={`font-mono ${row.pnl_percentage >= 0 ? 'text-success' : 'text-danger'}`}>
                                        {row.pnl_percentage ? row.pnl_percentage.toFixed(2) : '—'}%
                                    </td>
                                    <td className="text-xs text-secondary">
                                        {row.opened_at ? new Date(row.opened_at).toLocaleString() : '—'}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={7} className="text-center py-8 text-secondary">
                                    Nenhuma posição aberta no momento.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Footer Stats */}
            <div className="mt-4 pt-4 border-t border-gray-700 flex gap-6 text-sm text-secondary">
                <div>Exposição Total: <span className="text-primary font-mono">{data?.portfolio?.exposure_total || '0.00'}</span></div>
                <div>Unrealized PnL: <span className={`font-mono ${data?.portfolio?.unrealized_pnl_total >= 0 ? 'text-success' : 'text-danger'}`}>{data?.portfolio?.unrealized_pnl_total || '0.00'}</span></div>
            </div>
        </div>
    );
};
