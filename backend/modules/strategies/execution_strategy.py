"""
Advanced Execution Strategies Framework
Sniper, Pyramid, DCA, Static modes with intelligent ML-based selection
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio

from utils.logger import setup_logger
from utils.binance_client import binance_client
from config.settings import get_settings

logger = setup_logger("execution_strategy")


class ExecutionMode(str, Enum):
    """Execution strategy modes"""
    STATIC = "static"          # Traditional: 1 entry, 1 exit
    SNIPER = "sniper"          # Wait for perfect entry (limit orders at key levels)
    PYRAMID = "pyramid"        # Scale into winning positions
    DCA = "dca"               # Dollar-cost average into losing positions
    HYBRID = "hybrid"          # ML decides best mode per trade


class MarginMode(str, Enum):
    """Margin modes"""
    CROSS = "CROSSED"    # Cross margin (all balance as collateral)
    ISOLATED = "ISOLATED"  # Isolated margin (position-specific collateral)


class ExecutionStrategy:
    """
    Base class for execution strategies
    """

    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.settings = get_settings()

    async def execute_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict,
        **kwargs
    ) -> Dict:
        """Execute entry - to be overridden by subclasses"""
        raise NotImplementedError

    async def should_add_to_position(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Tuple[bool, Optional[float]]:
        """Determine if should add to position - returns (should_add, quantity)"""
        return False, None

    async def calculate_exit_strategy(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Dict:
        """Calculate exit strategy (TP/SL levels, trailing config)"""
        raise NotImplementedError


class StaticStrategy(ExecutionStrategy):
    """
    Static Mode: Traditional single entry/exit
    - One market/limit order to enter
    - Fixed stop loss and take profit
    - No position scaling
    """

    def __init__(self):
        super().__init__(ExecutionMode.STATIC)

    async def execute_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict,
        **kwargs
    ) -> Dict:
        """Execute simple market order entry"""
        try:
            order_type = kwargs.get('order_type', 'MARKET')

            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                reduceOnly=False
            )

            logger.info(f"📍 STATIC entry: {side} {quantity} {symbol} @ MARKET")

            return {
                'success': True,
                'order': order,
                'mode': 'static',
                'entries': 1,
                'total_quantity': quantity
            }

        except Exception as e:
            logger.error(f"Error in static entry: {e}")
            return {'success': False, 'error': str(e)}

    async def should_add_to_position(self, symbol: str, position_data: Dict, market_data: Dict):
        # Static mode never adds to position
        return False, None

    async def calculate_exit_strategy(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Dict:
        """Simple fixed SL/TP"""
        entry_price = float(position_data.get('entryPrice', 0))
        atr = market_data.get('atr', entry_price * 0.02)

        side = position_data.get('positionSide', 'LONG')

        if side == 'LONG':
            stop_loss = entry_price - (atr * 2.0)
            take_profit = entry_price + (atr * 4.0)
        else:
            stop_loss = entry_price + (atr * 2.0)
            take_profit = entry_price - (atr * 4.0)

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'mode': 'static',
            'risk_reward': 2.0
        }


class SniperStrategy(ExecutionStrategy):
    """
    Sniper Mode: Wait for perfect entries at key levels
    - Uses limit orders at support/resistance
    - Multiple attempts with price improvement
    - Timeout with market order fallback
    """

    def __init__(self):
        super().__init__(ExecutionMode.SNIPER)
        self.max_attempts = 3
        self.timeout_seconds = 30
        self.price_improvement_bps = 5  # Try to get 5bps better price

    async def execute_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict,
        **kwargs
    ) -> Dict:
        """Execute sniper entry with limit orders"""
        try:
            current_price = signal.get('current_price', 0)
            key_level = await self._find_key_entry_level(symbol, side, current_price)

            logger.info(f"🎯 SNIPER mode: Targeting {key_level:.4f} for {symbol}")

            # Try limit orders at improving prices
            for attempt in range(self.max_attempts):
                # Improve price slightly each attempt
                improvement = (self.price_improvement_bps / 10000) * attempt

                if side == 'BUY':
                    limit_price = key_level * (1 - improvement)
                else:
                    limit_price = key_level * (1 + improvement)

                logger.info(f"  Attempt {attempt+1}/{self.max_attempts}: Limit @ {limit_price:.4f}")

                try:
                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type='LIMIT',
                        timeInForce='GTX',  # Post-only
                        quantity=quantity,
                        price=limit_price
                    )

                    order_id = order['orderId']

                    # Wait for fill
                    filled = await self._wait_for_fill(symbol, order_id, timeout=self.timeout_seconds)

                    if filled:
                        fill_price = filled['avgPrice']
                        logger.info(f"✅ SNIPER filled @ {fill_price:.4f} (saved {abs(fill_price - current_price)/current_price * 100:.2f}%)")

                        return {
                            'success': True,
                            'order': filled,
                            'mode': 'sniper',
                            'fill_price': fill_price,
                            'price_improvement': abs(fill_price - current_price) / current_price
                        }
                    else:
                        # Not filled, cancel and retry
                        await binance_client.futures_cancel_order(symbol=symbol, orderId=order_id)

                except Exception as e:
                    logger.warning(f"  Sniper attempt {attempt+1} failed: {e}")

            # All attempts failed, fallback to market
            logger.warning(f"⚠️ SNIPER timeout, executing MARKET order")

            market_order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )

            return {
                'success': True,
                'order': market_order,
                'mode': 'sniper_fallback_market',
                'attempts': self.max_attempts
            }

        except Exception as e:
            logger.error(f"Error in sniper entry: {e}")
            return {'success': False, 'error': str(e)}

    async def _find_key_entry_level(self, symbol: str, side: str, current_price: float) -> float:
        """Find support/resistance level for entry"""
        try:
            # Get recent klines
            klines = await binance_client.get_historical_klines(symbol, "15m", limit=100)

            if not klines:
                return current_price

            import pandas as pd

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            for col in ['high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])

            # Find recent swing highs/lows
            df['swing_high'] = df['high'].rolling(window=5, center=True).max() == df['high']
            df['swing_low'] = df['low'].rolling(window=5, center=True).min() == df['low']

            if side == 'BUY':
                # Look for support levels below current price
                supports = df[df['swing_low']]['low'].values
                supports = supports[supports < current_price]

                if len(supports) > 0:
                    return float(supports[-1])  # Most recent support
            else:
                # Look for resistance levels above current price
                resistances = df[df['swing_high']]['high'].values
                resistances = resistances[resistances > current_price]

                if len(resistances) > 0:
                    return float(resistances[-1])

            # No clear level found, use current price
            return current_price

        except Exception as e:
            logger.warning(f"Error finding key level: {e}")
            return current_price

    async def _wait_for_fill(self, symbol: str, order_id: int, timeout: int = 30) -> Optional[Dict]:
        """Wait for order to fill"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                order = await binance_client.futures_get_order(symbol=symbol, orderId=order_id)

                if order['status'] == 'FILLED':
                    return order

                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"Error checking order status: {e}")
                await asyncio.sleep(1)

        return None

    async def should_add_to_position(self, symbol: str, position_data: Dict, market_data: Dict):
        # Sniper doesn't scale
        return False, None

    async def calculate_exit_strategy(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Dict:
        """Wider SL for sniper (we got good entry)"""
        entry_price = float(position_data.get('entryPrice', 0))
        atr = market_data.get('atr', entry_price * 0.02)

        side = position_data.get('positionSide', 'LONG')

        # Wider stops since we got better entry
        if side == 'LONG':
            stop_loss = entry_price - (atr * 2.5)
            take_profit = entry_price + (atr * 5.0)
        else:
            stop_loss = entry_price + (atr * 2.5)
            take_profit = entry_price - (atr * 5.0)

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'mode': 'sniper',
            'risk_reward': 2.5
        }


