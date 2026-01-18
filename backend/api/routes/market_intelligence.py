"""
Market Intelligence API Routes
Endpoints for advanced market analysis and intelligence features
"""

import asyncio
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from utils.logger import setup_logger
from modules.market_intelligence import (
    funding_sentiment_engine,
    orderbook_analyzer,
    liquidation_heatmap,
    mtf_confluence,
    correlation_matrix,
    volume_profile
)
from modules.execution import smart_order_router, adaptive_tp_ladder
from modules.risk import dynamic_risk_heatmap
from modules.meta import meta_strategy_selector

logger = setup_logger("market_intelligence_api")

router = APIRouter(prefix="/api/intelligence", tags=["Market Intelligence"])


# ============================================================
# Funding & Sentiment Endpoints
# ============================================================

@router.get("/funding/sentiment/{symbol}")
async def get_funding_sentiment(symbol: str):
    """
    Get funding rate and sentiment analysis for symbol

    Returns sentiment classification, bias, and confidence
    """
    try:
        analysis = await funding_sentiment_engine.analyze_sentiment(symbol)

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis failed")

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error getting funding sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funding/arbitrage")
async def get_funding_arbitrage_opportunities(
    min_funding: float = Query(0.1, description="Minimum funding rate %")
):
    """
    Scan market for funding arbitrage opportunities

    Returns symbols with high funding rates
    """
    try:
        opportunities = await funding_sentiment_engine.get_funding_arbitrage_opportunities(
            min_funding=min_funding
        )

        return {
            "status": "success",
            "count": len(opportunities),
            "opportunities": opportunities
        }

    except Exception as e:
        logger.error(f"Error scanning funding opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Order Book Analysis Endpoints
# ============================================================

@router.get("/orderbook/analysis/{symbol}")
async def get_orderbook_analysis(symbol: str):
    """
    Get order book depth analysis with whale walls

    Returns support/resistance from large orders
    """
    try:
        analysis = await orderbook_analyzer.analyze_order_book(symbol)

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis failed")

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing order book: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/levels/{symbol}")
async def get_support_resistance_levels(
    symbol: str,
    num_levels: int = Query(3, ge=1, le=10)
):
    """
    Get dynamic support/resistance levels from order book

    Returns nearest key levels above/below price
    """
    try:
        levels = await orderbook_analyzer.get_support_resistance_levels(symbol, num_levels)

        return {
            "status": "success",
            "data": levels
        }

    except Exception as e:
        logger.error(f"Error getting levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Liquidation Heatmap Endpoints
# ============================================================

@router.get("/liquidations/heatmap/{symbol}")
async def get_liquidation_heatmap(symbol: str):
    """
    Get liquidation heatmap for symbol

    Returns liquidation clusters and cascade risk
    """
    try:
        heatmap = await liquidation_heatmap.calculate_heatmap(symbol)

        if not heatmap:
            raise HTTPException(status_code=404, detail="Heatmap calculation failed")

        return {
            "status": "success",
            "data": heatmap
        }

    except Exception as e:
        logger.error(f"Error calculating heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/liquidations/levels/{symbol}")
async def get_liquidation_levels(
    symbol: str,
    num_levels: int = Query(5, ge=1, le=10)
):
    """
    Get nearest liquidation levels above/below current price
    """
    try:
        levels = await liquidation_heatmap.get_nearest_liquidation_levels(symbol, num_levels)

        return {
            "status": "success",
            "data": levels
        }

    except Exception as e:
        logger.error(f"Error getting liquidation levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Multi-Timeframe Confluence Endpoints
# ============================================================

@router.get("/mtf/confluence/{symbol}")
async def get_mtf_confluence(symbol: str):
    """
    Get multi-timeframe confluence analysis

    Returns alignment across 1m, 5m, 15m, 1h, 4h, 1d
    """
    try:
        analysis = await mtf_confluence.analyze_confluence(symbol)

        if not analysis:
            raise HTTPException(status_code=404, detail="Confluence analysis failed")

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing confluence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Correlation Matrix Endpoints
# ============================================================

@router.post("/correlation/matrix")
async def calculate_correlation_matrix(
    symbols: List[str],
    period: str = Query("1d", regex="^(1h|4h|1d|1w)$")
):
    """
    Calculate correlation matrix for list of symbols

    Returns correlations and pairs trading opportunities
    """
    try:
        result = await correlation_matrix.calculate_correlation_matrix(symbols, period)

        if not result:
            raise HTTPException(status_code=500, detail="Correlation calculation failed")

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error calculating correlation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation/hedge/{symbol}")
async def get_hedge_recommendation(
    symbol: str,
    candidates: List[str] = Query(...),
    period: str = Query("1d", regex="^(1h|4h|1d|1w)$")
):
    """
    Find best hedge for a symbol

    Returns symbols with highest correlation
    """
    try:
        recommendation = await correlation_matrix.get_hedge_recommendation(
            symbol, candidates, period
        )

        return {
            "status": "success",
            "data": recommendation
        }

    except Exception as e:
        logger.error(f"Error getting hedge recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation/pairs-signal")
async def get_pairs_trade_signal(
    pair1: str = Query(...),
    pair2: str = Query(...),
    period: str = Query("1d", regex="^(1h|4h|1d|1w)$")
):
    """
    Get pairs trading signal for two symbols

    Returns z-score and mean reversion signal
    """
    try:
        signal = await correlation_matrix.get_pairs_trade_signal(pair1, pair2, period)

        return {
            "status": "success",
            "data": signal
        }

    except Exception as e:
        logger.error(f"Error getting pairs signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Volume Profile Endpoints
# ============================================================

@router.get("/volume-profile/analysis/{symbol}")
async def get_volume_profile_analysis(
    symbol: str,
    interval: str = Query("5m"),
    lookback: int = Query(200, ge=50, le=500)
):
    """
    Get volume profile analysis for symbol

    Returns POC, Value Area, HVN/LVN zones
    """
    try:
        analysis = await volume_profile.analyze_volume_profile(symbol, interval, lookback)

        if not analysis:
            raise HTTPException(status_code=404, detail="Volume profile analysis failed")

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing volume profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volume-profile/levels/{symbol}")
async def get_volume_levels(
    symbol: str,
    interval: str = Query("5m"),
    lookback: int = Query(200),
    num_levels: int = Query(5, ge=1, le=10)
):
    """
    Get nearest high-volume nodes above/below price
    """
    try:
        levels = await volume_profile.get_nearest_volume_levels(
            symbol, interval, lookback, num_levels
        )

        return {
            "status": "success",
            "data": levels
        }

    except Exception as e:
        logger.error(f"Error getting volume levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volume-profile/compare/{symbol}")
async def compare_volume_profiles(
    symbol: str,
    current_interval: str = Query("5m"),
    historical_interval: str = Query("1h")
):
    """
    Compare current vs historical volume profile

    Shows POC migration and value area shifts
    """
    try:
        comparison = await volume_profile.compare_current_to_historical_profile(
            symbol, current_interval, historical_interval
        )

        return {
            "status": "success",
            "data": comparison
        }

    except Exception as e:
        logger.error(f"Error comparing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Smart Order Routing Endpoints
# ============================================================

class OrderRoutingRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    algorithm: str = "ADAPTIVE"  # TWAP, ICEBERG, ADAPTIVE
    duration_seconds: Optional[int] = 300
    visible_quantity: Optional[float] = None
    limit_price: Optional[float] = None
    urgency: Optional[str] = "NORMAL"
    dry_run: bool = True


@router.post("/order-routing/execute")
async def execute_smart_order(request: OrderRoutingRequest):
    """
    Execute smart order with advanced routing

    Supports TWAP, Iceberg, and Adaptive algorithms
    """
    try:
        if request.algorithm == "TWAP":
            result = await smart_order_router.execute_twap(
                symbol=request.symbol,
                side=request.side,
                total_quantity=request.quantity,
                duration_seconds=request.duration_seconds,
                limit_price=request.limit_price
            )

        elif request.algorithm == "ICEBERG":
            if not request.visible_quantity or not request.limit_price:
                raise HTTPException(
                    status_code=400,
                    detail="Iceberg requires visible_quantity and limit_price"
                )

            result = await smart_order_router.execute_iceberg(
                symbol=request.symbol,
                side=request.side,
                total_quantity=request.quantity,
                visible_quantity=request.visible_quantity,
                limit_price=request.limit_price
            )

        elif request.algorithm == "ADAPTIVE":
            result = await smart_order_router.execute_adaptive(
                symbol=request.symbol,
                side=request.side,
                total_quantity=request.quantity,
                urgency=request.urgency
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid algorithm")

        return {
            "status": "success",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing smart order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/order-routing/recommend/{symbol}")
async def get_order_routing_recommendation(
    symbol: str,
    side: str = Query(..., regex="^(BUY|SELL)$"),
    quantity: float = Query(...)
):
    """
    Get recommended order routing parameters

    Returns optimal algorithm and parameters based on market conditions
    """
    try:
        params = await smart_order_router.calculate_optimal_execution_params(
            symbol, side, quantity
        )

        return {
            "status": "success",
            "data": params
        }

    except Exception as e:
        logger.error(f"Error getting routing recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Adaptive TP Ladder Endpoints
# ============================================================

class TPLadderRequest(BaseModel):
    symbol: str
    side: str
    entry_price: float
    quantity: float
    leverage: int = 1
    num_levels: int = 3
    strategy: str = "ADAPTIVE"  # ADAPTIVE, AGGRESSIVE, CONSERVATIVE


@router.post("/tp-ladder/calculate")
async def calculate_tp_ladder(request: TPLadderRequest):
    """
    Calculate adaptive TP ladder based on market conditions
    """
    try:
        ladder = await adaptive_tp_ladder.calculate_tp_ladder(
            symbol=request.symbol,
            side=request.side,
            entry_price=request.entry_price,
            quantity=request.quantity,
            leverage=request.leverage,
            num_levels=request.num_levels,
            strategy=request.strategy
        )

        return {
            "status": "success",
            "data": ladder
        }

    except Exception as e:
        logger.error(f"Error calculating TP ladder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tp-ladder/place-orders")
async def place_tp_ladder_orders(
    ladder_config: Dict,
    dry_run: bool = Query(True)
):
    """
    Place TP limit orders for calculated ladder
    """
    try:
        symbol = ladder_config.get('symbol')
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol required in ladder_config")

        result = await adaptive_tp_ladder.place_tp_orders(symbol, ladder_config, dry_run)

        return {
            "status": "success",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing TP orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Dynamic Risk Heatmap Endpoints
# ============================================================

@router.get("/risk/portfolio-heat")
async def get_portfolio_risk_heatmap():
    """
    Get real-time portfolio risk heatmap

    Returns heat score, high-risk positions, and rebalance recommendations
    """
    try:
        analysis = await dynamic_risk_heatmap.analyze_portfolio_risk()

        return {
            "status": "success",
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing portfolio risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/auto-rebalance")
async def execute_auto_rebalance(dry_run: bool = Query(True)):
    """
    Execute automatic portfolio rebalancing

    Only executes CRITICAL priority actions unless dry_run=False
    """
    try:
        # Get current risk analysis
        analysis = await dynamic_risk_heatmap.analyze_portfolio_risk()

        if 'error' in analysis:
            raise HTTPException(status_code=500, detail=analysis['error'])

        actions = analysis.get('rebalance_actions', [])

        if not actions:
            return {
                "status": "success",
                "message": "No rebalancing needed",
                "portfolio_heat": analysis.get('portfolio_heat_score', 0)
            }

        # Execute rebalancing
        result = await dynamic_risk_heatmap.execute_auto_rebalance(actions, dry_run)

        return {
            "status": "success",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing rebalance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Meta Strategy Selector Endpoints
# ============================================================

class MetaAnalysisRequest(BaseModel):
    symbol: str
    include_funding: bool = True
    include_orderbook: bool = True
    include_liquidations: bool = True
    include_mtf: bool = True
    include_volume_profile: bool = True


@router.post("/meta/analyze-and-recommend")
async def meta_analyze_and_recommend(request: MetaAnalysisRequest):
    """
    Run complete meta-analysis and get strategy recommendation

    Analyzes all available market intelligence and recommends optimal strategy
    """
    try:
        # Gather market data based on request
        market_data = {}

        if request.include_funding:
            market_data['funding_sentiment'] = await funding_sentiment_engine.analyze_sentiment(
                request.symbol
            )

        if request.include_orderbook:
            market_data['orderbook'] = await orderbook_analyzer.analyze_order_book(
                request.symbol
            )

        if request.include_liquidations:
            market_data['liquidations'] = await liquidation_heatmap.calculate_heatmap(
                request.symbol
            )

        if request.include_mtf:
            market_data['mtf_confluence'] = await mtf_confluence.analyze_confluence(
                request.symbol
            )

        if request.include_volume_profile:
            market_data['volume_profile'] = await volume_profile.analyze_volume_profile(
                request.symbol
            )

        # Get portfolio state
        portfolio_state = await dynamic_risk_heatmap.analyze_portfolio_risk()

        # Meta-analysis
        recommendation = await meta_strategy_selector.analyze_and_recommend(
            symbol=request.symbol,
            market_data=market_data,
            portfolio_state=portfolio_state
        )

        return {
            "status": "success",
            "data": recommendation
        }

    except Exception as e:
        logger.error(f"Error in meta-analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/best-strategies")
async def get_best_strategies_for_condition(
    condition: str = Query(...),
    top_n: int = Query(3, ge=1, le=10)
):
    """
    Get historically best strategies for a market condition

    Returns top strategies with scores based on past performance
    """
    try:
        from modules.meta.strategy_selector import MarketCondition

        # Validate condition
        try:
            market_condition = MarketCondition(condition)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid condition. Must be one of: {[c.value for c in MarketCondition]}"
            )

        strategies = meta_strategy_selector.get_best_strategies(market_condition, top_n)

        return {
            "status": "success",
            "condition": condition,
            "strategies": strategies
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting best strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Combined Intelligence Endpoint
# ============================================================

@router.get("/complete-analysis/{symbol}")
async def get_complete_market_intelligence(symbol: str):
    """
    Get complete market intelligence for symbol

    Runs all analyses in parallel for comprehensive view
    """
    try:
        # Run all analyses in parallel
        funding_task = funding_sentiment_engine.analyze_sentiment(symbol)
        orderbook_task = orderbook_analyzer.analyze_order_book(symbol)
        liquidation_task = liquidation_heatmap.calculate_heatmap(symbol)
        mtf_task = mtf_confluence.analyze_confluence(symbol)
        vp_task = volume_profile.analyze_volume_profile(symbol)

        funding, orderbook, liquidations, mtf, vp = await asyncio.gather(
            funding_task, orderbook_task, liquidation_task, mtf_task, vp_task,
            return_exceptions=True
        )

        # Compile results
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "funding_sentiment": funding if not isinstance(funding, Exception) else None,
            "orderbook_analysis": orderbook if not isinstance(orderbook, Exception) else None,
            "liquidation_heatmap": liquidations if not isinstance(liquidations, Exception) else None,
            "mtf_confluence": mtf if not isinstance(mtf, Exception) else None,
            "volume_profile": vp if not isinstance(vp, Exception) else None
        }

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error in complete analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
