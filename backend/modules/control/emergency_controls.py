"""
Emergency Controls
Panic button, emergency stop, reduce-all positions, circuit breakers
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("emergency_controls")


class EmergencyAction(str, Enum):
    """Emergency action types"""
    PANIC_CLOSE_ALL = "panic_close_all"
    EMERGENCY_STOP = "emergency_stop"
    REDUCE_ALL_POSITIONS = "reduce_all_positions"
    CANCEL_ALL_ORDERS = "cancel_all_orders"
    CIRCUIT_BREAKER = "circuit_breaker"


class EmergencyController:
    """
    Emergency Controls System

    Provides critical emergency functions:
    - Panic button (close all positions immediately)
    - Emergency stop (stop bot + cancel orders)
    - Reduce all positions (partial close)
    - Cancel all pending orders
    - Circuit breaker (automatic emergency stop on loss threshold)
    """

    def __init__(self):
        self.emergency_history: List[Dict] = []
        self.max_history = 100

        # Circuit breaker settings
        self.circuit_breaker_enabled = False
        self.circuit_breaker_loss_pct = 10.0  # 10% daily loss
        self.circuit_breaker_triggered = False

    async def panic_close_all(self, reason: str = "Panic button") -> Dict:
        """
        PANIC: Close all positions immediately using market orders

        Args:
            reason: Reason for panic close

        Returns:
            Result dict with closed positions
        """
        try:
            logger.warning(f"🚨 PANIC CLOSE ALL TRIGGERED: {reason}")

            # Stop bot first
            from modules.autonomous_bot import autonomous_bot
            if autonomous_bot.is_running:
                await autonomous_bot.stop()

            # Get all positions
            positions = await binance_client.futures_position_information()

            closed_positions = []
            errors = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))

                    if abs(position_amt) == 0:
                        continue

                    # Determine close side
                    close_side = 'SELL' if position_amt > 0 else 'BUY'

                    # Close with market order
                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )

                    closed_positions.append({
                        'symbol': symbol,
                        'quantity': abs(position_amt),
                        'side': close_side,
                        'order_id': order.get('orderId')
                    })

                    logger.info(f"Panic closed: {symbol}")

                except Exception as e:
                    logger.error(f"Error closing {symbol}: {e}")
                    errors.append({
                        'symbol': symbol,
                        'error': str(e)
                    })

            # Cancel all remaining orders
            await self.cancel_all_orders()

            # Log emergency action
            await self._log_emergency_action(
                EmergencyAction.PANIC_CLOSE_ALL,
                {
                    'reason': reason,
                    'closed_positions': len(closed_positions),
                    'errors': len(errors)
                }
            )

            # Send notification
            try:
                from modules.control.notification_engine import notification_engine, NotificationType, NotificationPriority

                await notification_engine.send_notification(
                    notification_type=NotificationType.BOT_ERROR,
                    title="🚨 PANIC CLOSE ALL",
                    message=f"Closed {len(closed_positions)} positions. Reason: {reason}",
                    priority=NotificationPriority.CRITICAL,
                    data={
                        'closed_count': len(closed_positions),
                        'error_count': len(errors)
                    }
                )

            except Exception as e:
                logger.error(f"Error sending notification: {e}")

            return {
                'success': True,
                'message': f'Closed {len(closed_positions)} positions',
                'closed_positions': closed_positions,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in panic close all: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def emergency_stop(self, reason: str = "Emergency stop") -> Dict:
        """
        Emergency stop: Stop bot + cancel all orders (keep positions open)

        Args:
            reason: Reason for emergency stop

        Returns:
            Result dict
        """
        try:
            logger.warning(f"⚠️ EMERGENCY STOP TRIGGERED: {reason}")

            # Stop bot
            from modules.autonomous_bot import autonomous_bot
            if autonomous_bot.is_running:
                await autonomous_bot.stop()

            # Pause bot
            from modules.control.manual_controls import manual_control_manager
            await manual_control_manager.pause_bot(reason=f"Emergency stop: {reason}")

            # Cancel all orders
            cancelled = await self.cancel_all_orders()

            # Log emergency action
            await self._log_emergency_action(
                EmergencyAction.EMERGENCY_STOP,
                {
                    'reason': reason,
                    'cancelled_orders': cancelled.get('cancelled_count', 0)
                }
            )

            # Send notification
            try:
                from modules.control.notification_engine import notification_engine, NotificationType, NotificationPriority

                await notification_engine.send_notification(
                    notification_type=NotificationType.BOT_STOPPED,
                    title="⚠️ EMERGENCY STOP",
                    message=f"Bot stopped and orders cancelled. Reason: {reason}",
                    priority=NotificationPriority.CRITICAL,
                    data={'reason': reason}
                )

            except Exception as e:
                logger.error(f"Error sending notification: {e}")

            return {
                'success': True,
                'message': 'Emergency stop completed',
                'bot_stopped': True,
                'orders_cancelled': cancelled.get('cancelled_count', 0),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in emergency stop: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def reduce_all_positions(self, reduce_pct: float = 50.0) -> Dict:
        """
        Reduce all positions by percentage

        Args:
            reduce_pct: Percentage to reduce (0-100)

        Returns:
            Result dict
        """
        try:
            if reduce_pct <= 0 or reduce_pct > 100:
                return {
                    'success': False,
                    'message': 'Reduce percentage must be between 0 and 100'
                }

            logger.warning(f"⚠️ REDUCING ALL POSITIONS BY {reduce_pct}%")

            # Get all positions
            positions = await binance_client.futures_position_information()

            reduced_positions = []
            errors = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))

                    if abs(position_amt) == 0:
                        continue

                    # Calculate reduce quantity
                    reduce_qty = abs(position_amt) * (reduce_pct / 100)

                    # Determine side
                    reduce_side = 'SELL' if position_amt > 0 else 'BUY'

                    # Place market order
                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=reduce_side,
                        type='MARKET',
                        quantity=reduce_qty,
                        reduceOnly=True
                    )

                    reduced_positions.append({
                        'symbol': symbol,
                        'original_size': abs(position_amt),
                        'reduced_by': reduce_qty,
                        'remaining': abs(position_amt) - reduce_qty,
                        'order_id': order.get('orderId')
                    })

                    logger.info(f"Reduced {symbol} by {reduce_pct}%")

                except Exception as e:
                    logger.error(f"Error reducing {symbol}: {e}")
                    errors.append({
                        'symbol': symbol,
                        'error': str(e)
                    })

            # Log emergency action
            await self._log_emergency_action(
                EmergencyAction.REDUCE_ALL_POSITIONS,
                {
                    'reduce_pct': reduce_pct,
                    'reduced_positions': len(reduced_positions),
                    'errors': len(errors)
                }
            )

            return {
                'success': True,
                'message': f'Reduced {len(reduced_positions)} positions by {reduce_pct}%',
                'reduced_positions': reduced_positions,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error reducing all positions: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def cancel_all_orders(self) -> Dict:
        """
        Cancel all open orders across all symbols

        Returns:
            Result dict
        """
        try:
            logger.info("Cancelling all open orders")

            # Get all open orders
            open_orders = await binance_client.futures_get_all_orders()

            if not open_orders:
                return {
                    'success': True,
                    'message': 'No open orders to cancel',
                    'cancelled_count': 0
                }

            # Group by symbol
            orders_by_symbol = {}
            for order in open_orders:
                if order.get('status') in ['NEW', 'PARTIALLY_FILLED']:
                    symbol = order.get('symbol')
                    if symbol not in orders_by_symbol:
                        orders_by_symbol[symbol] = []
                    orders_by_symbol[symbol].append(order)

            cancelled_count = 0
            errors = []

            # Cancel all orders per symbol
            for symbol, orders in orders_by_symbol.items():
                try:
                    # Batch cancel all orders for symbol
                    await binance_client.futures_cancel_all_open_orders(symbol=symbol)
                    cancelled_count += len(orders)
                    logger.info(f"Cancelled {len(orders)} orders for {symbol}")

                except Exception as e:
                    logger.error(f"Error cancelling orders for {symbol}: {e}")
                    errors.append({
                        'symbol': symbol,
                        'error': str(e)
                    })

            # Log emergency action
            await self._log_emergency_action(
                EmergencyAction.CANCEL_ALL_ORDERS,
                {
                    'cancelled_count': cancelled_count,
                    'errors': len(errors)
                }
            )

            return {
                'success': True,
                'message': f'Cancelled {cancelled_count} orders',
                'cancelled_count': cancelled_count,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def trigger_circuit_breaker(self, reason: str) -> Dict:
        """
        Trigger circuit breaker (automatic emergency stop)

        Args:
            reason: Reason for circuit breaker

        Returns:
            Result dict
        """
        try:
            if self.circuit_breaker_triggered:
                return {
                    'success': False,
                    'message': 'Circuit breaker already triggered'
                }

            logger.critical(f"🔴 CIRCUIT BREAKER TRIGGERED: {reason}")

            self.circuit_breaker_triggered = True

            # Emergency stop
            result = await self.emergency_stop(reason=f"Circuit breaker: {reason}")

            # Log emergency action
            await self._log_emergency_action(
                EmergencyAction.CIRCUIT_BREAKER,
                {
                    'reason': reason
                }
            )

            # Send notification
            try:
                from modules.control.notification_engine import notification_engine, NotificationType, NotificationPriority

                await notification_engine.send_notification(
                    notification_type=NotificationType.BOT_ERROR,
                    title="🔴 CIRCUIT BREAKER",
                    message=f"Trading halted. Reason: {reason}",
                    priority=NotificationPriority.CRITICAL,
                    data={'reason': reason}
                )

            except Exception as e:
                logger.error(f"Error sending notification: {e}")

            return {
                'success': True,
                'message': 'Circuit breaker triggered',
                'emergency_stop_result': result,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error triggering circuit breaker: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def reset_circuit_breaker(self) -> Dict:
        """Reset circuit breaker (manual override)"""
        try:
            if not self.circuit_breaker_triggered:
                return {
                    'success': False,
                    'message': 'Circuit breaker not triggered'
                }

            self.circuit_breaker_triggered = False

            logger.info("Circuit breaker reset")

            return {
                'success': True,
                'message': 'Circuit breaker reset'
            }

        except Exception as e:
            logger.error(f"Error resetting circuit breaker: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def enable_circuit_breaker(self, loss_pct: float = 10.0):
        """Enable circuit breaker with loss threshold"""
        self.circuit_breaker_enabled = True
        self.circuit_breaker_loss_pct = loss_pct
        logger.info(f"Circuit breaker enabled: {loss_pct}% loss threshold")

    def disable_circuit_breaker(self):
        """Disable circuit breaker"""
        self.circuit_breaker_enabled = False
        logger.info("Circuit breaker disabled")

    async def _log_emergency_action(self, action: EmergencyAction, data: Dict):
        """Log emergency action"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action.value,
            'data': data
        }

        self.emergency_history.append(log_entry)

        if len(self.emergency_history) > self.max_history:
            self.emergency_history.pop(0)

    async def get_emergency_history(self, limit: int = 50) -> List[Dict]:
        """Get emergency action history"""
        return list(reversed(self.emergency_history[-limit:]))

    def get_circuit_breaker_status(self) -> Dict:
        """Get circuit breaker status"""
        return {
            'enabled': self.circuit_breaker_enabled,
            'loss_threshold_pct': self.circuit_breaker_loss_pct,
            'triggered': self.circuit_breaker_triggered
        }


# Singleton instance
emergency_controller = EmergencyController()
