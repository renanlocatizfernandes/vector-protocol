"""
User Control & Visibility API Routes
Comprehensive endpoints for all user control and monitoring features
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

from utils.logger import setup_logger

logger = setup_logger("user_control_api")

router = APIRouter(prefix="/api/control", tags=["User Control & Visibility"])


# ============================================================
# Real-Time Snapshot Stream
# ============================================================

@router.post("/snapshot/start")
async def start_snapshot_stream():
    """Start real-time snapshot streaming"""
    try:
        from modules.control import snapshot_stream_manager

        await snapshot_stream_manager.start_stream()

        return {
            "status": "success",
            "message": "Snapshot stream started"
        }

    except Exception as e:
        logger.error(f"Error starting snapshot stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/stop")
async def stop_snapshot_stream():
    """Stop real-time snapshot streaming"""
    try:
        from modules.control import snapshot_stream_manager

        await snapshot_stream_manager.stop_stream()

        return {
            "status": "success",
            "message": "Snapshot stream stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping snapshot stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/current")
async def get_current_snapshot():
    """Get current snapshot immediately"""
    try:
        from modules.control import snapshot_stream_manager

        snapshot = await snapshot_stream_manager.get_current_snapshot()

        return {
            "status": "success",
            "data": snapshot
        }

    except Exception as e:
        logger.error(f"Error getting current snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/history")
async def get_snapshot_history(count: Optional[int] = Query(None, ge=1, le=60)):
    """Get snapshot history"""
    try:
        from modules.control import snapshot_stream_manager

        history = await snapshot_stream_manager.get_snapshot_history(count)

        return {
            "status": "success",
            "count": len(history),
            "data": history
        }

    except Exception as e:
        logger.error(f"Error getting snapshot history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/snapshot/config")
async def configure_snapshot_stream(
    capital: bool = Query(True),
    positions: bool = Query(True),
    bot_status: bool = Query(True),
    market_data: bool = Query(False),
    update_interval: float = Query(1.0, ge=0.1, le=60.0)
):
    """Configure snapshot stream modules and update interval"""
    try:
        from modules.control import snapshot_stream_manager

        snapshot_stream_manager.configure_modules({
            'capital': capital,
            'positions': positions,
            'bot_status': bot_status,
            'market_data': market_data
        })

        snapshot_stream_manager.set_update_interval(update_interval)

        return {
            "status": "success",
            "message": "Snapshot stream configured"
        }

    except Exception as e:
        logger.error(f"Error configuring snapshot stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Manual Controls
# ============================================================

@router.post("/bot/pause")
async def pause_bot(reason: str = Query("Manual pause")):
    """Pause the autonomous bot"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.pause_bot(reason)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error pausing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/resume")
async def resume_bot():
    """Resume the autonomous bot"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.resume_bot()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error resuming bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position/close")
async def close_position(
    symbol: str = Query(...),
    reason: str = Query("Manual close")
):
    """Manually close a position"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.close_position(symbol, reason)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position/adjust-leverage")
async def adjust_leverage(
    symbol: str = Query(...),
    leverage: int = Query(..., ge=1, le=125)
):
    """Adjust leverage for a symbol"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.adjust_leverage(symbol, leverage)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error adjusting leverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position/modify-stop-loss")
async def modify_stop_loss(
    symbol: str = Query(...),
    stop_price: float = Query(...)
):
    """Modify stop loss for a position"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.modify_stop_loss(symbol, stop_price)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error modifying stop loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position/modify-take-profit")
async def modify_take_profit(
    symbol: str = Query(...),
    take_profit_price: float = Query(...)
):
    """Modify take profit for a position"""
    try:
        from modules.control import manual_control_manager

        result = await manual_control_manager.modify_take_profit(symbol, take_profit_price)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error modifying take profit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manual/history")
