"""
Dynamic Capital Manager
Real-time tracking of available capital, margin usage, and buying power
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("dynamic_capital_manager")


class CapitalStatus(str, Enum):
    """Capital health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class CapitalSnapshot:
    """Snapshot of capital at a point in time"""

    def __init__(
        self,
        timestamp: datetime,
        wallet_balance: float,
        available_balance: float,
        margin_used: float,
        unrealized_pnl: float
    ):
        self.timestamp = timestamp
        self.wallet_balance = wallet_balance
        self.available_balance = available_balance
        self.margin_used = margin_used
        self.unrealized_pnl = unrealized_pnl

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'wallet_balance': self.wallet_balance,
            'available_balance': self.available_balance,
            'margin_used': self.margin_used,
            'unrealized_pnl': self.unrealized_pnl
        }


class DynamicCapitalManager:
    """
    Dynamic Capital Manager

    Tracks capital in real-time:
    - Total wallet balance
    - Available balance (free for new trades)
    - Margin used
    - Unrealized P&L
    - Buying power (with leverage)
    - Capital history for trend analysis
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 5  # 5 seconds for capital data

        # Historical snapshots (last 24 hours, 1 per hour)
        self.snapshots = deque(maxlen=24)
        self.last_snapshot_time = None

    async def get_capital_state(self) -> Dict:
        """
        Get current capital state

        Returns:
            Complete capital information
        """
        cache_key = "capital_state"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Get account info from Binance
            account = await binance_client.futures_account()

            if not account:
                return {}

            # Extract balances
            total_wallet_balance = float(account.get('totalWalletBalance', 0))
            available_balance = float(account.get('availableBalance', 0))
            total_margin_balance = float(account.get('totalMarginBalance', 0))
            total_unrealized_profit = float(account.get('totalUnrealizedProfit', 0))
            total_position_initial_margin = float(account.get('totalPositionInitialMargin', 0))

            # Calculate derived metrics
            margin_used = total_position_initial_margin
            margin_used_pct = (margin_used / total_wallet_balance * 100) if total_wallet_balance > 0 else 0
            margin_free = total_wallet_balance - margin_used
            margin_free_pct = 100 - margin_used_pct

            # Get max leverage info (depends on position mode)
            max_leverage = 125  # Binance max for most pairs

            # Calculate buying power
            buying_power = available_balance * max_leverage

            # Determine capital status
            capital_status = self._determine_capital_status(
                margin_used_pct,
                total_unrealized_profit,
                total_wallet_balance
            )

            # Get positions for context
            positions = await binance_client.futures_position_information()
            active_positions = [
                p for p in positions
                if abs(float(p.get('positionAmt', 0))) > 0
            ]

            # Calculate equity (wallet + unrealized)
            total_equity = total_wallet_balance + total_unrealized_profit

            # ROI calculation (vs initial balance - would need to track)
            # For now, use unrealized P&L vs wallet balance
            roi_pct = (total_unrealized_profit / total_wallet_balance * 100) if total_wallet_balance > 0 else 0

            result = {
                'timestamp': datetime.now(),

                # Core balances
                'total_wallet_balance': total_wallet_balance,
                'available_balance': available_balance,
                'total_margin_balance': total_margin_balance,
                'total_equity': total_equity,

                # Margin metrics
                'margin_used': margin_used,
                'margin_used_pct': round(margin_used_pct, 2),
                'margin_free': margin_free,
                'margin_free_pct': round(margin_free_pct, 2),

                # P&L
                'unrealized_pnl': total_unrealized_profit,
                'unrealized_pnl_pct': round(roi_pct, 2),

                # Buying power
                'max_leverage': max_leverage,
                'buying_power': buying_power,

                # Position info
                'num_positions': len(active_positions),
                'positions_value': sum(
                    abs(float(p.get('positionAmt', 0))) * float(p.get('entryPrice', 0))
                    for p in active_positions
                ),

                # Status
                'capital_status': capital_status.value,
                'status_details': self._get_status_details(capital_status, margin_used_pct)
            }

            # Cache
            self.cache[cache_key] = result

            # Save snapshot if 1 hour passed
            await self._maybe_save_snapshot(result)

            return result

        except Exception as e:
            logger.error(f"Error getting capital state: {e}")
            return {}

    def _determine_capital_status(
        self,
        margin_used_pct: float,
        unrealized_pnl: float,
        wallet_balance: float
    ) -> CapitalStatus:
        """
        Determine capital health status

        Returns:
            CapitalStatus enum
        """
        # EMERGENCY: High margin + losing money
        if margin_used_pct > 90 or (margin_used_pct > 75 and unrealized_pnl < -wallet_balance * 0.1):
            return CapitalStatus.EMERGENCY

        # CRITICAL: Very high margin usage
        if margin_used_pct > 75:
            return CapitalStatus.CRITICAL

        # WARNING: High margin or significant losses
        if margin_used_pct > 50 or unrealized_pnl < -wallet_balance * 0.05:
            return CapitalStatus.WARNING

        # HEALTHY: Normal operation
        return CapitalStatus.HEALTHY

    def _get_status_details(self, status: CapitalStatus, margin_used_pct: float) -> str:
        """Get human-readable status details"""

        if status == CapitalStatus.EMERGENCY:
            return f"EMERGENCY: Margin usage {margin_used_pct:.1f}% - immediate action required"

        elif status == CapitalStatus.CRITICAL:
            return f"CRITICAL: Margin usage {margin_used_pct:.1f}% - stop opening new positions"

        elif status == CapitalStatus.WARNING:
            return f"WARNING: Margin usage {margin_used_pct:.1f}% - be cautious"

        else:
            return f"HEALTHY: Margin usage {margin_used_pct:.1f}% - operating normally"

    async def _maybe_save_snapshot(self, capital_state: Dict):
        """Save hourly snapshot for historical analysis"""

        now = datetime.now()

        # Save snapshot every hour
        if not self.last_snapshot_time or (now - self.last_snapshot_time).seconds >= 3600:
            snapshot = CapitalSnapshot(
                timestamp=now,
                wallet_balance=capital_state['total_wallet_balance'],
                available_balance=capital_state['available_balance'],
                margin_used=capital_state['margin_used'],
                unrealized_pnl=capital_state['unrealized_pnl']
            )

            self.snapshots.append(snapshot)
            self.last_snapshot_time = now

            logger.info(f"Saved capital snapshot: balance={snapshot.wallet_balance:.2f}")

    async def get_capital_history(self, hours: int = 24) -> Dict:
        """
        Get capital history for analysis

        Args:
            hours: Number of hours to look back

        Returns:
            Historical snapshots and trend analysis
        """
        try:
            # Get snapshots from deque
            snapshots_list = list(self.snapshots)

            if not snapshots_list:
                return {
                    'snapshots': [],
                    'trend': 'UNKNOWN',
                    'growth_pct': 0.0
                }

            # Filter by time
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered = [s for s in snapshots_list if s.timestamp >= cutoff]

            if not filtered:
                return {
                    'snapshots': [],
                    'trend': 'UNKNOWN',
                    'growth_pct': 0.0
                }

            # Calculate trend
            first_balance = filtered[0].wallet_balance
            last_balance = filtered[-1].wallet_balance

            growth_pct = ((last_balance - first_balance) / first_balance * 100) if first_balance > 0 else 0

            if growth_pct > 2:
                trend = 'GROWING'
            elif growth_pct < -2:
                trend = 'DECLINING'
            else:
                trend = 'STABLE'

            # Calculate volatility (std dev of balances)
            balances = [s.wallet_balance for s in filtered]
            avg_balance = sum(balances) / len(balances)
            variance = sum((b - avg_balance) ** 2 for b in balances) / len(balances)
            volatility = variance ** 0.5

            return {
                'snapshots': [s.to_dict() for s in filtered],
                'num_snapshots': len(filtered),
                'first_balance': first_balance,
                'last_balance': last_balance,
                'growth_pct': round(growth_pct, 2),
                'trend': trend,
                'avg_balance': round(avg_balance, 2),
                'volatility': round(volatility, 2),
                'peak_balance': round(max(balances), 2),
                'lowest_balance': round(min(balances), 2)
            }

        except Exception as e:
            logger.error(f"Error getting capital history: {e}")
            return {}

    async def get_available_for_new_position(
        self,
        max_margin_usage_pct: float = 75.0
    ) -> Dict:
        """
        Calculate how much capital is available for a new position

        Args:
            max_margin_usage_pct: Maximum margin usage % to allow

        Returns:
            Available capital metrics
        """
        try:
            capital_state = await self.get_capital_state()

            if not capital_state:
                return {}

            current_margin_used_pct = capital_state['margin_used_pct']
            total_wallet = capital_state['total_wallet_balance']

            # Calculate headroom
            margin_headroom_pct = max_margin_usage_pct - current_margin_used_pct

            if margin_headroom_pct <= 0:
                return {
                    'can_open_new': False,
                    'available_capital': 0.0,
                    'available_pct': 0.0,
                    'reason': f"Margin usage {current_margin_used_pct:.1f}% exceeds max {max_margin_usage_pct}%"
                }

            # Available capital = headroom % of wallet
            available_capital = total_wallet * (margin_headroom_pct / 100)

            return {
                'can_open_new': True,
                'available_capital': available_capital,
                'available_pct': margin_headroom_pct,
                'current_margin_used_pct': current_margin_used_pct,
                'max_allowed_pct': max_margin_usage_pct,
                'recommendation': self._get_position_recommendation(margin_headroom_pct)
            }

        except Exception as e:
            logger.error(f"Error calculating available capital: {e}")
            return {}

    def _get_position_recommendation(self, headroom_pct: float) -> str:
        """Get recommendation based on margin headroom"""

        if headroom_pct > 50:
            return "LOW UTILIZATION - can open multiple positions"
        elif headroom_pct > 25:
            return "MODERATE UTILIZATION - 1-2 more positions recommended"
        elif headroom_pct > 10:
            return "HIGH UTILIZATION - 1 small position max"
        else:
            return "NEAR LIMIT - avoid opening new positions"

    async def estimate_position_margin_impact(
        self,
        symbol: str,
        quantity: float,
        leverage: int
    ) -> Dict:
        """
        Estimate margin impact of a potential position

        Args:
            symbol: Trading pair
            quantity: Position quantity
            leverage: Position leverage

        Returns:
            Margin impact analysis
        """
        try:
            # Get current price
            mark_price_data = await binance_client.futures_mark_price(symbol=symbol)
            current_price = float(mark_price_data.get('markPrice', 0))

            # Calculate position notional
            notional_value = quantity * current_price

            # Margin required
            margin_required = notional_value / leverage

            # Get current capital state
            capital_state = await self.get_capital_state()

            if not capital_state:
                return {}

            total_wallet = capital_state['total_wallet_balance']
            current_margin_used = capital_state['margin_used']

            # New margin usage
            new_margin_used = current_margin_used + margin_required
            new_margin_used_pct = (new_margin_used / total_wallet * 100) if total_wallet > 0 else 0

            # Status after opening
            new_status = self._determine_capital_status(
                new_margin_used_pct,
                capital_state['unrealized_pnl'],
                total_wallet
            )

            return {
                'symbol': symbol,
                'quantity': quantity,
                'leverage': leverage,
                'current_price': current_price,
                'notional_value': notional_value,
                'margin_required': margin_required,
                'margin_required_pct': (margin_required / total_wallet * 100) if total_wallet > 0 else 0,
                'current_margin_used_pct': capital_state['margin_used_pct'],
                'new_margin_used_pct': round(new_margin_used_pct, 2),
                'margin_increase_pct': round(new_margin_used_pct - capital_state['margin_used_pct'], 2),
                'new_capital_status': new_status.value,
                'is_safe': new_margin_used_pct < 75.0,
                'recommendation': self._get_margin_impact_recommendation(new_margin_used_pct, new_status)
            }

        except Exception as e:
            logger.error(f"Error estimating margin impact: {e}")
            return {}

    def _get_margin_impact_recommendation(
        self,
        new_margin_pct: float,
        new_status: CapitalStatus
    ) -> str:
        """Get recommendation based on margin impact"""

        if new_status == CapitalStatus.EMERGENCY or new_margin_pct > 90:
            return "REJECT - Would exceed safe margin limits"
        elif new_status == CapitalStatus.CRITICAL or new_margin_pct > 75:
            return "HIGH RISK - Only with strong conviction"
        elif new_margin_pct > 50:
            return "MODERATE RISK - Acceptable if signal is strong"
        else:
            return "LOW RISK - Safe to proceed"


# Singleton instance
dynamic_capital_manager = DynamicCapitalManager()
