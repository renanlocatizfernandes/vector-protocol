import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { getPositionsDashboard, syncPositions, type DashboardData } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';

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
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <Layers className="h-5 w-5 text-primary" /> Posições Abertas
                </CardTitle>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm cursor-pointer select-none text-muted-foreground hover:text-foreground transition-colors">
                        <input
                            type="checkbox"
                            checked={agg}
                            onChange={e => setAgg(e.target.checked)}
                            className="rounded border-input bg-background text-primary focus:ring-primary"
                        />
                        Agrupar por Símbolo
                    </label>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleSync(false)} disabled={loading}>
                            <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Sync
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleSync(true)} disabled={loading}>
                            <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Sync (Strict)
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {message && (
                    <div className={cn(
                        "mb-4 p-2 rounded text-sm font-medium text-center",
                        message.type === 'success' ? "bg-green-500/15 text-green-500" : "bg-red-500/15 text-red-500"
                    )}>
                        {message.text}
                    </div>
                )}

                <div className="rounded-md border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Símbolo</TableHead>
                                <TableHead>Direção</TableHead>
                                <TableHead>Entrada</TableHead>
                                <TableHead>Qtd</TableHead>
                                <TableHead>PNL (USDT)</TableHead>
                                <TableHead>PNL %</TableHead>
                                <TableHead>Aberto em</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.length > 0 ? (
                                rows.map((row: any) => (
                                    <TableRow key={row.id}>
                                        <TableCell className="font-mono font-bold">{row.symbol}</TableCell>
                                        <TableCell>
                                            <Badge variant={row.direction === 'LONG' ? 'success' : 'destructive'}>
                                                {row.direction}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="font-mono">{Number(row.entry_price).toFixed(4)}</TableCell>
                                        <TableCell className="font-mono">{Number(row.quantity).toFixed(4)}</TableCell>
                                        <TableCell className={cn("font-mono font-bold", row.pnl >= 0 ? 'text-green-500' : 'text-red-500')}>
                                            {row.pnl ? row.pnl.toFixed(2) : '—'}
                                        </TableCell>
                                        <TableCell className={cn("font-mono", row.pnl_percentage >= 0 ? 'text-green-500' : 'text-red-500')}>
                                            {row.pnl_percentage ? row.pnl_percentage.toFixed(2) : '—'}%
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground">
                                            {row.opened_at ? new Date(row.opened_at).toLocaleString() : '—'}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                                        Nenhuma posição aberta no momento.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>

                {/* Footer Stats */}
                <div className="mt-4 pt-4 border-t flex gap-6 text-sm text-muted-foreground">
                    <div>Exposição Total: <span className="text-foreground font-mono">{data?.portfolio?.exposure_total || '0.00'}</span></div>
                    <div>Unrealized PnL: <span className={cn("font-mono", data?.portfolio?.unrealized_pnl_total >= 0 ? 'text-green-500' : 'text-red-500')}>{data?.portfolio?.unrealized_pnl_total || '0.00'}</span></div>
                </div>
            </CardContent>
        </Card>
    );
};
