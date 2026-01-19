"""
Advanced Notification Engine
Configurable multi-channel notifications with triggers and filters
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import setup_logger

logger = setup_logger("notification_engine")


class NotificationType(str, Enum):
    """Notification types"""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    POSITION_PROFIT = "position_profit"
    POSITION_LOSS = "position_loss"
    MARGIN_WARNING = "margin_warning"
    MARGIN_CRITICAL = "margin_critical"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_ERROR = "bot_error"
    CAPITAL_MILESTONE = "capital_milestone"
    DRAWDOWN_ALERT = "drawdown_alert"
    PRICE_ALERT = "price_alert"
    CUSTOM_ALERT = "custom_alert"


class NotificationPriority(str, Enum):
    """Notification priorities"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Notification channels"""
    TELEGRAM = "telegram"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class NotificationRule:
    """Notification rule configuration"""
    id: str
    name: str
    notification_type: NotificationType
    enabled: bool = True
    channels: List[NotificationChannel] = field(default_factory=list)
    priority: NotificationPriority = NotificationPriority.MEDIUM

    # Filters
    min_profit_pct: Optional[float] = None
    min_loss_pct: Optional[float] = None
    symbols: Optional[List[str]] = None  # None = all symbols

    # Rate limiting
    cooldown_seconds: int = 0  # 0 = no cooldown
    last_triggered: Optional[datetime] = None


@dataclass
class Notification:
    """Notification message"""
    id: str
    timestamp: datetime
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict = field(default_factory=dict)
    channels: List[NotificationChannel] = field(default_factory=list)


