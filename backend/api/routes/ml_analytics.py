"""
ML Analytics API Routes
Endpoints for monitoring and managing the Adaptive Intelligence Engine
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from utils.logger import setup_logger
from modules.ml.adaptive_engine import adaptive_engine
from modules.ml.feature_store import feature_store
from modules.ml.regime_detector import regime_detector
from modules.ml.indicator_optimizer import indicator_optimizer
from modules.ml.adaptive_controller import adaptive_controller
from modules.ml.anomaly_detector import anomaly_detector

logger = setup_logger("ml_analytics_api")

router = APIRouter(prefix="/api/ml", tags=["ML Analytics"])


@router.get("/status")
async def get_ml_status():
    """
    Get current status of the Adaptive Intelligence Engine

    Returns comprehensive status including:
    - Initialization state
    - Current market regime
    - Model training status
    - Active filter rules count
    - Current configuration
    """
    try:
        status = await adaptive_engine.get_status()
        return {
            "status": "success",
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting ML status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_ml_engine(historical_days: int = Query(90, ge=30, le=180)):
    """
    Initialize or re-initialize the Adaptive Intelligence Engine

    Args:
        historical_days: Number of days of historical data to use (30-180)

    Returns:
        Initialization status
    """
    try:
        logger.info(f"🔄 Initializing ML engine with {historical_days} days of data...")
        await adaptive_engine.initialize(historical_days=historical_days)

        return {
            "status": "success",
            "message": f"ML engine initialized with {historical_days} days of data",
            "engine_status": await adaptive_engine.get_status()
        }
    except Exception as e:
        logger.error(f"Error initializing ML engine: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regimes")
async def get_regime_analysis():
    """
    Get analysis of performance by market regime

    Returns:
    - Configuration for each regime
    - Performance metrics per regime
    - Historical regime distribution
    """
    try:
        analysis = {}

        for regime_id, regime_name in regime_detector.REGIMES.items():
            config = regime_detector.get_regime_config(regime_id)

            # Get historical performance for this regime
            regime_data = await feature_store.get_historical_features(days=30, regime=regime_id)

            if not regime_data.empty:
                wins = len(regime_data[regime_data['outcome'] == 'WIN'])
                total = len(regime_data)
                win_rate = wins / total if total > 0 else 0.0
                avg_pnl = regime_data['pnl_pct'].mean()
            else:
                win_rate = 0.0
                avg_pnl = 0.0
                total = 0

            analysis[regime_name] = {
                "regime_id": regime_id,
                "config": config,
                "metrics": {
                    "total_trades": total,
                    "win_rate": win_rate,
                    "avg_pnl_pct": avg_pnl,
                }
            }

        # Add current regime
        current_regime = adaptive_engine.current_regime
        if current_regime is not None:
            analysis['current_regime'] = {
                "id": current_regime,
                "name": regime_detector.REGIMES[current_regime]
            }

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error getting regime analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicator-importance")
async def get_indicator_importance():
    """
    Get feature importance for all indicators

    Returns:
    - Sorted list of indicators by importance
    - Importance grouped by category
    - Top and bottom performers
    """
    try:
        report = await indicator_optimizer.get_feature_importance_report()

        if 'error' in report:
            return {
                "status": "error",
                "message": "Indicator importance not yet calculated. Train the model first."
            }

        return {
            "status": "success",
            "data": report
        }

    except Exception as e:
        logger.error(f"Error getting indicator importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter-rules")
async def get_filter_rules(active_only: bool = Query(True)):
    """
    Get loss pattern filter rules

    Args:
        active_only: Only return active rules (default True)

    Returns:
        List of filter rules with metrics
    """
    try:
        from models.database import SessionLocal
        from api.models.ml_models import FilterRule
        from sqlalchemy import select

        with SessionLocal() as db:
            query = select(FilterRule)

            if active_only:
                query = query.where(FilterRule.is_active == True)

            rules = db.execute(query).scalars().all()

            rules_data = []
            for rule in rules:
                rules_data.append({
                    "id": rule.id,
                    "rule_name": rule.rule_name,
                    "confidence": rule.confidence,
                    "support": rule.support,
                    "lift": rule.lift,
                    "is_active": rule.is_active,
                    "trades_prevented": rule.trades_prevented,
                    "false_negatives": rule.false_negatives,
                    "effectiveness": (rule.trades_prevented - rule.false_negatives) / rule.trades_prevented
                        if rule.trades_prevented > 0 else 0.0,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                })

            return {
                "status": "success",
                "count": len(rules_data),
                "data": rules_data
            }

    except Exception as e:
        logger.error(f"Error getting filter rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filter-rules/{rule_id}/toggle")
async def toggle_filter_rule(rule_id: int):
    """
    Toggle a filter rule on/off

    Args:
        rule_id: ID of the rule to toggle

    Returns:
        Updated rule status
    """
    try:
        from models.database import SessionLocal
        from api.models.ml_models import FilterRule
        from sqlalchemy import select

        with SessionLocal() as db:
            rule = db.execute(
                select(FilterRule).where(FilterRule.id == rule_id)
            ).scalar_one_or_none()

            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")

            rule.is_active = not rule.is_active
            db.commit()

            # Reload rules in anomaly detector
            await anomaly_detector.load_active_rules()

            return {
                "status": "success",
                "message": f"Rule {rule_id} {'activated' if rule.is_active else 'deactivated'}",
                "is_active": rule.is_active
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrain")
async def trigger_manual_retrain(lookback_days: int = Query(30, ge=7, le=90)):
    """
    Manually trigger model retraining

    Args:
        lookback_days: Number of days of recent data to use (7-90)

    Returns:
        Retraining status
    """
    try:
        logger.info(f"🔄 Manual retraining triggered with {lookback_days} days")
        await adaptive_engine.retrain_models(lookback_days=lookback_days)

        return {
            "status": "success",
            "message": f"Models retrained with {lookback_days} days of data",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error retraining models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/recent")
async def get_recent_performance(days: int = Query(7, ge=1, le=30)):
    """
    Get recent performance metrics

    Args:
        days: Number of days to analyze (1-30)

    Returns:
        Performance metrics including Sharpe, win rate, drawdown
    """
    try:
        metrics = await adaptive_controller.calculate_recent_metrics(days=days)

        return {
            "status": "success",
            "period_days": days,
            "data": metrics
        }

    except Exception as e:
        logger.error(f"Error getting recent performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/current")
async def get_current_adaptive_config():
    """
    Get current adaptive configuration

    Returns:
        Current trading parameters and regime info
    """
    try:
        config = await adaptive_engine.get_adaptive_config()

        return {
            "status": "success",
            "data": config
        }

    except Exception as e:
        logger.error(f"Error getting current config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/by-regime")
async def get_performance_by_regime(days: int = Query(30, ge=7, le=90)):
    """
    Get performance breakdown by market regime

    Args:
        days: Number of days to analyze

    Returns:
        Performance metrics grouped by regime
    """
    try:
        from models.database import SessionLocal
        from api.models.ml_models import MLTradeFeature
        from sqlalchemy import select, and_
        import pandas as pd

        performance_by_regime = {}

        with SessionLocal() as db:
            cutoff = datetime.now() - timedelta(days=days)

            for regime_id, regime_name in regime_detector.REGIMES.items():
                query = select(MLTradeFeature).where(
                    and_(
                        MLTradeFeature.market_regime == regime_id,
                        MLTradeFeature.timestamp >= cutoff,
                        MLTradeFeature.outcome.isnot(None)
                    )
                )

                results = db.execute(query).scalars().all()

                if results:
                    pnls = [r.pnl_pct for r in results if r.pnl_pct is not None]
                    outcomes = [r.outcome for r in results]

                    win_rate = outcomes.count('WIN') / len(outcomes) if outcomes else 0.0
                    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
                    sharpe = (avg_pnl / (pd.Series(pnls).std())) if len(pnls) > 1 else 0.0

                    performance_by_regime[regime_name] = {
                        "regime_id": regime_id,
                        "total_trades": len(results),
                        "win_rate": win_rate,
                        "avg_pnl_pct": avg_pnl,
                        "sharpe_ratio": sharpe,
                    }
                else:
                    performance_by_regime[regime_name] = {
                        "regime_id": regime_id,
                        "total_trades": 0,
                        "win_rate": 0.0,
                        "avg_pnl_pct": 0.0,
                        "sharpe_ratio": 0.0,
                    }

        return {
            "status": "success",
            "period_days": days,
            "data": performance_by_regime
        }

    except Exception as e:
        logger.error(f"Error getting performance by regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-outcome")
async def record_trade_outcome(
    trade_id: str,
    symbol: str,
    outcome: str = Query(..., regex="^(WIN|LOSS)$"),
    pnl_pct: float = Query(...),
    pnl_absolute: Optional[float] = None,
    duration_minutes: Optional[int] = None
):
    """
    Record trade outcome for continuous learning

    Args:
        trade_id: Unique trade identifier
        symbol: Trading symbol
        outcome: 'WIN' or 'LOSS'
        pnl_pct: PnL percentage
        pnl_absolute: Absolute PnL amount
        duration_minutes: Trade duration in minutes

    Returns:
        Confirmation of recording
    """
    try:
        outcome_data = {
            'outcome': outcome,
            'pnl_pct': pnl_pct,
            'pnl_absolute': pnl_absolute,
            'duration_minutes': duration_minutes,
        }

        await adaptive_engine.record_trade_outcome(
            trade_id=trade_id,
            symbol=symbol,
            outcome=outcome_data
        )

        return {
            "status": "success",
            "message": f"Trade outcome recorded for {trade_id}",
            "trades_until_retrain": 100 - adaptive_engine.trades_since_retrain
        }

    except Exception as e:
        logger.error(f"Error recording trade outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))
