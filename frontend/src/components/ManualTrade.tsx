import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Zap, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { http } from '../services/api';

type AmountType = 'quantity' | 'usdt_total' | 'usdt_margin';

export const ManualTrade: React.FC = () => {
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [direction, setDirection] = useState('LONG');
    const [amount, setAmount] = useState('0.001');
    const [amountType, setAmountType] = useState<AmountType>('quantity');
    const [leverage, setLeverage] = useState('10');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const handleTrade = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);

        try {
            const payload = {
                symbol: symbol.toUpperCase(),
                direction,
                amount: parseFloat(amount),
                amount_type: amountType,
                leverage: parseInt(leverage),
            };

            const response = await http.post('/api/trading/manual', payload);

            if (response.data.success) {
                setMessage({ type: 'success', text: `Order Executed: ${response.data.symbol} ${response.data.direction} @ ${response.data.entry_price}` });
            } else {
                setMessage({ type: 'error', text: `Failed: ${response.data.reason || 'Unknown Error'}` });
            }
        } catch (error: any) {
            setMessage({ type: 'error', text: `Error: ${error.response?.data?.detail || error.message}` });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
                <Zap className="w-24 h-24 text-warning" />
            </div>

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-dark-700/50">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Zap className="h-4 w-4 text-warning animate-pulse" /> Manual Trade Execution
                </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
                <form onSubmit={handleTrade} className="flex flex-col gap-6">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground">Symbol</label>
                            <Input
                                type="text"
                                className="font-mono uppercase bg-dark-800 border-dark-700 focus:border-primary/50"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                placeholder="BTCUSDT"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground">Leverage</label>
                            <Input
                                type="number"
                                className="bg-dark-800 border-dark-700 focus:border-primary/50"
                                value={leverage}
                                onChange={(e) => setLeverage(e.target.value)}
                                min="1"
                                max="125"
                                required
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground">Direction</label>
                            <div className="flex gap-2">
                                <Button
                                    type="button"
                                    variant={direction === 'LONG' ? 'default' : 'outline'}
                                    className={cn(
                                        "flex-1 transition-all duration-300",
                                        direction === 'LONG'
                                            ? "bg-success hover:bg-success/90 text-dark-950 shadow-[0_0_15px_rgba(0,255,157,0.4)]"
                                            : "border-dark-700 hover:border-success/50 hover:text-success"
                                    )}
                                    onClick={() => setDirection('LONG')}
                                >
                                    <TrendingUp className="mr-2 h-4 w-4" /> LONG
                                </Button>
                                <Button
                                    type="button"
                                    variant={direction === 'SHORT' ? 'destructive' : 'outline'}
                                    className={cn(
                                        "flex-1 transition-all duration-300",
                                        direction === 'SHORT'
                                            ? "bg-danger hover:bg-danger/90 text-white shadow-[0_0_15px_rgba(255,77,77,0.4)]"
                                            : "border-dark-700 hover:border-danger/50 hover:text-danger"
                                    )}
                                    onClick={() => setDirection('SHORT')}
                                >
                                    <TrendingDown className="mr-2 h-4 w-4" /> SHORT
                                </Button>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-medium text-muted-foreground">Amount</label>
                            <Input
                                type="number"
                                className="bg-dark-800 border-dark-700 focus:border-primary/50"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                step="0.0001"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-3">
                        <label className="text-xs font-medium text-muted-foreground">Amount Type</label>
                        <div className="flex bg-dark-800 p-1 rounded-lg gap-1 border border-dark-700/50">
                            {[
                                { id: 'quantity', label: 'Coin Qty' },
                                { id: 'usdt_total', label: 'Total USDT' },
                                { id: 'usdt_margin', label: 'Margin USDT' }
                            ].map((type) => (
                                <button
                                    key={type.id}
                                    type="button"
                                    className={cn(
                                        "flex-1 py-1.5 px-2 rounded-md text-xs transition-all duration-300",
                                        amountType === type.id
                                            ? "bg-primary/20 text-primary shadow-sm font-medium border border-primary/20"
                                            : "text-muted-foreground hover:text-white hover:bg-dark-700"
                                    )}
                                    onClick={() => setAmountType(type.id as AmountType)}
                                >
                                    {type.label}
                                </button>
                            ))}
                        </div>
                        <div className="text-[10px] text-muted-foreground text-center h-4 flex items-center justify-center gap-2">
                            <RefreshCw className="w-3 h-3 animate-spin duration-[3000ms]" />
                            {amountType === 'quantity' && "Ex: 0.001 BTC"}
                            {amountType === 'usdt_total' && "Ex: $1000 (Total Position Size)"}
                            {amountType === 'usdt_margin' && "Ex: $100 (Your Cost/Margin)"}
                        </div>
                    </div>

                    <Button type="submit" disabled={loading} className="w-full relative overflow-hidden group">
                        <div className="absolute inset-0 bg-primary/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                        <span className="relative flex items-center justify-center gap-2">
                            {loading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                            {loading ? 'Executing...' : 'Execute Order'}
                        </span>
                    </Button>

                    {message && (
                        <div className={cn(
                            "p-3 rounded-lg text-xs text-center font-medium border animate-in zoom-in-95",
                            message.type === 'success' ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"
                        )}>
                            {message.text}
                        </div>
                    )}
                </form>
            </CardContent>
        </Card>
    );
};
