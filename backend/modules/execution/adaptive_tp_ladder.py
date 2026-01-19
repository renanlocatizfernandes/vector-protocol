"""
Adaptive Take Profit Ladder
Dynamically adjusts TP levels based on market conditions, volatility, and momentum
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("adaptive_tp_ladder")


class TakeProfitLevel:
    """Represents a single TP level in the ladder"""

    def __init__(
        self,
        level_num: int,
        price: float,
        quantity_pct: float,
        reasoning: str
    ):
        self.level_num = level_num
        self.price = price
        self.quantity_pct = quantity_pct
        self.reasoning = reasoning
        self.order_id = None
        self.status = 'PENDING'
        self.filled_qty = 0
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'level': self.level_num,
            'price': self.price,
            'quantity_pct': self.quantity_pct,
            'reasoning': self.reasoning,
            'order_id': self.order_id,
            'status': self.status,
            'filled_qty': self.filled_qty,
            'timestamp': self.timestamp.isoformat()
        }


class AdaptiveTakeProfitLadder:
    """
    Adaptive Take Profit Ladder System

    Features:
    - Dynamic TP levels based on ATR, volatility, momentum
    - Multi-tier ladder (partial exits)
    - Adapts to market regime (trending vs ranging)
    - Considers key support/resistance levels
    - Integrates with volume profile POC/HVN
    """

    def __init__(self):
        self.active_ladders = {}  # symbol -> ladder config

    async def calculate_tp_ladder(
        self,
        symbol: str,
        side: str,  # LONG or SHORT
        entry_price: float,
        quantity: float,
        leverage: int = 1,
        num_levels: int = 3,
        strategy: str = 'ADAPTIVE'  # ADAPTIVE, AGGRESSIVE, CONSERVATIVE
    ) -> Dict:
        """
        Calculate adaptive TP ladder

        Args:
            symbol: Trading pair
            side: LONG or SHORT
            entry_price: Entry price
            quantity: Total position quantity
            leverage: Position leverage
            num_levels: Number of TP levels
            strategy: Ladder strategy

        Returns:
            TP ladder configuration
        """
        try:
            logger.info(f"Calculating TP ladder for {side} {symbol} @ {entry_price}")

            # Get market data
            klines = await binance_client.futures_klines(
                symbol=symbol,
                interval='5m',
                limit=100
            )

            if not klines or len(klines) < 20:
                return self._default_ladder(entry_price, side, quantity, num_levels)

            # Extract OHLCV
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])

            # Calculate technical indicators
            atr = self._calculate_atr(highs, lows, closes, 14)
            volatility_pct = (atr[-1] / closes[-1]) * 100

            momentum = self._calculate_momentum(closes)
            trend_strength = self._calculate_trend_strength(closes)

            # Determine market regime
            if trend_strength > 0.7 and momentum > 0:
                regime = 'STRONG_TREND'
            elif trend_strength > 0.5:
                regime = 'TRENDING'
            else:
                regime = 'RANGING'

            logger.info(
                f"Market regime: {regime} (trend: {trend_strength:.2f}, momentum: {momentum:.2f}, vol: {volatility_pct:.2f}%)"
            )

            # Calculate TP levels based on regime and strategy
            tp_levels = self._calculate_dynamic_tp_levels(
                entry_price,
                side,
                atr[-1],
                volatility_pct,
                momentum,
                trend_strength,
                regime,
                num_levels,
                strategy
            )

            # Distribute quantity across levels
            quantity_distribution = self._calculate_quantity_distribution(
                num_levels, regime, strategy
            )

            # Create ladder
            ladder_levels = []
            for i, (price, reasoning) in enumerate(tp_levels):
                level = TakeProfitLevel(
                    level_num=i + 1,
                    price=price,
                    quantity_pct=quantity_distribution[i],
                    reasoning=reasoning
                )
                ladder_levels.append(level)

            # Risk/Reward calculation
            total_potential_profit_pct = self._calculate_expected_profit(
                entry_price, ladder_levels, side
            )

            result = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'quantity': quantity,
                'leverage': leverage,
                'strategy': strategy,
                'timestamp': datetime.now(),

                # Market analysis
                'market_regime': regime,
                'volatility_pct': round(volatility_pct, 2),
                'atr': round(atr[-1], 6),
                'momentum': round(momentum, 2),
                'trend_strength': round(trend_strength, 2),

                # TP Ladder
                'num_levels': num_levels,
                'tp_levels': [level.to_dict() for level in ladder_levels],

                # Metrics
                'expected_profit_pct': round(total_potential_profit_pct, 2),
                'risk_reward_ratio': round(total_potential_profit_pct / 2, 2)  # Assuming 2% stop
            }

            # Store active ladder
            self.active_ladders[symbol] = result

            return result

        except Exception as e:
            logger.error(f"Error calculating TP ladder: {e}")
            return self._default_ladder(entry_price, side, quantity, num_levels)

    def _calculate_dynamic_tp_levels(
        self,
        entry_price: float,
        side: str,
        atr: float,
        volatility_pct: float,
        momentum: float,
        trend_strength: float,
        regime: str,
        num_levels: int,
        strategy: str
    ) -> List[Tuple[float, str]]:
        """
        Calculate dynamic TP prices based on market conditions

        Returns:
            List of (price, reasoning) tuples
        """
        tp_levels = []

        # Base multipliers for TP levels
        if regime == 'STRONG_TREND':
            # Wide targets in strong trends
            base_multipliers = [2.0, 4.0, 7.0, 12.0][:num_levels]
        elif regime == 'TRENDING':
            # Moderate targets in trends
            base_multipliers = [1.5, 3.0, 5.0, 8.0][:num_levels]
        else:
            # Tight targets in ranging market
            base_multipliers = [1.0, 2.0, 3.5, 5.0][:num_levels]

        # Adjust for strategy
        if strategy == 'AGGRESSIVE':
            base_multipliers = [m * 1.3 for m in base_multipliers]
        elif strategy == 'CONSERVATIVE':
            base_multipliers = [m * 0.7 for m in base_multipliers]

        # Calculate TP prices
        for i, multiplier in enumerate(base_multipliers):
            # TP distance = ATR * multiplier
            tp_distance = atr * multiplier

            if side == 'LONG':
                tp_price = entry_price + tp_distance
                reasoning = f"TP{i+1}: +{multiplier}x ATR ({regime})"
            else:  # SHORT
                tp_price = entry_price - tp_distance
                reasoning = f"TP{i+1}: -{multiplier}x ATR ({regime})"

            tp_levels.append((tp_price, reasoning))

        return tp_levels

    def _calculate_quantity_distribution(
        self,
        num_levels: int,
        regime: str,
        strategy: str
    ) -> List[float]:
        """
        Calculate how to distribute quantity across TP levels

        Returns:
            List of percentages (must sum to 100)
        """
        if num_levels == 1:
            return [100.0]

        elif num_levels == 2:
            if regime == 'RANGING':
                return [60.0, 40.0]  # Take more profit early
            else:
                return [40.0, 60.0]  # Let more run in trends

        elif num_levels == 3:
            if regime == 'STRONG_TREND':
                # Let winners run
                return [20.0, 30.0, 50.0]
            elif regime == 'TRENDING':
                return [25.0, 35.0, 40.0]
            else:
                # Take profit quickly in range
                return [40.0, 35.0, 25.0]

        elif num_levels >= 4:
            if regime == 'STRONG_TREND':
                return [15.0, 20.0, 30.0, 35.0]
            elif regime == 'TRENDING':
                return [20.0, 25.0, 30.0, 25.0]
            else:
                return [35.0, 30.0, 20.0, 15.0]

        else:
            # Equal distribution fallback
            pct = 100.0 / num_levels
            return [pct] * num_levels

    def _calculate_expected_profit(
        self,
        entry_price: float,
        ladder_levels: List[TakeProfitLevel],
        side: str
    ) -> float:
        """
        Calculate expected profit % from ladder

        Weighted average of all TP levels

        Returns:
            Expected profit percentage
        """
        total_weighted_profit = 0

        for level in ladder_levels:
            if side == 'LONG':
                profit_pct = (level.price - entry_price) / entry_price * 100
            else:
                profit_pct = (entry_price - level.price) / entry_price * 100

            weighted_profit = profit_pct * (level.quantity_pct / 100)
            total_weighted_profit += weighted_profit

        return total_weighted_profit

    def _default_ladder(
        self,
        entry_price: float,
        side: str,
        quantity: float,
        num_levels: int
    ) -> Dict:
        """Generate default ladder when analysis fails"""

        logger.warning("Using default TP ladder (analysis failed)")

        # Simple 2% intervals
        tp_levels = []
        qty_distribution = [100.0 / num_levels] * num_levels

        for i in range(num_levels):
            multiplier = (i + 1) * 2  # 2%, 4%, 6%, etc.

            if side == 'LONG':
                tp_price = entry_price * (1 + multiplier / 100)
            else:
                tp_price = entry_price * (1 - multiplier / 100)

            level = TakeProfitLevel(
                level_num=i + 1,
                price=tp_price,
                quantity_pct=qty_distribution[i],
                reasoning=f"Default TP{i+1} (+{multiplier}%)"
            )
            tp_levels.append(level)

        return {
            'symbol': 'UNKNOWN',
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'strategy': 'DEFAULT',
            'market_regime': 'UNKNOWN',
            'tp_levels': [level.to_dict() for level in tp_levels]
        }

    async def place_tp_orders(
        self,
        symbol: str,
        ladder_config: Dict,
        dry_run: bool = False
    ) -> Dict:
        """
        Place TP limit orders for ladder

        Args:
            symbol: Trading pair
            ladder_config: Ladder configuration from calculate_tp_ladder
            dry_run: If True, simulate only

        Returns:
            Placement results
        """
        try:
            side = ladder_config['side']
            quantity = ladder_config['quantity']
            tp_levels = ladder_config['tp_levels']

            # Determine order side (opposite of position)
            order_side = 'SELL' if side == 'LONG' else 'BUY'

            placement_results = []

            for level_data in tp_levels:
                level_num = level_data['level']
                tp_price = level_data['price']
                qty_pct = level_data['quantity_pct']

                # Calculate quantity for this level
                level_qty = quantity * (qty_pct / 100)

                if dry_run:
                    logger.info(
                        f"[DRY RUN] TP{level_num}: {order_side} {level_qty} @ {tp_price} ({qty_pct}%)"
                    )
                    result = {
                        'level': level_num,
                        'status': 'SIMULATED',
                        'price': tp_price,
                        'quantity': level_qty
                    }
                else:
                    try:
                        order = await binance_client.futures_create_order(
                            symbol=symbol,
                            side=order_side,
                            type='LIMIT',
                            quantity=level_qty,
                            price=tp_price,
                            timeInForce='GTC',
                            reduceOnly=True
                        )

                        logger.info(
                            f"TP{level_num} placed: {order_side} {level_qty} @ {tp_price} (orderId: {order.get('orderId')})"
                        )

                        result = {
                            'level': level_num,
                            'status': 'PLACED',
                            'order_id': order.get('orderId'),
                            'price': tp_price,
                            'quantity': level_qty
                        }

                    except Exception as e:
                        logger.error(f"Error placing TP{level_num}: {e}")
                        result = {
                            'level': level_num,
                            'status': 'FAILED',
                            'error': str(e)
                        }

                placement_results.append(result)

            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'dry_run': dry_run,
                'total_levels': len(tp_levels),
                'results': placement_results
            }

        except Exception as e:
            logger.error(f"Error placing TP orders: {e}")
            return {'error': str(e)}

    async def adjust_active_ladder(
        self,
        symbol: str,
        new_market_conditions: Optional[Dict] = None
    ) -> Dict:
        """
        Adjust active TP ladder based on changing market conditions

        Args:
            symbol: Trading pair
            new_market_conditions: Optional new conditions (will fetch if None)

        Returns:
            Adjustment results
        """
        try:
            if symbol not in self.active_ladders:
                return {'error': f'No active ladder for {symbol}'}

            current_ladder = self.active_ladders[symbol]

            # Recalculate ladder with updated conditions
            new_ladder = await self.calculate_tp_ladder(
                symbol=symbol,
                side=current_ladder['side'],
                entry_price=current_ladder['entry_price'],
                quantity=current_ladder['quantity'],
                leverage=current_ladder.get('leverage', 1),
                num_levels=current_ladder['num_levels'],
                strategy=current_ladder['strategy']
            )

            # Compare and determine if adjustment needed
            adjustments_needed = []

            for i, (current_level, new_level) in enumerate(
                zip(current_ladder['tp_levels'], new_ladder['tp_levels'])
            ):
                price_change_pct = abs(
                    (new_level['price'] - current_level['price']) / current_level['price'] * 100
                )

                # If price changed by more than 1%, consider adjustment
                if price_change_pct > 1.0:
                    adjustments_needed.append({
                        'level': i + 1,
                        'old_price': current_level['price'],
                        'new_price': new_level['price'],
                        'change_pct': round(price_change_pct, 2)
                    })

            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'adjustment_required': len(adjustments_needed) > 0,
                'adjustments': adjustments_needed,
                'new_ladder': new_ladder
            }

        except Exception as e:
            logger.error(f"Error adjusting ladder: {e}")
            return {'error': str(e)}

    # Technical indicator helper functions

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

    def _calculate_momentum(self, closes: np.ndarray, period: int = 20) -> float:
        """Calculate price momentum (-1 to +1)"""
        if len(closes) < period:
            return 0.0

        price_change = closes[-1] - closes[-period]
        price_change_pct = price_change / closes[-period] * 100 if closes[-period] > 0 else 0

        # Normalize to -1 to +1 (assuming typical move is ±5%)
        momentum = np.clip(price_change_pct / 5.0, -1.0, 1.0)

        return momentum

    def _calculate_trend_strength(self, closes: np.ndarray, period: int = 20) -> float:
        """Calculate trend strength (0 to 1)"""
        if len(closes) < period:
            return 0.5

        # Calculate R-squared of linear regression
        x = np.arange(period)
        y = closes[-period:]

        # Linear regression
        coefficients = np.polyfit(x, y, 1)
        y_pred = np.polyval(coefficients, x)

        # R-squared
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return max(0, min(1, r_squared))


# Singleton instance
adaptive_tp_ladder = AdaptiveTakeProfitLadder()
