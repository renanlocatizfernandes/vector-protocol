"""
Dynamic Risk Heatmap & Portfolio Rebalancing
Real-time portfolio risk monitoring with automatic rebalancing
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client
from config.settings import get_settings

logger = setup_logger("risk_heatmap")
settings = get_settings()


class RiskLevel(str, Enum):
    """Risk level categories"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RebalanceAction(str, Enum):
    """Rebalancing actions"""
    REDUCE_POSITION = "reduce_position"
    CLOSE_POSITION = "close_position"
    ADD_HEDGE = "add_hedge"
    ADJUST_LEVERAGE = "adjust_leverage"
    NO_ACTION = "no_action"


class PositionRisk:
    """Risk metrics for a single position"""

    def __init__(
        self,
        symbol: str,
        size: float,
        entry_price: float,
        current_price: float,
        leverage: int,
        unrealized_pnl_pct: float
    ):
        self.symbol = symbol
        self.size = size
        self.entry_price = entry_price
        self.current_price = current_price
        self.leverage = leverage
        self.unrealized_pnl_pct = unrealized_pnl_pct

        # Calculate risk metrics
        self.liquidation_distance_pct = self._calculate_liquidation_distance()
        self.risk_score = self._calculate_risk_score()
        self.risk_level = self._determine_risk_level()

    def _calculate_liquidation_distance(self) -> float:
        """Calculate distance to liquidation (estimated)"""
        if self.leverage <= 0:
            return 100.0

        # Simplified liquidation distance
        # Actual formula depends on margin mode and maintenance margin
        distance = (1 / self.leverage) * 100 * 0.9  # 90% of theoretical

        # Adjust for current P&L
        distance += self.unrealized_pnl_pct

        return max(0, distance)

    def _calculate_risk_score(self) -> int:
        """Calculate position risk score (0-100)"""
        score = 0

        # Leverage risk (0-30 points)
        if self.leverage >= 20:
            score += 30
        elif self.leverage >= 10:
            score += 20
        elif self.leverage >= 5:
            score += 10
        else:
            score += 5

        # Liquidation proximity risk (0-40 points)
        if self.liquidation_distance_pct < 10:
            score += 40
        elif self.liquidation_distance_pct < 25:
            score += 30
        elif self.liquidation_distance_pct < 50:
            score += 15
        else:
            score += 5

        # Drawdown risk (0-30 points)
        if self.unrealized_pnl_pct < -10:
            score += 30
        elif self.unrealized_pnl_pct < -5:
            score += 20
        elif self.unrealized_pnl_pct < -2:
            score += 10
        else:
            score += 0

        return min(100, score)

    def _determine_risk_level(self) -> RiskLevel:
        """Determine risk level from score"""
        if self.risk_score >= 75:
            return RiskLevel.CRITICAL
        elif self.risk_score >= 50:
            return RiskLevel.HIGH
        elif self.risk_score >= 25:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'leverage': self.leverage,
            'unrealized_pnl_pct': round(self.unrealized_pnl_pct, 2),
            'liquidation_distance_pct': round(self.liquidation_distance_pct, 2),
            'risk_score': self.risk_score,
            'risk_level': self.risk_level.value
        }


