"""
Capital Orchestrator
Master module that integrates all 10 capital management optimizations
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import math
from collections import defaultdict

from utils.logger import setup_logger
from utils.binance_client import binance_client
from modules.capital.dynamic_capital_manager import dynamic_capital_manager, CapitalStatus
from modules.capital.leverage_optimizer import leverage_optimizer
from modules.capital.position_sizer import position_sizer
from modules.capital.margin_monitor import margin_monitor

logger = setup_logger("capital_orchestrator")


class CapitalOrchestrator:
    """
    Capital Orchestrator - Master Integration Module

    Combines all 10 capital management optimizations:
    1. Dynamic Capital Manager ✓
    2. Adaptive Leverage Optimizer ✓
    3. Smart Position Sizer ✓
    4. Margin Utilization Monitor ✓
    5. Capital Scaling Strategy
    6. Risk-Parity Allocator
    7. Drawdown Protection
    8. Opportunity Cost Analyzer
    9. Multi-Tier Allocation
    10. Liquidity-Aware Sizer
    """

    def __init__(self):
        # Drawdown tracking
        self.peak_balance = 0.0
        self.current_drawdown_pct = 0.0
        self.drawdown_state = "NORMAL"

        # Multi-tier allocation targets
        self.tier_allocations = {
            'CORE': 0.50,      # 50% in BTC/ETH
            'GROWTH': 0.30,    # 30% in top altcoins
            'OPPORTUNITY': 0.15,  # 15% in volatile/setups
            'RESERVE': 0.05    # 5% always free
        }

        # Historical performance for opportunity cost
        self.position_performance = defaultdict(list)

    # ============================================================================
    # 5. CAPITAL SCALING STRATEGY
    # ============================================================================

    def get_strategy_for_capital_size(self, capital: float) -> Dict:
        """Adapt strategy based on account size"""

        if capital < 1000:  # Small account
            return {
                'account_tier': 'SMALL',
                'capital_range': '$100-$1000',
                'max_positions': 5,
                'leverage_range': '5-10x',
                'risk_per_trade_pct': 3.5,
                'strategy_focus': 'GROWTH',
                'execution_mode': 'sniper',
                'priority_assets': ['BTCUSDT', 'ETHUSDT'],
                'tp_strategy': 'CONSERVATIVE',
                'description': 'Focus on rapid growth with controlled risk'
            }

        elif capital < 5000:  # Medium account
            return {
                'account_tier': 'MEDIUM',
                'capital_range': '$1000-$5000',
                'max_positions': 10,
                'leverage_range': '3-8x',
                'risk_per_trade_pct': 2.5,
                'strategy_focus': 'CONSISTENCY',
                'execution_mode': 'pyramid',
                'priority_assets': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
                'tp_strategy': 'ADAPTIVE',
                'description': 'Balance growth and capital preservation'
            }

        else:  # Large account
            return {
                'account_tier': 'LARGE',
                'capital_range': '$5000+',
                'max_positions': 15,
                'leverage_range': '2-5x',
                'risk_per_trade_pct': 1.5,
                'strategy_focus': 'PRESERVATION',
                'execution_mode': 'adaptive',
                'priority_assets': ['Diversified across top 10'],
                'tp_strategy': 'AGGRESSIVE',
                'description': 'Preserve capital while seeking consistent returns',
                'use_pairs_trading': True,
                'use_hedging': True,
                'smart_order_routing': True
            }

    # ============================================================================
    # 6. RISK-PARITY ALLOCATOR
    # ============================================================================

    async def calculate_risk_parity_allocation(
        self,
        symbols: List[str],
        total_capital: float
    ) -> Dict:
        """Allocate capital based on inverse volatility (risk parity)"""

        try:
            volatilities = {}

            # Calculate volatility for each symbol
            for symbol in symbols:
                klines = await binance_client.futures_klines(
                    symbol=symbol,
                    interval='5m',
                    limit=100
                )

                if klines and len(klines) >= 20:
                    closes = np.array([float(k[4]) for k in klines])
                    returns = np.diff(closes) / closes[:-1]
                    volatility = np.std(returns) * 100  # As percentage
                    volatilities[symbol] = max(0.5, volatility)  # Min 0.5%
                else:
                    volatilities[symbol] = 2.5  # Default

            # Inverse volatility
            inv_vol = {s: 1.0 / v for s, v in volatilities.items()}
            total_inv_vol = sum(inv_vol.values())

            # Normalize to total capital
            allocations = {}
            for symbol, inv_v in inv_vol.items():
                allocation_pct = (inv_v / total_inv_vol) * 100
                allocation_usd = total_capital * (allocation_pct / 100)

                allocations[symbol] = {
                    'allocation_pct': round(allocation_pct, 2),
                    'allocation_usd': round(allocation_usd, 2),
                    'volatility_pct': round(volatilities[symbol], 3),
                    'risk_contribution': 'Equal'  # Risk parity ensures equal risk
                }

            return {
                'strategy': 'RISK_PARITY',
                'total_capital': total_capital,
                'allocations': allocations,
                'description': 'Capital allocated inversely to volatility for equal risk contribution'
            }

        except Exception as e:
            logger.error(f"Risk parity calculation error: {e}")
            return {}

    # ============================================================================
    # 7. DRAWDOWN PROTECTION SYSTEM
    # ============================================================================

    def update_drawdown_state(self, current_balance: float) -> Dict:
        """Update drawdown protection state"""

        # Update peak
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance

        # Calculate current drawdown
        if self.peak_balance > 0:
            drawdown_pct = ((self.peak_balance - current_balance) / self.peak_balance) * 100
        else:
            drawdown_pct = 0.0

        self.current_drawdown_pct = drawdown_pct

        # Determine state and adjustments
        if drawdown_pct >= 20:
            state = 'HEAVY_DRAWDOWN'
            position_size_mult = 0.25
            leverage_adj = -7  # Much lower leverage
            max_positions_mult = 0.2
            action = 'CIRCUIT_BREAKER - Pause bot for 24h'
        elif drawdown_pct >= 10:
            state = 'MODERATE_DRAWDOWN'
            position_size_mult = 0.50
            leverage_adj = -5
            max_positions_mult = 0.4
            action = 'Reduce risk significantly'
        elif drawdown_pct >= 5:
            state = 'LIGHT_DRAWDOWN'
            position_size_mult = 0.70
            leverage_adj = -2
            max_positions_mult = 0.7
            action = 'Reduce risk moderately'
        else:
            state = 'NORMAL'
            position_size_mult = 1.0
            leverage_adj = 0
            max_positions_mult = 1.0
            action = 'Normal operation'

        self.drawdown_state = state

        return {
            'state': state,
            'current_balance': current_balance,
            'peak_balance': self.peak_balance,
            'drawdown_pct': round(drawdown_pct, 2),
            'position_size_multiplier': position_size_mult,
            'leverage_adjustment': leverage_adj,
            'max_positions_multiplier': max_positions_mult,
            'recommended_action': action,
            'recovery_progress_pct': round(max(0, 100 - drawdown_pct), 2)
        }

    # ============================================================================
    # 8. OPPORTUNITY COST ANALYZER
    # ============================================================================

    def analyze_opportunity_cost(
        self,
        new_opportunity: Dict,
        current_positions: List[Dict],
        margin_free_pct: float
    ) -> Dict:
        """Analyze if new opportunity is worth taking vs holding capital"""

        new_score = new_opportunity.get('score', 0)
        new_expected_return = new_opportunity.get('expected_return_pct', 2.0)

        if not current_positions:
            return {
                'decision': 'ENTER_NEW' if margin_free_pct > 20 else 'SKIP',
                'reason': 'No current positions' if margin_free_pct > 20 else 'Insufficient margin'
            }

        # Find worst current position
        worst_position = min(current_positions, key=lambda x: x.get('score', 50))
        worst_score = worst_position.get('score', 50)

        # Decision logic
        if new_score > worst_score + 10:
            decision = 'ENTER_AND_CLOSE_WORST'
            reason = f"New opportunity (score: {new_score}) significantly better than worst position (score: {worst_score})"
        elif new_score > 80 and margin_free_pct > 30:
            decision = 'ENTER_NEW'
            reason = f"Excellent opportunity (score: {new_score}) and sufficient margin ({margin_free_pct:.1f}%)"
        elif margin_free_pct < 20:
            decision = 'SKIP'
            reason = f"Insufficient free margin ({margin_free_pct:.1f}%)"
        else:
            decision = 'HOLD'
            reason = "Hold capital - no compelling reason to enter"

        return {
            'new_opportunity_score': new_score,
            'worst_current_score': worst_score,
            'margin_free_pct': margin_free_pct,
            'decision': decision,
            'reason': reason,
            'expected_return_pct': new_expected_return
        }

    # ============================================================================
    # 9. MULTI-TIER CAPITAL ALLOCATION
    # ============================================================================

    async def calculate_multi_tier_allocation(
        self,
        total_capital: float,
        current_positions: List[Dict]
    ) -> Dict:
        """Allocate capital across CORE, GROWTH, OPPORTUNITY, RESERVE tiers"""

        # Calculate target allocation (USD)
        allocations = {}
        for tier, pct in self.tier_allocations.items():
            allocations[tier] = {
                'target_pct': pct * 100,
                'target_usd': total_capital * pct,
                'current_usd': 0.0,
                'deviation_usd': 0.0,
                'needs_rebalance': False
            }

        # Classify current positions into tiers
        tier_assets = {
            'CORE': ['BTCUSDT', 'ETHUSDT'],
            'GROWTH': ['BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'MATICUSDT', 'ADAUSDT'],
            'OPPORTUNITY': [],  # Everything else
            'RESERVE': []  # Always empty (free capital)
        }

        for position in current_positions:
            symbol = position.get('symbol', '')
            position_value = position.get('value_usd', 0)

            # Classify
            if symbol in tier_assets['CORE']:
                allocations['CORE']['current_usd'] += position_value
            elif symbol in tier_assets['GROWTH']:
                allocations['GROWTH']['current_usd'] += position_value
            else:
                allocations['OPPORTUNITY']['current_usd'] += position_value

        # Calculate deviations and rebalance needs
        rebalance_needed = False
        for tier in allocations:
            current = allocations[tier]['current_usd']
            target = allocations[tier]['target_usd']
            deviation = current - target
            deviation_pct = (abs(deviation) / target * 100) if target > 0 else 0

            allocations[tier]['current_pct'] = (current / total_capital * 100) if total_capital > 0 else 0
            allocations[tier]['deviation_usd'] = round(deviation, 2)
            allocations[tier]['deviation_pct'] = round(deviation_pct, 2)
            allocations[tier]['needs_rebalance'] = deviation_pct > 20  # >20% deviation

            if deviation_pct > 20:
                rebalance_needed = True

        return {
            'total_capital': total_capital,
            'tiers': allocations,
            'rebalance_recommended': rebalance_needed,
            'rebalance_frequency': 'Daily if deviation >20%, Weekly otherwise',
            'tier_descriptions': {
                'CORE': '50% - BTC, ETH - Stability, 3-5x leverage',
                'GROWTH': '30% - Top altcoins - Growth, 5-10x leverage',
                'OPPORTUNITY': '15% - Volatile/setups - High return, 3-8x leverage',
                'RESERVE': '5% - Always free - Emergency buffer'
            }
        }

    # ============================================================================
    # 10. LIQUIDITY-AWARE POSITION SIZER
    # ============================================================================

    async def calculate_liquidity_aware_size(
        self,
        symbol: str,
        desired_size: float,
        desired_size_usd: float
    ) -> Dict:
        """Adjust position size based on order book liquidity"""

        try:
            # Get order book
            order_book = await binance_client.futures_order_book(symbol=symbol, limit=100)

            if not order_book:
                return {
                    'adjusted_size': desired_size,
                    'adjustment_reason': 'Order book unavailable - using desired size'
                }

            asks = [[float(p), float(q)] for p, q in order_book.get('asks', [])]

            if not asks:
                return {
                    'adjusted_size': desired_size,
                    'adjustment_reason': 'Empty order book - using desired size'
                }

            # Calculate available liquidity
            liquidity_5_levels = sum(qty for _, qty in asks[:5])
            liquidity_20_levels = sum(qty for _, qty in asks[:20])

            # Estimate market impact
            cumulative_qty = 0
            total_cost = 0
            for price, qty in asks[:20]:
                take_qty = min(qty, desired_size - cumulative_qty)
                total_cost += price * take_qty
                cumulative_qty += take_qty

                if cumulative_qty >= desired_size:
                    break

            avg_fill_price = (total_cost / cumulative_qty) if cumulative_qty > 0 else asks[0][0]
            market_impact_pct = abs(avg_fill_price - asks[0][0]) / asks[0][0] * 100

            # Adjust size based on impact
            if market_impact_pct > 0.5:
                adjusted_size = desired_size * 0.3
                reason = f"High market impact ({market_impact_pct:.2f}%) - reduce by 70%"
                use_twap = True
            elif market_impact_pct > 0.2:
                adjusted_size = desired_size * 0.6
                reason = f"Moderate market impact ({market_impact_pct:.2f}%) - reduce by 40%"
                use_twap = True
            else:
                adjusted_size = desired_size
                reason = f"Low market impact ({market_impact_pct:.2f}%) - OK to proceed"
                use_twap = False

            # Liquidity limits
            size_vs_liquidity_5 = (desired_size / liquidity_5_levels * 100) if liquidity_5_levels > 0 else 100

            if size_vs_liquidity_5 > 10:  # >10% of first 5 levels
                adjusted_size = min(adjusted_size, liquidity_5_levels * 0.05)
                reason += "; Limited by liquidity"

            return {
                'desired_size': desired_size,
                'adjusted_size': round(adjusted_size, 6),
                'liquidity_5_levels': round(liquidity_5_levels, 4),
                'liquidity_20_levels': round(liquidity_20_levels, 4),
                'market_impact_pct': round(market_impact_pct, 3),
                'size_vs_liquidity_pct': round(size_vs_liquidity_5, 2),
                'use_twap': use_twap,
                'use_iceberg': size_vs_liquidity_5 > 10,
                'adjustment_reason': reason
            }

        except Exception as e:
            logger.error(f"Liquidity analysis error: {e}")
            return {
                'adjusted_size': desired_size,
                'adjustment_reason': f'Error: {str(e)}'
            }

    # ============================================================================
    # MASTER ORCHESTRATION METHOD
    # ============================================================================

    async def get_complete_capital_analysis(self) -> Dict:
        """
        Get complete capital analysis with all 10 optimizations

        This is the master method that combines everything
        """
        try:
            logger.info("Running complete capital analysis...")

            # 1. Dynamic Capital Manager
            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return {'error': 'Failed to get capital state'}

            total_capital = capital_state['total_wallet_balance']
            margin_used_pct = capital_state['margin_used_pct']

            # 5. Capital Scaling Strategy
            scaling_strategy = self.get_strategy_for_capital_size(total_capital)

            # 7. Drawdown Protection
            drawdown_state = self.update_drawdown_state(total_capital)

            # 4. Margin Monitor
            margin_status = margin_monitor.analyze_margin_status(
                margin_used_pct,
                capital_state['unrealized_pnl'],
                total_capital
            )

            # Get current positions for further analysis
            positions = await binance_client.futures_position_information()
            active_positions = [
                {
                    'symbol': p['symbol'],
                    'value_usd': abs(float(p.get('positionAmt', 0))) * float(p.get('entryPrice', 0)),
                    'score': 70  # Would come from signal quality
                }
                for p in positions
                if abs(float(p.get('positionAmt', 0))) > 0
            ]

            # 9. Multi-Tier Allocation
            tier_allocation = await self.calculate_multi_tier_allocation(
                total_capital,
                active_positions
            )

            # Capital history
            capital_history = await dynamic_capital_manager.get_capital_history(hours=24)

            return {
                'timestamp': datetime.now().isoformat(),

                # 1. Dynamic Capital State
                'capital_state': capital_state,
                'capital_history': capital_history,

                # 4. Margin Monitor
                'margin_status': margin_status,

                # 5. Capital Scaling
                'account_strategy': scaling_strategy,

                # 7. Drawdown Protection
                'drawdown_protection': drawdown_state,

                # 9. Multi-Tier Allocation
                'tier_allocation': tier_allocation,

                # Summary
                'summary': {
                    'total_capital': total_capital,
                    'capital_status': capital_state['capital_status'],
                    'margin_zone': margin_status['zone'],
                    'drawdown_state': drawdown_state['state'],
                    'account_tier': scaling_strategy['account_tier'],
                    'can_trade': margin_status['can_open_new'] and drawdown_state['state'] != 'HEAVY_DRAWDOWN'
                }
            }

        except Exception as e:
            logger.error(f"Complete capital analysis error: {e}")
            return {'error': str(e)}

    async def get_position_recommendation(
        self,
        symbol: str,
        signal_score: int,
        expected_return_pct: float,
        market_regime: Optional[str] = None,
        win_rate: Optional[float] = None,
        avg_win_pct: float = 3.5,
        avg_loss_pct: float = 2.0
    ) -> Dict:
        """
        Get complete position recommendation using all optimizations

        This is what the bot should call before entering a trade
        """
        try:
            logger.info(f"Generating position recommendation for {symbol}")

            # Get capital state
            capital_state = await dynamic_capital_manager.get_capital_state()
            total_capital = capital_state['total_wallet_balance']
            margin_free_pct = capital_state['margin_free_pct']

            # Check if can trade
            margin_status = margin_monitor.analyze_margin_status(
                capital_state['margin_used_pct'],
                capital_state['unrealized_pnl'],
                total_capital
            )

            if not margin_status['can_open_new']:
                return {
                    'recommendation': 'REJECT',
                    'reason': margin_status['alert_message']
                }

            # 2. Adaptive Leverage
            leverage_rec = await leverage_optimizer.calculate_optimal_leverage(
                symbol,
                total_capital,
                win_rate,
                market_regime
            )
            optimal_leverage = leverage_rec['optimal_leverage']

            # 7. Check drawdown state
            drawdown_state = self.update_drawdown_state(total_capital)

            if drawdown_state['state'] == 'HEAVY_DRAWDOWN':
                return {
                    'recommendation': 'REJECT',
                    'reason': 'Heavy drawdown - circuit breaker active'
                }

            # Apply drawdown adjustments to leverage
            optimal_leverage = max(3, optimal_leverage + drawdown_state['leverage_adjustment'])

            # 3. Smart Position Sizing (Kelly)
            portfolio_heat = capital_state.get('portfolio_heat', 0)  # Would come from risk heatmap

            kelly_size = position_sizer.calculate_kelly_size(
                total_capital,
                win_rate or 0.55,
                avg_win_pct,
                avg_loss_pct,
                market_regime,
                portfolio_heat
            )

            # Apply drawdown adjustment to position size
            position_size_usd = kelly_size['position_size_usd'] * drawdown_state['position_size_multiplier']

            # Get current price
            mark_price_data = await binance_client.futures_mark_price(symbol=symbol)
            current_price = float(mark_price_data.get('markPrice', 0))

            # Calculate quantity
            quantity = position_size_usd / current_price

            # 10. Liquidity-Aware Sizing
            liquidity_adjustment = await self.calculate_liquidity_aware_size(
                symbol,
                quantity,
                position_size_usd
            )

            final_quantity = liquidity_adjustment['adjusted_size']
            final_size_usd = final_quantity * current_price

            # 8. Opportunity Cost Analysis
            positions = await binance_client.futures_position_information()
            active_positions = [
                {'symbol': p['symbol'], 'score': 70}
                for p in positions
                if abs(float(p.get('positionAmt', 0))) > 0
            ]

            opportunity_analysis = self.analyze_opportunity_cost(
                {'score': signal_score, 'expected_return_pct': expected_return_pct},
                active_positions,
                margin_free_pct
            )

            # Final recommendation
            if opportunity_analysis['decision'] == 'SKIP':
                recommendation = 'REJECT'
                reason = opportunity_analysis['reason']
            elif liquidity_adjustment['market_impact_pct'] > 1.0:
                recommendation = 'CAUTION'
                reason = 'High market impact - consider reducing size or using TWAP'
            else:
                recommendation = 'ENTER'
                reason = 'All checks passed - safe to enter'

            return {
                'recommendation': recommendation,
                'reason': reason,

                # Position parameters
                'symbol': symbol,
                'optimal_leverage': optimal_leverage,
                'position_size_usd': round(final_size_usd, 2),
                'quantity': round(final_quantity, 6),
                'expected_margin_required': round(final_size_usd / optimal_leverage, 2),

                # Risk metrics
                'risk_pct_of_capital': round((final_size_usd / total_capital) * 100, 2),
                'kelly_recommendation_pct': kelly_size['adjusted_kelly_pct'],

                # Adjustments applied
                'leverage_analysis': leverage_rec,
                'liquidity_analysis': liquidity_adjustment,
                'opportunity_cost': opportunity_analysis,
                'drawdown_adjustments': {
                    'state': drawdown_state['state'],
                    'size_multiplier': drawdown_state['position_size_multiplier'],
                    'leverage_adj': drawdown_state['leverage_adjustment']
                },

                # Execution recommendation
                'execution_method': 'TWAP' if liquidity_adjustment.get('use_twap') else 'LIMIT',
                'use_iceberg': liquidity_adjustment.get('use_iceberg', False),

                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Position recommendation error: {e}")
            return {
                'recommendation': 'ERROR',
                'reason': str(e)
            }


# Singleton instance
capital_orchestrator = CapitalOrchestrator()
