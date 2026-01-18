"""
Quick Actions Manager
One-click actions for common trading operations
"""

import asyncio
from datetime import datetime
from typing import Dict, List
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("quick_actions")


class QuickAction(str, Enum):
    """Quick action types"""
    CLOSE_ALL_PROFITABLE = "close_all_profitable"
    CLOSE_ALL_LOSING = "close_all_losing"
    REDUCE_RISK_MODE = "reduce_risk_mode"
    EMERGENCY_MODE = "emergency_mode"
    SCALE_OUT_WINNERS = "scale_out_winners"
    ADD_TO_WINNERS = "add_to_winners"
    SET_BREAKEVEN_STOPS = "set_breakeven_stops"
    TIGHTEN_ALL_STOPS = "tighten_all_stops"


class QuickActionsManager:
    """
    Quick Actions Manager

    Provides one-click actions:
    - Close all profitable positions
    - Close all losing positions
    - Reduce risk mode (reduce all positions + lower leverage)
    - Emergency mode (stop bot + close losing positions)
    - Scale out winners (take partial profits on winning positions)
    - Add to winners (add to winning positions)
    - Set breakeven stops
    - Tighten all stops
    """

    def __init__(self):
        self.action_history: List[Dict] = []
        self.max_history = 200

    async def close_all_profitable(self, min_profit_pct: float = 1.0) -> Dict:
        """
        Close all profitable positions

        Args:
            min_profit_pct: Minimum profit % to close

        Returns:
            Result dict
        """
        try:
            logger.info(f"Closing all profitable positions (min profit: {min_profit_pct}%)")

            # Get all positions
            positions = await binance_client.futures_position_information()

            closed_positions = []
            errors = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))
                    unrealized_profit = float(pos.get('unRealizedProfit', 0))

                    if abs(position_amt) == 0:
                        continue

                    # Calculate profit %
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))

                    if entry_price == 0:
                        continue

                    price_change_pct = ((mark_price - entry_price) / entry_price) * 100
                    leverage = int(pos.get('leverage', 1))
                    pnl_pct = price_change_pct * leverage * (1 if position_amt > 0 else -1)

                    # Only close if profitable above threshold
                    if pnl_pct < min_profit_pct:
                        continue

                    # Close position
                    close_side = 'SELL' if position_amt > 0 else 'BUY'

                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )

                    closed_positions.append({
                        'symbol': symbol,
                        'pnl': unrealized_profit,
                        'pnl_pct': round(pnl_pct, 2),
                        'order_id': order.get('orderId')
                    })

                    logger.info(f"Closed profitable position: {symbol} (+{pnl_pct:.2f}%)")

                except Exception as e:
                    logger.error(f"Error closing {symbol}: {e}")
                    errors.append({'symbol': symbol, 'error': str(e)})

            # Log action
            await self._log_action(QuickAction.CLOSE_ALL_PROFITABLE, {
                'min_profit_pct': min_profit_pct,
                'closed_count': len(closed_positions),
                'total_profit': sum(p['pnl'] for p in closed_positions)
            })

            return {
                'success': True,
                'message': f'Closed {len(closed_positions)} profitable positions',
                'closed_positions': closed_positions,
                'errors': errors,
                'total_profit': sum(p['pnl'] for p in closed_positions)
            }

        except Exception as e:
            logger.error(f"Error in close_all_profitable: {e}")
            return {'success': False, 'message': str(e)}

    async def close_all_losing(self, max_loss_pct: float = -2.0) -> Dict:
        """
        Close all losing positions

        Args:
            max_loss_pct: Maximum loss % to close (negative value)

        Returns:
            Result dict
        """
        try:
            logger.info(f"Closing all losing positions (max loss: {max_loss_pct}%)")

            # Get all positions
            positions = await binance_client.futures_position_information()

            closed_positions = []
            errors = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))
                    unrealized_profit = float(pos.get('unRealizedProfit', 0))

                    if abs(position_amt) == 0:
                        continue

                    # Calculate P&L %
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))

                    if entry_price == 0:
                        continue

                    price_change_pct = ((mark_price - entry_price) / entry_price) * 100
                    leverage = int(pos.get('leverage', 1))
                    pnl_pct = price_change_pct * leverage * (1 if position_amt > 0 else -1)

                    # Only close if losing below threshold
                    if pnl_pct > max_loss_pct:
                        continue

                    # Close position
                    close_side = 'SELL' if position_amt > 0 else 'BUY'

                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )

                    closed_positions.append({
                        'symbol': symbol,
                        'pnl': unrealized_profit,
                        'pnl_pct': round(pnl_pct, 2),
                        'order_id': order.get('orderId')
                    })

                    logger.info(f"Closed losing position: {symbol} ({pnl_pct:.2f}%)")

                except Exception as e:
                    logger.error(f"Error closing {symbol}: {e}")
                    errors.append({'symbol': symbol, 'error': str(e)})

            # Log action
            await self._log_action(QuickAction.CLOSE_ALL_LOSING, {
                'max_loss_pct': max_loss_pct,
                'closed_count': len(closed_positions),
                'total_loss': sum(p['pnl'] for p in closed_positions)
            })

            return {
                'success': True,
                'message': f'Closed {len(closed_positions)} losing positions',
                'closed_positions': closed_positions,
                'errors': errors,
                'total_loss': sum(p['pnl'] for p in closed_positions)
            }

        except Exception as e:
            logger.error(f"Error in close_all_losing: {e}")
            return {'success': False, 'message': str(e)}

    async def reduce_risk_mode(self) -> Dict:
        """
        Reduce risk mode: Reduce all positions by 50% and lower leverage

        Returns:
            Result dict
        """
        try:
            logger.warning("🛡️ REDUCE RISK MODE ACTIVATED")

            # Pause bot
            from modules.control.manual_controls import manual_control_manager
            await manual_control_manager.pause_bot(reason="Reduce risk mode")

            # Reduce all positions by 50%
            from modules.control.emergency_controls import emergency_controller
            reduce_result = await emergency_controller.reduce_all_positions(reduce_pct=50.0)

            # Lower leverage on all symbols
            positions = await binance_client.futures_position_information()

            leverage_changes = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    current_leverage = int(pos.get('leverage', 1))

                    # Reduce leverage by half (min 3x)
                    new_leverage = max(3, current_leverage // 2)

                    if new_leverage != current_leverage:
                        await binance_client.futures_change_leverage(
                            symbol=symbol,
                            leverage=new_leverage
                        )

                        leverage_changes.append({
                            'symbol': symbol,
                            'old_leverage': current_leverage,
                            'new_leverage': new_leverage
                        })

                except Exception as e:
                    logger.error(f"Error changing leverage for {symbol}: {e}")

            # Log action
            await self._log_action(QuickAction.REDUCE_RISK_MODE, {
                'reduced_positions': len(reduce_result.get('reduced_positions', [])),
                'leverage_changes': len(leverage_changes)
            })

            return {
                'success': True,
                'message': 'Risk reduction mode activated',
                'bot_paused': True,
                'positions_reduced': reduce_result.get('reduced_positions', []),
                'leverage_changes': leverage_changes
            }

        except Exception as e:
            logger.error(f"Error in reduce_risk_mode: {e}")
            return {'success': False, 'message': str(e)}

    async def emergency_mode(self) -> Dict:
        """
        Emergency mode: Stop bot + close all losing positions

        Returns:
            Result dict
        """
        try:
            logger.critical("🚨 EMERGENCY MODE ACTIVATED")

            # Stop bot
            from modules.autonomous_bot import autonomous_bot
            if autonomous_bot.is_running:
                await autonomous_bot.stop()

            # Close all losing positions (>-1%)
            close_result = await self.close_all_losing(max_loss_pct=-1.0)

            # Cancel all orders
            from modules.control.emergency_controls import emergency_controller
            cancel_result = await emergency_controller.cancel_all_orders()

            # Log action
            await self._log_action(QuickAction.EMERGENCY_MODE, {
                'closed_losing': len(close_result.get('closed_positions', [])),
                'cancelled_orders': cancel_result.get('cancelled_count', 0)
            })

            return {
                'success': True,
                'message': 'Emergency mode activated',
                'bot_stopped': True,
                'closed_positions': close_result.get('closed_positions', []),
                'cancelled_orders': cancel_result.get('cancelled_count', 0)
            }

        except Exception as e:
            logger.error(f"Error in emergency_mode: {e}")
            return {'success': False, 'message': str(e)}

    async def scale_out_winners(self, profit_threshold_pct: float = 3.0, scale_pct: float = 50.0) -> Dict:
        """
        Scale out of winning positions (take partial profits)

        Args:
            profit_threshold_pct: Minimum profit % to scale out
            scale_pct: Percentage to scale out (0-100)

        Returns:
            Result dict
        """
        try:
            logger.info(f"Scaling out {scale_pct}% of positions with >{profit_threshold_pct}% profit")

            # Get all positions
            positions = await binance_client.futures_position_information()

            scaled_positions = []
            errors = []

            for pos in positions:
                try:
                    symbol = pos.get('symbol')
                    position_amt = float(pos.get('positionAmt', 0))

                    if abs(position_amt) == 0:
                        continue

                    # Calculate P&L %
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))

                    if entry_price == 0:
                        continue

                    price_change_pct = ((mark_price - entry_price) / entry_price) * 100
                    leverage = int(pos.get('leverage', 1))
                    pnl_pct = price_change_pct * leverage * (1 if position_amt > 0 else -1)

                    # Only scale if profitable above threshold
                    if pnl_pct < profit_threshold_pct:
                        continue

                    # Calculate scale quantity
                    scale_qty = abs(position_amt) * (scale_pct / 100)

                    # Close partial position
                    close_side = 'SELL' if position_amt > 0 else 'BUY'

                    order = await binance_client.futures_create_order(
                        symbol=symbol,
                        side=close_side,
                        type='MARKET',
                        quantity=scale_qty,
                        reduceOnly=True
                    )

                    scaled_positions.append({
                        'symbol': symbol,
                        'original_size': abs(position_amt),
                        'scaled_qty': scale_qty,
                        'remaining': abs(position_amt) - scale_qty,
                        'pnl_pct': round(pnl_pct, 2),
                        'order_id': order.get('orderId')
                    })

                    logger.info(f"Scaled out {symbol}: {scale_pct}% at +{pnl_pct:.2f}%")

                except Exception as e:
                    logger.error(f"Error scaling {symbol}: {e}")
                    errors.append({'symbol': symbol, 'error': str(e)})

            # Log action
            await self._log_action(QuickAction.SCALE_OUT_WINNERS, {
                'profit_threshold_pct': profit_threshold_pct,
                'scale_pct': scale_pct,
                'scaled_count': len(scaled_positions)
            })

            return {
                'success': True,
                'message': f'Scaled out {len(scaled_positions)} positions',
                'scaled_positions': scaled_positions,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error in scale_out_winners: {e}")
            return {'success': False, 'message': str(e)}

    async def _log_action(self, action: QuickAction, data: Dict):
        """Log quick action"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action.value,
            'data': data
        }

        self.action_history.append(log_entry)

        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)

    async def get_action_history(self, limit: int = 100) -> List[Dict]:
        """Get quick action history"""
        return list(reversed(self.action_history[-limit:]))


# Singleton instance
quick_actions_manager = QuickActionsManager()
