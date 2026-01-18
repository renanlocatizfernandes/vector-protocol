"""
Market Intelligence Module
Advanced market analysis using Binance API data
"""

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

__all__ = [
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
