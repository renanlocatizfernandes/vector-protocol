"""
User Control & Visibility System
Comprehensive control and monitoring features for trading bot
"""

from modules.control.snapshot_stream import (
    snapshot_stream_manager,
    SnapshotStreamManager
)
from modules.control.notification_engine import (
    notification_engine,
    NotificationEngine,
    NotificationType,
    NotificationPriority
)
from modules.control.manual_controls import (
    manual_control_manager,
    ManualControlManager
)
from modules.control.trade_journal import (
    trade_journal,
    TradeJournal
)
from modules.control.performance_analytics import (
    performance_analytics,
    PerformanceAnalytics
)
from modules.control.alert_engine import (
    alert_engine,
    AlertEngine,
    AlertType
)
from modules.control.emergency_controls import (
    emergency_controller,
    EmergencyController
)
from modules.control.audit_logger import (
    audit_logger,
    AuditLogger,
    AuditAction
)
from modules.control.rules_engine import (
    rules_engine,
    RulesEngine
)
from modules.control.quick_actions import (
    quick_actions_manager,
    QuickActionsManager
)
from modules.control.user_settings import (
    user_settings_manager,
    UserSettingsManager
)

__all__ = [
    # Snapshot Stream
    'snapshot_stream_manager',
    'SnapshotStreamManager',

    # Notification Engine
    'notification_engine',
    'NotificationEngine',
    'NotificationType',
    'NotificationPriority',

    # Manual Controls
    'manual_control_manager',
    'ManualControlManager',

    # Trade Journal
    'trade_journal',
    'TradeJournal',

    # Performance Analytics
    'performance_analytics',
    'PerformanceAnalytics',

    # Alert Engine
    'alert_engine',
    'AlertEngine',
    'AlertType',

    # Emergency Controls
    'emergency_controller',
    'EmergencyController',

    # Audit Logger
    'audit_logger',
    'AuditLogger',
    'AuditAction',

    # Rules Engine
    'rules_engine',
    'RulesEngine',

    # Quick Actions
    'quick_actions_manager',
    'QuickActionsManager',

    # User Settings
    'user_settings_manager',
    'UserSettingsManager',
]