class NotificationEngine:
    """
    Advanced Notification Engine

    Features:
    - Multi-channel delivery (Telegram, WebSocket, Email, Webhook)
    - Configurable triggers and filters
    - Priority-based routing
    - Rate limiting per rule
    - Template system
    - Delivery tracking
    """

    def __init__(self):
        self.rules: Dict[str, NotificationRule] = {}
        self.notification_history: List[Notification] = []
        self.max_history = 1000

        # Channel handlers
        self.channel_handlers: Dict[NotificationChannel, Callable] = {}

        # Default rules
        self._create_default_rules()

        # Register default handlers
        self._register_default_handlers()

    def _create_default_rules(self):
        """Create default notification rules"""

        # Trade opened
        self.add_rule(NotificationRule(
            id="trade_opened_telegram",
            name="Trade Opened (Telegram)",
            notification_type=NotificationType.TRADE_OPENED,
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.WEBSOCKET],
            priority=NotificationPriority.MEDIUM
        ))

        # Trade closed
        self.add_rule(NotificationRule(
            id="trade_closed_telegram",
            name="Trade Closed (Telegram)",
            notification_type=NotificationType.TRADE_CLOSED,
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.WEBSOCKET],
            priority=NotificationPriority.MEDIUM
        ))

        # Big profit (>5%)
        self.add_rule(NotificationRule(
            id="big_profit",
            name="Big Profit Alert (>5%)",
            notification_type=NotificationType.POSITION_PROFIT,
            channels=[NotificationChannel.TELEGRAM],
            priority=NotificationPriority.HIGH,
            min_profit_pct=5.0
        ))

        # Big loss (>3%)
        self.add_rule(NotificationRule(
            id="big_loss",
            name="Big Loss Alert (>3%)",
            notification_type=NotificationType.POSITION_LOSS,
            channels=[NotificationChannel.TELEGRAM],
            priority=NotificationPriority.HIGH,
            min_loss_pct=3.0
        ))

        # Margin warning
        self.add_rule(NotificationRule(
            id="margin_warning",
            name="Margin Warning",
            notification_type=NotificationType.MARGIN_WARNING,
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.WEBSOCKET],
            priority=NotificationPriority.HIGH,
            cooldown_seconds=300  # 5 minutes
        ))

        # Margin critical
        self.add_rule(NotificationRule(
            id="margin_critical",
            name="Margin Critical",
            notification_type=NotificationType.MARGIN_CRITICAL,
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.WEBSOCKET],
            priority=NotificationPriority.CRITICAL,
            cooldown_seconds=60  # 1 minute
        ))

        # Bot errors
        self.add_rule(NotificationRule(
            id="bot_error",
            name="Bot Error",
            notification_type=NotificationType.BOT_ERROR,
            channels=[NotificationChannel.TELEGRAM],
            priority=NotificationPriority.CRITICAL
        ))

    def _register_default_handlers(self):
        """Register default channel handlers"""

        # Telegram handler
        self.register_channel_handler(
            NotificationChannel.TELEGRAM,
            self._handle_telegram
        )

        # WebSocket handler
        self.register_channel_handler(
            NotificationChannel.WEBSOCKET,
            self._handle_websocket
        )

        # Console handler
        self.register_channel_handler(
            NotificationChannel.CONSOLE,
            self._handle_console
        )

    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict] = None,
        priority: Optional[NotificationPriority] = None
    ):
        """
        Send notification through configured channels

        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data
            priority: Override priority
        """
        # Find matching rules
        matching_rules = self._find_matching_rules(notification_type, data or {})

        if not matching_rules:
            logger.debug(f"No matching rules for {notification_type}")
            return

        # Create notification
        notification = Notification(
            id=f"{notification_type.value}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            notification_type=notification_type,
            priority=priority or NotificationPriority.MEDIUM,
            title=title,
            message=message,
            data=data or {}
        )

        # Collect all channels from matching rules
        channels = set()
        for rule in matching_rules:
            channels.update(rule.channels)

        notification.channels = list(channels)

        # Save to history
        self.notification_history.append(notification)
        if len(self.notification_history) > self.max_history:
            self.notification_history.pop(0)

        # Send to all channels
        await self._deliver_notification(notification)

    def _find_matching_rules(
        self,
        notification_type: NotificationType,
        data: Dict
    ) -> List[NotificationRule]:
        """Find rules that match notification criteria"""
        matching = []

        for rule in self.rules.values():
            # Check if enabled
            if not rule.enabled:
                continue

            # Check type
            if rule.notification_type != notification_type:
                continue

            # Check cooldown
            if rule.cooldown_seconds > 0 and rule.last_triggered:
                elapsed = (datetime.now() - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue

            # Check profit filter
            if rule.min_profit_pct is not None:
                profit_pct = data.get('profit_pct', 0)
                if profit_pct < rule.min_profit_pct:
                    continue

            # Check loss filter
            if rule.min_loss_pct is not None:
                loss_pct = abs(data.get('profit_pct', 0))
                if loss_pct < rule.min_loss_pct:
                    continue

            # Check symbol filter
            if rule.symbols is not None:
                symbol = data.get('symbol')
                if symbol and symbol not in rule.symbols:
                    continue

            # Rule matches
            matching.append(rule)

            # Update last triggered
            rule.last_triggered = datetime.now()

        return matching

    async def _deliver_notification(self, notification: Notification):
        """Deliver notification to all channels"""
        tasks = []

        for channel in notification.channels:
            handler = self.channel_handlers.get(channel)

            if handler:
                tasks.append(handler(notification))
            else:
                logger.warning(f"No handler for channel: {channel}")

        # Execute all deliveries in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_telegram(self, notification: Notification):
        """Send notification via Telegram"""
        try:
            from utils.telegram_client import telegram_client

            # Format message
            priority_emoji = {
                NotificationPriority.LOW: "ℹ️",
                NotificationPriority.MEDIUM: "📢",
                NotificationPriority.HIGH: "⚠️",
                NotificationPriority.CRITICAL: "🚨"
            }

            emoji = priority_emoji.get(notification.priority, "📢")

            text = f"{emoji} *{notification.title}*\n\n{notification.message}"

            await telegram_client.send_message(text)

        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    async def _handle_websocket(self, notification: Notification):
        """Send notification via WebSocket"""
        try:
            from utils.redis_client import get_redis_client

            redis_client = await get_redis_client()

            if redis_client:
                message = {
                    'type': 'notification',
                    'notification': {
                        'id': notification.id,
                        'timestamp': notification.timestamp.isoformat(),
                        'notification_type': notification.notification_type.value,
                        'priority': notification.priority.value,
                        'title': notification.title,
                        'message': notification.message,
                        'data': notification.data
                    }
                }

                await redis_client.publish(
                    'bot_events',
                    json.dumps(message, default=str)
                )

        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")

    async def _handle_console(self, notification: Notification):
        """Log notification to console"""
        logger.info(
            f"[{notification.priority.value.upper()}] "
            f"{notification.title}: {notification.message}"
        )

    def add_rule(self, rule: NotificationRule):
        """Add notification rule"""
        self.rules[rule.id] = rule
        logger.info(f"Added notification rule: {rule.name}")

    def update_rule(self, rule_id: str, **kwargs):
        """Update notification rule"""
        if rule_id not in self.rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        logger.info(f"Updated notification rule: {rule_id}")

    def delete_rule(self, rule_id: str):
        """Delete notification rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Deleted notification rule: {rule_id}")

    def get_rules(self) -> List[NotificationRule]:
        """Get all notification rules"""
        return list(self.rules.values())

    def get_notification_history(
        self,
        limit: int = 100,
        notification_type: Optional[NotificationType] = None
    ) -> List[Notification]:
        """Get notification history"""
        history = self.notification_history

        if notification_type:
            history = [n for n in history if n.notification_type == notification_type]

        return list(reversed(history[-limit:]))

    def register_channel_handler(
        self,
        channel: NotificationChannel,
        handler: Callable
    ):
        """Register custom channel handler"""
        self.channel_handlers[channel] = handler
        logger.info(f"Registered handler for channel: {channel}")


# Singleton instance
notification_engine = NotificationEngine()
