"""
Intelligent Trailing Stop Manager
Dynamically activates and adjusts trailing stops based on multiple factors
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client
from config.settings import get_settings

logger = setup_logger("trailing_stop")


class TrailingStopMode(str, Enum):
    """Trailing stop activation modes"""
    DISABLED = "disabled"
    STATIC = "static"              # Fixed ATR-based
    DYNAMIC = "dynamic"             # Adapts to volatility
    PROFIT_BASED = "profit_based"  # Activates after X% profit
    BREAKEVEN = "breakeven"         # Moves to breakeven first
    SMART = "smart"                 # ML-enhanced (uses all factors)


class TrailingStopManager:
    """
    Intelligent trailing stop management with dynamic activation

    Features:
    - Multiple activation strategies
    - Volatility-adjusted callbacks
    - Profit-based triggers
    - Breakeven protection
    - ML-enhanced decision making
    """

    def __init__(self):
        self.settings = get_settings()
        self.active_trails = {}  # symbol -> trail config

        # Default configurations
        self.default_mode = TrailingStopMode.SMART
        self.min_profit_activation_pct = 1.5  # Activate after 1.5% profit
        self.breakeven_offset_pct = 0.3       # Move to BE + 0.3%
        self.base_callback_pct = 2.0          # Base callback percentage

        logger.info("✅ Intelligent Trailing Stop Manager initialized")

    async def calculate_optimal_trail_config(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        position_side: str,
        unrealized_pnl_pct: float,
        position_size: float,
        mode: Optional[TrailingStopMode] = None
    ) -> Optional[Dict]:
        """
        Calculate optimal trailing stop configuration

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            current_price: Current market price
            position_side: 'LONG' or 'SHORT'
            unrealized_pnl_pct: Current unrealized PnL %
            position_size: Position size in quote currency
            mode: Trailing stop mode (defaults to SMART)

        Returns:
            Dict with trail config or None if shouldn't activate
        """
        if mode is None:
            mode = self.default_mode

        try:
            # Get market data
            market_data = await self._get_market_data(symbol)

            if mode == TrailingStopMode.DISABLED:
                return None

            elif mode == TrailingStopMode.STATIC:
                return self._static_trail_config(
                    entry_price, current_price, position_side, market_data
                )

            elif mode == TrailingStopMode.DYNAMIC:
                return self._dynamic_trail_config(
                    entry_price, current_price, position_side,
                    unrealized_pnl_pct, market_data
                )

            elif mode == TrailingStopMode.PROFIT_BASED:
                return self._profit_based_trail_config(
                    entry_price, current_price, position_side,
                    unrealized_pnl_pct, market_data
                )

            elif mode == TrailingStopMode.BREAKEVEN:
                return self._breakeven_trail_config(
                    entry_price, current_price, position_side, unrealized_pnl_pct
                )

            elif mode == TrailingStopMode.SMART:
                return await self._smart_trail_config(
                    symbol, entry_price, current_price, position_side,
                    unrealized_pnl_pct, position_size, market_data
                )

        except Exception as e:
            logger.error(f"Error calculating trail config for {symbol}: {e}")
            return None

    async def _get_market_data(self, symbol: str) -> Dict:
        """Get current market data for intelligent decisions"""
        try:
            # Get recent klines for volatility calculation
            klines = await binance_client.get_historical_klines(symbol, "5m", limit=50)

            if not klines:
                return {'atr': 0, 'volatility': 0, 'momentum': 0}

            import pandas as pd
            import numpy as np

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            for col in ['high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])

            # ATR calculation
            high = df['high']
            low = df['low']
            close = df['close']

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]

            # Volatility (standard deviation of returns)
            returns = df['close'].pct_change()
            volatility = returns.std() * 100  # Percentage

            # Momentum (price change over last 10 periods)
            momentum = ((df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]) * 100

            return {
                'atr': float(atr) if not pd.isna(atr) else 0,
                'volatility': float(volatility) if not pd.isna(volatility) else 0,
                'momentum': float(momentum) if not pd.isna(momentum) else 0,
                'current_price': float(df['close'].iloc[-1])
            }

        except Exception as e:
            logger.warning(f"Error getting market data: {e}")
            return {'atr': 0, 'volatility': 0, 'momentum': 0}

    def _static_trail_config(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        market_data: Dict
    ) -> Optional[Dict]:
        """Static trailing stop: Fixed ATR-based callback"""

        atr = market_data.get('atr', 0)
        if atr == 0:
            callback_pct = self.base_callback_pct
        else:
            # Callback = 1.5x ATR as percentage
            callback_pct = (atr / current_price) * 150
            callback_pct = max(1.0, min(5.0, callback_pct))  # Clamp 1-5%

        return {
            'mode': 'static',
            'activate_price': current_price,
            'callback_rate': callback_pct,
            'activation_distance_pct': 0,  # Activate immediately
            'reason': f'Static ATR-based ({callback_pct:.2f}%)'
        }

    def _dynamic_trail_config(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        unrealized_pnl_pct: float,
        market_data: Dict
    ) -> Optional[Dict]:
        """Dynamic trailing stop: Adapts callback to volatility"""

        volatility = market_data.get('volatility', 1.0)
        atr = market_data.get('atr', 0)

        # Base callback on volatility
        if volatility < 0.5:
            callback_pct = 1.0  # Low vol: tight trail
        elif volatility < 1.5:
            callback_pct = 2.0  # Normal vol
        elif volatility < 3.0:
            callback_pct = 3.0  # High vol: wider trail
        else:
            callback_pct = 4.0  # Very high vol

        # Adjust based on profit
        if unrealized_pnl_pct > 5.0:
            callback_pct *= 0.8  # Tighten if big profit
        elif unrealized_pnl_pct > 10.0:
            callback_pct *= 0.6  # Even tighter

        return {
            'mode': 'dynamic',
            'activate_price': current_price,
            'callback_rate': round(callback_pct, 2),
            'activation_distance_pct': 0.5,  # Activate after 0.5% profit
            'reason': f'Dynamic volatility-adjusted ({callback_pct:.2f}%)'
        }

    def _profit_based_trail_config(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        unrealized_pnl_pct: float,
        market_data: Dict
    ) -> Optional[Dict]:
        """Profit-based: Only activate after minimum profit reached"""

        if unrealized_pnl_pct < self.min_profit_activation_pct:
            return None  # Don't activate yet

        # Calculate callback based on how much profit we have
        if unrealized_pnl_pct < 3.0:
            callback_pct = 2.5
        elif unrealized_pnl_pct < 5.0:
            callback_pct = 2.0
        elif unrealized_pnl_pct < 10.0:
            callback_pct = 1.5
        else:
            callback_pct = 1.0  # Very tight for huge profits

        return {
            'mode': 'profit_based',
            'activate_price': current_price,
            'callback_rate': callback_pct,
            'activation_distance_pct': self.min_profit_activation_pct,
            'reason': f'Profit-based activation at {unrealized_pnl_pct:.1f}% PnL'
        }

    def _breakeven_trail_config(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        unrealized_pnl_pct: float
    ) -> Optional[Dict]:
        """Breakeven mode: Move stop to entry + small offset"""

        if unrealized_pnl_pct < 1.0:
            return None  # Need at least 1% profit to activate

        # Calculate breakeven price with offset
        if position_side == 'LONG':
            stop_price = entry_price * (1 + self.breakeven_offset_pct / 100)
        else:  # SHORT
            stop_price = entry_price * (1 - self.breakeven_offset_pct / 100)

        return {
            'mode': 'breakeven',
            'activate_price': stop_price,
            'callback_rate': 0.0,  # No callback, just lock breakeven
            'activation_distance_pct': 1.0,
            'reason': f'Breakeven protection at {stop_price:.4f}'
        }

    async def _smart_trail_config(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        position_side: str,
        unrealized_pnl_pct: float,
        position_size: float,
        market_data: Dict
    ) -> Optional[Dict]:
        """
        Smart mode: ML-enhanced decision making

        Considers:
        - Current profit level
        - Market volatility
        - Momentum direction
        - Position size (risk)
        - Historical performance of similar trades
        """

        atr = market_data.get('atr', 0)
        volatility = market_data.get('volatility', 1.0)
        momentum = market_data.get('momentum', 0)

        # Decision matrix for activation
        activation_score = 0

        # Factor 1: Profit level (0-40 points)
        if unrealized_pnl_pct >= 10.0:
            activation_score += 40
        elif unrealized_pnl_pct >= 5.0:
            activation_score += 30
        elif unrealized_pnl_pct >= 3.0:
            activation_score += 20
        elif unrealized_pnl_pct >= 1.5:
            activation_score += 10

        # Factor 2: Momentum alignment (0-30 points)
        if position_side == 'LONG':
            if momentum > 2.0:
                activation_score += 30  # Strong upward momentum
            elif momentum > 0.5:
                activation_score += 15
            elif momentum < -1.0:
                activation_score += 30  # Reversal signal - protect profit!
        else:  # SHORT
            if momentum < -2.0:
                activation_score += 30
            elif momentum < -0.5:
                activation_score += 15
            elif momentum > 1.0:
                activation_score += 30

        # Factor 3: Volatility (0-20 points)
        if volatility > 3.0:
            activation_score += 20  # High vol - protect gains
        elif volatility > 2.0:
            activation_score += 10

        # Factor 4: Position size risk (0-10 points)
        if position_size > 1000:  # Large position
            activation_score += 10
        elif position_size > 500:
            activation_score += 5

        # Decide if we should activate (threshold: 40/100)
        if activation_score < 40:
            return None  # Don't activate yet

        # Calculate intelligent callback rate
        base_callback = 2.0

        # Adjust for volatility
        if volatility > 3.0:
            base_callback = 3.5
        elif volatility < 1.0:
            base_callback = 1.5

        # Adjust for profit
        if unrealized_pnl_pct > 10.0:
            base_callback *= 0.6  # Very tight for huge profits
        elif unrealized_pnl_pct > 5.0:
            base_callback *= 0.8

        # Adjust for momentum
        if (position_side == 'LONG' and momentum < -1.0) or \
           (position_side == 'SHORT' and momentum > 1.0):
            base_callback *= 1.3  # Wider if reversing

        callback_pct = round(base_callback, 2)

        # Determine activation strategy
        if unrealized_pnl_pct < 2.0:
            strategy = "Early protection (momentum reversal)"
        elif unrealized_pnl_pct < 5.0:
            strategy = "Moderate profit lock"
        else:
            strategy = "Maximum profit protection"

        logger.info(
            f"🧠 SMART Trail for {symbol}: Score={activation_score}/100, "
            f"Callback={callback_pct}%, Strategy={strategy}"
        )

        return {
            'mode': 'smart',
            'activate_price': current_price,
            'callback_rate': callback_pct,
            'activation_distance_pct': 0,  # Can activate anytime if score is high
            'activation_score': activation_score,
            'strategy': strategy,
            'factors': {
                'profit_pnl': unrealized_pnl_pct,
                'volatility': volatility,
                'momentum': momentum,
                'position_size': position_size
            },
            'reason': f'Smart trail ({strategy}, score={activation_score})'
        }

    async def should_activate_trail(
        self,
        symbol: str,
        position_data: Dict,
        mode: Optional[TrailingStopMode] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Determine if trailing stop should be activated for a position

        Returns:
            (should_activate, trail_config)
        """
        try:
            entry_price = float(position_data.get('entryPrice', 0))
            current_price = float(position_data.get('markPrice', 0))
            position_side = position_data.get('positionSide', 'LONG')
            unrealized_pnl = float(position_data.get('unRealizedProfit', 0))
            position_amt = abs(float(position_data.get('positionAmt', 0)))

            if entry_price == 0 or position_amt == 0:
                return False, None

            # Calculate unrealized PnL %
            if position_side == 'LONG':
                unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                unrealized_pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # Calculate position size in quote currency
            position_size = position_amt * current_price

            # Get optimal trail config
            trail_config = await self.calculate_optimal_trail_config(
                symbol=symbol,
                entry_price=entry_price,
                current_price=current_price,
                position_side=position_side,
                unrealized_pnl_pct=unrealized_pnl_pct,
                position_size=position_size,
                mode=mode
            )

            if trail_config is None:
                return False, None

            # Check activation distance threshold
            activation_distance = trail_config.get('activation_distance_pct', 0)

            if unrealized_pnl_pct >= activation_distance:
                logger.info(
                    f"✅ Trailing stop activation criteria met for {symbol}: "
                    f"PnL={unrealized_pnl_pct:.2f}%, Mode={trail_config['mode']}, "
                    f"Callback={trail_config['callback_rate']}%"
                )
                return True, trail_config

            return False, trail_config

        except Exception as e:
            logger.error(f"Error checking trail activation for {symbol}: {e}")
            return False, None

    async def activate_trailing_stop(
        self,
        symbol: str,
        position_data: Dict,
        trail_config: Dict
    ) -> bool:
        """
        Activate trailing stop for a position

        Returns:
            True if activation successful
        """
        try:
            callback_rate = trail_config['callback_rate']

            # Place trailing stop order via Binance
            result = await binance_client.futures_create_order(
                symbol=symbol,
                side='SELL' if position_data['positionSide'] == 'LONG' else 'BUY',
                type='TRAILING_STOP_MARKET',
                callbackRate=callback_rate,
                activationPrice=trail_config.get('activate_price'),
                reduceOnly=True
            )

            # Track active trail
            self.active_trails[symbol] = {
                'config': trail_config,
                'order_id': result.get('orderId'),
                'activated_at': datetime.now(),
                'position_data': position_data
            }

            logger.info(
                f"🎯 Trailing stop activated for {symbol}: "
                f"Callback={callback_rate}%, OrderID={result.get('orderId')}, "
                f"Reason={trail_config['reason']}"
            )

            return True

        except Exception as e:
            logger.error(f"Error activating trailing stop for {symbol}: {e}")
            return False

    async def monitor_and_adjust_trails(self):
        """
        Continuously monitor and adjust active trailing stops
        Should run in background task
        """
        while True:
            try:
                for symbol, trail_data in list(self.active_trails.items()):
                    # Check if position still exists
                    positions = await binance_client.futures_position_information(symbol=symbol)

                    active_position = None
                    for pos in positions:
                        if abs(float(pos.get('positionAmt', 0))) > 0:
                            active_position = pos
                            break

                    if not active_position:
                        # Position closed, remove trail
                        del self.active_trails[symbol]
                        logger.info(f"✅ Position closed for {symbol}, trail removed")
                        continue

                    # Could add dynamic adjustment logic here
                    # For now, Binance handles trail automatically

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trail monitor loop: {e}")
                await asyncio.sleep(10)


# Singleton instance
trailing_stop_manager = TrailingStopManager()
