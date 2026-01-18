"""
Funding Rate & Sentiment Engine
Analyzes funding rates, open interest, and long/short ratios for market sentiment
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("funding_sentiment")


class MarketSentiment(str, Enum):
    """Market sentiment states"""
    EXTREME_BULLISH = "extreme_bullish"      # Funding > 0.15%
    BULLISH = "bullish"                      # Funding 0.05-0.15%
    NEUTRAL = "neutral"                      # Funding -0.05 to 0.05%
    BEARISH = "bearish"                      # Funding -0.15 to -0.05%
    EXTREME_BEARISH = "extreme_bearish"      # Funding < -0.15%


class FundingSentimentEngine:
    """
    Analyzes market sentiment using:
    - Funding rates (cost to hold positions)
    - Open Interest (total contract value)
    - Long/Short ratio (positioning)
    - Top trader sentiment
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Get current funding rate for symbol

        Returns:
            Funding rate as percentage (e.g., 0.01 = 0.01%)
        """
        try:
            funding_info = await binance_client.futures_funding_rate(
                symbol=symbol,
                limit=1
            )

            if funding_info and len(funding_info) > 0:
                rate = float(funding_info[0].get('fundingRate', 0))
                return rate * 100  # Convert to percentage

            return None

        except Exception as e:
            logger.error(f"Error getting funding rate for {symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> Dict:
        """
        Get open interest data

        Returns:
            Dict with current OI, OI change %, and OI value
        """
        try:
            # Current OI
            oi = await binance_client.futures_open_interest(symbol=symbol)
            current_oi = float(oi.get('openInterest', 0))

            # Historical OI for change calculation
            oi_hist = await binance_client.futures_open_interest_hist(
                symbol=symbol,
                period='5m',
                limit=12  # Last hour
            )

            if len(oi_hist) >= 2:
                prev_oi = float(oi_hist[-2].get('sumOpenInterest', current_oi))
                oi_change_pct = ((current_oi - prev_oi) / prev_oi * 100) if prev_oi > 0 else 0
            else:
                oi_change_pct = 0

            # OI value in USD
            mark_price = await binance_client.futures_mark_price(symbol=symbol)
            current_price = float(mark_price.get('markPrice', 0))
            oi_value = current_oi * current_price

            return {
                'open_interest': current_oi,
                'oi_change_pct': oi_change_pct,
                'oi_value_usd': oi_value,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error getting open interest for {symbol}: {e}")
            return {'open_interest': 0, 'oi_change_pct': 0, 'oi_value_usd': 0}

    async def get_long_short_ratio(self, symbol: str) -> Dict:
        """
        Get long/short positioning ratios

        Returns:
            Dict with account ratio and top trader ratio
        """
        try:
            # Global long/short account ratio
            account_ratio = await binance_client.futures_global_long_short_ratio(
                symbol=symbol,
                period='5m',
                limit=1
            )

            # Top trader long/short ratio
            top_ratio = await binance_client.futures_top_long_short_account_ratio(
                symbol=symbol,
                period='5m',
                limit=1
            )

            if account_ratio and len(account_ratio) > 0:
                acc_long_short = float(account_ratio[0].get('longShortRatio', 1.0))
            else:
                acc_long_short = 1.0

            if top_ratio and len(top_ratio) > 0:
                top_long_short = float(top_ratio[0].get('longShortRatio', 1.0))
            else:
                top_long_short = 1.0

            return {
                'account_long_short_ratio': acc_long_short,
                'top_trader_long_short_ratio': top_long_short,
                'retail_bullish_pct': (acc_long_short / (acc_long_short + 1)) * 100,
                'pro_bullish_pct': (top_long_short / (top_long_short + 1)) * 100,
            }

        except Exception as e:
            logger.error(f"Error getting long/short ratio for {symbol}: {e}")
            return {
                'account_long_short_ratio': 1.0,
                'top_trader_long_short_ratio': 1.0,
                'retail_bullish_pct': 50.0,
                'pro_bullish_pct': 50.0
            }

    async def analyze_sentiment(self, symbol: str) -> Dict:
        """
        Complete sentiment analysis for symbol

        Returns:
            Comprehensive sentiment data with trading signals
        """
        cache_key = f"{symbol}_sentiment"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Gather all data in parallel
            funding_task = self.get_funding_rate(symbol)
            oi_task = self.get_open_interest(symbol)
            ratio_task = self.get_long_short_ratio(symbol)

            funding_rate, oi_data, ratio_data = await asyncio.gather(
                funding_task, oi_task, ratio_task
            )

            # Determine sentiment
            sentiment = self._calculate_sentiment(funding_rate)

            # Generate signals
            signals = self._generate_signals(
                funding_rate, oi_data, ratio_data, sentiment
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),

                # Funding
                'funding_rate': funding_rate,
                'funding_rate_annualized': funding_rate * 365 * 3 if funding_rate else 0,  # 3x/day

                # Open Interest
                **oi_data,

                # Positioning
                **ratio_data,

                # Sentiment
                'sentiment': sentiment.value,
                'sentiment_score': self._sentiment_to_score(sentiment),

                # Signals
                **signals
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return {}

    def _calculate_sentiment(self, funding_rate: Optional[float]) -> MarketSentiment:
        """Calculate market sentiment from funding rate"""
        if funding_rate is None:
            return MarketSentiment.NEUTRAL

        if funding_rate >= 0.15:
            return MarketSentiment.EXTREME_BULLISH
        elif funding_rate >= 0.05:
            return MarketSentiment.BULLISH
        elif funding_rate >= -0.05:
            return MarketSentiment.NEUTRAL
        elif funding_rate >= -0.15:
            return MarketSentiment.BEARISH
        else:
            return MarketSentiment.EXTREME_BEARISH

    def _sentiment_to_score(self, sentiment: MarketSentiment) -> int:
        """Convert sentiment to numerical score (-100 to +100)"""
        scores = {
            MarketSentiment.EXTREME_BEARISH: -100,
            MarketSentiment.BEARISH: -50,
            MarketSentiment.NEUTRAL: 0,
            MarketSentiment.BULLISH: 50,
            MarketSentiment.EXTREME_BULLISH: 100,
        }
        return scores.get(sentiment, 0)

    def _generate_signals(
        self,
        funding_rate: Optional[float],
        oi_data: Dict,
        ratio_data: Dict,
        sentiment: MarketSentiment
    ) -> Dict:
        """
        Generate trading signals from sentiment data

        Returns:
            Dict with bias, confidence, and reasoning
        """
        signals = {
            'bias': 'NEUTRAL',
            'confidence': 0,
            'reasoning': [],
            'contrarian_opportunity': False,
            'trend_confirmation': False
        }

        if funding_rate is None:
            return signals

        # CONTRARIAN SIGNALS (high funding = contrarian short opportunity)
        if sentiment == MarketSentiment.EXTREME_BULLISH:
            signals['bias'] = 'SHORT'
            signals['confidence'] = 70
            signals['reasoning'].append(f"Extreme bullish funding ({funding_rate:.3f}%) - overcrowded longs")
            signals['contrarian_opportunity'] = True

        elif sentiment == MarketSentiment.EXTREME_BEARISH:
            signals['bias'] = 'LONG'
            signals['confidence'] = 70
            signals['reasoning'].append(f"Extreme bearish funding ({funding_rate:.3f}%) - overcrowded shorts")
            signals['contrarian_opportunity'] = True

        # TREND CONFIRMATION (moderate funding + OI increase)
        elif sentiment == MarketSentiment.BULLISH:
            oi_change = oi_data.get('oi_change_pct', 0)

            if oi_change > 5:  # OI increasing
                signals['bias'] = 'LONG'
                signals['confidence'] = 60
                signals['reasoning'].append(f"Bullish funding + OI rising {oi_change:.1f}% - strong uptrend")
                signals['trend_confirmation'] = True
            else:
                signals['bias'] = 'NEUTRAL'
                signals['confidence'] = 30
                signals['reasoning'].append("Bullish funding but OI not confirming")

        elif sentiment == MarketSentiment.BEARISH:
            oi_change = oi_data.get('oi_change_pct', 0)

            if oi_change > 5:
                signals['bias'] = 'SHORT'
                signals['confidence'] = 60
                signals['reasoning'].append(f"Bearish funding + OI rising {oi_change:.1f}% - strong downtrend")
                signals['trend_confirmation'] = True
            else:
                signals['bias'] = 'NEUTRAL'
                signals['confidence'] = 30
                signals['reasoning'].append("Bearish funding but OI not confirming")

        # POSITIONING DIVERGENCE
        retail_bullish = ratio_data.get('retail_bullish_pct', 50)
        pro_bullish = ratio_data.get('pro_bullish_pct', 50)

        divergence = abs(retail_bullish - pro_bullish)

        if divergence > 20:  # Significant divergence
            if pro_bullish > retail_bullish:
                signals['reasoning'].append(f"Smart money bullish ({pro_bullish:.0f}% vs retail {retail_bullish:.0f}%)")
                if signals['bias'] == 'LONG':
                    signals['confidence'] += 10
            else:
                signals['reasoning'].append(f"Smart money bearish ({pro_bullish:.0f}% vs retail {retail_bullish:.0f}%)")
                if signals['bias'] == 'SHORT':
                    signals['confidence'] += 10

        # Cap confidence at 100
        signals['confidence'] = min(100, signals['confidence'])

        return signals

    async def get_funding_arbitrage_opportunities(self, min_funding: float = 0.1) -> List[Dict]:
        """
        Scan market for funding arbitrage opportunities

        Args:
            min_funding: Minimum funding rate to consider (%)

        Returns:
            List of symbols with high funding rates
        """
        try:
            # Get all futures symbols
            exchange_info = await binance_client.futures_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols']
                      if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT']

            opportunities = []

            # Check funding for each (limit to top volume pairs)
            for symbol in symbols[:50]:  # Top 50 by volume
                try:
                    sentiment = await self.analyze_sentiment(symbol)

                    funding_rate = sentiment.get('funding_rate', 0)

                    if abs(funding_rate) >= min_funding:
                        opportunities.append({
                            'symbol': symbol,
                            'funding_rate': funding_rate,
                            'funding_annualized': sentiment.get('funding_rate_annualized', 0),
                            'sentiment': sentiment.get('sentiment'),
                            'bias': sentiment.get('bias'),
                            'confidence': sentiment.get('confidence'),
                        })

                except Exception:
                    continue

            # Sort by absolute funding rate
            opportunities.sort(key=lambda x: abs(x['funding_rate']), reverse=True)

            logger.info(f"Found {len(opportunities)} funding arbitrage opportunities (>{min_funding}%)")

            return opportunities

        except Exception as e:
            logger.error(f"Error scanning for funding opportunities: {e}")
            return []


# Singleton instance
funding_sentiment_engine = FundingSentimentEngine()
