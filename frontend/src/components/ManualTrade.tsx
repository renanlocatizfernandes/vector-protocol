import React, { useState } from 'react';
import axios from 'axios';

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
        <div className="card">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="text-blue">⚡</span> Trade Manual
            </h2>

            <form onSubmit={handleTrade} className="flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="label">Símbolo</label>
                        <input
                            type="text"
                            className="input font-mono uppercase"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value)}
                            placeholder="BTCUSDT"
                            required
                        />
                    </div>
                    <div>
                        <label className="label">Alavancagem</label>
                        <input
                            type="number"
                            className="input"
                            value={leverage}
                            onChange={(e) => setLeverage(e.target.value)}
                            min="1"
                            max="125"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="label">Direção</label>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                className={`btn flex-1 ${direction === 'LONG' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setDirection('LONG')}
                                style={{ backgroundColor: direction === 'LONG' ? 'var(--accent-success)' : '', color: direction === 'LONG' ? '#202124' : '' }}
                            >
                                LONG
                            </button>
                            <button
                                type="button"
                                className={`btn flex-1 ${direction === 'SHORT' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setDirection('SHORT')}
                                style={{ backgroundColor: direction === 'SHORT' ? 'var(--accent-danger)' : '', color: direction === 'SHORT' ? '#202124' : '' }}
                            >
                                SHORT
                            </button>
                        </div>
                    </div>
                    <div>
                        <label className="label">Quantidade / Valor</label>
                        <input
                            type="number"
                            className="input"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            step="0.0001"
                            required
                        />
                    </div>
                </div>

                {/* Amount Type Selector */}
                <div>
                    <label className="label mb-2">Tipo de Valor</label>
                    <div className="flex bg-tertiary rounded p-1 gap-1">
                        <button
                            type="button"
                            className={`flex-1 py-1 px-2 rounded text-xs transition-colors ${amountType === 'quantity' ? 'bg-blue-600 text-white' : 'text-secondary hover:text-primary'}`}
                            onClick={() => setAmountType('quantity')}
                        >
                            Qtd (Moeda)
                        </button>
                        <button
                            type="button"
                            className={`flex-1 py-1 px-2 rounded text-xs transition-colors ${amountType === 'usdt_total' ? 'bg-blue-600 text-white' : 'text-secondary hover:text-primary'}`}
                            onClick={() => setAmountType('usdt_total')}
                        >
                            Total USDT
                        </button>
                        <button
                            type="button"
                            className={`flex-1 py-1 px-2 rounded text-xs transition-colors ${amountType === 'usdt_margin' ? 'bg-blue-600 text-white' : 'text-secondary hover:text-primary'}`}
                            onClick={() => setAmountType('usdt_margin')}
                        >
                            Margem USDT
                        </button>
                    </div>
                    <div className="text-xs text-secondary mt-1 text-center">
                        {amountType === 'quantity' && `Ex: 0.001 BTC`}
                        {amountType === 'usdt_total' && `Ex: $1000 (Posição Total)`}
                        {amountType === 'usdt_margin' && `Ex: $100 (Custo da Margem)`}
                    </div>
                </div>

                <button
                    type="submit"
                    className="btn btn-primary w-full mt-2"
                    disabled={loading}
                >
                    {loading ? 'Executando...' : '🚀 Executar Ordem'}
                </button>

                {message && (
                    <div className={`p-3 rounded text-sm ${message.type === 'success' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}`}>
                        {message.text}
                    </div>
                )}
            </form>
        </div>
    );
};
