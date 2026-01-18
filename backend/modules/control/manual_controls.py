"""
Manual Control Manager
Provides manual override capabilities for bot and positions
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("manual_controls")


class ControlAction(str, Enum):
    """Manual control actions"""
    PAUSE_BOT = "pause_bot"
    RESUME_BOT = "resume_bot"
    CLOSE_POSITION = "close_position"
    ADJUST_LEVERAGE = "adjust_leverage"
    MODIFY_STOP_LOSS = "modify_stop_loss"
    MODIFY_TAKE_PROFIT = "modify_take_profit"
    ADD_TO_POSITION = "add_to_position"
    REDUCE_POSITION = "reduce_position"


class ManualControlManager:
    """
    Manual Control Manager

    Provides comprehensive manual control over:
    - Bot state (pause/resume)
    - Individual positions (close, adjust, modify)
    - Leverage adjustment
    - Stop loss / Take profit modification
    - Position sizing (add/reduce)
    """

    def __init__(self):
        self.control_history: List[Dict] = []
        self.max_history = 500

        # Bot state
        self.bot_paused = False
        self.pause_reason = None
        self.pause_timestamp = None

    async def pause_bot(self, reason: str = "Manual pause") -> Dict:
        """
        Pause the autonomous bot

        Args:
            reason: Reason for pausing

        Returns:
            Status dict
        """
        try:
            from modules.autonomous_bot import autonomous_bot

            if self.bot_paused:
                return {
                    'success': False,
                    'message': 'Bot is already paused',
                    'paused_since': self.pause_timestamp.isoformat() if self.pause_timestamp else None
                }

            # Set pause flag
            self.bot_paused = True
            self.pause_reason = reason
            self.pause_timestamp = datetime.now()

            # Set flag on bot instance (will be checked in bot loop)
            autonomous_bot.is_paused = True

            # Log action
            await self._log_action(ControlAction.PAUSE_BOT, {
                'reason': reason
            })

            logger.info(f"Bot paused: {reason}")

            return {
                'success': True,
                'message': 'Bot paused successfully',
                'reason': reason,
                'timestamp': self.pause_timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error pausing bot: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def resume_bot(self) -> Dict:
        """
        Resume the autonomous bot

        Returns:
            Status dict
        """
        try:
            from modules.autonomous_bot import autonomous_bot

            if not self.bot_paused:
                return {
                    'success': False,
                    'message': 'Bot is not paused'
                }

            # Clear pause flag
            self.bot_paused = False
            pause_duration = (datetime.now() - self.pause_timestamp).total_seconds() if self.pause_timestamp else 0
            self.pause_reason = None
            self.pause_timestamp = None

            # Clear flag on bot instance
            autonomous_bot.is_paused = False

            # Log action
            await self._log_action(ControlAction.RESUME_BOT, {
                'pause_duration_seconds': pause_duration
            })

            logger.info(f"Bot resumed after {pause_duration:.1f} seconds")

            return {
                'success': True,
                'message': 'Bot resumed successfully',
                'pause_duration_seconds': pause_duration
            }

        except Exception as e:
            logger.error(f"Error resuming bot: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def close_position(
        self,
        symbol: str,
        reason: str = "Manual close"
    ) -> Dict:
        """
        Manually close a position

        Args:
            symbol: Trading pair
            reason: Reason for closing

        Returns:
            Result dict
        """
        try:
            # Get current position
            positions = await binance_client.futures_position_information(symbol=symbol)

            if not positions:
                return {
                    'success': False,
                    'message': f'No position found for {symbol}'
                }

            position = positions[0]
            position_amt = float(position.get('positionAmt', 0))

            if abs(position_amt) == 0:
                return {
                    'success': False,
                    'message': f'No open position for {symbol}'
                }

            # Determine side for closing
            close_side = 'SELL' if position_amt > 0 else 'BUY'
            close_quantity = abs(position_amt)

            # Place market order to close
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=close_side,
                type='MARKET',
                quantity=close_quantity,
                reduceOnly=True
            )

            # Log action
            await self._log_action(ControlAction.CLOSE_POSITION, {
                'symbol': symbol,
                'quantity': close_quantity,
                'side': close_side,
                'reason': reason,
                'order_id': order.get('orderId')
            })

            logger.info(f"Manually closed position: {symbol}")

            return {
                'success': True,
                'message': f'Position closed for {symbol}',
                'order': order,
                'reason': reason
            }

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def adjust_leverage(
        self,
        symbol: str,
        leverage: int
    ) -> Dict:
        """
        Adjust leverage for a symbol

        Args:
            symbol: Trading pair
            leverage: New leverage (1-125)

        Returns:
            Result dict
        """
        try:
            # Validate leverage
            if leverage < 1 or leverage > 125:
                return {
                    'success': False,
                    'message': 'Leverage must be between 1 and 125'
                }

            # Change leverage
            result = await binance_client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )

            # Log action
            await self._log_action(ControlAction.ADJUST_LEVERAGE, {
                'symbol': symbol,
                'leverage': leverage
            })

            logger.info(f"Adjusted leverage for {symbol} to {leverage}x")

            return {
                'success': True,
                'message': f'Leverage set to {leverage}x for {symbol}',
                'result': result
            }

        except Exception as e:
            logger.error(f"Error adjusting leverage for {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def modify_stop_loss(
        self,
        symbol: str,
        stop_price: float
    ) -> Dict:
        """
        Modify stop loss for a position

        Args:
            symbol: Trading pair
            stop_price: New stop loss price

        Returns:
            Result dict
        """
        try:
            # Get current position
            positions = await binance_client.futures_position_information(symbol=symbol)

            if not positions:
                return {
                    'success': False,
                    'message': f'No position found for {symbol}'
                }

            position = positions[0]
            position_amt = float(position.get('positionAmt', 0))

            if abs(position_amt) == 0:
                return {
                    'success': False,
                    'message': f'No open position for {symbol}'
                }

            # Cancel existing stop loss orders
            open_orders = await binance_client.futures_get_open_orders(symbol=symbol)

            for order in open_orders:
                if order.get('type') in ['STOP_MARKET', 'STOP']:
                    await binance_client.futures_cancel_order(
                        symbol=symbol,
                        orderId=order.get('orderId')
                    )

            # Determine side for stop loss
            stop_side = 'SELL' if position_amt > 0 else 'BUY'

            # Place new stop loss
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=stop_side,
                type='STOP_MARKET',
                quantity=abs(position_amt),
                stopPrice=stop_price,
                reduceOnly=True
            )

            # Log action
            await self._log_action(ControlAction.MODIFY_STOP_LOSS, {
                'symbol': symbol,
                'stop_price': stop_price,
                'order_id': order.get('orderId')
            })

            logger.info(f"Modified stop loss for {symbol} to {stop_price}")

            return {
                'success': True,
                'message': f'Stop loss updated to {stop_price}',
                'order': order
            }

        except Exception as e:
            logger.error(f"Error modifying stop loss for {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def modify_take_profit(
        self,
        symbol: str,
        take_profit_price: float
    ) -> Dict:
        """
        Modify take profit for a position

        Args:
            symbol: Trading pair
            take_profit_price: New take profit price

        Returns:
            Result dict
        """
        try:
            # Get current position
            positions = await binance_client.futures_position_information(symbol=symbol)

            if not positions:
                return {
                    'success': False,
                    'message': f'No position found for {symbol}'
                }

            position = positions[0]
            position_amt = float(position.get('positionAmt', 0))

            if abs(position_amt) == 0:
                return {
                    'success': False,
                    'message': f'No open position for {symbol}'
                }

            # Cancel existing take profit orders
            open_orders = await binance_client.futures_get_open_orders(symbol=symbol)

            for order in open_orders:
                if order.get('type') in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT']:
                    if order.get('reduceOnly'):
                        await binance_client.futures_cancel_order(
                            symbol=symbol,
                            orderId=order.get('orderId')
                        )

            # Determine side for take profit
            tp_side = 'SELL' if position_amt > 0 else 'BUY'

            # Place new take profit
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=tp_side,
                type='TAKE_PROFIT_MARKET',
                quantity=abs(position_amt),
                stopPrice=take_profit_price,
                reduceOnly=True
            )

            # Log action
            await self._log_action(ControlAction.MODIFY_TAKE_PROFIT, {
                'symbol': symbol,
                'take_profit_price': take_profit_price,
                'order_id': order.get('orderId')
            })

            logger.info(f"Modified take profit for {symbol} to {take_profit_price}")

            return {
                'success': True,
                'message': f'Take profit updated to {take_profit_price}',
                'order': order
            }

        except Exception as e:
            logger.error(f"Error modifying take profit for {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def add_to_position(
        self,
        symbol: str,
        additional_quantity: float
    ) -> Dict:
        """
        Add to existing position

        Args:
            symbol: Trading pair
            additional_quantity: Quantity to add

        Returns:
            Result dict
        """
        try:
            # Get current position
            positions = await binance_client.futures_position_information(symbol=symbol)

            if not positions:
                return {
                    'success': False,
                    'message': f'No position found for {symbol}'
                }

            position = positions[0]
            position_amt = float(position.get('positionAmt', 0))

            if abs(position_amt) == 0:
                return {
                    'success': False,
                    'message': f'No open position for {symbol}'
                }

            # Determine side (same as current position)
            side = 'BUY' if position_amt > 0 else 'SELL'

            # Place market order to add
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=additional_quantity
            )

            # Log action
            await self._log_action(ControlAction.ADD_TO_POSITION, {
                'symbol': symbol,
                'quantity': additional_quantity,
                'side': side,
                'order_id': order.get('orderId')
            })

            logger.info(f"Added {additional_quantity} to position: {symbol}")

            return {
                'success': True,
                'message': f'Added {additional_quantity} to {symbol} position',
                'order': order
            }

        except Exception as e:
            logger.error(f"Error adding to position {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def reduce_position(
        self,
        symbol: str,
        reduce_quantity: float
    ) -> Dict:
        """
        Reduce existing position

        Args:
            symbol: Trading pair
            reduce_quantity: Quantity to reduce

        Returns:
            Result dict
        """
        try:
            # Get current position
            positions = await binance_client.futures_position_information(symbol=symbol)

            if not positions:
                return {
                    'success': False,
                    'message': f'No position found for {symbol}'
                }

            position = positions[0]
            position_amt = float(position.get('positionAmt', 0))

            if abs(position_amt) == 0:
                return {
                    'success': False,
                    'message': f'No open position for {symbol}'
                }

            # Validate quantity
            if reduce_quantity > abs(position_amt):
                return {
                    'success': False,
                    'message': f'Reduce quantity ({reduce_quantity}) exceeds position size ({abs(position_amt)})'
                }

            # Determine side (opposite of position)
            side = 'SELL' if position_amt > 0 else 'BUY'

            # Place market order to reduce
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=reduce_quantity,
                reduceOnly=True
            )

            # Log action
            await self._log_action(ControlAction.REDUCE_POSITION, {
                'symbol': symbol,
                'quantity': reduce_quantity,
                'side': side,
                'order_id': order.get('orderId')
            })

            logger.info(f"Reduced position by {reduce_quantity}: {symbol}")

            return {
                'success': True,
                'message': f'Reduced {symbol} position by {reduce_quantity}',
                'order': order
            }

        except Exception as e:
            logger.error(f"Error reducing position {symbol}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def _log_action(self, action: ControlAction, data: Dict):
        """Log manual control action"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action.value,
            'data': data
        }

        self.control_history.append(log_entry)

        if len(self.control_history) > self.max_history:
            self.control_history.pop(0)

    def get_control_history(self, limit: int = 100) -> List[Dict]:
        """Get manual control history"""
        return list(reversed(self.control_history[-limit:]))

    def is_bot_paused(self) -> bool:
        """Check if bot is paused"""
        return self.bot_paused

    def get_pause_info(self) -> Optional[Dict]:
        """Get pause information"""
        if not self.bot_paused:
            return None

        return {
            'paused': True,
            'reason': self.pause_reason,
            'paused_since': self.pause_timestamp.isoformat() if self.pause_timestamp else None,
            'paused_for_seconds': (datetime.now() - self.pause_timestamp).total_seconds() if self.pause_timestamp else 0
        }


# Singleton instance
manual_control_manager = ManualControlManager()
