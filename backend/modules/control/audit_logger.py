"""
Audit Log System
Centralized logging of all critical actions for compliance and debugging
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import setup_logger

logger = setup_logger("audit_logger")


class AuditAction(str, Enum):
    """Audit action types"""
    # Trading actions
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_MODIFIED = "order_modified"

    # Position actions
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_MODIFIED = "position_modified"
    LEVERAGE_CHANGED = "leverage_changed"
    STOP_LOSS_MODIFIED = "stop_loss_modified"
    TAKE_PROFIT_MODIFIED = "take_profit_modified"

    # Bot actions
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_PAUSED = "bot_paused"
    BOT_RESUMED = "bot_resumed"
    BOT_CONFIG_CHANGED = "bot_config_changed"

    # Manual control
    MANUAL_CLOSE = "manual_close"
    MANUAL_ADJUSTMENT = "manual_adjustment"

    # Emergency actions
    PANIC_CLOSE = "panic_close"
    EMERGENCY_STOP = "emergency_stop"
    CIRCUIT_BREAKER = "circuit_breaker"

    # Alert actions
    ALERT_CREATED = "alert_created"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_DELETED = "alert_deleted"

    # Settings
    SETTINGS_CHANGED = "settings_changed"
    RULE_CREATED = "rule_created"
    RULE_MODIFIED = "rule_modified"
    RULE_DELETED = "rule_deleted"

    # System
    API_KEY_CHANGED = "api_key_changed"
    WEBHOOK_TRIGGERED = "webhook_triggered"
    ERROR_OCCURRED = "error_occurred"


class AuditLevel(str, Enum):
    """Audit log levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Audit log entry"""
    id: int
    timestamp: datetime
    action: AuditAction
    level: AuditLevel
    user: str  # "bot" or "manual" or user ID
    message: str
    metadata: Dict = field(default_factory=dict)

    # Request info (for API calls)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action': self.action.value,
            'level': self.level.value,
            'user': self.user,
            'message': self.message,
            'metadata': self.metadata,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }


class AuditLogger:
    """
    Audit Log System

    Features:
    - Centralized logging of all critical actions
    - Structured logging with metadata
    - Search and filter capabilities
    - Export to JSON/CSV
    - Retention policy
    """

    def __init__(self):
        self.audit_log: List[AuditEntry] = []
        self.max_entries = 10000
        self.entry_counter = 0

        # Retention settings
        self.retention_days = 90  # Keep logs for 90 days

    async def log(
        self,
        action: AuditAction,
        message: str,
        level: AuditLevel = AuditLevel.INFO,
        user: str = "bot",
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEntry:
        """
        Log an audit entry

        Args:
            action: Action type
            message: Human-readable message
            level: Log level
            user: User who performed action
            metadata: Additional metadata
            ip_address: IP address (for API calls)
            user_agent: User agent (for API calls)

        Returns:
            Created audit entry
        """
        try:
            entry = AuditEntry(
                id=self.entry_counter,
                timestamp=datetime.now(),
                action=action,
                level=level,
                user=user,
                message=message,
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent
            )

            self.entry_counter += 1

            # Add to log
            self.audit_log.append(entry)

            # Trim if needed
            if len(self.audit_log) > self.max_entries:
                self.audit_log.pop(0)

            # Log to file logger as well
            if level == AuditLevel.CRITICAL:
                logger.critical(f"[AUDIT] {action.value}: {message}")
            elif level == AuditLevel.WARNING:
                logger.warning(f"[AUDIT] {action.value}: {message}")
            else:
                logger.info(f"[AUDIT] {action.value}: {message}")

            return entry

        except Exception as e:
            logger.error(f"Error logging audit entry: {e}")
            return None

    async def search(
        self,
        action: Optional[AuditAction] = None,
        level: Optional[AuditLevel] = None,
        user: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Search audit log

        Args:
            action: Filter by action type
            level: Filter by level
            user: Filter by user
            start_date: Filter by start date
            end_date: Filter by end date
            search_text: Search in message and metadata
            limit: Maximum results

        Returns:
            Filtered audit entries
        """
        try:
            filtered = []

            for entry in reversed(self.audit_log):
                # Apply filters
                if action and entry.action != action:
                    continue

                if level and entry.level != level:
                    continue

                if user and entry.user != user:
                    continue

                if start_date and entry.timestamp < start_date:
                    continue

                if end_date and entry.timestamp > end_date:
                    continue

                if search_text:
                    search_lower = search_text.lower()
                    if (search_lower not in entry.message.lower() and
                        search_lower not in json.dumps(entry.metadata).lower()):
                        continue

                filtered.append(entry)

                if len(filtered) >= limit:
                    break

            return filtered

        except Exception as e:
            logger.error(f"Error searching audit log: {e}")
            return []

    async def get_recent(self, limit: int = 100) -> List[AuditEntry]:
        """Get most recent audit entries"""
        return list(reversed(self.audit_log[-limit:]))

    async def get_by_id(self, entry_id: int) -> Optional[AuditEntry]:
        """Get audit entry by ID"""
        for entry in self.audit_log:
            if entry.id == entry_id:
                return entry
        return None

    async def cleanup_old_entries(self):
        """Remove entries older than retention period"""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)

            original_count = len(self.audit_log)

            self.audit_log = [
                entry for entry in self.audit_log
                if entry.timestamp >= cutoff
            ]

            removed_count = original_count - len(self.audit_log)

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old audit entries")

        except Exception as e:
            logger.error(f"Error cleaning up audit log: {e}")

    async def export_json(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export audit log to JSON

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            JSON string
        """
        try:
            entries = self.audit_log

            # Filter by date if provided
            if start_date or end_date:
                entries = []
                for entry in self.audit_log:
                    if start_date and entry.timestamp < start_date:
                        continue
                    if end_date and entry.timestamp > end_date:
                        continue
                    entries.append(entry)

            # Convert to dict
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_entries': len(entries),
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'entries': [entry.to_dict() for entry in entries]
            }

            return json.dumps(export_data, indent=2)

        except Exception as e:
            logger.error(f"Error exporting audit log: {e}")
            return ""

    async def get_statistics(self) -> Dict:
        """Get audit log statistics"""
        try:
            if len(self.audit_log) == 0:
                return {
                    'total_entries': 0,
                    'by_action': {},
                    'by_level': {},
                    'by_user': {},
                    'oldest_entry': None,
                    'newest_entry': None
                }

            # Count by action
            by_action = {}
            for entry in self.audit_log:
                action = entry.action.value
                by_action[action] = by_action.get(action, 0) + 1

            # Count by level
            by_level = {}
            for entry in self.audit_log:
                level = entry.level.value
                by_level[level] = by_level.get(level, 0) + 1

            # Count by user
            by_user = {}
            for entry in self.audit_log:
                user = entry.user
                by_user[user] = by_user.get(user, 0) + 1

            return {
                'total_entries': len(self.audit_log),
                'by_action': by_action,
                'by_level': by_level,
                'by_user': by_user,
                'oldest_entry': self.audit_log[0].timestamp.isoformat() if self.audit_log else None,
                'newest_entry': self.audit_log[-1].timestamp.isoformat() if self.audit_log else None
            }

        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {}


# Singleton instance
audit_logger = AuditLogger()
