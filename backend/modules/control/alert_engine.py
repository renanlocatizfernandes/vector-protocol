"""
Custom Alert Engine
Configurable alerts for price, profit, loss, margin, and portfolio metrics
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("alert_engine")


class AlertType(str, Enum):
    """Alert types"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PROFIT_TARGET = "profit_target"
    LOSS_LIMIT = "loss_limit"
    MARGIN_USAGE = "margin_usage"
    PORTFOLIO_VALUE = "portfolio_value"
    POSITION_SIZE = "position_size"
    DRAWDOWN = "drawdown"
    CUSTOM = "custom"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"
    EXPIRED = "expired"


@dataclass
class Alert:
    """Alert configuration"""
    id: str
    name: str
    alert_type: AlertType
    status: AlertStatus = AlertStatus.ACTIVE

    # Trigger conditions
    symbol: Optional[str] = None
    target_value: Optional[float] = None
    comparison: str = ">"  # >, <, >=, <=, ==

    # Notification settings
    notify_once: bool = True
    cooldown_seconds: int = 300  # 5 minutes

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    last_check: Optional[datetime] = None
    trigger_count: int = 0

    # Custom condition function (for CUSTOM alerts)
    condition_fn: Optional[Callable] = None


class AlertEngine:
    """
    Custom Alert Engine

    Supports configurable alerts for:
    - Price movements (above/below thresholds)
    - Profit targets
    - Loss limits
    - Margin usage warnings
    - Portfolio value milestones
    - Position size limits
    - Drawdown alerts
    - Custom conditions
    """

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Dict] = []
        self.max_history = 1000

        self.is_monitoring = False
        self.monitor_task = None
        self.check_interval = 5.0  # 5 seconds

    async def start_monitoring(self):
        """Start alert monitoring"""
        if self.is_monitoring:
            logger.warning("Alert monitoring already running")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Alert monitoring started")

    async def stop_monitoring(self):
        """Stop alert monitoring"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        try:
            while self.is_monitoring:
                try:
                    await self._check_all_alerts()
                except Exception as e:
                    logger.error(f"Error in alert monitoring: {e}")

                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Alert monitoring loop cancelled")

    async def _check_all_alerts(self):
        """Check all active alerts"""
        for alert in self.alerts.values():
            if alert.status != AlertStatus.ACTIVE:
                continue

            try:
                await self._check_alert(alert)
            except Exception as e:
                logger.error(f"Error checking alert {alert.id}: {e}")

    async def _check_alert(self, alert: Alert):
        """Check individual alert"""
        alert.last_check = datetime.now()

        # Price alerts
        if alert.alert_type in [AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW]:
            await self._check_price_alert(alert)

        # Profit/Loss alerts
        elif alert.alert_type in [AlertType.PROFIT_TARGET, AlertType.LOSS_LIMIT]:
            await self._check_pnl_alert(alert)

        # Margin alert
        elif alert.alert_type == AlertType.MARGIN_USAGE:
            await self._check_margin_alert(alert)

        # Portfolio value alert
        elif alert.alert_type == AlertType.PORTFOLIO_VALUE:
            await self._check_portfolio_alert(alert)

        # Position size alert
        elif alert.alert_type == AlertType.POSITION_SIZE:
            await self._check_position_size_alert(alert)

        # Drawdown alert
        elif alert.alert_type == AlertType.DRAWDOWN:
            await self._check_drawdown_alert(alert)

        # Custom alert
        elif alert.alert_type == AlertType.CUSTOM and alert.condition_fn:
            if await alert.condition_fn():
                await self._trigger_alert(alert, "Custom condition met")

    async def _check_price_alert(self, alert: Alert):
        """Check price alert"""
        try:
            if not alert.symbol or alert.target_value is None:
                return

            # Get current price
            ticker = await binance_client.futures_symbol_ticker(symbol=alert.symbol)

            if not ticker:
                return

            current_price = float(ticker.get('price', 0))

            # Check condition
            triggered = False

            if alert.alert_type == AlertType.PRICE_ABOVE and current_price > alert.target_value:
                triggered = True
            elif alert.alert_type == AlertType.PRICE_BELOW and current_price < alert.target_value:
                triggered = True

            if triggered:
                message = f"{alert.symbol} price {current_price:.2f} (target: {alert.target_value:.2f})"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking price alert: {e}")

    async def _check_pnl_alert(self, alert: Alert):
        """Check profit/loss alert"""
        try:
            # Get capital state
            from modules.capital import dynamic_capital_manager

            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return

            unrealized_pnl_pct = capital_state.get('unrealized_pnl_pct', 0)

            # Check condition
            triggered = False

            if alert.alert_type == AlertType.PROFIT_TARGET:
                if alert.target_value and unrealized_pnl_pct >= alert.target_value:
                    triggered = True

            elif alert.alert_type == AlertType.LOSS_LIMIT:
                if alert.target_value and unrealized_pnl_pct <= -alert.target_value:
                    triggered = True

            if triggered:
                message = f"Portfolio P&L: {unrealized_pnl_pct:.2f}% (target: {alert.target_value}%)"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking P&L alert: {e}")

    async def _check_margin_alert(self, alert: Alert):
        """Check margin usage alert"""
        try:
            # Get capital state
            from modules.capital import dynamic_capital_manager

            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return

            margin_used_pct = capital_state.get('margin_used_pct', 0)

            # Check condition
            if alert.target_value and margin_used_pct >= alert.target_value:
                message = f"Margin usage: {margin_used_pct:.1f}% (threshold: {alert.target_value}%)"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking margin alert: {e}")

    async def _check_portfolio_alert(self, alert: Alert):
        """Check portfolio value alert"""
        try:
            # Get capital state
            from modules.capital import dynamic_capital_manager

            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return

            total_equity = capital_state.get('total_equity', 0)

            # Check condition
            if alert.target_value and self._compare_values(total_equity, alert.target_value, alert.comparison):
                message = f"Portfolio value: ${total_equity:.2f} (target: ${alert.target_value:.2f})"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking portfolio alert: {e}")

    async def _check_position_size_alert(self, alert: Alert):
        """Check position size alert"""
        try:
            if not alert.symbol:
                return

            # Get position
            positions = await binance_client.futures_position_information(symbol=alert.symbol)

            if not positions:
                return

            position = positions[0]
            position_amt = abs(float(position.get('positionAmt', 0)))

            # Check condition
            if alert.target_value and position_amt >= alert.target_value:
                message = f"{alert.symbol} position size: {position_amt} (threshold: {alert.target_value})"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking position size alert: {e}")

    async def _check_drawdown_alert(self, alert: Alert):
        """Check drawdown alert"""
        try:
            # Get drawdown status
            from modules.capital import capital_orchestrator

            # Get capital state
            from modules.capital import dynamic_capital_manager

            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return

            current_balance = capital_state['total_wallet_balance']
            drawdown_state = capital_orchestrator.update_drawdown_state(current_balance)

            current_dd_pct = drawdown_state.get('current_drawdown_pct', 0)

            # Check condition
            if alert.target_value and current_dd_pct >= alert.target_value:
                message = f"Drawdown: {current_dd_pct:.2f}% (threshold: {alert.target_value}%)"
                await self._trigger_alert(alert, message)

        except Exception as e:
            logger.error(f"Error checking drawdown alert: {e}")

    def _compare_values(self, current: float, target: float, comparison: str) -> bool:
        """Compare values based on comparison operator"""
        if comparison == ">":
            return current > target
        elif comparison == "<":
            return current < target
        elif comparison == ">=":
            return current >= target
        elif comparison == "<=":
            return current <= target
        elif comparison == "==":
            return abs(current - target) < 0.01
        return False

    async def _trigger_alert(self, alert: Alert, message: str):
        """Trigger an alert"""
        # Check cooldown
        if alert.triggered_at and alert.cooldown_seconds > 0:
            elapsed = (datetime.now() - alert.triggered_at).total_seconds()
            if elapsed < alert.cooldown_seconds:
                return

        # Update alert
        alert.triggered_at = datetime.now()
        alert.trigger_count += 1

        # If notify_once, disable alert
        if alert.notify_once:
            alert.status = AlertStatus.TRIGGERED

        # Log to history
        history_entry = {
            'alert_id': alert.id,
            'alert_name': alert.name,
            'alert_type': alert.alert_type.value,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'trigger_count': alert.trigger_count
        }

        self.alert_history.append(history_entry)

        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)

        # Send notification
        try:
            from modules.control.notification_engine import notification_engine, NotificationType, NotificationPriority

            await notification_engine.send_notification(
                notification_type=NotificationType.CUSTOM_ALERT,
                title=f"🔔 Alert: {alert.name}",
                message=message,
                priority=NotificationPriority.HIGH,
                data={
                    'alert_id': alert.id,
                    'alert_type': alert.alert_type.value
                }
            )

        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")

        logger.info(f"Alert triggered: {alert.name} - {message}")

    async def create_alert(self, alert: Alert) -> Dict:
        """Create new alert"""
        try:
            self.alerts[alert.id] = alert
            logger.info(f"Created alert: {alert.name}")

            return {
                'success': True,
                'alert_id': alert.id
            }

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def update_alert(self, alert_id: str, **kwargs) -> Dict:
        """Update existing alert"""
        try:
            if alert_id not in self.alerts:
                return {
                    'success': False,
                    'message': 'Alert not found'
                }

            alert = self.alerts[alert_id]

            for key, value in kwargs.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)

            logger.info(f"Updated alert: {alert_id}")

            return {
                'success': True,
                'alert_id': alert_id
            }

        except Exception as e:
            logger.error(f"Error updating alert: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def delete_alert(self, alert_id: str) -> Dict:
        """Delete alert"""
        try:
            if alert_id in self.alerts:
                del self.alerts[alert_id]
                logger.info(f"Deleted alert: {alert_id}")

                return {
                    'success': True
                }
            else:
                return {
                    'success': False,
                    'message': 'Alert not found'
                }

        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    async def get_alerts(self, status: Optional[AlertStatus] = None) -> List[Dict]:
        """Get all alerts"""
        alerts = list(self.alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]

        return [
            {
                'id': a.id,
                'name': a.name,
                'alert_type': a.alert_type.value,
                'status': a.status.value,
                'symbol': a.symbol,
                'target_value': a.target_value,
                'comparison': a.comparison,
                'notify_once': a.notify_once,
                'trigger_count': a.trigger_count,
                'created_at': a.created_at.isoformat(),
                'triggered_at': a.triggered_at.isoformat() if a.triggered_at else None,
                'last_check': a.last_check.isoformat() if a.last_check else None
            }
            for a in alerts
        ]

    async def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get alert history"""
        return list(reversed(self.alert_history[-limit:]))


# Singleton instance
alert_engine = AlertEngine()
