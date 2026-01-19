import React, { useEffect, useState, useCallback } from 'react';
import { getClosedTrades } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { History, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export const TradeHistory: React.FC = () => {
    const [trades, setTrades] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const res = await getClosedTrades();
            setTrades(res.trades || []);
        } catch (error) {
            console.error("Erro ao carregar histórico:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    return (
        <Card className="elevated-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-gray-100">
                <div className="flex items-center gap-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2 text-gray-900">
                        <History className="h-5 w-5 text-purple-600" /> Histórico de Trades
                    </CardTitle>
                </div>
                <Button variant="outline" size="sm" onClick={loadData} disabled={loading} className="h-8 text-xs">
                    <RefreshCw className={cn("mr-2 h-3 w-3", loading && "animate-spin")} /> Atualizar
                </Button>
            </CardHeader>
            <CardContent className="p-0">
                <div className="rounded-none border-0 max-h-[500px] overflow-y-auto">
                    <Table>
                        <TableHeader className="bg-gray-50 sticky top-0 z-10">
                            <TableRow className="border-b border-gray-200">
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Símbolo</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Direção</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right">Preço Ent.</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right">Preço Saída</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right hidden md:table-cell">Qtd</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right">P&L</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right">P&L %</TableHead>
                                <TableHead className="text-xs font-semibold text-gray-700 uppercase tracking-wider text-right hidden lg:table-cell">Fechado em</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {trades.length > 0 ? (
                                trades.map((trade: any) => (
                                    <TableRow key={trade.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                        <TableCell className="font-mono font-semibold text-gray-900">
                                            {trade.symbol}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={cn(
                                                "font-mono text-[10px] px-2 py-0.5",
                                                trade.direction === 'LONG'
                                                    ? "bg-green-100 text-green-700 border-green-200"
                                                    : "bg-red-100 text-red-700 border-red-200"
                                            )}>
                                                {trade.direction}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-gray-600">
                                            ${Number(trade.entry_price).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-gray-600">
                                            ${Number(trade.exit_price || trade.current_price || 0).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="font-mono text-right text-gray-600 hidden md:table-cell">
                                            {Number(trade.quantity).toFixed(4)}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <span className={cn(
                                                "font-mono font-bold",
                                                trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                            )}>
                                                {trade.pnl ? (trade.pnl >= 0 ? '+' : '') + Number(trade.pnl).toFixed(2) : '--'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className={cn(
                                                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                                                trade.pnl_percentage >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                            )}>
                                                {trade.pnl_percentage >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                                {trade.pnl_percentage ? Math.abs(trade.pnl_percentage).toFixed(2) : '0.00'}%
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-xs text-gray-500 text-right font-mono hidden lg:table-cell">
                                            {trade.closed_at ? new Date(trade.closed_at).toLocaleString() : '--'}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                                        Nenhum trade fechado encontrado.
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>
            </CardContent>
        </Card>
    );
};
