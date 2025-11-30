import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Zap, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

            const response = await axios.post(`${API_URL}/api/trading/manual`, payload);

            if (response.data.success) {
                setMessage({ type: 'success', text: `✅ Ordem executada: ${response.data.symbol} ${response.data.direction} @ ${response.data.entry_price}` });
            } else {
                setMessage({ type: 'error', text: `❌ Falha: ${response.data.reason || 'Erro desconhecido'}` });
            }
        } catch (error: any) {
            setMessage({ type: 'error', text: `❌ Erro: ${error.response?.data?.detail || error.message}` });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Zap className="h-4 w-4 text-yellow-500" /> Trade Manual
                </CardTitle>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleTrade} className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="text-xs font-medium">Símbolo</label>
                            <Input
                                type="text"
                                className="font-mono uppercase"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                placeholder="BTCUSDT"
                                required
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-medium">Alavancagem</label>
                            <Input
                                type="number"
                                value={leverage}
                                onChange={(e) => setLeverage(e.target.value)}
                                min="1"
                                max="125"
                                required
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="text-xs font-medium">Direção</label>
                            <div className="flex gap-2">
                                <Button
                                    type="button"
                                    variant={direction === 'LONG' ? 'default' : 'outline'}
                                    className={cn("flex-1", direction === 'LONG' && "bg-green-600 hover:bg-green-700")}
                                    onClick={() => setDirection('LONG')}
                                >
                                    <TrendingUp className="mr-2 h-4 w-4" /> LONG
                                </Button>
                                <Button
                                    type="button"
                                    variant={direction === 'SHORT' ? 'destructive' : 'outline'}
                                    className="flex-1"
                                    onClick={() => setDirection('SHORT')}
                                >
                                    <TrendingDown className="mr-2 h-4 w-4" /> SHORT
                                </Button>
                            </div>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-medium">Quantidade</label>
                            <Input
                                type="number"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                step="0.0001"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-medium">Tipo de Valor</label>
                        <div className="flex bg-muted rounded-md p-1 gap-1">
                            <button
                                type="button"
                                className={cn(
                                    "flex-1 py-1 px-2 rounded-sm text-xs transition-all",
                                    amountType === 'quantity' ? "bg-background shadow-sm text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
                                )}
                                onClick={() => setAmountType('quantity')}
                            >
                                Qtd (Moeda)
                            </button>
                            <button
                                type="button"
                                className={cn(
                                    "flex-1 py-1 px-2 rounded-sm text-xs transition-all",
                                    amountType === 'usdt_total' ? "bg-background shadow-sm text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
                                )}
                                onClick={() => setAmountType('usdt_total')}
                            >
                                Total USDT
                            </button>
                            <button
                                type="button"
                                className={cn(
                                    "flex-1 py-1 px-2 rounded-sm text-xs transition-all",
                                    amountType === 'usdt_margin' ? "bg-background shadow-sm text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
                                )}
                                onClick={() => setAmountType('usdt_margin')}
                            >
                                Margem USDT
                            </button>
                        </div>
                        <div className="text-[10px] text-muted-foreground text-center h-4">
                            {amountType === 'quantity' && `Ex: 0.001 BTC`}
                            {amountType === 'usdt_total' && `Ex: $1000 (Posição Total)`}
                            {amountType === 'usdt_margin' && `Ex: $100 (Custo da Margem)`}
                        </div>
                    </div>

                    <Button type="submit" disabled={loading} className="w-full">
                        {loading ? 'Executando...' : '🚀 Executar Ordem'}
                    </Button>

                    {message && (
                        <div className={cn(
                            "p-3 rounded-md text-xs text-center font-medium",
                            message.type === 'success' ? "bg-green-500/15 text-green-500" : "bg-red-500/15 text-red-500"
                        )}>
                            {message.text}
                        </div>
                    )}
                </form>
            </CardContent>
        </Card>
    );
};
