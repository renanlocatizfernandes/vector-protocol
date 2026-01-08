"""
Market Monitor - Phase 4
Monitors market conditions for health dashboard
"""
from typing import List, Dict, Optional
from datetime import datetime

from utils.binance_client import binance_client
from utils.logger import setup_logger

logger = setup_logger("market_monitor")


class MarketMonitor:
    """
    Monitors market-wide conditions.

    Features:
    - High funding rate detection
    - Trending symbols identification
    - Market volatility index calculation
    """

    def __init__(self):
        self.client = binance_client

    async def get_high_funding_symbols(
        self,
        threshold: float = 0.001
    ) -> List[Dict]:
        """
        Find symbols with extreme funding rates.

        Args:
            threshold: Absolute funding rate threshold (0.001 = 0.1%)

        Returns:
            List of symbols with high funding rates
        """
        try:
            # Get premium index (includes funding rate)
            premium_data = await self.client.get_premium_index()

            high_funding = []
            for data in premium_data:
                funding_rate = float(data.get('lastFundingRate', 0))

                if abs(funding_rate) > threshold:
                    high_funding.append({
                        "symbol": data['symbol'],
                        "funding_rate": funding_rate,
                        "funding_rate_pct": round(funding_rate * 100, 4),
                        "next_funding_time": data.get('nextFundingTime'),
                        "mark_price": float(data.get('markPrice', 0))
                    })

            # Sort by absolute funding rate (highest first)
            high_funding.sort(key=lambda x: abs(x['funding_rate']), reverse=True)

            logger.debug(f"Found {len(high_funding)} symbols with funding rate > {threshold}")
            return high_funding

        except Exception as e:
            logger.error(f"Error getting high funding symbols: {e}")
            return []

    async def get_trending_symbols(
        self,
        min_change_pct: float = 5.0,
        limit: int = 20
    ) -> List[Dict]:
        """
        Find symbols with strong price movement in last 24h.

        Args:
            min_change_pct: Minimum price change percentage
            limit: Maximum symbols to return

        Returns:
            List of trending symbols
        """
        try:
            # Get 24h ticker data
            tickers = await self.client.get_24h_ticker()

            trending = []
            for ticker in tickers:
                # Skip non-USDT pairs
                if not ticker['symbol'].endswith('USDT'):
                    continue

                change_pct = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('quoteVolume', 0))

                # Filter by change and minimum volume (1M USDT)
                if abs(change_pct) >= min_change_pct and volume > 1_000_000:
                    trending.append({
                        "symbol": ticker['symbol'],
                        "price_change_pct": round(change_pct, 2),
                        "volume": round(volume, 2),
                        "volume_usd": f"${volume/1_000_000:.1f}M",
                        "price": float(ticker.get('lastPrice', 0)),
                        "direction": "up" if change_pct > 0 else "down"
                    })

            # Sort by absolute change (highest first)
            trending.sort(key=lambda x: abs(x['price_change_pct']), reverse=True)

            logger.debug(f"Found {len(trending)} trending symbols")
            return trending[:limit]

        except Exception as e:
            logger.error(f"Error getting trending symbols: {e}")
            return []

    async def calculate_volatility_index(self) -> float:
        """
        Calculate market-wide volatility index (0-100).

        Uses standard deviation of 24h price changes.

        Returns:
            Volatility index (0 = calm, 100 = extreme volatility)
        """
        try:
            tickers = await self.client.get_24h_ticker()

            # Filter USDT pairs with sufficient volume
            changes = []
            for ticker in tickers:
                if not ticker['symbol'].endswith('USDT'):
                    continue

                volume = float(ticker.get('quoteVolume', 0))
                if volume < 1_000_000:  # Min 1M USDT volume
                    continue

                change_pct = abs(float(ticker.get('priceChangePercent', 0)))
                changes.append(change_pct)

            if not changes:
                return 0.0

            # Calculate mean and standard deviation
            mean = sum(changes) / len(changes)
            variance = sum((x - mean) ** 2 for x in changes) / len(changes)
            std_dev = variance ** 0.5

            # Normalize to 0-100 scale (assume max std dev = 20%)
            volatility_index = min(100, (std_dev / 20) * 100)

            logger.debug(f"Volatility index: {volatility_index:.2f} (std_dev={std_dev:.2f}%)")
            return round(volatility_index, 2)

        except Exception as e:
            logger.error(f"Error calculating volatility index: {e}")
            return 0.0

    async def get_market_conditions(self) -> Dict:
        """
        Get comprehensive market conditions summary.

        Returns:
            Dict with funding, trending, and volatility data
        """
        try:
            # Fetch all data concurrently would be ideal, but for simplicity we'll do sequential
            high_funding = await self.get_high_funding_symbols(threshold=0.001)
            trending = await self.get_trending_symbols(min_change_pct=5.0, limit=20)
            volatility = await self.calculate_volatility_index()

            return {
                "high_funding": high_funding[:10],  # Top 10
                "trending_symbols": trending,
                "volatility_index": volatility,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting market conditions: {e}")
            return {
                "high_funding": [],
                "trending_symbols": [],
                "volatility_index": 0.0,
                "timestamp": datetime.utcnow().isoformat()
            }


# Singleton instance
market_monitor = MarketMonitor()