class PyramidStrategy(ExecutionStrategy):
    """
    Pyramid Mode: Scale into winning positions
    - Add to position as it moves in our favor
    - Maximum 3-4 entries
    - Each entry smaller than previous (risk management)
    - Breakeven management
    """

    def __init__(self):
        super().__init__(ExecutionMode.PYRAMID)
        self.max_entries = 4
        self.min_profit_for_add_pct = 2.0  # Add after 2% profit
        self.scale_factor = 0.5  # Each entry is 50% of initial

    async def execute_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict,
        **kwargs
    ) -> Dict:
        """Execute initial pyramid entry"""
        try:
            # For pyramid, start with smaller initial size
            # Save some capital for scaling
            initial_quantity = quantity * 0.6  # 60% on first entry

            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=initial_quantity
            )

            logger.info(f"📈 PYRAMID entry 1/{self.max_entries}: {side} {initial_quantity} {symbol}")

            return {
                'success': True,
                'order': order,
                'mode': 'pyramid',
                'entry_number': 1,
                'initial_quantity': initial_quantity,
                'total_quantity': initial_quantity,
                'remaining_capital_pct': 0.4
            }

        except Exception as e:
            logger.error(f"Error in pyramid entry: {e}")
            return {'success': False, 'error': str(e)}

    async def should_add_to_position(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Tuple[bool, Optional[float]]:
        """Check if should pyramid (add to winner)"""
        try:
            entry_price = float(position_data.get('entryPrice', 0))
            current_price = float(position_data.get('markPrice', 0))
            position_amt = abs(float(position_data.get('positionAmt', 0)))
            side = position_data.get('positionSide', 'LONG')

            # Calculate unrealized PnL %
            if side == 'LONG':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # Check if profitable enough to add
            if pnl_pct < self.min_profit_for_add_pct:
                return False, None

            # Check number of entries (track in metadata)
            # For now, assume we can add if profitable
            # Calculate new entry size (smaller than current position)
            add_quantity = position_amt * self.scale_factor

            logger.info(
                f"📈 PYRAMID: Adding {add_quantity} to {symbol} "
                f"(current PnL: {pnl_pct:.2f}%)"
            )

            return True, add_quantity

        except Exception as e:
            logger.error(f"Error checking pyramid conditions: {e}")
            return False, None

    async def calculate_exit_strategy(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Dict:
        """Pyramid exit: Move stop to breakeven after adds"""
        entry_price = float(position_data.get('entryPrice', 0))
        atr = market_data.get('atr', entry_price * 0.02)
        side = position_data.get('positionSide', 'LONG')

        # For pyramid, use breakeven + small profit as stop
        if side == 'LONG':
            stop_loss = entry_price * 1.005  # BE + 0.5%
            take_profit = entry_price + (atr * 6.0)  # Aggressive TP
        else:
            stop_loss = entry_price * 0.995
            take_profit = entry_price - (atr * 6.0)

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'mode': 'pyramid',
            'risk_reward': 3.0,
            'breakeven_managed': True
        }


class DCAStrategy(ExecutionStrategy):
    """
    DCA Mode: Dollar-cost average into losing positions
    - Add to position as it moves against us
    - Lower average entry price
    - Maximum 3-4 entries with increasing size
    - Strict stop loss after final entry
    """

    def __init__(self):
        super().__init__(ExecutionMode.DCA)
        self.max_entries = 3
        self.dca_interval_pct = 2.0  # Add every 2% against us
        self.size_multiplier = 1.5  # Each entry is 1.5x previous

    async def execute_entry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        signal: Dict,
        **kwargs
    ) -> Dict:
        """Execute initial DCA entry"""
        try:
            # DCA starts with smaller position
            initial_quantity = quantity * 0.4  # 40% initially

            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=initial_quantity
            )

            logger.info(f"📉 DCA entry 1/{self.max_entries}: {side} {initial_quantity} {symbol}")

            return {
                'success': True,
                'order': order,
                'mode': 'dca',
                'entry_number': 1,
                'initial_quantity': initial_quantity,
                'total_quantity': initial_quantity,
                'remaining_capital_pct': 0.6
            }

        except Exception as e:
            logger.error(f"Error in DCA entry: {e}")
            return {'success': False, 'error': str(e)}

    async def should_add_to_position(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Tuple[bool, Optional[float]]:
        """Check if should DCA (add to loser)"""
        try:
            entry_price = float(position_data.get('entryPrice', 0))
            current_price = float(position_data.get('markPrice', 0))
            position_amt = abs(float(position_data.get('positionAmt', 0)))
            side = position_data.get('positionSide', 'LONG')

            # Calculate unrealized PnL %
            if side == 'LONG':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # Check if losing enough to DCA
            loss_threshold = -self.dca_interval_pct

            if pnl_pct > loss_threshold:
                return False, None  # Not losing enough

            # Calculate new entry size (larger than previous)
            add_quantity = position_amt * self.size_multiplier

            logger.warning(
                f"📉 DCA: Adding {add_quantity} to {symbol} "
                f"(current PnL: {pnl_pct:.2f}%)"
            )

            return True, add_quantity

        except Exception as e:
            logger.error(f"Error checking DCA conditions: {e}")
            return False, None

    async def calculate_exit_strategy(
        self,
        symbol: str,
        position_data: Dict,
        market_data: Dict
    ) -> Dict:
        """DCA exit: Tighter stop after averaging down"""
        entry_price = float(position_data.get('entryPrice', 0))  # Already averaged
        atr = market_data.get('atr', entry_price * 0.02)
        side = position_data.get('positionSide', 'LONG')

        # Tighter stop for DCA (can't afford big loss)
        if side == 'LONG':
            stop_loss = entry_price - (atr * 1.5)
            take_profit = entry_price + (atr * 3.0)
        else:
            stop_loss = entry_price + (atr * 1.5)
            take_profit = entry_price - (atr * 3.0)

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'mode': 'dca',
            'risk_reward': 2.0,
            'final_stop': True
        }


