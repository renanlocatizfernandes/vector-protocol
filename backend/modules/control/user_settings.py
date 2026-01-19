"""
User Settings & Preferences Manager
Persistent configuration and user profiles
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict

from utils.logger import setup_logger

logger = setup_logger("user_settings")


class SettingsCategory(str, Enum):
    """Settings categories"""
    TRADING = "trading"
    NOTIFICATIONS = "notifications"
    DISPLAY = "display"
    RISK = "risk"
    ALERTS = "alerts"
    ADVANCED = "advanced"


@dataclass
class UserProfile:
    """User profile/preset"""
    id: str
    name: str
    description: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    is_active: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'settings': self.settings,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'is_active': self.is_active
        }


class UserSettingsManager:
    """
    User Settings & Preferences Manager

    Features:
    - Persistent user settings
    - Multiple profiles/presets
    - Category-based organization
    - Settings validation
    - Import/export
    """

    def __init__(self):
        self.settings: Dict[str, Any] = {}
        self.profiles: Dict[str, UserProfile] = {}
        self.active_profile_id: Optional[str] = None

        # Initialize default settings
        self._initialize_default_settings()

        # Create default profiles
        self._create_default_profiles()

    def _initialize_default_settings(self):
        """Initialize default settings"""
        self.settings = {
            # Trading settings
            'trading': {
                'default_leverage': 10,
                'max_leverage': 20,
                'default_risk_pct': 2.0,
                'max_daily_trades': 20,
                'min_signal_score': 70,
                'enable_trailing_stop': True,
                'use_post_only_orders': False,
                'order_timeout_sec': 3
            },

            # Notification settings
            'notifications': {
                'telegram_enabled': True,
                'websocket_enabled': True,
                'email_enabled': False,
                'notify_on_trade_open': True,
                'notify_on_trade_close': True,
                'notify_on_profit': True,
                'notify_on_loss': True,
                'notify_on_margin_warning': True,
                'min_profit_pct_notify': 5.0,
                'min_loss_pct_notify': 3.0
            },

            # Display settings
            'display': {
                'theme': 'dark',
                'language': 'en',
                'currency': 'USD',
                'decimal_places': 2,
                'show_pnl_as_percentage': True,
                'dashboard_refresh_interval': 5,
                'chart_default_timeframe': '5m'
            },

            # Risk settings
            'risk': {
                'max_portfolio_risk_pct': 15.0,
                'max_margin_usage_pct': 75.0,
                'enable_circuit_breaker': True,
                'circuit_breaker_loss_pct': 10.0,
                'enable_drawdown_protection': True,
                'max_drawdown_pct': 20.0
            },

            # Alert settings
            'alerts': {
                'enable_price_alerts': True,
                'enable_profit_alerts': True,
                'enable_margin_alerts': True,
                'alert_check_interval': 5
            },

            # Advanced settings
            'advanced': {
                'enable_auto_sync': True,
                'enable_market_stream': True,
                'enable_user_stream': False,
                'log_level': 'INFO',
                'cache_ttl': 60,
                'max_concurrent_trades': 5
            }
        }

    def _create_default_profiles(self):
        """Create default profiles"""

        # Conservative profile
        self.create_profile(UserProfile(
            id="conservative",
            name="Conservative",
            description="Low risk, stable returns",
            settings={
                'trading': {
                    'default_leverage': 5,
                    'max_leverage': 10,
                    'default_risk_pct': 1.0,
                    'max_daily_trades': 10
                },
                'risk': {
                    'max_portfolio_risk_pct': 10.0,
                    'max_margin_usage_pct': 50.0,
                    'circuit_breaker_loss_pct': 5.0
                }
            }
        ))

        # Moderate profile (default)
        self.create_profile(UserProfile(
            id="moderate",
            name="Moderate",
            description="Balanced risk and reward",
            settings={
                'trading': {
                    'default_leverage': 10,
                    'max_leverage': 20,
                    'default_risk_pct': 2.0,
                    'max_daily_trades': 20
                },
                'risk': {
                    'max_portfolio_risk_pct': 15.0,
                    'max_margin_usage_pct': 75.0,
                    'circuit_breaker_loss_pct': 10.0
                }
            },
            is_active=True
        ))

        # Aggressive profile
        self.create_profile(UserProfile(
            id="aggressive",
            name="Aggressive",
            description="High risk, high reward",
            settings={
                'trading': {
                    'default_leverage': 15,
                    'max_leverage': 20,
                    'default_risk_pct': 3.0,
                    'max_daily_trades': 30
                },
                'risk': {
                    'max_portfolio_risk_pct': 20.0,
                    'max_margin_usage_pct': 85.0,
                    'circuit_breaker_loss_pct': 15.0
                }
            }
        ))

        self.active_profile_id = "moderate"

    def get_setting(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a specific setting

        Args:
            category: Settings category
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        try:
            if category in self.settings and key in self.settings[category]:
                return self.settings[category][key]
            return default

        except Exception as e:
            logger.error(f"Error getting setting {category}.{key}: {e}")
            return default

    def set_setting(self, category: str, key: str, value: Any) -> Dict:
        """
        Set a specific setting

        Args:
            category: Settings category
            key: Setting key
            value: Setting value

        Returns:
            Result dict
        """
        try:
            if category not in self.settings:
                self.settings[category] = {}

            self.settings[category][key] = value

            logger.info(f"Setting updated: {category}.{key} = {value}")

            return {
                'success': True,
                'category': category,
                'key': key,
                'value': value
            }

        except Exception as e:
            logger.error(f"Error setting {category}.{key}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def get_category(self, category: str) -> Dict:
        """Get all settings in a category"""
        return self.settings.get(category, {})

    def set_category(self, category: str, settings: Dict) -> Dict:
        """Set multiple settings in a category"""
        try:
            if category not in self.settings:
                self.settings[category] = {}

            self.settings[category].update(settings)

            logger.info(f"Category updated: {category}")

            return {
                'success': True,
                'category': category,
                'updated_keys': list(settings.keys())
            }

        except Exception as e:
            logger.error(f"Error updating category {category}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def get_all_settings(self) -> Dict:
        """Get all settings"""
        return self.settings.copy()

    def reset_to_defaults(self) -> Dict:
        """Reset all settings to defaults"""
        try:
            self._initialize_default_settings()

            logger.info("Settings reset to defaults")

            return {
                'success': True,
                'message': 'Settings reset to defaults'
            }

        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def create_profile(self, profile: UserProfile) -> Dict:
        """Create new profile"""
        try:
            self.profiles[profile.id] = profile

            logger.info(f"Profile created: {profile.name}")

            return {
                'success': True,
                'profile_id': profile.id
            }

        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def update_profile(self, profile_id: str, **kwargs) -> Dict:
        """Update existing profile"""
        try:
            if profile_id not in self.profiles:
                return {
                    'success': False,
                    'message': 'Profile not found'
                }

            profile = self.profiles[profile_id]

            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            profile.last_modified = datetime.now()

            logger.info(f"Profile updated: {profile_id}")

            return {
                'success': True,
                'profile_id': profile_id
            }

        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def delete_profile(self, profile_id: str) -> Dict:
        """Delete profile"""
        try:
            if profile_id not in self.profiles:
                return {
                    'success': False,
                    'message': 'Profile not found'
                }

            # Don't allow deleting active profile
            if profile_id == self.active_profile_id:
                return {
                    'success': False,
                    'message': 'Cannot delete active profile'
                }

            del self.profiles[profile_id]

            logger.info(f"Profile deleted: {profile_id}")

            return {
                'success': True
            }

        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def activate_profile(self, profile_id: str) -> Dict:
        """Activate a profile (apply its settings)"""
        try:
            if profile_id not in self.profiles:
                return {
                    'success': False,
                    'message': 'Profile not found'
                }

            # Deactivate current profile
            if self.active_profile_id and self.active_profile_id in self.profiles:
                self.profiles[self.active_profile_id].is_active = False

            # Activate new profile
            profile = self.profiles[profile_id]
            profile.is_active = True
            self.active_profile_id = profile_id

            # Apply profile settings
            for category, settings in profile.settings.items():
                if category in self.settings:
                    self.settings[category].update(settings)

            logger.info(f"Profile activated: {profile.name}")

            return {
                'success': True,
                'active_profile': profile.to_dict()
            }

        except Exception as e:
            logger.error(f"Error activating profile: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def get_profiles(self) -> List[Dict]:
        """Get all profiles"""
        return [p.to_dict() for p in self.profiles.values()]

    def get_active_profile(self) -> Optional[Dict]:
        """Get active profile"""
        if self.active_profile_id and self.active_profile_id in self.profiles:
            return self.profiles[self.active_profile_id].to_dict()
        return None

    def export_settings(self) -> str:
        """Export settings to JSON"""
        try:
            export_data = {
                'export_date': datetime.now().isoformat(),
                'settings': self.settings,
                'profiles': [p.to_dict() for p in self.profiles.values()],
                'active_profile_id': self.active_profile_id
            }

            return json.dumps(export_data, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return ""

    def import_settings(self, json_data: str) -> Dict:
        """Import settings from JSON"""
        try:
            data = json.loads(json_data)

            # Import settings
            if 'settings' in data:
                self.settings = data['settings']

            # Import profiles
            if 'profiles' in data:
                for profile_data in data['profiles']:
                    profile = UserProfile(
                        id=profile_data['id'],
                        name=profile_data['name'],
                        description=profile_data.get('description', ''),
                        settings=profile_data.get('settings', {}),
                        created_at=datetime.fromisoformat(profile_data['created_at']),
                        last_modified=datetime.fromisoformat(profile_data['last_modified']),
                        is_active=profile_data.get('is_active', False)
                    )
                    self.profiles[profile.id] = profile

            # Set active profile
            if 'active_profile_id' in data:
                self.active_profile_id = data['active_profile_id']

            logger.info("Settings imported successfully")

            return {
                'success': True,
                'message': 'Settings imported successfully'
            }

        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return {
                'success': False,
                'message': str(e)
            }


# Singleton instance
user_settings_manager = UserSettingsManager()
