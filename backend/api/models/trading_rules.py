"""
Trading Rules Model - Phase 3
Stores persistent trading rules (whitelist, sniper configs, risk adjustments)
"""
import sys
import os
from datetime import datetime

current_file = os.path.abspath(__file__)
models_dir = os.path.dirname(current_file)
api_dir = os.path.dirname(models_dir)
backend_dir = os.path.dirname(api_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from models.database import Base


class TradingRule(Base):
    """
    Trading rule for persistent configuration.

    Rule Types:
    - 'whitelist': Symbol allow/block rules
    - 'sniper': Quick trade configurations
    - 'filter': Market scanning filters
    - 'risk_adjustment': Symbol-specific risk multipliers

    Config Examples:
    - Whitelist: {"action": "allow", "pattern": ".*USDT", "reason": "All USDT pairs"}
    - Sniper: {"tp_pct": 1.5, "sl_pct": 0.8, "leverage": 5, "max_slots": 2}
    - Risk: {"risk_multiplier": 1.5, "max_leverage": 20}
    """
    __tablename__ = "trading_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False, index=True)  # whitelist, sniper, filter, risk_adjustment
    symbol = Column(String(20), nullable=True, index=True)      # null = applies to all symbols
    priority = Column(Integer, default=0, nullable=False)       # Higher priority = executed first

    # Rule configuration as JSON
    config = Column(JSON, nullable=False)

    # Status and metadata
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)  # user/system identifier

    # Optional user note/description
    note = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<TradingRule(id={self.id}, type={self.rule_type}, symbol={self.symbol}, enabled={self.enabled})>"
