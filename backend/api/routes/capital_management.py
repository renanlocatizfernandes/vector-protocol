"""
Capital Management API Routes
Endpoints for intelligent capital and leverage management
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

from utils.logger import setup_logger
from modules.capital import (
    dynamic_capital_manager,
    leverage_optimizer,
    position_sizer,
    margin_monitor,
    capital_orchestrator
)

logger = setup_logger("capital_management_api")

router = APIRouter(prefix="/api/capital", tags=["Capital Management"])


# ============================================================
# Dynamic Capital Manager Endpoints
# ============================================================

@router.get("/state")
async def get_capital_state():
    """
    Get current capital state

    Returns complete capital information including balances,
    margin usage, buying power, and status
    """
    try:
        state = await dynamic_capital_manager.get_capital_state()

        if not state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        return {
            "status": "success",
            "data": state
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting capital state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_capital_history(hours: int = Query(24, ge=1, le=168)):
    """
    Get capital history for trend analysis

    Args:
        hours: Number of hours to look back (1-168)
    """
    try:
        history = await dynamic_capital_manager.get_capital_history(hours)

        return {
            "status": "success",
            "data": history
        }

    except Exception as e:
        logger.error(f"Error getting capital history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-for-new-position")
async def get_available_for_new_position(
    max_margin_usage_pct: float = Query(75.0, ge=50.0, le=90.0)
):
    """
    Calculate available capital for new positions

    Args:
        max_margin_usage_pct: Maximum allowed margin usage %
    """
    try:
        available = await dynamic_capital_manager.get_available_for_new_position(
            max_margin_usage_pct
        )

        return {
            "status": "success",
            "data": available
        }

    except Exception as e:
        logger.error(f"Error calculating available capital: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/estimate-position-impact")
async def estimate_position_impact(
    symbol: str,
    quantity: float,
    leverage: int = Query(..., ge=1, le=125)
):
    """
    Estimate margin impact of a potential position

    Returns how the position would affect margin usage
    """
    try:
        impact = await dynamic_capital_manager.estimate_position_margin_impact(
            symbol, quantity, leverage
        )

        return {
            "status": "success",
            "data": impact
        }

    except Exception as e:
        logger.error(f"Error estimating position impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Leverage Optimizer Endpoints
# ============================================================

@router.get("/leverage/optimal/{symbol}")
async def get_optimal_leverage(
    symbol: str,
    win_rate: Optional[float] = Query(None, ge=0.0, le=1.0),
    market_regime: Optional[str] = None
):
    """
    Get optimal leverage for symbol

    Considers volatility, spread, liquidity, account size, and market regime
    """
    try:
        # Get account balance
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        account_balance = capital_state['total_wallet_balance']

        # Calculate optimal leverage
        recommendation = await leverage_optimizer.calculate_optimal_leverage(
            symbol,
            account_balance,
            win_rate,
            market_regime
        )

        return {
            "status": "success",
            "data": recommendation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating optimal leverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leverage/bulk-recommendations")
async def get_leverage_recommendations_bulk(symbols: List[str]):
    """
    Get leverage recommendations for multiple symbols

    Returns optimal leverage for each symbol in parallel
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        account_balance = capital_state['total_wallet_balance']

        recommendations = await leverage_optimizer.get_leverage_recommendations_bulk(
            symbols, account_balance
        )

        return {
            "status": "success",
            "data": recommendations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bulk recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Position Sizing Endpoints
# ============================================================

@router.post("/position-size/kelly")
async def calculate_kelly_position_size(
    capital: float,
    win_rate: float = Query(..., ge=0.0, le=1.0),
    avg_win_pct: float = Query(3.5, ge=0.1),
    avg_loss_pct: float = Query(2.0, ge=0.1),
    market_regime: Optional[str] = None,
    portfolio_heat: int = Query(0, ge=0, le=100)
):
    """
    Calculate position size using Kelly Criterion

    Returns optimal position size as % of capital
    """
    try:
        result = position_sizer.calculate_kelly_size(
            capital,
            win_rate,
            avg_win_pct,
            avg_loss_pct,
            market_regime,
            portfolio_heat
        )

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error calculating Kelly size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Margin Monitor Endpoints
# ============================================================

@router.get("/margin/status")
async def get_margin_status():
    """
    Get current margin utilization status

    Returns zone (GREEN/YELLOW/ORANGE/RED) and recommended actions
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        status = margin_monitor.analyze_margin_status(
            capital_state['margin_used_pct'],
            capital_state['unrealized_pnl'],
            capital_state['total_wallet_balance']
        )

        return {
            "status": "success",
            "data": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting margin status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Capital Orchestrator Endpoints (Master)
# ============================================================

@router.get("/analysis/complete")
async def get_complete_capital_analysis():
    """
    Get complete capital analysis with all 10 optimizations

    This is the master endpoint that combines everything:
    1. Dynamic Capital State
    2. Leverage Optimization
    3. Position Sizing (Kelly)
    4. Margin Monitoring
    5. Capital Scaling Strategy
    6. Risk-Parity Allocation
    7. Drawdown Protection
    8. Opportunity Cost Analysis
    9. Multi-Tier Allocation
    10. Liquidity-Aware Sizing
    """
    try:
        analysis = await capital_orchestrator.get_complete_capital_analysis()

        if 'error' in analysis:
            raise HTTPException(status_code=500, detail=analysis['error'])

        return {
            "status": "success",
            "data": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in complete analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PositionRecommendationRequest(BaseModel):
    symbol: str
    signal_score: int
    expected_return_pct: float
    market_regime: Optional[str] = None
    win_rate: Optional[float] = None
    avg_win_pct: float = 3.5
    avg_loss_pct: float = 2.0


@router.post("/recommendation/position")
async def get_position_recommendation(request: PositionRecommendationRequest):
    """
    Get complete position recommendation using all optimizations

    **This is what the bot should call before entering a trade**

    Returns:
    - Recommendation (ENTER/REJECT/CAUTION)
    - Optimal leverage
    - Position size
    - Risk metrics
    - Execution method
    """
    try:
        recommendation = await capital_orchestrator.get_position_recommendation(
            symbol=request.symbol,
            signal_score=request.signal_score,
            expected_return_pct=request.expected_return_pct,
            market_regime=request.market_regime,
            win_rate=request.win_rate,
            avg_win_pct=request.avg_win_pct,
            avg_loss_pct=request.avg_loss_pct
        )

        return {
            "status": "success",
            "data": recommendation
        }

    except Exception as e:
        logger.error(f"Error getting position recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy/scaling")
async def get_capital_scaling_strategy():
    """
    Get strategy recommendations based on account size

    Returns different strategies for small/medium/large accounts
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        total_capital = capital_state['total_wallet_balance']

        strategy = capital_orchestrator.get_strategy_for_capital_size(total_capital)

        return {
            "status": "success",
            "data": {
                "current_capital": total_capital,
                "strategy": strategy
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scaling strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/allocation/risk-parity")
async def calculate_risk_parity_allocation(symbols: List[str]):
    """
    Calculate risk-parity allocation for symbols

    Allocates capital inversely to volatility for equal risk contribution
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        total_capital = capital_state['total_wallet_balance']

        allocation = await capital_orchestrator.calculate_risk_parity_allocation(
            symbols, total_capital
        )

        return {
            "status": "success",
            "data": allocation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating risk parity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation/multi-tier")
async def get_multi_tier_allocation():
    """
    Get multi-tier capital allocation (CORE/GROWTH/OPPORTUNITY/RESERVE)

    Shows current allocation vs targets and rebalance recommendations
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        total_capital = capital_state['total_wallet_balance']

        # Get current positions
        from utils.binance_client import binance_client
        positions = await binance_client.futures_position_information()

        active_positions = [
            {
                'symbol': p['symbol'],
                'value_usd': abs(float(p.get('positionAmt', 0))) * float(p.get('entryPrice', 0)),
                'score': 70
            }
            for p in positions
            if abs(float(p.get('positionAmt', 0))) > 0
        ]

        allocation = await capital_orchestrator.calculate_multi_tier_allocation(
            total_capital, active_positions
        )

        return {
            "status": "success",
            "data": allocation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multi-tier allocation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drawdown/status")
async def get_drawdown_status():
    """
    Get current drawdown protection status

    Returns drawdown state and position size/leverage adjustments
    """
    try:
        capital_state = await dynamic_capital_manager.get_capital_state()

        if not capital_state:
            raise HTTPException(status_code=500, detail="Failed to get capital state")

        current_balance = capital_state['total_wallet_balance']

        drawdown_state = capital_orchestrator.update_drawdown_state(current_balance)

        return {
            "status": "success",
            "data": drawdown_state
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting drawdown status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