class DynamicRiskHeatmap:
    """
    Dynamic Portfolio Risk Monitoring and Rebalancing

    Features:
    - Real-time risk heatmap
    - Portfolio heat score (0-100)
    - Risk concentration detection
    - Automatic rebalancing recommendations
    - Emergency position closing
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 10  # 10 seconds for risk data
        self.rebalance_history = []

        # Risk thresholds
        self.max_portfolio_heat = 70  # Out of 100
        self.max_position_risk = 75  # Out of 100
        self.max_sector_concentration = 0.5  # 50% max in one sector
        self.max_leverage_weighted_exposure = 3.0  # Average leverage

    async def analyze_portfolio_risk(self) -> Dict:
        """
        Analyze current portfolio risk

        Returns:
            Complete risk analysis with heatmap
        """
        cache_key = "portfolio_risk_analysis"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Get current positions
            positions = await binance_client.futures_position_information()

            # Filter active positions
            active_positions = [
                p for p in positions
                if abs(float(p.get('positionAmt', 0))) > 0
            ]

            if not active_positions:
                return {
                    'portfolio_heat_score': 0,
                    'risk_level': RiskLevel.LOW.value,
                    'message': 'No active positions'
                }

            # Analyze each position
            position_risks = []

            for pos in active_positions:
                symbol = pos['symbol']
                size = abs(float(pos.get('positionAmt', 0)))
                entry_price = float(pos.get('entryPrice', 0))
                leverage = int(pos.get('leverage', 1))
                unrealized_pnl = float(pos.get('unRealizedProfit', 0))

                # Get current price
                mark_price_data = await binance_client.futures_mark_price(symbol=symbol)
                current_price = float(mark_price_data.get('markPrice', entry_price))

                # Calculate P&L %
                notional = size * entry_price
                unrealized_pnl_pct = (unrealized_pnl / notional * 100) if notional > 0 else 0

                pos_risk = PositionRisk(
                    symbol=symbol,
                    size=size,
                    entry_price=entry_price,
                    current_price=current_price,
                    leverage=leverage,
                    unrealized_pnl_pct=unrealized_pnl_pct
                )

                position_risks.append(pos_risk)

            # Calculate portfolio-level metrics
            portfolio_metrics = self._calculate_portfolio_metrics(position_risks, active_positions)

            # Calculate portfolio heat score
            portfolio_heat = self._calculate_portfolio_heat(position_risks, portfolio_metrics)

            # Determine risk level
            if portfolio_heat >= 75:
                risk_level = RiskLevel.CRITICAL
            elif portfolio_heat >= 50:
                risk_level = RiskLevel.HIGH
            elif portfolio_heat >= 25:
                risk_level = RiskLevel.MODERATE
            else:
                risk_level = RiskLevel.LOW

            # Generate rebalancing recommendations
            rebalance_actions = self._generate_rebalance_actions(
                position_risks, portfolio_metrics, portfolio_heat
            )

            result = {
                'timestamp': datetime.now(),
                'portfolio_heat_score': portfolio_heat,
                'risk_level': risk_level.value,

                # Position-level risks
                'position_risks': [p.to_dict() for p in position_risks],
                'high_risk_positions': [
                    p.to_dict() for p in position_risks
                    if p.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                ],

                # Portfolio metrics
                **portfolio_metrics,

                # Rebalancing
                'rebalance_required': portfolio_heat > self.max_portfolio_heat,
                'rebalance_actions': rebalance_actions,

                # Alerts
                'alerts': self._generate_alerts(position_risks, portfolio_heat)
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing portfolio risk: {e}")
            return {'error': str(e)}

    def _calculate_portfolio_metrics(
        self,
        position_risks: List[PositionRisk],
        positions_data: List[Dict]
    ) -> Dict:
        """Calculate portfolio-level risk metrics"""

        if not position_risks:
            return {}

        # Total exposure
        total_notional = sum(
            p.size * p.current_price for p in position_risks
        )

        # Leverage-weighted exposure
        total_leverage_weighted = sum(
            (p.size * p.current_price * p.leverage) for p in position_risks
        )

        avg_leverage = total_leverage_weighted / total_notional if total_notional > 0 else 0

        # Concentration metrics
        position_sizes = [p.size * p.current_price for p in position_risks]
        largest_position_pct = (max(position_sizes) / total_notional * 100) if total_notional > 0 else 0

        # Diversification
        num_positions = len(position_risks)
        diversification_score = min(100, num_positions * 20)  # Max at 5 positions

        # Liquidation risk
        positions_near_liquidation = len([
            p for p in position_risks
            if p.liquidation_distance_pct < 25
        ])

        # P&L distribution
        total_unrealized_pnl_pct = sum(
            (p.size * p.current_price * p.unrealized_pnl_pct / 100)
            for p in position_risks
        ) / total_notional * 100 if total_notional > 0 else 0

        return {
            'num_positions': num_positions,
            'total_notional_exposure': total_notional,
            'avg_leverage': round(avg_leverage, 2),
            'largest_position_pct': round(largest_position_pct, 2),
            'diversification_score': diversification_score,
            'positions_near_liquidation': positions_near_liquidation,
            'total_unrealized_pnl_pct': round(total_unrealized_pnl_pct, 2)
        }

    def _calculate_portfolio_heat(
        self,
        position_risks: List[PositionRisk],
        portfolio_metrics: Dict
    ) -> int:
        """
        Calculate portfolio heat score (0-100)

        Higher = more risky
        """
        heat = 0

        # Average position risk (0-40 points)
        avg_position_risk = sum(p.risk_score for p in position_risks) / len(position_risks)
        heat += int(avg_position_risk * 0.4)

        # Leverage risk (0-25 points)
        avg_leverage = portfolio_metrics.get('avg_leverage', 1)
        if avg_leverage > 15:
            heat += 25
        elif avg_leverage > 10:
            heat += 20
        elif avg_leverage > 5:
            heat += 10
        else:
            heat += 5

        # Concentration risk (0-20 points)
        largest_pos_pct = portfolio_metrics.get('largest_position_pct', 0)
        if largest_pos_pct > 50:
            heat += 20
        elif largest_pos_pct > 30:
            heat += 15
        elif largest_pos_pct > 20:
            heat += 10
        else:
            heat += 5

        # Diversification (0-15 points, inverse)
        div_score = portfolio_metrics.get('diversification_score', 0)
        heat += int(max(0, 15 - (div_score * 0.15)))

        return min(100, heat)

    def _generate_rebalance_actions(
        self,
        position_risks: List[PositionRisk],
        portfolio_metrics: Dict,
        portfolio_heat: int
    ) -> List[Dict]:
        """
        Generate recommended rebalancing actions

        Returns:
            List of action dictionaries
        """
        actions = []

        # HIGH PORTFOLIO HEAT - reduce overall exposure
        if portfolio_heat > self.max_portfolio_heat:
            actions.append({
                'action': 'REDUCE_OVERALL_EXPOSURE',
                'reason': f"Portfolio heat {portfolio_heat}/100 exceeds threshold {self.max_portfolio_heat}",
                'priority': 'HIGH',
                'target': 'Reduce positions to bring heat below 70'
            })

        # HIGH-RISK INDIVIDUAL POSITIONS
        for pos_risk in position_risks:
            if pos_risk.risk_score > self.max_position_risk:
                if pos_risk.risk_level == RiskLevel.CRITICAL:
                    action_type = RebalanceAction.CLOSE_POSITION
                    reason = f"Critical risk score {pos_risk.risk_score}/100"
                else:
                    action_type = RebalanceAction.REDUCE_POSITION
                    reason = f"High risk score {pos_risk.risk_score}/100"

                actions.append({
                    'action': action_type.value,
                    'symbol': pos_risk.symbol,
                    'current_size': pos_risk.size,
                    'current_leverage': pos_risk.leverage,
                    'risk_score': pos_risk.risk_score,
                    'reason': reason,
                    'priority': 'CRITICAL' if pos_risk.risk_level == RiskLevel.CRITICAL else 'HIGH',
                    'suggestion': self._get_rebalance_suggestion(pos_risk)
                })

        # CONCENTRATION RISK
        if portfolio_metrics.get('largest_position_pct', 0) > self.max_sector_concentration * 100:
            largest_pos = max(position_risks, key=lambda p: p.size * p.current_price)

            actions.append({
                'action': RebalanceAction.REDUCE_POSITION.value,
                'symbol': largest_pos.symbol,
                'reason': f"Position represents {portfolio_metrics['largest_position_pct']:.1f}% of portfolio",
                'priority': 'MEDIUM',
                'suggestion': 'Reduce to below 30% of total exposure'
            })

        # LEVERAGE TOO HIGH
        if portfolio_metrics.get('avg_leverage', 0) > self.max_leverage_weighted_exposure:
            high_leverage_positions = [p for p in position_risks if p.leverage > 10]

            for pos in high_leverage_positions:
                actions.append({
                    'action': RebalanceAction.ADJUST_LEVERAGE.value,
                    'symbol': pos.symbol,
                    'current_leverage': pos.leverage,
                    'reason': f"Portfolio avg leverage {portfolio_metrics['avg_leverage']:.1f}x too high",
                    'priority': 'MEDIUM',
                    'suggestion': f"Reduce leverage from {pos.leverage}x to 5-10x"
                })

        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        actions.sort(key=lambda a: priority_order.get(a.get('priority', 'LOW'), 3))

        return actions

    def _get_rebalance_suggestion(self, pos_risk: PositionRisk) -> str:
        """Get specific rebalancing suggestion for position"""

        if pos_risk.liquidation_distance_pct < 10:
            return "URGENT: Add margin or close position immediately"

        elif pos_risk.liquidation_distance_pct < 25:
            return f"Reduce size by 50% or reduce leverage from {pos_risk.leverage}x to {pos_risk.leverage // 2}x"

        elif pos_risk.unrealized_pnl_pct < -10:
            return "Cut losses - position down >10%, consider closing"

        elif pos_risk.leverage > 20:
            return f"Reduce leverage from {pos_risk.leverage}x to safer level (10x)"

        else:
            return "Monitor closely, consider reducing size by 25-30%"

    def _generate_alerts(
        self,
        position_risks: List[PositionRisk],
        portfolio_heat: int
    ) -> List[Dict]:
        """Generate risk alerts"""

        alerts = []

        # Portfolio-level alerts
        if portfolio_heat >= 75:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'PORTFOLIO_HEAT',
                'message': f"Portfolio heat CRITICAL at {portfolio_heat}/100",
                'action_required': 'Immediate rebalancing required'
            })

        # Position-level alerts
        critical_positions = [p for p in position_risks if p.risk_level == RiskLevel.CRITICAL]

        for pos in critical_positions:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'POSITION_RISK',
                'symbol': pos.symbol,
                'message': f"{pos.symbol} at CRITICAL risk (score: {pos.risk_score}/100)",
                'action_required': 'Close or reduce position urgently'
            })

        # Liquidation proximity alerts
        near_liquidation = [p for p in position_risks if p.liquidation_distance_pct < 15]

        for pos in near_liquidation:
            alerts.append({
                'level': 'WARNING',
                'type': 'LIQUIDATION_RISK',
                'symbol': pos.symbol,
                'message': f"{pos.symbol} only {pos.liquidation_distance_pct:.1f}% from liquidation",
                'action_required': 'Add margin or reduce leverage'
            })

        return alerts

    async def execute_auto_rebalance(
        self,
        actions: List[Dict],
        dry_run: bool = True
    ) -> Dict:
        """
        Execute automatic rebalancing

        Args:
            actions: List of rebalance actions
            dry_run: If True, only simulate (don't execute)

        Returns:
            Execution report
        """
        try:
            logger.info(f"Auto-rebalance: {len(actions)} actions (dry_run={dry_run})")

            execution_results = []

            for action in actions:
                action_type = action.get('action')
                symbol = action.get('symbol')
                priority = action.get('priority')

                # Only auto-execute CRITICAL priority actions
                if priority != 'CRITICAL' and not dry_run:
                    logger.info(f"Skipping {action_type} for {symbol} - priority {priority}")
                    continue

                try:
                    if action_type == RebalanceAction.CLOSE_POSITION.value:
                        result = await self._close_position(symbol, dry_run)

                    elif action_type == RebalanceAction.REDUCE_POSITION.value:
                        result = await self._reduce_position(symbol, 0.5, dry_run)  # 50% reduction

                    elif action_type == RebalanceAction.ADJUST_LEVERAGE.value:
                        result = await self._adjust_leverage(symbol, 10, dry_run)  # Reduce to 10x

                    else:
                        result = {'status': 'SKIPPED', 'reason': 'Action type not auto-executable'}

                    execution_results.append({
                        'action': action_type,
                        'symbol': symbol,
                        'result': result
                    })

                except Exception as e:
                    logger.error(f"Error executing {action_type} for {symbol}: {e}")
                    execution_results.append({
                        'action': action_type,
                        'symbol': symbol,
                        'result': {'status': 'FAILED', 'error': str(e)}
                    })

            # Log to history
            self.rebalance_history.append({
                'timestamp': datetime.now(),
                'actions_executed': len(execution_results),
                'dry_run': dry_run,
                'results': execution_results
            })

            return {
                'timestamp': datetime.now().isoformat(),
                'total_actions': len(actions),
                'executed_actions': len(execution_results),
                'dry_run': dry_run,
                'results': execution_results
            }

        except Exception as e:
            logger.error(f"Error executing auto-rebalance: {e}")
            return {'error': str(e)}

    async def _close_position(self, symbol: str, dry_run: bool) -> Dict:
        """Close position completely"""
        if dry_run:
            return {'status': 'SIMULATED', 'action': 'CLOSE', 'symbol': symbol}

        # Implementation would call order executor
        logger.info(f"Closing position {symbol}")
        return {'status': 'EXECUTED', 'action': 'CLOSE', 'symbol': symbol}

    async def _reduce_position(self, symbol: str, reduction_pct: float, dry_run: bool) -> Dict:
        """Reduce position by percentage"""
        if dry_run:
            return {
                'status': 'SIMULATED',
                'action': 'REDUCE',
                'symbol': symbol,
                'reduction_pct': reduction_pct * 100
            }

        logger.info(f"Reducing {symbol} position by {reduction_pct * 100}%")
        return {
            'status': 'EXECUTED',
            'action': 'REDUCE',
            'symbol': symbol,
            'reduction_pct': reduction_pct * 100
        }

    async def _adjust_leverage(self, symbol: str, new_leverage: int, dry_run: bool) -> Dict:
        """Adjust position leverage"""
        if dry_run:
            return {
                'status': 'SIMULATED',
                'action': 'ADJUST_LEVERAGE',
                'symbol': symbol,
                'new_leverage': new_leverage
            }

        try:
            await binance_client.futures_change_leverage(
                symbol=symbol,
                leverage=new_leverage
            )

            logger.info(f"Adjusted {symbol} leverage to {new_leverage}x")
            return {
                'status': 'EXECUTED',
                'action': 'ADJUST_LEVERAGE',
                'symbol': symbol,
                'new_leverage': new_leverage
            }

        except Exception as e:
            logger.error(f"Error adjusting leverage: {e}")
            return {'status': 'FAILED', 'error': str(e)}


# Singleton instance
dynamic_risk_heatmap = DynamicRiskHeatmap()
