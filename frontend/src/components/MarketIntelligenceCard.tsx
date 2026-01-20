import React, { useEffect, useState } from 'react';
import { BarChart3, TrendingUp, TrendingDown, DollarSign, Activity, RefreshCw, AlertCircle } from 'lucide-react';
import { getFundingSentiment, getOrderBookAnalysis, getPortfolioHeat, type FundingSentiment, type OrderBookAnalysis } from '../services/api';

interface Props {
  symbol?: string;
}

export const MarketIntelligenceCard: React.FC<Props> = ({ symbol = 'BTCUSDT' }) => {
  const [funding, setFunding] = useState<FundingSentiment | null>(null);
  const [orderbook, setOrderbook] = useState<OrderBookAnalysis | null>(null);
  const [portfolioHeat, setPortfolioHeat] = useState<{ total_risk_pct: number; risk_level: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState(symbol);

  const commonSymbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'];

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [fundingRes, orderbookRes, heatRes] = await Promise.all([
        getFundingSentiment(selectedSymbol).catch(() => null),
        getOrderBookAnalysis(selectedSymbol).catch(() => null),
        getPortfolioHeat().catch(() => null)
      ]);
      // Handle nested data format: { status: "success", data: {...} }
      const fundingData = fundingRes?.data || fundingRes;
      const orderbookData = orderbookRes?.data || orderbookRes;
      const heatData = heatRes?.data || heatRes;

      if (fundingData) {
        setFunding({
          symbol: fundingData.symbol,
          funding_rate: fundingData.funding_rate || 0,
          funding_rate_pct: (fundingData.funding_rate || 0) * 100,
          sentiment: fundingData.sentiment,
          sentiment_score: fundingData.sentiment_score || 0
        });
      }
      if (orderbookData) {
        setOrderbook({
          symbol: orderbookData.symbol,
          bid_liquidity_5pct: orderbookData.total_bid_volume || orderbookData.bid_liquidity_5pct,
          ask_liquidity_5pct: orderbookData.total_ask_volume || orderbookData.ask_liquidity_5pct,
          imbalance_pct: orderbookData.imbalance || orderbookData.imbalance_pct,
          dominant_side: orderbookData.bias || orderbookData.dominant_side,
          depth_score: orderbookData.depth_score,
          whale_walls: orderbookData.whale_bids || orderbookData.whale_walls
        });
      }
      if (heatData) {
        setPortfolioHeat({
          total_risk_pct: heatData.total_risk_pct || 0,
          risk_level: heatData.risk_level || 'UNKNOWN'
        });
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 30000); // Atualiza a cada 30s
    return () => clearInterval(timer);
  }, [selectedSymbol]);

  const getSentimentColor = (sentiment: string | undefined) => {
    if (!sentiment) return 'text-slate-500';
    if (sentiment === 'BULLISH' || sentiment === 'VERY_BULLISH') return 'text-green-600';
    if (sentiment === 'BEARISH' || sentiment === 'VERY_BEARISH') return 'text-red-600';
    return 'text-slate-600';
  };

  const getSentimentBg = (sentiment: string | undefined) => {
    if (!sentiment) return 'bg-slate-100';
    if (sentiment === 'BULLISH' || sentiment === 'VERY_BULLISH') return 'bg-green-100';
    if (sentiment === 'BEARISH' || sentiment === 'VERY_BEARISH') return 'bg-red-100';
    return 'bg-slate-100';
  };

  const getRiskColor = (level: string | undefined) => {
    if (!level) return 'text-slate-500';
    if (level === 'LOW') return 'text-green-600';
    if (level === 'MEDIUM') return 'text-yellow-600';
    if (level === 'HIGH' || level === 'CRITICAL') return 'text-red-600';
    return 'text-slate-600';
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-slate-200/50 bg-gradient-to-r from-blue-50/50 to-cyan-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Market Intelligence</h3>
              <p className="text-xs text-slate-500 font-medium">Sentiment & Order Flow</p>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-slate-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Symbol Selector */}
        <div className="flex gap-2 flex-wrap">
          {commonSymbols.map((sym) => (
            <button
              key={sym}
              onClick={() => setSelectedSymbol(sym)}
              className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                selectedSymbol === sym
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {sym.replace('USDT', '')}
            </button>
          ))}
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Funding Sentiment */}
        {funding && (
          <div className={`p-4 rounded-xl border ${getSentimentBg(funding.sentiment)}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-slate-600 uppercase">Funding & Sentiment</span>
              <div className={`flex items-center gap-1 ${getSentimentColor(funding.sentiment)}`}>
                {funding.sentiment?.includes('BULLISH') ? (
                  <TrendingUp className="w-4 h-4" />
                ) : funding.sentiment?.includes('BEARISH') ? (
                  <TrendingDown className="w-4 h-4" />
                ) : (
                  <Activity className="w-4 h-4" />
                )}
                <span className="text-sm font-bold">{funding.sentiment || 'NEUTRAL'}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500">Funding Rate</p>
                <p className={`text-lg font-bold ${(funding.funding_rate || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(funding.funding_rate_pct || 0).toFixed(4)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Sentiment Score</p>
                <p className={`text-lg font-bold ${getSentimentColor(funding.sentiment)}`}>
                  {(funding.sentiment_score || 0).toFixed(0)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Order Book Analysis */}
        {orderbook && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-slate-600 uppercase">Order Book</span>
              <span className={`text-sm font-bold ${
                orderbook.dominant_side === 'BID' ? 'text-green-600' :
                orderbook.dominant_side === 'ASK' ? 'text-red-600' : 'text-slate-600'
              }`}>
                {orderbook.dominant_side || 'NEUTRAL'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500">Bid Liquidity (5%)</p>
                <p className="text-lg font-bold text-green-600">
                  ${(orderbook.bid_liquidity_5pct || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Ask Liquidity (5%)</p>
                <p className="text-lg font-bold text-red-600">
                  ${(orderbook.ask_liquidity_5pct || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>
            {orderbook.imbalance_pct !== undefined && orderbook.imbalance_pct !== null && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-500">Imbalance</span>
                  <span className={`font-bold ${(orderbook.imbalance_pct || 0) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {(orderbook.imbalance_pct || 0) > 0 ? '+' : ''}{(orderbook.imbalance_pct || 0).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      (orderbook.imbalance_pct || 0) > 0 ? 'bg-green-500' : 'bg-red-500'
                    }`}
                    style={{
                      width: `${Math.min(100, Math.abs(orderbook.imbalance_pct || 0))}%`,
                      marginLeft: (orderbook.imbalance_pct || 0) > 0 ? '50%' : `${50 - Math.min(50, Math.abs(orderbook.imbalance_pct || 0))}%`
                    }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Portfolio Heat */}
        {portfolioHeat && (
          <div className="flex items-center justify-between p-3 bg-gradient-to-r from-slate-50 to-orange-50 rounded-lg border border-slate-200">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-orange-600" />
              <span className="text-sm font-medium text-slate-700">Portfolio Risk</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold ${getRiskColor(portfolioHeat.risk_level)}`}>
                {(portfolioHeat.total_risk_pct || 0).toFixed(1)}%
              </span>
              <span className={`text-xs px-2 py-1 rounded-lg font-bold ${
                portfolioHeat.risk_level === 'LOW' ? 'bg-green-100 text-green-700' :
                portfolioHeat.risk_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                {portfolioHeat.risk_level || 'UNKNOWN'}
              </span>
            </div>
          </div>
        )}

        {loading && !funding && !orderbook && (
          <div className="flex items-center justify-center p-8">
            <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketIntelligenceCard;
