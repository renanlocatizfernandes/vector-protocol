import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import {
    getPositionsDashboard,
    syncPositions,
    closePositionExchange,
    setPositionStopLoss,
    setPositionTakeProfit,
    setPositionBreakeven,
    setPositionTrailingStop,
    cancelOpenOrders,
    type DashboardData
} from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { RefreshCw, Layers, ArrowUpRight, ArrowDownRight, Filter, MoreHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';

const useMediaQuery = (query: string): boolean => {
    const [matches, setMatches] = useState(false);

    useEffect(() => {
        const media = window.matchMedia(query);
        if (media.matches !== matches) {
            setMatches(media.matches);
        }
        const listener = () => setMatches(media.matches);
        media.addEventListener('change', listener);
        return () => media.removeEventListener('change', listener);
    }, [matches, query]);

    return matches;
};

const quickActions = [
    { id: 'tp_1', label: 'TP1', title: 'Set TP +1%', tone: 'positive' },
    { id: 'tp_2', label: 'TP2', title: 'Set TP +2%', tone: 'positive' },
    { id: 'sl_1', label: 'SL1', title: 'Set SL -1%', tone: 'negative' },
    { id: 'breakeven', label: 'BE', title: 'Move SL to breakeven', tone: 'neutral' },
    { id: 'trailing', label: 'Trail', title: 'Set trailing stop (auto)', tone: 'neutral' },
    { id: 'close', label: 'Close', title: 'Close position (market)', tone: 'danger' }
];

const mobileQuickActions = [
    { id: 'close', label: 'Close', title: 'Close position (market)', tone: 'danger' },
    { id: 'tp_1', label: 'TP1', title: 'Set TP +1%', tone: 'positive' },
    { id: 'sl_1', label: 'SL1', title: 'Set SL -1%', tone: 'negative' }
];

const drawerActions = [
    { id: 'tp_2', label: 'TP +2%', title: 'Set TP +2%', tone: 'positive' },
    { id: 'sl_2', label: 'SL -2%', title: 'Set SL -2%', tone: 'negative' },
    { id: 'tp_3', label: 'TP +3%', title: 'Set TP +3%', tone: 'positive' },
    { id: 'sl_3', label: 'SL -3%', title: 'Set SL -3%', tone: 'negative' },
    { id: 'breakeven', label: 'Move SL to Breakeven', title: 'Move SL to breakeven', tone: 'neutral' },
    { id: 'trailing', label: 'Set Trailing Stop', title: 'Set trailing stop (auto)', tone: 'neutral' },
    { id: 'cancel_orders', label: 'Cancel Open Orders', title: 'Cancel open orders', tone: 'neutral' }
];

const quickActionClass = (tone: string, active: boolean) => cn(
    "h-7 px-2 rounded-md border text-[11px] font-medium transition-colors",
    tone === 'positive' && "border-success/30 text-success hover:bg-success/10",
    tone === 'negative' && "border-danger/30 text-danger hover:bg-danger/10",
    tone === 'danger' && "border-danger/50 text-danger hover:bg-danger/20",
    tone === 'neutral' && "border-white/10 text-white/80 hover:bg-white/10",
    active && "bg-primary/10 ring-1 ring-primary/30"
);

export const PositionsTable: React.FC = () => {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [confirmCloseBySymbol, setConfirmCloseBySymbol] = useState<Record<string, boolean>>({});
    const confirmCloseTimeouts = useRef<Record<string, number>>({});
    const [agg, setAgg] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [drawerOpenBySymbol, setDrawerOpenBySymbol] = useState<Record<string, boolean>>({});
    const isMobile = useMediaQuery('(max-width: 1024px)');
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

    const runAction = async (symbol: string, actionId: string) => {
        if (!actionId) return;

        setActionLoading(true);
        setMessage(null);
        try {
            if (actionId === 'close') {
                await closePositionExchange(symbol);
            } else if (actionId.startsWith('tp_')) {
                const pct = Number(actionId.split('_')[1]);
                await setPositionTakeProfit({ symbol, take_profit_pct: pct });
            } else if (actionId.startsWith('sl_')) {
                const pct = Number(actionId.split('_')[1]);
                await setPositionStopLoss({ symbol, stop_pct: pct });
            } else if (actionId === 'breakeven') {
                await setPositionBreakeven(symbol);
            } else if (actionId === 'trailing') {
                await setPositionTrailingStop(symbol);
            } else if (actionId === 'cancel_orders') {
                await cancelOpenOrders(symbol);
            }

            const allActions = [...quickActions, ...drawerActions];
            const label = allActions.find(a => a.id === actionId)?.label || actionId;
            setMessage({ type: 'success', text: `${label} applied to ${symbol}` });

            // Close drawer if open
            setDrawerOpenBySymbol((prev) => ({ ...prev, [symbol]: false }));

            await loadData();
        } catch (e: any) {
            setMessage({ type: 'error', text: e?.message || 'Action Error' });
        } finally {
            setConfirmCloseBySymbol((prev) => ({ ...prev, [symbol]: false }));
            setActionLoading(false);
        }
    };

    const armCloseConfirm = useCallback((symbol: string) => {
        setConfirmCloseBySymbol((prev) => ({ ...prev, [symbol]: true }));
        const existing = confirmCloseTimeouts.current[symbol];
        if (existing) {
            window.clearTimeout(existing);
        }
        confirmCloseTimeouts.current[symbol] = window.setTimeout(() => {
            setConfirmCloseBySymbol((prev) => ({ ...prev, [symbol]: false }));
        }, 4000);
    }, []);

    const activeRows = useMemo(() => {
        if (data?.exchange_positions?.length) {
            return data.exchange_positions;
        }
        return data?.open_trades || [];
    }, [data?.exchange_positions, data?.open_trades]);

    const positionsSource = data?.positions_source || (data?.exchange_positions?.length ? 'exchange' : 'db');

    const aggRows = useMemo(() => {
        if (!activeRows?.length) return [];
        const map = new Map<string, any>();

        for (const t of activeRows) {
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
    }, [activeRows]);

    const rows = agg ? aggRows : activeRows;

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                        <Layers className="h-5 w-5 text-primary" /> Open Positions
                    </CardTitle>
                    <Badge variant="outline" className="border-white/10 text-muted-foreground text-xs">
                        Source: {positionsSource}
                    </Badge>
                </div>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-xs font-medium cursor-pointer select-none text-muted-foreground hover:text-white transition-colors p-2 rounded-md hover:bg-white/5">
                        <input
                            type="checkbox"
                            checked={agg}
                            onChange={e => setAgg(e.target.checked)}
                            className="rounded border-white/10 bg-white/5 text-primary focus:ring-primary h-4 w-4"
                        />
                        <Filter className="w-3 h-3" /> Group by Symbol
                    </label>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleSync(false)} disabled={loading} className="h-8 text-xs border-white/10 hover:bg-white/5">
                            <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Sync
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleSync(true)} disabled={loading} className="h-8 text-xs border-white/10 hover:bg-white/5">
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
                        <TableHeader className="bg-white/5">
                            <TableRow className="border-white/10 hover:bg-transparent">
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Symbol</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Direction</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right hidden lg:table-cell">Entry Price</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right hidden lg:table-cell">Qty</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">PnL (USDT)</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right hidden md:table-cell">PnL %</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right hidden lg:table-cell">Time</TableHead>
                                <TableHead className="text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {rows.length > 0 ? (
                                rows.map((row: any) => (
                                    <TableRow key={row.id} className="border-white/10 hover:bg-white/5 transition-colors">
                                        <TableCell className="font-mono font-bold text-white">
                                            <div className="flex items-center gap-2">
                                                <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-[10px] text-muted-foreground">
                                                    Coin
                                                </div>
                                                <span>{row.symbol}</span>
                                            </div>
                                            <div className="mt-1 text-[11px] text-muted-foreground md:hidden">
                                                Entry ${Number(row.entry_price).toFixed(4)} | Qty ${Number(row.quantity).toFixed(4)}
                                                {row.opened_at ? ` | ${new Date(row.opened_at).toLocaleTimeString()}` : ''}
                                            </div>
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
                                        <TableCell className="font-mono text-right text-muted-foreground hidden lg:table-cell">
                                            ${Number(row.entry_price).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-muted-foreground hidden lg:table-cell">
                                            {Number(row.quantity).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <span className={cn(
                                                "font-mono font-bold block",
                                                row.pnl >= 0 ? 'text-success' : 'text-danger'
                                            )}>
                                                {row.pnl ? (row.pnl >= 0 ? '+' : '') + row.pnl.toFixed(2) : '--'}
                                            </span>
                                            <div className={cn(
                                                "mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium md:hidden",
                                                row.pnl_percentage >= 0 ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                                            )}>
                                                {row.pnl_percentage >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                                {row.pnl_percentage ? Math.abs(row.pnl_percentage).toFixed(2) : '0.00'}%
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right hidden md:table-cell">
                                            <div className={cn(
                                                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                                                row.pnl_percentage >= 0 ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                                            )}>
                                                {row.pnl_percentage >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                                {row.pnl_percentage ? Math.abs(row.pnl_percentage).toFixed(2) : '0.00'}%
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground text-right font-mono hidden lg:table-cell">
                                            {row.opened_at ? new Date(row.opened_at).toLocaleTimeString() : '--'}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {isMobile ? (
                                                <>
                                                    <div className="flex flex-wrap items-center justify-end gap-1">
                                                        {mobileQuickActions.map((action) => {
                                                            const isClose = action.id === 'close';
                                                            const confirmClose = isClose && confirmCloseBySymbol[row.symbol];
                                                            const title = confirmClose ? 'Click again to confirm close' : action.title;
                                                            const label = confirmClose ? 'Confirm' : action.label;

                                                            const handleClick = () => {
                                                                if (actionLoading) return;
                                                                if (isClose) {
                                                                    if (confirmClose) {
                                                                        const existing = confirmCloseTimeouts.current[row.symbol];
                                                                        if (existing) window.clearTimeout(existing);
                                                                        runAction(row.symbol, action.id);
                                                                    } else {
                                                                        armCloseConfirm(row.symbol);
                                                                    }
                                                                    return;
                                                                }
                                                                const existing = confirmCloseTimeouts.current[row.symbol];
                                                                if (existing) window.clearTimeout(existing);
                                                                setConfirmCloseBySymbol((prev) => ({ ...prev, [row.symbol]: false }));
                                                                runAction(row.symbol, action.id);
                                                            };

                                                            return (
                                                                <button
                                                                    key={action.id}
                                                                    type="button"
                                                                    title={title}
                                                                    disabled={actionLoading}
                                                                    onClick={handleClick}
                                                                    className={quickActionClass(action.tone, confirmClose)}
                                                                >
                                                                    {label}
                                                                </button>
                                                            );
                                                        })}
                                                        <button
                                                            type="button"
                                                            title="More actions"
                                                            disabled={actionLoading}
                                                            onClick={() => setDrawerOpenBySymbol((prev) => ({ ...prev, [row.symbol]: true }))}
                                                            className="h-7 px-2 rounded-md border border-white/10 text-white/80 hover:bg-white/10 text-[11px]"
                                                        >
                                                            <MoreHorizontal className="w-3 h-3" />
                                                        </button>
                                                    </div>
                                                    <Sheet
                                                        open={drawerOpenBySymbol[row.symbol]}
                                                        onOpenChange={(open) => setDrawerOpenBySymbol((prev) => ({ ...prev, [row.symbol]: open }))}
                                                    >
                                                        <SheetContent className="bg-dark-950 border-white/10">
                                                            <SheetHeader>
                                                                <SheetTitle className="text-white">Actions for {row.symbol}</SheetTitle>
                                                            </SheetHeader>
                                                            <div className="mt-6 flex flex-col gap-2">
                                                                {drawerActions.map((action) => {
                                                                    const handleClick = () => {
                                                                        if (actionLoading) return;
                                                                        runAction(row.symbol, action.id);
                                                                    };

                                                                    return (
                                                                        <button
                                                                            key={action.id}
                                                                            type="button"
                                                                            disabled={actionLoading}
                                                                            onClick={handleClick}
                                                                            className={cn(
                                                                                "w-full px-4 py-3 rounded-md border text-sm font-medium transition-colors text-left",
                                                                                action.tone === 'positive' && "border-success/30 text-success hover:bg-success/10",
                                                                                action.tone === 'negative' && "border-danger/30 text-danger hover:bg-danger/10",
                                                                                action.tone === 'neutral' && "border-white/10 text-white/80 hover:bg-white/10"
                                                                            )}
                                                                        >
                                                                            {action.label}
                                                                        </button>
                                                                    );
                                                                })}
                                                            </div>
                                                        </SheetContent>
                                                    </Sheet>
                                                </>
                                            ) : (
                                                <div className="flex flex-wrap items-center justify-end gap-1">
                                                    {quickActions.map((action) => {
                                                        const isClose = action.id === 'close';
                                                        const confirmClose = isClose && confirmCloseBySymbol[row.symbol];
                                                        const title = confirmClose ? 'Click again to confirm close' : action.title;
                                                        const label = confirmClose ? 'Confirm' : action.label;

                                                        const handleClick = () => {
                                                            if (actionLoading) return;
                                                            if (isClose) {
                                                                if (confirmClose) {
                                                                    const existing = confirmCloseTimeouts.current[row.symbol];
                                                                    if (existing) window.clearTimeout(existing);
                                                                    runAction(row.symbol, action.id);
                                                                } else {
                                                                    armCloseConfirm(row.symbol);
                                                                }
                                                                return;
                                                            }
                                                            const existing = confirmCloseTimeouts.current[row.symbol];
                                                            if (existing) window.clearTimeout(existing);
                                                            setConfirmCloseBySymbol((prev) => ({ ...prev, [row.symbol]: false }));
                                                            runAction(row.symbol, action.id);
                                                        };

                                                        return (
                                                            <button
                                                                key={action.id}
                                                                type="button"
                                                                title={title}
                                                                disabled={actionLoading}
                                                                onClick={handleClick}
                                                                className={quickActionClass(action.tone, confirmClose)}
                                                            >
                                                                {label}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow className="hover:bg-transparent">
                                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
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
                <div className="bg-white/5 p-4 border-t border-white/10 flex flex-wrap gap-6 text-sm">
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Total Exposure</span>
                        <span className="font-mono text-white font-bold">${data?.portfolio?.exposure_total || '0.00'}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground uppercase">Unrealized PnL</span>
                        <span className={cn(
                            "font-mono font-bold text-lg",
                            data?.portfolio?.unrealized_pnl_total >= 0 ? 'text-success drop-shadow-[0_0_8px_rgba(43,212,165,0.3)]' : 'text-danger drop-shadow-[0_0_8px_rgba(255,90,95,0.3)]'
                        )}>
                            {data?.portfolio?.unrealized_pnl_total ? (data?.portfolio?.unrealized_pnl_total >= 0 ? '+' : '') + data?.portfolio?.unrealized_pnl_total : '0.00'}
                        </span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};


