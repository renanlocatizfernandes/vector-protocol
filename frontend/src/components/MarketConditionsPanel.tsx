import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface MarketConditions {
    high_funding: Array<{
        symbol: string;
        funding_rate: number;
        funding_rate_pct: number;
    }>;
    trending_symbols: Array<{
        symbol: string;
        price_change_pct: number;
        volume: number;
        direction: 'up' | 'down';
    }>;
    volatility_index: number;
}

export const MarketConditionsPanel: React.FC = () => {
    const [conditions, setConditions] = useState<MarketConditions | null>(null);

    useEffect(() => {
        // Mock data - will be replaced with real API calls in Phase 4
        const mockConditions: MarketConditions = {
            high_funding: [
                { symbol: 'BTCUSDT', funding_rate: 0.0012, funding_rate_pct: 0.12 },
                { symbol: 'ETHUSDT', funding_rate: -0.0008, funding_rate_pct: -0.08 }
            ],
            trending_symbols: [
                { symbol: 'SOLUSDT', price_change_pct: 8.5, volume: 1500000, direction: 'up' },
                { symbol: 'AVAXUSDT', price_change_pct: -5.2, volume: 800000, direction: 'down' }
            ],
            volatility_index: 42
        };

        setConditions(mockConditions);
    }, []);

    if (!conditions) return null;

    return (
        <Card className="glass-card border-white/10 bg-white/5">
            <CardHeader>
                <CardTitle className="text-lg font-semibold flex items-center gap-2 text-slate-900">
                    <TrendingUp className="h-5 w-5 text-warning" />
                    Market Conditions
                </CardTitle>
                <CardDescription className="text-slate-600">
                    Volatility Index:{' '}
                    <span className={cn(
                        "font-semibold",
                        conditions.volatility_index > 60 ? 'text-danger' : conditions.volatility_index > 40 ? 'text-warning' : 'text-success'
                    )}>
                        {conditions.volatility_index}
                    </span>
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    <div>
                        <h4 className="text-xs text-slate-600 font-semibold uppercase mb-2">High Funding Rates</h4>
                        {conditions.high_funding.length > 0 ? (
                            <div className="space-y-1">
                                {conditions.high_funding.map((item, idx) => (
                                    <div key={idx} className="flex justify-between items-center text-sm bg-white/5 p-2 rounded">
                                        <span className="font-mono text-slate-900">{item.symbol}</span>
                                        <span className={cn(
                                            "font-mono font-semibold",
                                            item.funding_rate_pct > 0 ? 'text-success' : 'text-danger'
                                        )}>
                                            {item.funding_rate_pct > 0 ? '+' : ''}{item.funding_rate_pct.toFixed(2)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-600">No extreme funding rates</p>
                        )}
                    </div>

                    <div>
                        <h4 className="text-xs text-slate-600 font-semibold uppercase mb-2">Trending Symbols</h4>
                        {conditions.trending_symbols.length > 0 ? (
                            <div className="space-y-1">
                                {conditions.trending_symbols.map((item, idx) => (
                                    <div key={idx} className="flex justify-between items-center text-sm bg-white/5 p-2 rounded">
                                        <div className="flex items-center gap-2">
                                            {item.direction === 'up' ? (
                                                <TrendingUp className="w-4 h-4 text-success" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-danger" />
                                            )}
                                            <span className="font-mono text-slate-900">{item.symbol}</span>
                                        </div>
                                        <span className={cn(
                                            "font-mono font-semibold",
                                            item.direction === 'up' ? 'text-success' : 'text-danger'
                                        )}>
                                            {item.price_change_pct > 0 ? '+' : ''}{item.price_change_pct.toFixed(1)}%
                                        </span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-600">No trending symbols</p>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};
