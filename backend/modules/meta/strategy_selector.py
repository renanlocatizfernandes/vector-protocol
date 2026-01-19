"""
Meta-Learning Strategy Selector
Learns which strategies work best in different market conditions and auto-selects optimal approach
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict
from enum import Enum

from utils.logger import setup_logger

logger = setup_logger("meta_strategy_selector")


class MarketCondition(str, Enum):
    """Market condition categories"""
    STRONG_UPTREND = "strong_uptrend"
    MILD_UPTREND = "mild_uptrend"
    RANGING = "ranging"
    MILD_DOWNTREND = "mild_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class StrategyRecommendation:
    """Recommended strategy configuration"""

    def __init__(
        self,
        execution_mode: str,
        trailing_stop_mode: str,
        tp_ladder_strategy: str,
        order_routing: str,
        confidence: int,
        reasoning: List[str]
    ):
        self.execution_mode = execution_mode
        self.trailing_stop_mode = trailing_stop_mode
        self.tp_ladder_strategy = tp_ladder_strategy
        self.order_routing = order_routing
        self.confidence = confidence  # 0-100
        self.reasoning = reasoning
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'execution_mode': self.execution_mode,
            'trailing_stop_mode': self.trailing_stop_mode,
            'tp_ladder_strategy': self.tp_ladder_strategy,
            'order_routing': self.order_routing,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat()
        }


class MetaStrategySelector:
    """
    Meta-Learning Strategy Selector

    Analyzes:
    - Market intelligence (funding, order book, liquidations, etc.)
    - Multi-timeframe confluence
    - Volume profile
    - Portfolio risk
    - Historical performance of strategies in similar conditions

    Selects:
    - Optimal execution mode (static, sniper, pyramid, DCA)
    - Optimal trailing stop mode
    - TP ladder strategy
    - Order routing algorithm
    """

    def __init__(self):
        self.performance_history = defaultdict(list)  # condition -> [results]
        self.strategy_scores = defaultdict(lambda: defaultdict(float))  # condition -> strategy -> score

    async def analyze_and_recommend(
        self,
        symbol: str,
        market_data: Dict,
        portfolio_state: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze market conditions and recommend optimal strategy

        Args:
            symbol: Trading pair
            market_data: Dict with all market intelligence data
            portfolio_state: Current portfolio state

        Returns:
            Strategy recommendation with confidence
        """
        try:
            logger.info(f"Meta-analysis for {symbol}")

            # Extract intelligence from market_data
            funding_sentiment = market_data.get('funding_sentiment', {})
            orderbook_analysis = market_data.get('orderbook', {})
            liquidation_heatmap = market_data.get('liquidations', {})
            mtf_confluence = market_data.get('mtf_confluence', {})
            volume_profile = market_data.get('volume_profile', {})

            # Classify market condition
            market_condition = self._classify_market_condition(
                funding_sentiment,
                mtf_confluence,
                volume_profile,
                orderbook_analysis
            )

            # Analyze each dimension
            execution_analysis = self._analyze_execution_mode(
                market_condition,
                orderbook_analysis,
                mtf_confluence
            )

            trailing_analysis = self._analyze_trailing_stop(
                market_condition,
                volume_profile,
                mtf_confluence
            )

            tp_ladder_analysis = self._analyze_tp_ladder(
                market_condition,
                mtf_confluence,
                funding_sentiment
            )

            order_routing_analysis = self._analyze_order_routing(
                orderbook_analysis,
                execution_analysis['mode']
            )

            # Portfolio risk consideration
            risk_adjustment = self._apply_risk_adjustment(
                portfolio_state,
                market_condition
            )

            # Combine analyses
            recommendation = self._create_recommendation(
                execution_analysis,
                trailing_analysis,
                tp_ladder_analysis,
                order_routing_analysis,
                risk_adjustment,
                market_condition
            )

            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                execution_analysis,
                trailing_analysis,
                tp_ladder_analysis,
                mtf_confluence,
                funding_sentiment
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),

                # Market condition
                'market_condition': market_condition.value,
                'market_condition_confidence': self._get_condition_confidence(market_data),

                # Recommendation
                'recommended_strategy': recommendation.to_dict(),
                'overall_confidence': overall_confidence,

                # Component analyses
                'execution_mode_analysis': execution_analysis,
                'trailing_stop_analysis': trailing_analysis,
                'tp_ladder_analysis': tp_ladder_analysis,
                'order_routing_analysis': order_routing_analysis,

                # Risk
                'risk_adjustment': risk_adjustment,

                # Decision factors
                'key_factors': self._extract_key_factors(market_data)
            }

            return result

        except Exception as e:
            logger.error(f"Error in meta-analysis: {e}")
            return self._default_recommendation(symbol)

    def _classify_market_condition(
        self,
        funding_sentiment: Dict,
        mtf_confluence: Dict,
        volume_profile: Dict,
        orderbook: Dict
    ) -> MarketCondition:
        """Classify current market condition"""

        # MTF direction
        mtf_direction = mtf_confluence.get('overall_direction', 'NEUTRAL')
        mtf_score = mtf_confluence.get('confluence_score', 0)

        # Volume profile position
        vp_position = volume_profile.get('position_relative_to_value_area', 'UNKNOWN')

        # Volatility from volume profile
        volatility = volume_profile.get('market_regime', 'UNKNOWN')

        # Funding sentiment
        funding_bias = funding_sentiment.get('bias', 'NEUTRAL')

        # Order book imbalance
        ob_imbalance = orderbook.get('bid_ask_imbalance', 0)

        # Determine condition
        if mtf_direction == 'BULLISH' and mtf_score > 70:
            if vp_position == 'ABOVE_VALUE_AREA':
                return MarketCondition.STRONG_UPTREND
            else:
                return MarketCondition.MILD_UPTREND

        elif mtf_direction == 'BEARISH' and mtf_score > 70:
            if vp_position == 'BELOW_VALUE_AREA':
                return MarketCondition.STRONG_DOWNTREND
            else:
                return MarketCondition.MILD_DOWNTREND

        elif abs(ob_imbalance) < 10 and mtf_score < 50:
            return MarketCondition.RANGING

        elif volatility in ['high', 'extreme']:
            return MarketCondition.HIGH_VOLATILITY

        else:
            return MarketCondition.LOW_VOLATILITY

    def _analyze_execution_mode(
        self,
        condition: MarketCondition,
        orderbook: Dict,
        mtf: Dict
    ) -> Dict:
        """Determine optimal execution mode"""

        depth_score = orderbook.get('depth_score', 50)
        confluence = mtf.get('confluence_score', 0)

        # Decision tree
        if condition in [MarketCondition.STRONG_UPTREND, MarketCondition.STRONG_DOWNTREND]:
            if confluence > 75:
                mode = 'pyramid'  # Scale into winners
                confidence = 85
                reason = "Strong trend with high confluence - pyramid into position"
            else:
                mode = 'sniper'  # Wait for better entry
                confidence = 70
                reason = "Strong trend but lower confluence - wait for pullback"

        elif condition in [MarketCondition.MILD_UPTREND, MarketCondition.MILD_DOWNTREND]:
            if depth_score > 70:
                mode = 'static'  # Single entry
                confidence = 75
                reason = "Moderate trend with good liquidity - standard entry"
            else:
                mode = 'sniper'
                confidence = 65
                reason = "Moderate trend, low liquidity - precise entry needed"

        elif condition == MarketCondition.RANGING:
            mode = 'dca'  # Average into position
            confidence = 60
            reason = "Ranging market - DCA to average entry"

        elif condition == MarketCondition.HIGH_VOLATILITY:
            mode = 'sniper'
            confidence = 70
            reason = "High volatility - wait for optimal entry points"

        else:
            mode = 'static'
            confidence = 50
            reason = "Default mode for unclear conditions"

        return {
            'mode': mode,
            'confidence': confidence,
            'reasoning': reason
        }

    def _analyze_trailing_stop(
        self,
        condition: MarketCondition,
        volume_profile: Dict,
        mtf: Dict
    ) -> Dict:
        """Determine optimal trailing stop mode"""

        vp_position = volume_profile.get('position_relative_to_value_area', 'UNKNOWN')
        trend_strength = mtf.get('confluence_score', 0)

        # Decision tree
        if condition in [MarketCondition.STRONG_UPTREND, MarketCondition.STRONG_DOWNTREND]:
            if trend_strength > 80:
                mode = 'smart'
                confidence = 90
                reason = "Strong trend - smart trailing to maximize profit"
            else:
                mode = 'dynamic'
                confidence = 75
                reason = "Strong trend - dynamic callback based on volatility"

        elif condition in [MarketCondition.MILD_UPTREND, MarketCondition.MILD_DOWNTREND]:
            mode = 'profit_based'
            confidence = 70
            reason = "Moderate trend - activate trail after min profit"

        elif condition == MarketCondition.RANGING:
            mode = 'breakeven'
            confidence = 65
            reason = "Ranging market - protect with breakeven stop"

        elif condition == MarketCondition.HIGH_VOLATILITY:
            mode = 'dynamic'
            confidence = 75
            reason = "High volatility - wide callback to avoid stops"

        else:
            mode = 'static'
            confidence = 50
            reason = "Standard ATR-based trailing stop"

        return {
            'mode': mode,
            'confidence': confidence,
            'reasoning': reason
        }

    def _analyze_tp_ladder(
        self,
        condition: MarketCondition,
        mtf: Dict,
        funding: Dict
    ) -> Dict:
        """Determine optimal TP ladder strategy"""

        confluence = mtf.get('confluence_score', 0)
        sentiment_score = funding.get('sentiment_score', 0)

        # Decision tree
        if condition in [MarketCondition.STRONG_UPTREND, MarketCondition.STRONG_DOWNTREND]:
            strategy = 'AGGRESSIVE'
            confidence = 85
            reason = "Strong trend - wider TP targets"

        elif condition in [MarketCondition.MILD_UPTREND, MarketCondition.MILD_DOWNTREND]:
            if confluence > 70:
                strategy = 'ADAPTIVE'
                confidence = 80
                reason = "Good confluence - adaptive TP based on momentum"
            else:
                strategy = 'CONSERVATIVE'
                confidence = 65
                reason = "Weaker confluence - tighter TPs"

        elif condition == MarketCondition.RANGING:
            strategy = 'CONSERVATIVE'
            confidence = 70
            reason = "Ranging market - quick profit taking"

        else:
            strategy = 'ADAPTIVE'
            confidence = 60
            reason = "Adaptive TP for uncertain conditions"

        return {
            'strategy': strategy,
            'confidence': confidence,
            'reasoning': reason
        }

    def _analyze_order_routing(
        self,
        orderbook: Dict,
        execution_mode: str
    ) -> Dict:
        """Determine optimal order routing algorithm"""

        depth_score = orderbook.get('depth_score', 50)
        spread_bps = orderbook.get('spread_bps', 5) if 'spread_bps' in orderbook else 5

        # Decision tree
        if depth_score < 40 or spread_bps > 15:
            # Low liquidity
            algorithm = 'TWAP'
            confidence = 80
            reason = "Low liquidity - split orders over time"

        elif execution_mode == 'pyramid':
            algorithm = 'ICEBERG'
            confidence = 75
            reason = "Pyramid mode - hide full order size"

        elif depth_score > 70 and spread_bps < 5:
            # High liquidity
            algorithm = 'LIMIT'
            confidence = 85
            reason = "Good liquidity - simple limit order"

        else:
            algorithm = 'ADAPTIVE'
            confidence = 70
            reason = "Adaptive routing based on conditions"

        return {
            'algorithm': algorithm,
            'confidence': confidence,
            'reasoning': reason
        }

    def _apply_risk_adjustment(
        self,
        portfolio_state: Optional[Dict],
        condition: MarketCondition
    ) -> Dict:
        """Apply risk-based adjustments"""

        if not portfolio_state:
            return {
                'adjustment': 'NONE',
                'reason': 'No portfolio state provided'
            }

        portfolio_heat = portfolio_state.get('portfolio_heat_score', 0)
        num_positions = portfolio_state.get('num_positions', 0)

        # Risk adjustments
        if portfolio_heat > 70:
            return {
                'adjustment': 'REDUCE_LEVERAGE',
                'reason': f"High portfolio heat ({portfolio_heat}/100) - reduce leverage",
                'leverage_multiplier': 0.5,
                'confidence_penalty': -20
            }

        elif num_positions >= 10:
            return {
                'adjustment': 'SKIP_TRADE',
                'reason': f"Too many positions ({num_positions}) - skip new trades",
                'confidence_penalty': -50
            }

        elif condition == MarketCondition.HIGH_VOLATILITY and portfolio_heat > 50:
            return {
                'adjustment': 'REDUCE_SIZE',
                'reason': "High volatility + moderate portfolio heat - reduce size",
                'size_multiplier': 0.7,
                'confidence_penalty': -10
            }

        else:
            return {
                'adjustment': 'NONE',
                'reason': 'Portfolio risk acceptable'
            }

    def _create_recommendation(
        self,
        execution: Dict,
        trailing: Dict,
        tp_ladder: Dict,
        routing: Dict,
        risk: Dict,
        condition: MarketCondition
    ) -> StrategyRecommendation:
        """Create combined strategy recommendation"""

        # Apply risk adjustments
        confidence_penalty = risk.get('confidence_penalty', 0)

        # Combine reasoning
        reasoning = [
            f"Market: {condition.value}",
            f"Execution: {execution['reasoning']}",
            f"Trailing: {trailing['reasoning']}",
            f"TP: {tp_ladder['reasoning']}",
            f"Routing: {routing['reasoning']}"
        ]

        if risk['adjustment'] != 'NONE':
            reasoning.append(f"Risk: {risk['reason']}")

        # Average confidence
        base_confidence = int((
            execution['confidence'] +
            trailing['confidence'] +
            tp_ladder['confidence'] +
            routing['confidence']
        ) / 4)

        final_confidence = max(0, base_confidence + confidence_penalty)

        return StrategyRecommendation(
            execution_mode=execution['mode'],
            trailing_stop_mode=trailing['mode'],
            tp_ladder_strategy=tp_ladder['strategy'],
            order_routing=routing['algorithm'],
            confidence=final_confidence,
            reasoning=reasoning
        )

    def _calculate_overall_confidence(
        self,
        execution: Dict,
        trailing: Dict,
        tp_ladder: Dict,
        mtf: Dict,
        funding: Dict
    ) -> int:
        """Calculate overall confidence in the strategy"""

        # Component confidences
        component_confidence = (
            execution['confidence'] +
            trailing['confidence'] +
            tp_ladder['confidence']
        ) / 3

        # Market signal strength
        mtf_score = mtf.get('confluence_score', 0)
        funding_conf = funding.get('confidence', 0) if funding else 0

        signal_strength = (mtf_score + funding_conf) / 2

        # Combined
        overall = (component_confidence * 0.6 + signal_strength * 0.4)

        return int(overall)

    def _get_condition_confidence(self, market_data: Dict) -> int:
        """How confident are we in the market condition classification"""

        mtf = market_data.get('mtf_confluence', {})
        funding = market_data.get('funding_sentiment', {})
        vp = market_data.get('volume_profile', {})

        # Strong signals = high confidence
        mtf_conf = mtf.get('confluence_score', 0)
        funding_conf = funding.get('confidence', 0) if funding else 0

        avg_conf = (mtf_conf + funding_conf) / 2

        return int(avg_conf)

    def _extract_key_factors(self, market_data: Dict) -> List[str]:
        """Extract key decision factors"""

        factors = []

        # MTF
        mtf = market_data.get('mtf_confluence', {})
        if mtf.get('confluence_score', 0) > 70:
            factors.append(f"High MTF confluence ({mtf['confluence_score']}/100)")

        # Funding
        funding = market_data.get('funding_sentiment', {})
        if funding.get('contrarian_opportunity'):
            factors.append(f"Contrarian funding opportunity ({funding.get('funding_rate', 0):.3f}%)")

        # Order book
        ob = market_data.get('orderbook', {})
        if ob.get('spoofing_detected'):
            factors.append("Spoofing detected in order book")

        # Liquidations
        liq = market_data.get('liquidations', {})
        if liq.get('cascade_risk_score', 0) > 70:
            factors.append(f"High liquidation cascade risk ({liq['cascade_risk_score']}/100)")

        # Volume profile
        vp = market_data.get('volume_profile', {})
        if vp.get('position_relative_to_value_area') != 'INSIDE_VALUE_AREA':
            factors.append(f"Price {vp.get('position_relative_to_value_area', 'unknown')}")

        return factors

    def _default_recommendation(self, symbol: str) -> Dict:
        """Default recommendation when analysis fails"""

        logger.warning(f"Using default recommendation for {symbol}")

        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'market_condition': 'UNKNOWN',
            'recommended_strategy': {
                'execution_mode': 'static',
                'trailing_stop_mode': 'smart',
                'tp_ladder_strategy': 'ADAPTIVE',
                'order_routing': 'ADAPTIVE',
                'confidence': 30,
                'reasoning': ['Default configuration - analysis unavailable']
            },
            'overall_confidence': 30
        }

    def record_outcome(
        self,
        condition: MarketCondition,
        strategy_config: Dict,
        outcome: Dict
    ):
        """
        Record strategy outcome for learning

        Args:
            condition: Market condition
            strategy_config: Strategy used
            outcome: Trade outcome (P&L, win/loss, etc.)
        """
        try:
            # Store performance
            self.performance_history[condition.value].append({
                'timestamp': datetime.now(),
                'config': strategy_config,
                'outcome': outcome
            })

            # Update strategy scores
            pnl_pct = outcome.get('pnl_pct', 0)

            # Positive P&L = increase score, negative = decrease
            score_delta = pnl_pct * 10  # Scale

            strategy_key = f"{strategy_config['execution_mode']}_{strategy_config['trailing_stop_mode']}"

            self.strategy_scores[condition.value][strategy_key] += score_delta

            logger.info(
                f"Recorded outcome: {condition.value} -> {strategy_key} = {pnl_pct:.2f}% "
                f"(score: {self.strategy_scores[condition.value][strategy_key]:.1f})"
            )

        except Exception as e:
            logger.error(f"Error recording outcome: {e}")

    def get_best_strategies(self, condition: MarketCondition, top_n: int = 3) -> List[Dict]:
        """
        Get historically best strategies for a market condition

        Args:
            condition: Market condition
            top_n: Number of top strategies to return

        Returns:
            List of strategy configurations with scores
        """
        try:
            strategy_scores = self.strategy_scores.get(condition.value, {})

            if not strategy_scores:
                return []

            # Sort by score
            sorted_strategies = sorted(
                strategy_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )

            # Return top N
            results = []
            for strategy_key, score in sorted_strategies[:top_n]:
                parts = strategy_key.split('_')

                results.append({
                    'execution_mode': parts[0],
                    'trailing_stop_mode': parts[1] if len(parts) > 1 else 'smart',
                    'score': round(score, 2),
                    'trades': len([h for h in self.performance_history[condition.value]
                                  if h['config'].get('execution_mode') == parts[0]])
                })

            return results

        except Exception as e:
            logger.error(f"Error getting best strategies: {e}")
            return []


# Singleton instance
meta_strategy_selector = MetaStrategySelector()
