"""
Trading Rules API Routes - Phase 3
CRUD endpoints for managing trading rules in database
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from models.database import SessionLocal
from api.models.trading_rules import TradingRule
from modules.rules_engine import rules_engine
from utils.logger import setup_logger

router = APIRouter(prefix="/api/rules", tags=["rules"])
logger = setup_logger("rules_api")


# ========================================
# Pydantic Models
# ========================================

class TradingRuleCreate(BaseModel):
    """Schema for creating a new trading rule."""
    rule_type: str = Field(..., description="Rule type: whitelist, sniper, filter, risk_adjustment")
    symbol: Optional[str] = Field(None, description="Symbol to apply rule to (null = all symbols)")
    priority: int = Field(0, description="Priority (higher = executed first)")
    config: dict = Field(..., description="Rule configuration as JSON")
    enabled: bool = Field(True, description="Whether rule is active")
    created_by: Optional[str] = Field("system", description="User or system identifier")
    note: Optional[str] = Field(None, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "rule_type": "whitelist",
                "symbol": None,
                "priority": 10,
                "config": {"action": "allow", "pattern": ".*USDT", "reason": "All USDT pairs"},
                "enabled": True,
                "created_by": "admin",
                "note": "Allow all USDT perpetuals"
            }
        }


class TradingRuleUpdate(BaseModel):
    """Schema for updating an existing trading rule."""
    rule_type: Optional[str] = None
    symbol: Optional[str] = None
    priority: Optional[int] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None
    note: Optional[str] = None


class TradingRuleResponse(BaseModel):
    """Schema for trading rule response."""
    id: int
    rule_type: str
    symbol: Optional[str]
    priority: int
    config: dict
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True


class RuleTypeSchema(BaseModel):
    """Schema for rule type definition."""
    type: str
    description: str
    fields: List[str]
    example: dict


# ========================================
# Endpoints
# ========================================

@router.get("", response_model=List[TradingRuleResponse])
async def list_rules(
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """
    List all trading rules with optional filters.

    Returns all rules sorted by priority (descending).
    """
    db = SessionLocal()
    try:
        query = db.query(TradingRule)

        # Apply filters
        if rule_type:
            query = query.filter(TradingRule.rule_type == rule_type)
        if enabled is not None:
            query = query.filter(TradingRule.enabled == enabled)
        if symbol:
            query = query.filter(TradingRule.symbol == symbol)

        rules = query.order_by(TradingRule.priority.desc()).all()
        logger.info(f"Listed {len(rules)} rules (filters: type={rule_type}, enabled={enabled}, symbol={symbol})")
        return rules

    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("", response_model=TradingRuleResponse, status_code=201)
async def create_rule(rule: TradingRuleCreate):
    """
    Create a new trading rule.

    Validates config schema based on rule_type and adds to database.
    Invalidates rules cache after creation.
    """
    db = SessionLocal()
    try:
        # Validate rule type
        valid_types = ["whitelist", "sniper", "filter", "risk_adjustment"]
        if rule.rule_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rule_type. Must be one of: {', '.join(valid_types)}"
            )

        # Basic config validation
        if not isinstance(rule.config, dict):
            raise HTTPException(status_code=400, detail="config must be a JSON object")

        # Create rule
        db_rule = TradingRule(
            rule_type=rule.rule_type,
            symbol=rule.symbol,
            priority=rule.priority,
            config=rule.config,
            enabled=rule.enabled,
            created_by=rule.created_by,
            note=rule.note
        )

        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)

        # Invalidate cache
        rules_engine.invalidate_cache(rule.rule_type)

        logger.info(f"Created rule {db_rule.id}: {rule.rule_type} for {rule.symbol or 'all symbols'}")
        return db_rule

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{rule_id}", response_model=TradingRuleResponse)
async def get_rule(rule_id: int):
    """Get a specific trading rule by ID."""
    db = SessionLocal()
    try:
        rule = db.query(TradingRule).filter(TradingRule.id == rule_id).first()

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{rule_id}", response_model=TradingRuleResponse)
async def update_rule(rule_id: int, rule: TradingRuleUpdate):
    """
    Update an existing trading rule.

    Only provided fields will be updated.
    Invalidates rules cache after update.
    """
    db = SessionLocal()
    try:
        db_rule = db.query(TradingRule).filter(TradingRule.id == rule_id).first()

        if not db_rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        # Update fields
        if rule.rule_type is not None:
            valid_types = ["whitelist", "sniper", "filter", "risk_adjustment"]
            if rule.rule_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid rule_type. Must be one of: {', '.join(valid_types)}"
                )
            db_rule.rule_type = rule.rule_type

        if rule.symbol is not None:
            db_rule.symbol = rule.symbol
        if rule.priority is not None:
            db_rule.priority = rule.priority
        if rule.config is not None:
            if not isinstance(rule.config, dict):
                raise HTTPException(status_code=400, detail="config must be a JSON object")
            db_rule.config = rule.config
        if rule.enabled is not None:
            db_rule.enabled = rule.enabled
        if rule.note is not None:
            db_rule.note = rule.note

        db.commit()
        db.refresh(db_rule)

        # Invalidate cache
        rules_engine.invalidate_cache(db_rule.rule_type)

        logger.info(f"Updated rule {rule_id}")
        return db_rule

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int):
    """
    Delete a trading rule (soft delete by setting enabled=False).

    This prevents accidental deletion of historical rules.
    Use force=true query param for hard delete.
    """
    db = SessionLocal()
    try:
        db_rule = db.query(TradingRule).filter(TradingRule.id == rule_id).first()

        if not db_rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        # Soft delete: just disable the rule
        db_rule.enabled = False
        db.commit()

        # Invalidate cache
        rules_engine.invalidate_cache(db_rule.rule_type)

        logger.info(f"Deleted (disabled) rule {rule_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{rule_id}/toggle", response_model=TradingRuleResponse)
async def toggle_rule(rule_id: int):
    """
    Toggle rule enabled status (enable ↔ disable).

    Invalidates rules cache after toggle.
    """
    db = SessionLocal()
    try:
        db_rule = db.query(TradingRule).filter(TradingRule.id == rule_id).first()

        if not db_rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        # Toggle
        db_rule.enabled = not db_rule.enabled
        db.commit()
        db.refresh(db_rule)

        # Invalidate cache
        rules_engine.invalidate_cache(db_rule.rule_type)

        logger.info(f"Toggled rule {rule_id} to enabled={db_rule.enabled}")
        return db_rule

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/types/schemas", response_model=List[RuleTypeSchema])
async def get_rule_type_schemas():
    """
    Get available rule types and their configuration schemas.

    Useful for frontend form generation.
    """
    schemas = [
        {
            "type": "whitelist",
            "description": "Symbol allow/block rules with regex support",
            "fields": ["action", "pattern", "reason"],
            "example": {
                "action": "allow",
                "pattern": ".*USDT",
                "reason": "All USDT perpetual pairs"
            }
        },
        {
            "type": "sniper",
            "description": "Quick trade configurations for symbols",
            "fields": ["tp_pct", "sl_pct", "leverage", "max_slots"],
            "example": {
                "tp_pct": 1.5,
                "sl_pct": 0.8,
                "leverage": 5,
                "max_slots": 2
            }
        },
        {
            "type": "filter",
            "description": "Market scanning filters (volume, volatility, etc.)",
            "fields": ["min_volume_24h", "min_price_change_pct", "max_symbols"],
            "example": {
                "min_volume_24h": 50000000,
                "min_price_change_pct": 2.0,
                "max_symbols": 20
            }
        },
        {
            "type": "risk_adjustment",
            "description": "Symbol-specific risk multipliers",
            "fields": ["risk_multiplier", "max_leverage"],
            "example": {
                "risk_multiplier": 1.5,
                "max_leverage": 20
            }
        }
    ]

    return schemas
