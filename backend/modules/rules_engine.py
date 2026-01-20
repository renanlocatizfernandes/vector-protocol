"""
Rules Engine - Phase 3
Manages persistent trading rules from database with caching
"""
import re
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from models.database import SessionLocal
from api.models.trading_rules import TradingRule
from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("rules_engine")
settings = get_settings()


class RulesEngine:
    """
    Manages trading rules from database with intelligent caching.

    Features:
    - Rule caching with 1-minute TTL
    - Whitelist/blacklist filtering with regex support
    - Symbol-specific sniper configurations
    - Risk adjustment multipliers
    - Priority-based rule execution
    """

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # {cache_key: (data, expiry_time)}
        self._cache_ttl = 60  # 1 minute cache

    def _is_expired(self, cache_key: str) -> bool:
        """Check if cache entry is expired."""
        if cache_key not in self._cache:
            return True
        _, expiry = self._cache[cache_key]
        return time.time() > expiry

    async def get_active_rules(self, rule_type: Optional[str] = None) -> List[TradingRule]:
        """
        Fetch active rules from DB with caching.

        Args:
            rule_type: Filter by specific rule type (whitelist, sniper, etc.)

        Returns:
            List of active TradingRule objects, sorted by priority (descending)
        """
        cache_key = f"rules:{rule_type or 'all'}"

        # Check cache
        if not self._is_expired(cache_key):
            rules, _ = self._cache[cache_key]
            logger.debug(f"Cache hit for {cache_key} ({len(rules)} rules)")
            return rules

        # Fetch from DB
        db = SessionLocal()
        try:
            query = db.query(TradingRule).filter(TradingRule.enabled == True)
            if rule_type:
                query = query.filter(TradingRule.rule_type == rule_type)

            rules = query.order_by(TradingRule.priority.desc()).all()

            # Cache results
            expiry = time.time() + self._cache_ttl
            self._cache[cache_key] = (rules, expiry)

            logger.debug(f"Fetched {len(rules)} active rules from DB (type={rule_type or 'all'})")
            return rules

        except Exception as e:
            logger.error(f"Error fetching rules from DB: {e}")
            return []
        finally:
            db.close()

    async def apply_whitelist_rules(self, symbols: List[str]) -> List[str]:
        """
        Filter symbols through whitelist/blacklist rules.

        Rules are processed in priority order:
        - Allow rules add symbols to the allowed set
        - Block rules remove symbols from the final result

        Args:
            symbols: List of symbols to filter

        Returns:
            Filtered list of symbols
        """
        rules = await self.get_active_rules('whitelist')

        if not rules:
            logger.debug("No whitelist rules found, returning all symbols")
            return symbols

        allowed = set()
        blocked = set()

        for rule in rules:
            config = rule.config
            action = config.get('action', 'allow')

            if action == 'allow':
                # Symbol-specific allow
                if rule.symbol:
                    allowed.add(rule.symbol)
                # Pattern-based allow
                elif 'pattern' in config:
                    try:
                        pattern = re.compile(config['pattern'])
                        matched = [s for s in symbols if pattern.match(s)]
                        allowed.update(matched)
                        logger.debug(f"Pattern '{config['pattern']}' matched {len(matched)} symbols")
                    except re.error as e:
                        logger.error(f"Invalid regex pattern in rule {rule.id}: {e}")

            elif action == 'block':
                # Symbol-specific block
                if rule.symbol:
                    blocked.add(rule.symbol)
                # Pattern-based block
                elif 'pattern' in config:
                    try:
                        pattern = re.compile(config['pattern'])
                        matched = [s for s in symbols if pattern.match(s)]
                        blocked.update(matched)
                        logger.debug(f"Block pattern '{config['pattern']}' matched {len(matched)} symbols")
                    except re.error as e:
                        logger.error(f"Invalid regex pattern in rule {rule.id}: {e}")

        # Apply filters
        filtered = symbols
        if allowed:
            filtered = [s for s in filtered if s in allowed]
            logger.info(f"Whitelist rules: {len(allowed)} symbols allowed")

        if blocked:
            filtered = [s for s in filtered if s not in blocked]
            logger.info(f"Blacklist rules: {len(blocked)} symbols blocked")

        logger.info(f"Filtered {len(symbols)} → {len(filtered)} symbols via whitelist rules")
        return filtered

    async def get_sniper_config(self, symbol: Optional[str] = None) -> Dict:
        """
        Get sniper configuration for symbol or global default.

        Symbol-specific configs override global defaults.

        Args:
            symbol: Symbol to get config for (optional)

        Returns:
            Sniper config dict with tp_pct, sl_pct, leverage, max_slots
        """
        rules = await self.get_active_rules('sniper')

        # Check for symbol-specific override
        if symbol:
            for rule in rules:
                if rule.symbol == symbol:
                    logger.debug(f"Using symbol-specific sniper config for {symbol}")
                    return rule.config

        # Use global default
        for rule in rules:
            if rule.symbol is None:
                logger.debug(f"Using global sniper config{f' for {symbol}' if symbol else ''}")
                return rule.config

        # Fallback to settings
        fallback = {
            "tp_pct": getattr(settings, "SNIPER_TP_PCT", 1.5),
            "sl_pct": getattr(settings, "SNIPER_SL_PCT", 0.8),
            "leverage": getattr(settings, "SNIPER_DEFAULT_LEVERAGE", 5),
            "max_slots": getattr(settings, "SNIPER_EXTRA_SLOTS", 2)
        }
        logger.debug("No sniper rules found, using fallback config")
        return fallback

    async def get_risk_adjustment(self, symbol: str) -> Dict:
        """
        Get risk multipliers for specific symbol.

        Args:
            symbol: Symbol to check

        Returns:
            Dict with risk_multiplier and leverage_override
        """
        rules = await self.get_active_rules('risk_adjustment')

        for rule in rules:
            if rule.symbol == symbol:
                adjustment = {
                    "risk_multiplier": rule.config.get("risk_multiplier", 1.0),
                    "leverage_override": rule.config.get("max_leverage")
                }
                logger.debug(f"Risk adjustment for {symbol}: {adjustment}")
                return adjustment

        # Default: no adjustment
        return {"risk_multiplier": 1.0, "leverage_override": None}

    def invalidate_cache(self, rule_type: Optional[str] = None):
        """
        Manually invalidate cache for specific rule type or all rules.

        Args:
            rule_type: Rule type to invalidate, or None for all
        """
        if rule_type:
            cache_key = f"rules:{rule_type}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Cache invalidated for {rule_type}")
        else:
            self._cache.clear()
            logger.debug("All rule caches invalidated")


# Singleton instance
rules_engine = RulesEngine()
