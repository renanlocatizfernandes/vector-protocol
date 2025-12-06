import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { getPositionsDashboard, syncPositions, type DashboardData } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, Layers, ArrowUpRight, ArrowDownRight, Filter } from 'lucide-react';
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
        const interval = setInterval(loadData, 5000);
        return () => clearInterval(interval);
    }, [loadData]);

    const handleSync = async (strict: boolean) => {
        setLoading(true);
        setMessage(null);
        try {
            const res = await syncPositions(strict ? { mode: 'strict' } : undefined);
            setMessage({ type: 'success', text: `Sync Completed` });
            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Sync Error' });
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
        <Card className="border-dark-700/50 bg-dark-900/40 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 border-b border-dark-700/50">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <Layers className="h-5 w-5 text-primary" /> Open Positions
                </CardTitle>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-xs font-medium cursor-pointer select-none text-muted-foreground hover:text-white transition-colors p-2 rounded-md hover:bg-dark-800">
                        <input
                            type="checkbox"
                            checked={agg}
                            onChange={e => setAgg(e.target.checked)}
                            className="rounded border-dark-600 bg-dark-800 text-primary focus:ring-primary h-4 w-4"
                        />
                        <Filter className="w-3 h-3" /> Group by Symbol
                    </label>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleSync(false)} disabled={loading} className="h-8 text-xs border-dark-600 hover:bg-dark-800">
                            <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Sync
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleSync(true)} disabled={loading} className="h-8 text-xs border-dark-600 hover:bg-dark-800">
                            <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Strict Sync
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                {message && (
                    <div className={cn(
                        "m-4 p-2 rounded text-sm font-medium text-center border",
                        message.type === 'success'
                            ? "bg-green-500/10 text-green-500 border-green-500/20"
                            : "bg-red-500/10 text-red-500 border-red-500/20"
                    )}>
                        {message.text}
                    </div>
                )}

                <div className="rounded-none border-0">
                    <Table>
                        <TableHeader className="bg-dark-800/50">
                            <TableRow className="border-dark-700/50 hover:bg-transparent">
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Symbol</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Direction</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">Entry Price</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">Qty</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">PnL (USDT)</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">PnL %</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">Time</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.length > 0 ? (
                                rows.map((row: any) => (
                                    <TableRow key={row.id} className="border-dark-700/50 hover:bg-dark-800/50 transition-colors">
                                        <TableCell className="font-mono font-bold text-white flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-full bg-dark-800 flex items-center justify-center text-[10px] text-muted-foreground">
                                                Coin
                                            </div>
                                            {row.symbol}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={cn(
                                                "font-mono text-[10px] px-2 py-0.5 border-0",
                                                row.direction === 'LONG'
                                                    ? "bg-success/15 text-success ring-1 ring-success/20"
                                                    : "bg-danger/15 text-danger ring-1 ring-danger/20"
                                            )}>
                                                {row.direction}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-muted-foreground">
                                            ${Number(row.entry_price).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-muted-foreground">
                                            {Number(row.quantity).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <span className={cn(
                                                "font-mono font-bold block",
                                                row.pnl >= 0 ? 'text-success' : 'text-danger'
                                            )}>
                                                {row.pnl ? (row.pnl >= 0 ? '+' : '') + row.pnl.toFixed(2) : '—'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className={cn(
                                                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                                                row.pnl_percentage >= 0 ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                                            )}>
                                                {row.pnl_percentage >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                                {row.pnl_percentage ? Math.abs(row.pnl_percentage).toFixed(2) : '0.00'}%
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground text-right font-mono">
                                            {row.opened_at ? new Date(row.opened_at).toLocaleTimeString() : '—'}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow className="hover:bg-transparent">
                                    <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                                        <div className="flex flex-col items-center gap-2 opacity-50">
                                            <Layers className="w-8 h-8" />
                                            <span>No active positions</span>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>

                {/* Footer Stats */}
                <div className="bg-dark-900/50 p-4 border-t border-dark-700/50 flex flex-wrap gap-6 text-sm">
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Total Exposure</span>
                        <span className="font-mono text-white font-bold">${data?.portfolio?.exposure_total || '0.00'}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Unrealized PnL</span>
                        <span className={cn(
                            "font-mono font-bold text-lg",
                            data?.portfolio?.unrealized_pnl_total >= 0 ? 'text-success drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]' : 'text-danger drop-shadow-[0_0_8px_rgba(255,77,77,0.3)]'
                        )}>
                            {data?.portfolio?.unrealized_pnl_total ? (data?.portfolio?.unrealized_pnl_total >= 0 ? '+' : '') + data?.portfolio?.unrealized_pnl_total : '0.00'}
                        </span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
