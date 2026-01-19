"""
Advanced Trading Strategies API Routes
Endpoints for managing execution strategies, trailing stops, and strategy performance
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from utils.logger import setup_logger
from modules.strategies import (
    trailing_stop_manager,
    execution_strategy_manager,
    TrailingStopMode,
    ExecutionMode,
    MarginMode
)

logger = setup_logger("strategies_api")

router = APIRouter(prefix="/api/strategies", tags=["Advanced Strategies"])


# Pydantic models for request validation
class StrategyConfigUpdate(BaseModel):
    symbol: Optional[str] = None
    execution_mode: Optional[ExecutionMode] = None
    margin_mode: Optional[MarginMode] = None
    trailing_stop_mode: Optional[TrailingStopMode] = None
    min_profit_activation_pct: Optional[float] = None
    base_callback_pct: Optional[float] = None


class TrailingStopActivationRequest(BaseModel):
    symbol: str
    mode: Optional[TrailingStopMode] = None


# ============================================================
# Execution Strategy Endpoints
# ============================================================

@router.get("/execution-modes")
async def get_execution_modes():
    """
    Get available execution modes with descriptions

    Returns:
        Dictionary of execution modes and their characteristics
    """
    return {
        "status": "success",
        "modes": {
            "static": {
                "name": "Static Mode",
                "description": "Traditional single entry/exit trading",
                "best_for": "Standard trades with clear setups",
                "characteristics": [
                    "One market/limit entry",
                    "Fixed stop loss and take profit",
                    "No position scaling",
                    "Simple risk management"
                ]
            },
            "sniper": {
                "name": "Sniper Mode",
                "description": "Precision entries at key levels",
                "best_for": "High-confidence setups with clear support/resistance",
                "characteristics": [
                    "Limit orders at key levels",
                    "Multiple entry attempts",
                    "Price improvement focus",
                    "Timeout with market fallback"
                ]
            },
            "pyramid": {
                "name": "Pyramid Mode",
                "description": "Scale into winning positions",
                "best_for": "Strong trends with high win probability",
                "characteristics": [
                    "Add to winners (up to 4 entries)",
                    "Each entry smaller than previous",
                    "Breakeven management",
                    "Aggressive profit targets"
                ]
            },
            "dca": {
                "name": "DCA Mode",
                "description": "Dollar-cost average into losing positions",
                "best_for": "Mean-reversion strategies, high volatility",
                "characteristics": [
                    "Add to losers (up to 3 entries)",
                    "Lower average entry price",
                    "Increasing position sizes",
                    "Strict final stop loss"
                ]
            },
            "hybrid": {
                "name": "Hybrid Mode",
                "description": "ML-driven mode selection",
                "best_for": "Autonomous trading with AI optimization",
                "characteristics": [
                    "AI selects best mode per trade",
                    "Adapts to market conditions",
                    "Signal strength based",
                    "Historical performance weighted"
                ]
            }
        }
    }


@router.get("/trailing-stop-modes")
async def get_trailing_stop_modes():
    """
    Get available trailing stop modes

    Returns:
        Dictionary of trailing stop modes
    """
    return {
        "status": "success",
        "modes": {
            "disabled": {
                "name": "Disabled",
                "description": "No trailing stop"
            },
            "static": {
                "name": "Static",
                "description": "Fixed ATR-based callback",
                "callback": "1.5x ATR percentage"
            },
            "dynamic": {
                "name": "Dynamic",
                "description": "Volatility-adjusted callback",
                "callback": "Adapts to market volatility (1-4%)"
            },
            "profit_based": {
                "name": "Profit-Based",
                "description": "Activates after minimum profit",
                "activation": "After 1.5%+ profit"
            },
            "breakeven": {
                "name": "Breakeven",
                "description": "Moves stop to entry + small offset",
                "protection": "Locks in breakeven"
            },
            "smart": {
                "name": "Smart (AI-Enhanced)",
                "description": "ML-driven activation and callback",
                "features": [
                    "Multi-factor decision (profit, volatility, momentum, size)",
                    "Activation score > 40/100",
                    "Dynamic callback adjustment",
                    "Reversal protection"
                ]
            }
        }
    }


@router.get("/config")
async def get_strategy_config(symbol: Optional[str] = Query(None)):
    """
    Get strategy configuration for symbol or global

    Args:
        symbol: Optional symbol to get config for (None = global)

    Returns:
        Strategy configuration
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            if symbol:
                result = db.execute(
                    text("SELECT * FROM strategy_configurations WHERE symbol = :symbol"),
                    {"symbol": symbol}
                ).fetchone()
            else:
                result = db.execute(
                    text("SELECT * FROM strategy_configurations WHERE symbol IS NULL")
                ).fetchone()

            if result:
                return {
                    "status": "success",
                    "config": dict(result._mapping)
                }
            else:
                # Return defaults
                return {
                    "status": "success",
                    "config": {
                        "execution_mode": "static",
                        "margin_mode": "CROSSED",
                        "trailing_stop_mode": "smart",
                        "min_profit_activation_pct": 1.5,
                        "base_callback_pct": 2.0,
                        "is_active": True
                    },
                    "note": "Using default configuration"
                }

    except Exception as e:
        logger.error(f"Error getting strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_strategy_config(config: StrategyConfigUpdate):
    """
    Update strategy configuration

    Args:
        config: Strategy configuration updates

    Returns:
        Updated configuration
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            # Check if config exists
            symbol = config.symbol
            existing = db.execute(
                text("SELECT id FROM strategy_configurations WHERE symbol IS NOT DISTINCT FROM :symbol"),
                {"symbol": symbol}
            ).fetchone()

            if existing:
                # Update
                update_fields = []
                params = {"symbol": symbol}

                if config.execution_mode:
                    update_fields.append("execution_mode = :execution_mode")
                    params["execution_mode"] = config.execution_mode

                if config.margin_mode:
                    update_fields.append("margin_mode = :margin_mode")
                    params["margin_mode"] = config.margin_mode

                if config.trailing_stop_mode:
                    update_fields.append("trailing_stop_mode = :trailing_stop_mode")
                    params["trailing_stop_mode"] = config.trailing_stop_mode

                if config.min_profit_activation_pct is not None:
                    update_fields.append("min_profit_activation_pct = :min_profit_activation_pct")
                    params["min_profit_activation_pct"] = config.min_profit_activation_pct

                if config.base_callback_pct is not None:
                    update_fields.append("base_callback_pct = :base_callback_pct")
                    params["base_callback_pct"] = config.base_callback_pct

                update_fields.append("updated_at = NOW()")

                query = f"UPDATE strategy_configurations SET {', '.join(update_fields)} WHERE symbol IS NOT DISTINCT FROM :symbol"

                db.execute(text(query), params)
            else:
                # Insert
                db.execute(
                    text("""
                        INSERT INTO strategy_configurations
                        (symbol, execution_mode, margin_mode, trailing_stop_mode,
                         min_profit_activation_pct, base_callback_pct)
                        VALUES (:symbol, :execution_mode, :margin_mode, :trailing_stop_mode,
                                :min_profit_activation_pct, :base_callback_pct)
                    """),
                    {
                        "symbol": symbol,
                        "execution_mode": config.execution_mode or "static",
                        "margin_mode": config.margin_mode or "CROSSED",
                        "trailing_stop_mode": config.trailing_stop_mode or "smart",
                        "min_profit_activation_pct": config.min_profit_activation_pct or 1.5,
                        "base_callback_pct": config.base_callback_pct or 2.0
                    }
                )

            db.commit()

        return {
            "status": "success",
            "message": "Configuration updated",
            "config": config.dict(exclude_none=True)
        }

    except Exception as e:
        logger.error(f"Error updating strategy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Trailing Stop Endpoints
# ============================================================

@router.post("/trailing-stop/activate")
async def activate_trailing_stop_manual(request: TrailingStopActivationRequest):
    """
    Manually activate trailing stop for a position

    Args:
        request: Symbol and optional mode

    Returns:
        Activation result
    """
    try:
        from utils.binance_client import binance_client

        # Get current position
        positions = await binance_client.futures_position_information(symbol=request.symbol)

        active_position = None
        for pos in positions:
            if abs(float(pos.get('positionAmt', 0))) > 0:
                active_position = pos
                break

        if not active_position:
            raise HTTPException(status_code=404, detail="No active position found")

        # Check if should activate
        should_activate, trail_config = await trailing_stop_manager.should_activate_trail(
            request.symbol,
            active_position,
            mode=request.mode
        )

        if not should_activate:
            return {
                "status": "skip",
                "message": "Trailing stop activation criteria not met",
                "trail_config": trail_config
            }

        # Activate
        success = await trailing_stop_manager.activate_trailing_stop(
            request.symbol,
            active_position,
            trail_config
        )

        if success:
            return {
                "status": "success",
                "message": "Trailing stop activated",
                "trail_config": trail_config
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to activate trailing stop")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating trailing stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trailing-stop/active")
async def get_active_trailing_stops():
    """
    Get all active trailing stops

    Returns:
        List of active trailing stops
    """
    try:
        active_trails = []

        for symbol, trail_data in trailing_stop_manager.active_trails.items():
            active_trails.append({
                "symbol": symbol,
                "mode": trail_data['config']['mode'],
                "callback_rate": trail_data['config']['callback_rate'],
                "activated_at": trail_data['activated_at'].isoformat(),
                "order_id": trail_data.get('order_id'),
                "reason": trail_data['config'].get('reason', '')
            })

        return {
            "status": "success",
            "count": len(active_trails),
            "active_trails": active_trails
        }

    except Exception as e:
        logger.error(f"Error getting active trails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Strategy Performance Endpoints
# ============================================================

@router.get("/performance/summary")
async def get_strategy_performance_summary():
    """
    Get performance summary for all execution modes

    Returns:
        Performance statistics by mode
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            results = db.execute(
                text("SELECT * FROM strategy_performance_stats ORDER BY total_trades DESC")
            ).fetchall()

            stats = []
            for row in results:
                stats.append(dict(row._mapping))

            return {
                "status": "success",
                "data": stats
            }

    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/by-mode")
async def get_performance_by_mode(
    mode: ExecutionMode = Query(...),
    days: int = Query(30, ge=1, le=90)
):
    """
    Get detailed performance for specific execution mode

    Args:
        mode: Execution mode
        days: Lookback period

    Returns:
        Detailed performance metrics
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            cutoff = datetime.now() - timedelta(days=days)

            results = db.execute(
                text("""
                    SELECT *
                    FROM trade_strategy_executions
                    WHERE execution_mode = :mode
                      AND opened_at >= :cutoff
                      AND closed_at IS NOT NULL
                    ORDER BY opened_at DESC
                """),
                {"mode": mode.value, "cutoff": cutoff}
            ).fetchall()

            trades = []
            for row in results:
                trades.append(dict(row._mapping))

            # Calculate metrics
            if trades:
                total_trades = len(trades)
                winning_trades = len([t for t in trades if t.get('realized_pnl_pct', 0) > 0])
                total_pnl = sum([t.get('realized_pnl_pct', 0) for t in trades])
                avg_pnl = total_pnl / total_trades

                return {
                    "status": "success",
                    "mode": mode.value,
                    "period_days": days,
                    "summary": {
                        "total_trades": total_trades,
                        "winning_trades": winning_trades,
                        "win_rate": winning_trades / total_trades,
                        "total_pnl_pct": total_pnl,
                        "avg_pnl_pct": avg_pnl
                    },
                    "trades": trades[:50]  # Last 50
                }
            else:
                return {
                    "status": "success",
                    "mode": mode.value,
                    "period_days": days,
                    "message": "No trades found for this mode in the period"
                }

    except Exception as e:
        logger.error(f"Error getting performance by mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/trailing-stop-effectiveness")
async def get_trailing_stop_effectiveness(days: int = Query(30, ge=1, le=90)):
    """
    Analyze trailing stop effectiveness

    Args:
        days: Lookback period

    Returns:
        Trailing stop analytics
    """
    try:
        from models.database import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            cutoff = datetime.now() - timedelta(days=days)

            # Trades with trailing stop
            with_trail = db.execute(
                text("""
                    SELECT *
                    FROM trade_strategy_executions
                    WHERE trailing_stop_activated = true
                      AND opened_at >= :cutoff
                      AND closed_at IS NOT NULL
                """),
                {"cutoff": cutoff}
            ).fetchall()

            # Trades without trailing stop
            without_trail = db.execute(
                text("""
                    SELECT *
                    FROM trade_strategy_executions
                    WHERE (trailing_stop_activated = false OR trailing_stop_activated IS NULL)
                      AND opened_at >= :cutoff
                      AND closed_at IS NOT NULL
                """),
                {"cutoff": cutoff}
            ).fetchall()

            def calc_metrics(trades):
                if not trades:
                    return {}

                total = len(trades)
                wins = len([t for t in trades if t['realized_pnl_pct'] and t['realized_pnl_pct'] > 0])
                total_pnl = sum([t['realized_pnl_pct'] or 0 for t in trades])
                max_profits = [t['max_profit_pct'] or 0 for t in trades if t['max_profit_pct']]

                return {
                    "total_trades": total,
                    "win_rate": wins / total if total > 0 else 0,
                    "avg_pnl_pct": total_pnl / total if total > 0 else 0,
                    "avg_max_profit_captured": sum(max_profits) / len(max_profits) if max_profits else 0
                }

            return {
                "status": "success",
                "period_days": days,
                "with_trailing_stop": calc_metrics(with_trail),
                "without_trailing_stop": calc_metrics(without_trail),
                "analysis": {
                    "trailing_stop_usage_pct": len(with_trail) / (len(with_trail) + len(without_trail)) * 100
                        if (len(with_trail) + len(without_trail)) > 0 else 0,
                    "sample_size": {
                        "with_trail": len(with_trail),
                        "without_trail": len(without_trail)
                    }
                }
            }

    except Exception as e:
        logger.error(f"Error analyzing trailing stop effectiveness: {e}")
        raise HTTPException(status_code=500, detail=str(e))