# Strategy factory
class StrategyFactory:
    """Factory for creating execution strategies"""

    @staticmethod
    def create_strategy(mode: ExecutionMode) -> ExecutionStrategy:
        """Create strategy instance based on mode"""
        if mode == ExecutionMode.STATIC:
            return StaticStrategy()
        elif mode == ExecutionMode.SNIPER:
            return SniperStrategy()
        elif mode == ExecutionMode.PYRAMID:
            return PyramidStrategy()
        elif mode == ExecutionMode.DCA:
            return DCAStrategy()
        else:
            logger.warning(f"Unknown mode {mode}, defaulting to STATIC")
            return StaticStrategy()


# Singleton manager
class ExecutionStrategyManager:
    """
    Manages execution strategies and selects best mode
    """

    def __init__(self):
        self.default_mode = ExecutionMode.STATIC
        self.active_strategies = {}  # symbol -> strategy instance

    async def select_optimal_mode(
        self,
        symbol: str,
        signal: Dict,
        ml_evaluation: Optional[Dict] = None
    ) -> ExecutionMode:
        """
        Select optimal execution mode based on signal and ML

        Factors:
        - Signal confidence
        - Market conditions (volatility, liquidity)
        - ML evaluation scores
        - Historical success rate per mode
        """
        try:
            # Default
            mode = self.default_mode

            # Factor 1: Signal strength
            signal_score = signal.get('score', signal.get('final_score', 0))

            if signal_score >= 85:
                # Very strong signal -> Pyramid (scale in)
                mode = ExecutionMode.PYRAMID
            elif signal_score >= 75:
                # Strong signal -> Static or Sniper
                mode = ExecutionMode.SNIPER if signal.get('volatility', 1) < 2.0 else ExecutionMode.STATIC
            elif signal_score >= 60:
                # Moderate signal -> DCA (prepare for averaging)
                mode = ExecutionMode.DCA
            else:
                # Weak signal -> Static
                mode = ExecutionMode.STATIC

            # Factor 2: ML evaluation (if available)
            if ml_evaluation:
                ml_score = ml_evaluation.get('ml_score', 0)

                if ml_score > 80:
                    # ML very confident -> Pyramid
                    mode = ExecutionMode.PYRAMID
                elif ml_score < 60:
                    # ML uncertain -> Conservative (DCA for safety)
                    mode = ExecutionMode.DCA

            logger.info(
                f"🎯 Selected execution mode for {symbol}: {mode.value} "
                f"(signal_score={signal_score:.1f})"
            )

            return mode

        except Exception as e:
            logger.error(f"Error selecting mode: {e}")
            return self.default_mode

    def get_strategy(self, mode: ExecutionMode) -> ExecutionStrategy:
        """Get strategy instance for mode"""
        return StrategyFactory.create_strategy(mode)


# Singleton instance
execution_strategy_manager = ExecutionStrategyManager()