async def get_manual_control_history(limit: int = Query(100, ge=1, le=500)):
    """Get manual control history"""
    try:
        from modules.control import manual_control_manager

        history = manual_control_manager.get_control_history(limit)

        return {
            "status": "success",
            "data": history
        }

    except Exception as e:
        logger.error(f"Error getting control history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Trade Journal
# ============================================================

class TradeJournalEntry(BaseModel):
    symbol: str
    side: str
    entry_price: float
    quantity: float
    leverage: int
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    strategy: Optional[str] = None


@router.post("/journal/add")
async def add_journal_entry(entry: TradeJournalEntry):
    """Add trade to journal"""
    try:
        from modules.control import trade_journal

        result = await trade_journal.add_entry(
            symbol=entry.symbol,
            side=entry.side,
            entry_price=entry.entry_price,
            quantity=entry.quantity,
            leverage=entry.leverage,
            exit_price=entry.exit_price,
            pnl=entry.pnl,
            pnl_pct=entry.pnl_pct,
            tags=entry.tags,
            notes=entry.notes,
            strategy=entry.strategy
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error adding journal entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal/search")
async def search_journal(
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Search journal entries"""
    try:
        from modules.control import trade_journal
        from modules.control.trade_journal import TradeOutcome

        outcome_enum = None
        if outcome:
            outcome_enum = TradeOutcome(outcome)

        results = await trade_journal.search_entries(
            symbol=symbol,
            side=side,
            outcome=outcome_enum,
            limit=limit
        )

        return {
            "status": "success",
            "count": len(results),
            "data": results
        }

    except Exception as e:
        logger.error(f"Error searching journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal/statistics")
async def get_journal_statistics():
    """Get journal statistics"""
    try:
        from modules.control import trade_journal

        stats = await trade_journal.get_statistics()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting journal statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal/export/csv")
async def export_journal_csv():
    """Export journal to CSV"""
    try:
        from modules.control import trade_journal

        csv_content = await trade_journal.export_csv()

        return {
            "status": "success",
            "data": csv_content
        }

    except Exception as e:
        logger.error(f"Error exporting journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Performance Analytics
# ============================================================

@router.get("/analytics/complete")
async def get_complete_analytics():
    """Get complete performance analytics"""
    try:
        from modules.control import performance_analytics

        analytics = await performance_analytics.get_complete_analytics()

        return {
            "status": "success",
            "data": analytics
        }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/sharpe")
async def get_sharpe_ratio(period_days: int = Query(30, ge=1, le=365)):
    """Get Sharpe ratio"""
    try:
        from modules.control import performance_analytics

        sharpe = await performance_analytics.calculate_sharpe_ratio(period_days)

        return {
            "status": "success",
            "data": {
                "sharpe_ratio": sharpe,
                "period_days": period_days
            }
        }

    except Exception as e:
        logger.error(f"Error calculating Sharpe ratio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/sortino")
async def get_sortino_ratio(period_days: int = Query(30, ge=1, le=365)):
    """Get Sortino ratio"""
    try:
        from modules.control import performance_analytics

        sortino = await performance_analytics.calculate_sortino_ratio(period_days)

        return {
            "status": "success",
            "data": {
                "sortino_ratio": sortino,
                "period_days": period_days
            }
        }

    except Exception as e:
        logger.error(f"Error calculating Sortino ratio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/drawdown")
async def get_max_drawdown():
    """Get maximum drawdown"""
    try:
        from modules.control import performance_analytics

        drawdown = await performance_analytics.calculate_max_drawdown()

        return {
            "status": "success",
            "data": drawdown
        }

    except Exception as e:
        logger.error(f"Error calculating drawdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/win-rate")
async def get_win_rate(period_days: Optional[int] = Query(None, ge=1, le=365)):
    """Get win rate"""
    try:
        from modules.control import performance_analytics

        win_rate = await performance_analytics.calculate_win_rate(period_days)

        return {
            "status": "success",
            "data": win_rate
        }

    except Exception as e:
        logger.error(f"Error calculating win rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/profit-factor")
async def get_profit_factor(period_days: Optional[int] = Query(None, ge=1, le=365)):
    """Get profit factor"""
    try:
        from modules.control import performance_analytics

        profit_factor = await performance_analytics.calculate_profit_factor(period_days)

        return {
            "status": "success",
            "data": {
                "profit_factor": profit_factor,
                "period_days": period_days
            }
        }

    except Exception as e:
        logger.error(f"Error calculating profit factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Alert Engine
# ============================================================

class AlertCreate(BaseModel):
    id: str
    name: str
    alert_type: str
    symbol: Optional[str] = None
    target_value: Optional[float] = None
    comparison: str = ">"
    notify_once: bool = True
    cooldown_seconds: int = 300


@router.post("/alerts/create")
async def create_alert(alert: AlertCreate):
    """Create new alert"""
    try:
        from modules.control import alert_engine
        from modules.control.alert_engine import Alert, AlertType, AlertStatus

        new_alert = Alert(
            id=alert.id,
            name=alert.name,
            alert_type=AlertType(alert.alert_type),
            status=AlertStatus.ACTIVE,
            symbol=alert.symbol,
            target_value=alert.target_value,
            comparison=alert.comparison,
            notify_once=alert.notify_once,
            cooldown_seconds=alert.cooldown_seconds
        )

        result = await alert_engine.create_alert(new_alert)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/list")
async def list_alerts(status: Optional[str] = None):
    """List all alerts"""
    try:
        from modules.control import alert_engine
        from modules.control.alert_engine import AlertStatus

        status_enum = AlertStatus(status) if status else None

        alerts = await alert_engine.get_alerts(status_enum)

        return {
            "status": "success",
            "count": len(alerts),
            "data": alerts
        }

    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete alert"""
    try:
        from modules.control import alert_engine

        result = await alert_engine.delete_alert(alert_id)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/start-monitoring")
async def start_alert_monitoring():
    """Start alert monitoring"""
    try:
        from modules.control import alert_engine

        await alert_engine.start_monitoring()

        return {
            "status": "success",
            "message": "Alert monitoring started"
        }

    except Exception as e:
        logger.error(f"Error starting alert monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/stop-monitoring")
async def stop_alert_monitoring():
    """Stop alert monitoring"""
    try:
        from modules.control import alert_engine

        await alert_engine.stop_monitoring()

        return {
            "status": "success",
            "message": "Alert monitoring stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping alert monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Emergency Controls
# ============================================================

@router.post("/emergency/panic-close-all")
async def panic_close_all(reason: str = Query("Panic button")):
    """PANIC: Close all positions immediately"""
    try:
        from modules.control import emergency_controller

        result = await emergency_controller.panic_close_all(reason)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error in panic close: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency/stop")
async def emergency_stop(reason: str = Query("Emergency stop")):
    """Emergency stop: Stop bot + cancel orders"""
    try:
        from modules.control import emergency_controller

        result = await emergency_controller.emergency_stop(reason)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency/reduce-all")
async def reduce_all_positions(reduce_pct: float = Query(50.0, ge=1.0, le=100.0)):
    """Reduce all positions by percentage"""
    try:
        from modules.control import emergency_controller

        result = await emergency_controller.reduce_all_positions(reduce_pct)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error reducing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency/cancel-all-orders")
async def cancel_all_orders():
    """Cancel all open orders"""
    try:
        from modules.control import emergency_controller

        result = await emergency_controller.cancel_all_orders()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error cancelling orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emergency/circuit-breaker/status")
async def get_circuit_breaker_status():
    """Get circuit breaker status"""
    try:
        from modules.control import emergency_controller

        status = emergency_controller.get_circuit_breaker_status()

        return {
            "status": "success",
            "data": status
        }

    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Reset circuit breaker"""
    try:
        from modules.control import emergency_controller

        result = await emergency_controller.reset_circuit_breaker()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error resetting circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Audit Log
# ============================================================

@router.get("/audit/search")
async def search_audit_log(
    action: Optional[str] = None,
    level: Optional[str] = None,
    user: Optional[str] = None,
    search_text: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Search audit log"""
    try:
        from modules.control import audit_logger
        from modules.control.audit_logger import AuditAction, AuditLevel

        action_enum = AuditAction(action) if action else None
        level_enum = AuditLevel(level) if level else None

        results = await audit_logger.search(
            action=action_enum,
            level=level_enum,
            user=user,
            search_text=search_text,
            limit=limit
        )

        return {
            "status": "success",
            "count": len(results),
            "data": [entry.to_dict() for entry in results]
        }

    except Exception as e:
        logger.error(f"Error searching audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/recent")
async def get_recent_audit_logs(limit: int = Query(100, ge=1, le=500)):
    """Get recent audit logs"""
    try:
        from modules.control import audit_logger

        logs = await audit_logger.get_recent(limit)

        return {
            "status": "success",
            "count": len(logs),
            "data": [entry.to_dict() for entry in logs]
        }

    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/statistics")
async def get_audit_statistics():
    """Get audit log statistics"""
    try:
        from modules.control import audit_logger

        stats = await audit_logger.get_statistics()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/export")
async def export_audit_log():
    """Export audit log to JSON"""
    try:
        from modules.control import audit_logger

        export_data = await audit_logger.export_json()

        return {
            "status": "success",
            "data": export_data
        }

    except Exception as e:
        logger.error(f"Error exporting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Rules Engine
# ============================================================

@router.get("/rules/check")
async def check_trading_rules():
    """Check if trading is allowed based on rules"""
    try:
        from modules.control import rules_engine

        result = await rules_engine.check_can_trade()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error checking rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/list")
async def list_rules(status: Optional[str] = None):
    """List all trading rules"""
    try:
        from modules.control import rules_engine
        from modules.control.rules_engine import RuleStatus

        status_enum = RuleStatus(status) if status else None

        rules = rules_engine.get_rules(status_enum)

        return {
            "status": "success",
            "count": len(rules),
            "data": [
                {
                    'id': r.id,
                    'name': r.name,
                    'rule_type': r.rule_type.value,
                    'status': r.status.value,
                    'description': r.description,
                    'enforce': r.enforce,
                    'violation_count': r.violation_count
                }
                for r in rules
            ]
        }

    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/violations")
async def get_rule_violations(limit: int = Query(100, ge=1, le=500)):
    """Get rule violation history"""
    try:
        from modules.control import rules_engine

        violations = rules_engine.get_violation_history(limit)

        return {
            "status": "success",
            "count": len(violations),
            "data": violations
        }

    except Exception as e:
        logger.error(f"Error getting violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/daily-stats")
async def get_daily_stats():
    """Get daily trading statistics"""
    try:
        from modules.control import rules_engine

        stats = rules_engine.get_daily_stats()

        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Quick Actions
# ============================================================

@router.post("/quick-actions/close-profitable")
async def close_all_profitable(min_profit_pct: float = Query(1.0, ge=0.1)):
    """Close all profitable positions"""
    try:
        from modules.control import quick_actions_manager

        result = await quick_actions_manager.close_all_profitable(min_profit_pct)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error closing profitable positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-actions/close-losing")
async def close_all_losing(max_loss_pct: float = Query(-2.0, le=-0.1)):
    """Close all losing positions"""
    try:
        from modules.control import quick_actions_manager

        result = await quick_actions_manager.close_all_losing(max_loss_pct)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error closing losing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-actions/reduce-risk-mode")
async def activate_reduce_risk_mode():
    """Activate reduce risk mode"""
    try:
        from modules.control import quick_actions_manager

        result = await quick_actions_manager.reduce_risk_mode()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error activating reduce risk mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-actions/emergency-mode")
async def activate_emergency_mode():
    """Activate emergency mode"""
    try:
        from modules.control import quick_actions_manager

        result = await quick_actions_manager.emergency_mode()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error activating emergency mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-actions/scale-out-winners")
async def scale_out_winners(
    profit_threshold_pct: float = Query(3.0, ge=1.0),
    scale_pct: float = Query(50.0, ge=10.0, le=100.0)
):
    """Scale out of winning positions"""
    try:
        from modules.control import quick_actions_manager

        result = await quick_actions_manager.scale_out_winners(profit_threshold_pct, scale_pct)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error scaling out winners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-actions/history")
async def get_quick_actions_history(limit: int = Query(100, ge=1, le=500)):
    """Get quick actions history"""
    try:
        from modules.control import quick_actions_manager

        history = await quick_actions_manager.get_action_history(limit)

        return {
            "status": "success",
            "count": len(history),
            "data": history
        }

    except Exception as e:
        logger.error(f"Error getting quick actions history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# User Settings
# ============================================================

@router.get("/settings/all")
async def get_all_settings():
    """Get all user settings"""
    try:
        from modules.control import user_settings_manager

        settings = user_settings_manager.get_all_settings()

        return {
            "status": "success",
            "data": settings
        }

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{category}")
async def get_category_settings(category: str):
    """Get settings for a category"""
    try:
        from modules.control import user_settings_manager

        settings = user_settings_manager.get_category(category)

        return {
            "status": "success",
            "category": category,
            "data": settings
        }

    except Exception as e:
        logger.error(f"Error getting category settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SettingsUpdate(BaseModel):
    settings: Dict


@router.put("/settings/{category}")
async def update_category_settings(category: str, update: SettingsUpdate):
    """Update settings for a category"""
    try:
        from modules.control import user_settings_manager

        result = user_settings_manager.set_category(category, update.settings)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error updating category settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/reset")
async def reset_settings():
    """Reset all settings to defaults"""
    try:
        from modules.control import user_settings_manager

        result = user_settings_manager.reset_to_defaults()

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/profiles")
async def get_profiles():
    """Get all user profiles"""
    try:
        from modules.control import user_settings_manager

        profiles = user_settings_manager.get_profiles()

        return {
            "status": "success",
            "count": len(profiles),
            "data": profiles
        }

    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str):
    """Activate a profile"""
    try:
        from modules.control import user_settings_manager

        result = user_settings_manager.activate_profile(profile_id)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error activating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/export")
async def export_settings():
    """Export settings to JSON"""
    try:
        from modules.control import user_settings_manager

        export_data = user_settings_manager.export_settings()

        return {
            "status": "success",
            "data": export_data
        }

    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SettingsImport(BaseModel):
    json_data: str


@router.post("/settings/import")
async def import_settings(import_data: SettingsImport):
    """Import settings from JSON"""
    try:
        from modules.control import user_settings_manager

        result = user_settings_manager.import_settings(import_data.json_data)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error importing settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Notifications
# ============================================================

@router.get("/notifications/rules")
async def get_notification_rules():
    """Get all notification rules"""
    try:
        from modules.control import notification_engine

        rules = notification_engine.get_rules()

        return {
            "status": "success",
            "count": len(rules),
            "data": [
                {
                    'id': r.id,
                    'name': r.name,
                    'notification_type': r.notification_type.value,
                    'enabled': r.enabled,
                    'channels': [c.value for c in r.channels],
                    'priority': r.priority.value
                }
                for r in rules
            ]
        }

    except Exception as e:
        logger.error(f"Error getting notification rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/history")
async def get_notification_history(
    notification_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Get notification history"""
    try:
        from modules.control import notification_engine
        from modules.control.notification_engine import NotificationType

        type_enum = NotificationType(notification_type) if notification_type else None

        history = notification_engine.get_notification_history(limit, type_enum)

        return {
            "status": "success",
            "count": len(history),
            "data": [
                {
                    'id': n.id,
                    'timestamp': n.timestamp.isoformat(),
                    'notification_type': n.notification_type.value,
                    'priority': n.priority.value,
                    'title': n.title,
                    'message': n.message,
                    'channels': [c.value for c in n.channels]
                }
                for n in history
            ]
        }

    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
