"""
Market Intelligence Module
Advanced market analysis using Binance API data
"""

from typing import Dict, Optional
from utils.logger import setup_logger

from modules.market_intelligence.funding_sentiment import (
    funding_sentiment_engine,
    FundingSentimentEngine,
    MarketSentiment
)
from modules.market_intelligence.orderbook_analyzer import (
    orderbook_analyzer,
    OrderBookAnalyzer,
    OrderBookLevel
)
from modules.market_intelligence.liquidation_heatmap import (
    liquidation_heatmap,
    LiquidationHeatmap,
    LiquidationZone
)
from modules.market_intelligence.mtf_confluence import (
    mtf_confluence,
    MultiTimeframeConfluence,
    TimeframeSignal
)
from modules.market_intelligence.correlation_matrix import (
    correlation_matrix,
    CorrelationMatrix,
    PairOpportunity
)
from modules.market_intelligence.volume_profile import (
    volume_profile,
    VolumeProfile,
    VolumeNode
)

logger = setup_logger("market_intelligence")


class MarketIntelligence:
    """
    Facade class that aggregates all market intelligence components.
    Provides unified interface for autonomous_bot and other modules.
    """

    async def get_market_sentiment_score(self, symbol: str) -> Dict:
        """
        Get market sentiment score for a symbol.

        Returns:
            Dict with sentiment_score (-100 to 100)
        """
        try:
            analysis = await funding_sentiment_engine.analyze_sentiment(symbol)

            # Convert sentiment enum to numeric score
            sentiment_map = {
                MarketSentiment.EXTREME_BULLISH: 80,
                MarketSentiment.BULLISH: 40,
                MarketSentiment.NEUTRAL: 0,
                MarketSentiment.BEARISH: -40,
                MarketSentiment.EXTREME_BEARISH: -80,
            }

            sentiment = analysis.get('overall_sentiment', MarketSentiment.NEUTRAL)
            if isinstance(sentiment, str):
                sentiment = MarketSentiment(sentiment) if sentiment in [s.value for s in MarketSentiment] else MarketSentiment.NEUTRAL

            score = sentiment_map.get(sentiment, 0)

            # Adjust score based on funding rate
            funding_rate = analysis.get('funding_rate', 0) or 0
            score += int(funding_rate * 100)  # funding_rate is already in %

            # Clamp to -100 to 100
            score = max(-100, min(100, score))

            return {
                'sentiment_score': score,
                'sentiment': sentiment.value if hasattr(sentiment, 'value') else str(sentiment),
                'funding_rate': funding_rate,
                'symbol': symbol
            }

        except Exception as e:
            logger.debug(f"Error getting sentiment for {symbol}: {e}")
            return {'sentiment_score': 0, 'symbol': symbol}

    async def get_order_book_depth(self, symbol: str) -> Optional[Dict]:
        """
        Get order book depth analysis for a symbol.

        Returns:
            Dict with bid_liquidity_5pct, ask_liquidity_5pct (in USDT)
        """
        try:
            analysis = await orderbook_analyzer.analyze_order_book(symbol)

            if not analysis:
                return None

            # Calculate liquidity in USDT terms
            current_price = analysis.get('current_price', 1)
            bid_volume = analysis.get('total_bid_volume', 0)
            ask_volume = analysis.get('total_ask_volume', 0)

            # Convert to USDT value
            bid_liquidity = bid_volume * current_price
            ask_liquidity = ask_volume * current_price

            return {
                'bid_liquidity_5pct': bid_liquidity,
                'ask_liquidity_5pct': ask_liquidity,
                'imbalance': analysis.get('imbalance_pct', 0),
                'whale_walls': analysis.get('whale_bids', []) + analysis.get('whale_asks', []),
                'depth_score': analysis.get('depth_score', 0),
                'symbol': symbol
            }

        except Exception as e:
            logger.debug(f"Error getting order book depth for {symbol}: {e}")
            return None


# Singleton instance
market_intelligence = MarketIntelligence()


__all__ = [
    # Main facade
    'market_intelligence',
    'MarketIntelligence',

    # Funding & Sentiment
    'funding_sentiment_engine',
    'FundingSentimentEngine',
    'MarketSentiment',

    # Order Book
    'orderbook_analyzer',
    'OrderBookAnalyzer',
    'OrderBookLevel',

    # Liquidations
    'liquidation_heatmap',
    'LiquidationHeatmap',
    'LiquidationZone',

    # MTF Confluence
    'mtf_confluence',
    'MultiTimeframeConfluence',
    'TimeframeSignal',

    # Correlation
    'correlation_matrix',
    'CorrelationMatrix',
    'PairOpportunity',

    # Volume Profile
    'volume_profile',
    'VolumeProfile',
    'VolumeNode',
]
