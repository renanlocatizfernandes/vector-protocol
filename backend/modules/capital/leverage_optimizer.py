"""
Adaptive Leverage Optimizer
Selects optimal leverage per symbol based on multiple factors
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
import math

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("leverage_optimizer")


class AdaptiveLeverageOptimizer:
    """
    Adaptive Leverage Optimizer

    Determines optimal leverage based on:
    - Volatility (ATR)
    - Spread
    - Order book depth
    - Account size
    - Historical win rate
    - Market regime
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # 1 minute

        # Leverage constraints
        self.min_leverage = 3
        self.max_leverage = 20
        self.default_leverage = 10

        # Symbol-specific settings (can be overridden)
        self.symbol_max_leverage = {
            'BTCUSDT': 15,
            'ETHUSDT': 12,
            'BNBUSDT': 10,
        }

    async def calculate_optimal_leverage(
        self,
        symbol: str,
        account_balance: float,
        win_rate: Optional[float] = None,
        market_regime: Optional[str] = None
    ) -> Dict:
        """
        Calculate optimal leverage for symbol

        Args:
            symbol: Trading pair
            account_balance: Current account balance
            win_rate: Historical win rate (0-1), optional
            market_regime: Market regime (TRENDING, RANGING, etc), optional

        Returns:
            Optimal leverage recommendation
        """
        cache_key = f"{symbol}_leverage"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            logger.info(f"Calculating optimal leverage for {symbol}")

            # Get market data
            klines = await binance_client.futures_klines(
                symbol=symbol,
                interval='5m',
                limit=100
            )

            if not klines or len(klines) < 20:
                return self._default_leverage_result(symbol, "Insufficient data")

            # Calculate volatility (ATR)
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])

            atr = self._calculate_atr(highs, lows, closes, 14)
            atr_pct = (atr[-1] / closes[-1]) * 100

            # Get order book
            order_book = await binance_client.futures_order_book(symbol=symbol, limit=20)

            if not order_book:
                return self._default_leverage_result(symbol, "Order book unavailable")

            bids = [[float(p), float(q)] for p, q in order_book.get('bids', [])]
            asks = [[float(p), float(q)] for p, q in order_book.get('asks', [])]

            # Calculate spread
            if not bids or not asks:
                return self._default_leverage_result(symbol, "Empty order book")

            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread = best_ask - best_bid
            spread_bps = (spread / best_bid) * 10000

            # Calculate depth score
            depth_score = self._calculate_depth_score(bids, asks)

            # Calculate optimal leverage
            optimal_leverage = self._calculate_leverage_formula(
                volatility_pct=atr_pct,
                spread_bps=spread_bps,
                depth_score=depth_score,
                account_balance=account_balance,
                win_rate=win_rate,
                market_regime=market_regime,
                symbol=symbol
            )

            # Apply symbol-specific max
            symbol_max = self.symbol_max_leverage.get(symbol, self.max_leverage)
            optimal_leverage = min(optimal_leverage, symbol_max)

            # Generate recommendation
            recommendation = self._generate_recommendation(
                optimal_leverage,
                atr_pct,
                spread_bps,
                depth_score,
                symbol
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),

                # Recommended leverage
                'optimal_leverage': optimal_leverage,
                'min_leverage': self.min_leverage,
                'max_leverage': symbol_max,

                # Market factors
                'volatility_pct': round(atr_pct, 3),
                'spread_bps': round(spread_bps, 2),
                'depth_score': depth_score,

                # Account factors
                'account_balance': account_balance,
                'win_rate': win_rate,
                'market_regime': market_regime,

                # Recommendation
                'recommendation': recommendation,
                'confidence': self._calculate_confidence(atr_pct, depth_score)
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error calculating optimal leverage: {e}")
            return self._default_leverage_result(symbol, str(e))

    def _calculate_leverage_formula(
        self,
        volatility_pct: float,
        spread_bps: float,
        depth_score: int,
        account_balance: float,
        win_rate: Optional[float],
        market_regime: Optional[str],
        symbol: str
    ) -> int:
        """
        Calculate optimal leverage using multi-factor formula

        Formula:
        base_leverage = 10
        volatility_factor = 1.0 / (ATR_pct / 2.0)
        liquidity_factor = depth_score / 100
        account_size_factor = min(1.5, log10(capital) / 3)
        win_rate_factor = 1.0 + (win_rate - 0.5) if win_rate else 1.0
        regime_factor = regime multiplier

        optimal = base * volatility * liquidity / account_size * win_rate * regime
        """
        base_leverage = self.default_leverage

        # Volatility factor (higher volatility = lower leverage)
        # ATR 1% → factor 2.0, ATR 5% → factor 0.4
        volatility_factor = 1.0 / max(0.5, volatility_pct / 2.0)

        # Liquidity factor (better depth = can use more leverage)
        liquidity_factor = depth_score / 100.0

        # Account size factor (larger accounts = lower leverage)
        if account_balance > 0:
            account_size_factor = min(1.5, math.log10(account_balance) / 3.0)
        else:
            account_size_factor = 1.0

        # Win rate factor (better performance = can use more leverage)
        if win_rate is not None and win_rate > 0:
            # Win rate 60% → 1.2x, 50% → 1.0x, 40% → 0.8x
            win_rate_factor = 1.0 + (win_rate - 0.5) * 2.0
            win_rate_factor = max(0.5, min(1.5, win_rate_factor))
        else:
            win_rate_factor = 1.0

        # Market regime factor
        regime_factor = self._get_regime_factor(market_regime)

        # Spread penalty (wide spread = lower leverage)
        spread_penalty = 1.0 if spread_bps < 10 else (10.0 / spread_bps)

        # Calculate optimal leverage
        optimal = base_leverage * volatility_factor * liquidity_factor * win_rate_factor * regime_factor * spread_penalty
        optimal = optimal / account_size_factor

        # Clamp to min/max
        optimal = max(self.min_leverage, min(self.max_leverage, int(optimal)))

        return optimal

    def _get_regime_factor(self, regime: Optional[str]) -> float:
        """Get leverage multiplier for market regime"""

        if not regime:
            return 1.0

        regime_upper = regime.upper()

        if 'STRONG' in regime_upper and 'TREND' in regime_upper:
            return 1.3  # Strong trends can use more leverage
        elif 'TREND' in regime_upper:
            return 1.1
        elif 'RANGING' in regime_upper:
            return 0.8  # Ranging markets use less leverage
        elif 'VOLATILE' in regime_upper:
            return 0.6  # High volatility = much lower leverage
        else:
            return 1.0

    def _calculate_depth_score(self, bids: List[List[float]], asks: List[List[float]]) -> int:
        """
        Calculate order book depth score (0-100)

        Higher score = better liquidity
        """
        if not bids or not asks:
            return 0

        # Sum volume in first 5 levels
        bid_volume_5 = sum(qty for _, qty in bids[:5])
        ask_volume_5 = sum(qty for _, qty in asks[:5])

        # Total volume
        total_volume = bid_volume_5 + ask_volume_5

        # Scoring based on volume
        # This is simplified - adjust thresholds per symbol
        if total_volume > 100:
            score = 100
        elif total_volume > 50:
            score = 80
        elif total_volume > 20:
            score = 60
        elif total_volume > 10:
            score = 40
        else:
            score = 20

        return score

    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calculate Average True Range"""
        if len(highs) < 2:
            return np.full(len(highs), 0.0)

        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )

        # EMA of TR
        atr = self._ema(tr, period)

        # Pad to match original length
        result = np.zeros(len(highs))
        result[1:] = atr

        return result

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return np.full(len(data), np.mean(data) if len(data) > 0 else 0)

        multiplier = 2 / (period + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]

        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema

    def _generate_recommendation(
        self,
        leverage: int,
        volatility_pct: float,
        spread_bps: float,
        depth_score: int,
        symbol: str
    ) -> str:
        """Generate human-readable recommendation"""

        reasons = []

        # Volatility
        if volatility_pct > 4.0:
            reasons.append(f"High volatility ({volatility_pct:.2f}%) suggests conservative leverage")
        elif volatility_pct < 2.0:
            reasons.append(f"Low volatility ({volatility_pct:.2f}%) allows higher leverage")

        # Spread
        if spread_bps > 10:
            reasons.append(f"Wide spread ({spread_bps:.1f} bps) reduces optimal leverage")

        # Depth
        if depth_score < 50:
            reasons.append(f"Low liquidity (score: {depth_score}) limits leverage")
        elif depth_score > 80:
            reasons.append(f"High liquidity (score: {depth_score}) supports leverage")

        # Leverage assessment
        if leverage >= 15:
            assessment = "AGGRESSIVE"
        elif leverage >= 10:
            assessment = "MODERATE"
        elif leverage >= 5:
            assessment = "CONSERVATIVE"
        else:
            assessment = "VERY_CONSERVATIVE"

        summary = f"Optimal leverage: {leverage}x ({assessment})"

        if reasons:
            summary += ". " + "; ".join(reasons)

        return summary

    def _calculate_confidence(self, volatility_pct: float, depth_score: int) -> int:
        """Calculate confidence in leverage recommendation (0-100)"""

        confidence = 100

        # Reduce confidence for high volatility
        if volatility_pct > 5.0:
            confidence -= 30
        elif volatility_pct > 3.0:
            confidence -= 15

        # Reduce confidence for low liquidity
        if depth_score < 40:
            confidence -= 30
        elif depth_score < 60:
            confidence -= 15

        return max(0, confidence)

    def _default_leverage_result(self, symbol: str, reason: str) -> Dict:
        """Return default leverage when calculation fails"""

        logger.warning(f"Using default leverage for {symbol}: {reason}")

        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'optimal_leverage': self.default_leverage,
            'min_leverage': self.min_leverage,
            'max_leverage': self.max_leverage,
            'recommendation': f"Using default {self.default_leverage}x leverage ({reason})",
            'confidence': 30
        }

    async def get_leverage_recommendations_bulk(
        self,
        symbols: List[str],
        account_balance: float
    ) -> Dict:
        """
        Get leverage recommendations for multiple symbols

        Args:
            symbols: List of trading pairs
            account_balance: Current account balance

        Returns:
            Recommendations for all symbols
        """
        try:
            # Calculate in parallel
            tasks = [
                self.calculate_optimal_leverage(symbol, account_balance)
                for symbol in symbols
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Compile results
            recommendations = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    logger.error(f"Error for {symbol}: {result}")
                    recommendations[symbol] = self._default_leverage_result(symbol, str(result))
                else:
                    recommendations[symbol] = result

            return {
                'timestamp': datetime.now().isoformat(),
                'account_balance': account_balance,
                'num_symbols': len(symbols),
                'recommendations': recommendations
            }

        except Exception as e:
            logger.error(f"Error in bulk leverage calculation: {e}")
            return {}


# Singleton instance
leverage_optimizer = AdaptiveLeverageOptimizer()
