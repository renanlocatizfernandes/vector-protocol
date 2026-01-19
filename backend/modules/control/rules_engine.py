"""
Custom Rules Engine
Define and enforce trading rules based on time, limits, and conditions
"""

from datetime import datetime, time as datetime_time
from typing import Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import setup_logger

logger = setup_logger("rules_engine")


class RuleType(str, Enum):
    """Rule types"""
    TEMPORAL = "temporal"  # Time-based rules
    LIMIT = "limit"  # Value/count limits
    CONDITION = "condition"  # Custom conditions


class RuleStatus(str, Enum):
    """Rule status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    VIOLATED = "violated"


@dataclass
class TradingRule:
    """Trading rule definition"""
    id: str
    name: str
    rule_type: RuleType
    status: RuleStatus = RuleStatus.ACTIVE
    description: str = ""

    # Temporal rules (time-based)
    allowed_hours: Optional[List[int]] = None  # [9, 10, 11, ..., 16] for 9am-4pm
    allowed_days: Optional[List[int]] = None  # [1, 2, 3, 4, 5] for Mon-Fri (1=Mon, 7=Sun)
    start_time: Optional[datetime_time] = None  # e.g., 09:00
    end_time: Optional[datetime_time] = None  # e.g., 17:00

    # Limit rules
    max_daily_trades: Optional[int] = None
    max_position_size_usd: Optional[float] = None
    max_leverage: Optional[int] = None
    max_loss_per_day: Optional[float] = None
    max_loss_per_trade: Optional[float] = None
    min_profit_target: Optional[float] = None

    # Condition rules
    condition_fn: Optional[Callable] = None  # Custom condition function

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    last_checked: Optional[datetime] = None
    violation_count: int = 0

    # Enforcement
    enforce: bool = True  # If True, blocks actions; if False, only warns
    violation_action: str = "block"  # "block", "warn", "notify"


class RulesEngine:
    """
    Custom Rules Engine

    Enforces trading rules:
    - Temporal: Trading hours, days of week
    - Limits: Max trades per day, max position size, max leverage
    - Conditions: Custom rules (e.g., no trading during high volatility)
    """

    def __init__(self):
        self.rules: Dict[str, TradingRule] = {}
        self.violation_history: List[Dict] = []
        self.max_history = 500

        # Daily tracking
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades_count': 0,
            'total_loss': 0.0,
            'total_profit': 0.0
        }

        # Create default rules
        self._create_default_rules()

    def _create_default_rules(self):
        """Create default trading rules"""

        # Rule: No weekend trading
        self.add_rule(TradingRule(
            id="no_weekend_trading",
            name="No Weekend Trading",
            rule_type=RuleType.TEMPORAL,
            description="Block trading on weekends (Sat-Sun)",
            allowed_days=[1, 2, 3, 4, 5],  # Mon-Fri only
            enforce=True
        ))

        # Rule: Max 20 trades per day
        self.add_rule(TradingRule(
            id="max_daily_trades",
            name="Max 20 Trades Per Day",
            rule_type=RuleType.LIMIT,
            description="Limit to 20 trades per day",
            max_daily_trades=20,
            enforce=True
        ))

        # Rule: Max 10% loss per day
        self.add_rule(TradingRule(
            id="max_daily_loss",
            name="Max 10% Daily Loss",
            rule_type=RuleType.LIMIT,
            description="Stop trading if daily loss exceeds 10%",
            max_loss_per_day=10.0,
            enforce=True
        ))

        # Rule: Max 20x leverage
        self.add_rule(TradingRule(
            id="max_leverage_limit",
            name="Max Leverage 20x",
            rule_type=RuleType.LIMIT,
            description="Cap leverage at 20x",
            max_leverage=20,
            enforce=True
        ))

    async def check_can_trade(self) -> Dict:
        """
        Check if trading is allowed based on all rules

        Returns:
            Dict with 'allowed' (bool) and 'reasons' (list of violations)
        """
        try:
            violations = []

            for rule in self.rules.values():
                if rule.status != RuleStatus.ACTIVE:
                    continue

                rule.last_checked = datetime.now()

                # Check rule
                violated, reason = await self._check_rule(rule)

                if violated:
                    violations.append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'reason': reason,
                        'enforce': rule.enforce,
                        'action': rule.violation_action
                    })

                    # Log violation
                    await self._log_violation(rule, reason)

                    # Update rule
                    rule.violation_count += 1

                    if rule.enforce:
                        rule.status = RuleStatus.VIOLATED

            # Determine if trading is allowed
            enforced_violations = [v for v in violations if v['enforce']]

            allowed = len(enforced_violations) == 0

            return {
                'allowed': allowed,
                'violations': violations,
                'enforced_violations': enforced_violations,
                'total_active_rules': len([r for r in self.rules.values() if r.status == RuleStatus.ACTIVE])
            }

        except Exception as e:
            logger.error(f"Error checking trading rules: {e}")
            return {
                'allowed': True,  # Fail open
                'violations': [],
                'error': str(e)
            }

    async def _check_rule(self, rule: TradingRule) -> tuple[bool, str]:
        """
        Check if a rule is violated

        Returns:
            (violated: bool, reason: str)
        """
        try:
            # Temporal rules
            if rule.rule_type == RuleType.TEMPORAL:
                return self._check_temporal_rule(rule)

            # Limit rules
            elif rule.rule_type == RuleType.LIMIT:
                return await self._check_limit_rule(rule)

            # Condition rules
            elif rule.rule_type == RuleType.CONDITION:
                return await self._check_condition_rule(rule)

            return False, ""

        except Exception as e:
            logger.error(f"Error checking rule {rule.id}: {e}")
            return False, ""

    def _check_temporal_rule(self, rule: TradingRule) -> tuple[bool, str]:
        """Check temporal (time-based) rule"""
        now = datetime.now()

        # Check allowed days
        if rule.allowed_days:
            current_day = now.isoweekday()  # 1=Mon, 7=Sun
            if current_day not in rule.allowed_days:
                day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
                return True, f"Trading not allowed on {day_names[current_day]}"

        # Check allowed hours
        if rule.allowed_hours:
            current_hour = now.hour
            if current_hour not in rule.allowed_hours:
                return True, f"Trading not allowed at {current_hour}:00"

        # Check start/end time
        if rule.start_time and rule.end_time:
            current_time = now.time()
            if not (rule.start_time <= current_time <= rule.end_time):
                return True, f"Trading only allowed between {rule.start_time} and {rule.end_time}"

        return False, ""

    async def _check_limit_rule(self, rule: TradingRule) -> tuple[bool, str]:
        """Check limit rule"""
        # Reset daily stats if new day
        self._check_reset_daily_stats()

        # Check max daily trades
        if rule.max_daily_trades:
            if self.daily_stats['trades_count'] >= rule.max_daily_trades:
                return True, f"Max daily trades reached ({rule.max_daily_trades})"

        # Check max daily loss
        if rule.max_loss_per_day:
            # Get current capital state
            try:
                from modules.capital import dynamic_capital_manager
                capital_state = await dynamic_capital_manager.get_capital_state()

                if capital_state:
                    unrealized_pnl_pct = capital_state.get('unrealized_pnl_pct', 0)

                    if unrealized_pnl_pct < -rule.max_loss_per_day:
                        return True, f"Daily loss limit exceeded ({unrealized_pnl_pct:.2f}% < -{rule.max_loss_per_day}%)"

            except Exception as e:
                logger.error(f"Error checking daily loss: {e}")

        # Other limits would be checked when placing trade
        # (max_leverage, max_position_size, etc.)

        return False, ""

    async def _check_condition_rule(self, rule: TradingRule) -> tuple[bool, str]:
        """Check custom condition rule"""
        if rule.condition_fn:
            try:
                result = await rule.condition_fn()
                if isinstance(result, tuple):
                    violated, reason = result
                    return violated, reason
                elif result:
                    return True, "Custom condition violated"
            except Exception as e:
                logger.error(f"Error in custom condition: {e}")

        return False, ""

    def _check_reset_daily_stats(self):
        """Reset daily stats if new day"""
        today = datetime.now().date()

        if self.daily_stats['date'] != today:
            self.daily_stats = {
                'date': today,
                'trades_count': 0,
                'total_loss': 0.0,
                'total_profit': 0.0
            }

            # Reset violated rules
            for rule in self.rules.values():
                if rule.status == RuleStatus.VIOLATED and rule.rule_type == RuleType.LIMIT:
                    rule.status = RuleStatus.ACTIVE

            logger.info("Daily stats reset for new day")

    async def record_trade(self, pnl: float):
        """Record a trade for daily tracking"""
        self._check_reset_daily_stats()

        self.daily_stats['trades_count'] += 1

        if pnl > 0:
            self.daily_stats['total_profit'] += pnl
        else:
            self.daily_stats['total_loss'] += abs(pnl)

    async def _log_violation(self, rule: TradingRule, reason: str):
        """Log rule violation"""
        violation = {
            'timestamp': datetime.now().isoformat(),
            'rule_id': rule.id,
            'rule_name': rule.name,
            'reason': reason,
            'enforce': rule.enforce,
            'action': rule.violation_action
        }

        self.violation_history.append(violation)

        if len(self.violation_history) > self.max_history:
            self.violation_history.pop(0)

        logger.warning(f"Rule violation: {rule.name} - {reason}")

    def add_rule(self, rule: TradingRule):
        """Add trading rule"""
        self.rules[rule.id] = rule
        logger.info(f"Added trading rule: {rule.name}")

    def update_rule(self, rule_id: str, **kwargs):
        """Update trading rule"""
        if rule_id not in self.rules:
            raise ValueError(f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        logger.info(f"Updated trading rule: {rule_id}")

    def delete_rule(self, rule_id: str):
        """Delete trading rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Deleted trading rule: {rule_id}")

    def get_rules(self, status: Optional[RuleStatus] = None) -> List[TradingRule]:
        """Get all rules"""
        rules = list(self.rules.values())

        if status:
            rules = [r for r in rules if r.status == status]

        return rules

    def get_violation_history(self, limit: int = 100) -> List[Dict]:
        """Get violation history"""
        return list(reversed(self.violation_history[-limit:]))

    def get_daily_stats(self) -> Dict:
        """Get daily statistics"""
        self._check_reset_daily_stats()
        return self.daily_stats.copy()


# Singleton instance
rules_engine = RulesEngine()
