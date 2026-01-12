import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Zap, TrendingUp, TrendingDown, RefreshCw, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { http, getMarketTickers, type MarketTicker } from '../services/api';

type AmountType = 'quantity' | 'usdt_total' | 'usdt_margin';

export const ManualTrade: React.FC = () => {
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [direction, setDirection] = useState('LONG');
    const [amount, setAmount] = useState('0.001');
    const [amountType, setAmountType] = useState<AmountType>('quantity');
    const [leverage, setLeverage] = useState('10');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [tickers, setTickers] = useState<MarketTicker[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);

    useEffect(() => {
        fetchTickers();
        const interval = setInterval(fetchTickers, 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchTickers = async () => {
        try {
            const response = await getMarketTickers(100);
            // Ordenar por maior valor (volume * price)
            const sorted = response.tickers.sort((a, b) => {
                const aValue = a.last_price * a.quote_volume;
                const bValue = b.last_price * b.quote_volume;
                return bValue - aValue;
            });
            setTickers(sorted);
        } catch (error) {
            console.error('Erro ao carregar tickers:', error);
        }
    };

    const filteredTickers = tickers.filter(ticker => 
        ticker.symbol.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const selectedTicker = tickers.find(t => t.symbol === symbol);

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
        <Card className="relative overflow-hidden group h-full flex flex-col">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
                <Zap className="w-24 h-24 text-blue-600" />
            </div>

            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-slate-200/50">
                <CardTitle className="text-sm font-medium flex items-center gap-2 text-slate-900">
                    <Zap className="h-4 w-4 text-blue-600 animate-pulse" /> Trade Manual
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 pt-6">
                <form onSubmit={handleTrade} className="flex flex-col gap-4">
                    {/* Symbol com busca */}
                    <div className="space-y-2 relative">
                        <label className="text-xs font-bold text-slate-600 uppercase">Moeda</label>
                        <div className="relative">
                            <div className="flex items-center gap-2 p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-400 transition-colors cursor-pointer"
                                 onClick={() => setShowDropdown(!showDropdown)}>
                                <div className="flex-1">
                                    <span className="font-mono font-bold text-slate-900">{symbol}</span>
                                    {selectedTicker && (
                                        <span className="ml-2 text-xs font-medium text-slate-600">
                                            ${selectedTicker.last_price.toLocaleString()}
                                        </span>
                                    )}
                                </div>
                                <Search className="w-4 h-4 text-slate-400" />
                            </div>
                            
                            {showDropdown && (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl z-50 max-h-64 overflow-y-auto">
                                    <div className="p-2 border-b border-slate-100">
                                        <div className="flex items-center gap-2">
                                            <Search className="w-4 h-4 text-slate-400" />
                                            <Input
                                                type="text"
                                                placeholder="Buscar moeda..."
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                onClick={(e) => e.stopPropagation()}
                                                className="border-0 focus:ring-0 bg-slate-50"
                                            />
                                        </div>
                                    </div>
                                    <div className="max-h-48 overflow-y-auto">
                                        {filteredTickers.length === 0 ? (
                                            <div className="p-4 text-center text-sm text-slate-500">
                                                Nenhuma moeda encontrada
                                            </div>
                                        ) : (
                                            filteredTickers.map((ticker) => (
                                                <div
                                                    key={ticker.symbol}
                                                    className="flex items-center justify-between p-3 hover:bg-slate-50 cursor-pointer border-b border-slate-50 last:border-0"
                                                    onClick={() => {
                                                        setSymbol(ticker.symbol);
                                                        setShowDropdown(false);
                                                        setSearchQuery('');
                                                    }}
                                                >
                                                    <div>
                                                        <span className="font-mono font-bold text-slate-900">{ticker.symbol}</span>
                                                        <div className="text-xs text-slate-500 mt-0.5">
                                                            Vol: ${(ticker.quote_volume / 1000000).toFixed(1)}M
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="font-mono font-bold text-slate-900">
                                                            ${ticker.last_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                                                        </div>
                                                        <div className={cn(
                                                            "text-xs font-medium",
                                                            ticker.price_change_percent >= 0 ? "text-green-600" : "text-red-600"
                                                        )}>
                                                            {ticker.price_change_percent >= 0 ? '+' : ''}{ticker.price_change_percent.toFixed(2)}%
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-600 uppercase">Alavancagem</label>
                            <Input
                                type="number"
                                className="font-mono font-bold"
                                value={leverage}
                                onChange={(e) => setLeverage(e.target.value)}
                                min="1"
                                max="125"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-600 uppercase">Quantidade</label>
                            <Input
                                type="number"
                                className="font-mono font-bold"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                step="0.0001"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-600 uppercase">Direção</label>
                        <div className="flex gap-2">
                            <Button
                                type="button"
                                variant={direction === 'LONG' ? 'default' : 'outline'}
                                className={cn(
                                    "flex-1 transition-all duration-300 font-bold",
                                    direction === 'LONG'
                                        ? "bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-500/30"
                                        : "border-slate-200 hover:border-green-500 hover:text-green-600"
                                )}
                                onClick={() => setDirection('LONG')}
                            >
                                <TrendingUp className="mr-2 h-4 w-4" /> LONG
                            </Button>
                            <Button
                                type="button"
                                variant={direction === 'SHORT' ? 'default' : 'outline'}
                                className={cn(
                                    "flex-1 transition-all duration-300 font-bold",
                                    direction === 'SHORT'
                                        ? "bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-500/30"
                                        : "border-slate-200 hover:border-red-500 hover:text-red-600"
                                )}
                                onClick={() => setDirection('SHORT')}
                            >
                                <TrendingDown className="mr-2 h-4 w-4" /> SHORT
                            </Button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-600 uppercase">Tipo de Quantidade</label>
                        <div className="flex bg-slate-50 p-1 rounded-lg gap-1 border border-slate-200">
                            {[
                                { id: 'quantity', label: 'Moedas' },
                                { id: 'usdt_total', label: 'Total USDT' },
                                { id: 'usdt_margin', label: 'Margem USDT' }
                            ].map((type) => (
                                <button
                                    key={type.id}
                                    type="button"
                                    className={cn(
                                        "flex-1 py-2 px-2 rounded-md text-xs transition-all duration-300 font-medium",
                                        amountType === type.id
                                            ? "bg-white text-blue-600 shadow-sm border border-slate-200"
                                            : "text-slate-600 hover:bg-white"
                                    )}
                                    onClick={() => setAmountType(type.id as AmountType)}
                                >
                                    {type.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <Button 
                        type="submit" 
                        disabled={loading} 
                        className={cn(
                            "w-full relative overflow-hidden group font-bold text-sm py-6",
                            direction === 'LONG'
                                ? "bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                                : "bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700"
                        )}
                    >
                        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                        <span className="relative flex items-center justify-center gap-2">
                            {loading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                            {loading ? 'EXECUTANDO...' : 'EXECUTAR ORDEM'}
                        </span>
                    </Button>

                    {message && (
                        <div className={cn(
                            "p-3 rounded-lg text-xs text-center font-bold border",
                            message.type === 'success' 
                                ? "bg-green-50 text-green-700 border-green-200" 
                                : "bg-red-50 text-red-700 border-red-200"
                        )}>
                            {message.text}
                        </div>
                    )}
                </form>
            </CardContent>
        </Card>
    );
};
