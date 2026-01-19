"""
Adaptive Parameter Controller
Uses PID control and Bayesian Optimization to adjust trading parameters dynamically
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from simple_pid import PID
from skopt import gp_minimize
from skopt.space import Real, Integer
from sqlalchemy import select, and_

from utils.logger import setup_logger
from api.models.database import SessionLocal
from api.models.ml_models import MLTradeFeature

logger = setup_logger("adaptive_controller")


class AdaptiveParameterController:
    """
    Dynamically adjusts trading parameters based on performance metrics
    Uses PID controllers and Bayesian Optimization
    """

    # Parameter search space for Bayesian Optimization
    PARAM_SPACE = {
        'min_score': Integer(50, 90),
        'max_positions': Integer(5, 20),
        'risk_per_trade_pct': Real(0.5, 3.0),
        'rsi_oversold': Integer(20, 35),
        'rsi_overbought': Integer(65, 80),
        'adx_min': Integer(20, 35),
        'volume_threshold_pct': Real(30, 100),
        'stop_loss_atr_mult': Real(1.5, 3.0),
        'take_profit_ratio': Real(1.5, 4.0),
    }

    def __init__(self):
        # PID controllers for key metrics
        # Sharpe ratio target: 1.5
        self.sharpe_pid = PID(
            Kp=0.3,
            Ki=0.1,
            Kd=0.05,
            setpoint=1.5,
            output_limits=(-10, 10)
        )

        # Max drawdown target: 10% (we want to minimize this)
        self.drawdown_pid = PID(
            Kp=-0.4,
            Ki=-0.1,
            Kd=-0.05,
            setpoint=0.10,
            output_limits=(-10, 10)
        )

        # Win rate target: 60%
        self.winrate_pid = PID(
            Kp=0.2,
            Ki=0.08,
            Kd=0.03,
            setpoint=0.60,
            output_limits=(-5, 5)
        )

        self.current_params = self._get_default_params()
        self.performance_history = []

    def _get_default_params(self) -> Dict:
        """Get default parameter values"""
        return {
            'min_score': 70,
            'max_positions': 15,
            'risk_per_trade_pct': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'adx_min': 25,
            'volume_threshold_pct': 50.0,
            'stop_loss_atr_mult': 2.0,
            'take_profit_ratio': 2.0,
        }

    async def apply_pid_adjustments(self, current_metrics: Dict) -> Dict:
        """
        Apply PID-based adjustments to parameters based on recent performance

        Args:
            current_metrics: Dict with 'sharpe_ratio_7d', 'max_drawdown_7d', 'win_rate_7d'

        Returns:
            Dictionary of adjusted parameters
        """
        logger.info("⚙️ Applying PID adjustments...")

        try:
            # Extract metrics
            sharpe_ratio = current_metrics.get('sharpe_ratio_7d', 0.0)
            max_drawdown = current_metrics.get('max_drawdown_7d', 0.0)
            win_rate = current_metrics.get('win_rate_7d', 0.5)

            logger.info(f"  Current: Sharpe={sharpe_ratio:.2f}, "
                       f"DD={max_drawdown:.1%}, WinRate={win_rate:.1%}")

            # Calculate PID adjustments
            sharpe_adjustment = self.sharpe_pid(sharpe_ratio)
            drawdown_adjustment = self.drawdown_pid(max_drawdown)
            winrate_adjustment = self.winrate_pid(win_rate)

            logger.info(f"  PID outputs: Sharpe={sharpe_adjustment:.2f}, "
                       f"DD={drawdown_adjustment:.2f}, WR={winrate_adjustment:.2f}")

            # Start with current params
            adjusted = self.current_params.copy()

            # Apply adjustments based on PID outputs

            # If Sharpe is low, increase selectivity and reduce risk
            if sharpe_adjustment < -2:
                adjusted['min_score'] = min(90, adjusted['min_score'] + 5)
                adjusted['max_positions'] = max(5, adjusted['max_positions'] - 2)
                adjusted['risk_per_trade_pct'] = max(0.5, adjusted['risk_per_trade_pct'] * 0.9)
                logger.info("  → Increasing selectivity (low Sharpe)")

            # If Sharpe is high, can afford to be more aggressive
            elif sharpe_adjustment > 2:
                adjusted['min_score'] = max(50, adjusted['min_score'] - 3)
                adjusted['max_positions'] = min(20, adjusted['max_positions'] + 1)
                adjusted['risk_per_trade_pct'] = min(3.0, adjusted['risk_per_trade_pct'] * 1.05)
                logger.info("  → Increasing aggression (high Sharpe)")

            # If drawdown is high, reduce risk significantly
            if max_drawdown > 0.15:  # 15% drawdown threshold
                adjusted['risk_per_trade_pct'] = max(0.5, adjusted['risk_per_trade_pct'] * 0.7)
                adjusted['max_positions'] = max(5, adjusted['max_positions'] - 3)
                adjusted['stop_loss_atr_mult'] = min(3.0, adjusted['stop_loss_atr_mult'] * 1.2)
                logger.info("  → Reducing risk (high drawdown)")

            # If win rate is low, tighten entry criteria
            if win_rate < 0.50:
                adjusted['min_score'] = min(90, adjusted['min_score'] + 5)
                adjusted['adx_min'] = min(35, adjusted['adx_min'] + 2)
                logger.info("  → Tightening criteria (low win rate)")

            # If win rate is high, can relax a bit
            elif win_rate > 0.70:
                adjusted['min_score'] = max(50, adjusted['min_score'] - 2)
                logger.info("  → Relaxing criteria (high win rate)")

            # Update current params
            self.current_params = adjusted

            return adjusted

        except Exception as e:
            logger.error(f"Error applying PID adjustments: {e}")
            return self.current_params

    async def optimize_parameters(
        self,
        regime: int,
        lookback_days: int = 30,
        n_calls: int = 30
    ) -> Dict:
        """
        Use Bayesian Optimization to find optimal parameters for a regime

        Args:
            regime: Market regime ID
            lookback_days: Days of historical data to use
            n_calls: Number of optimization iterations

        Returns:
            Dictionary of optimized parameters
        """
        logger.info(f"🔍 Optimizing parameters for regime {regime}...")

        try:
            # Get historical trades for this regime
            trades_df = await self._get_regime_trades(regime, lookback_days)

            if trades_df.empty or len(trades_df) < 50:
                logger.warning(f"Insufficient data for regime {regime} optimization")
                return self._get_default_params()

            # Define objective function
            def objective_function(params_list):
                """
                Objective function for Bayesian Optimization
                Returns negative Sharpe ratio (we minimize, so negate to maximize Sharpe)
                """
                # Convert params list to dict
                params = dict(zip(sorted(self.PARAM_SPACE.keys()), params_list))

                # Simulate performance with these parameters
                sharpe = self._backtest_with_params(trades_df, params)

                return -sharpe  # Minimize negative = maximize positive

            # Define search space (in sorted order)
            dimensions = [self.PARAM_SPACE[k] for k in sorted(self.PARAM_SPACE.keys())]

            # Run Bayesian Optimization
            logger.info(f"  Running Bayesian Optimization with {n_calls} iterations...")

            result = gp_minimize(
                objective_function,
                dimensions,
                n_calls=n_calls,
                random_state=42,
                n_jobs=1,  # Sequential to avoid DB conflicts
                verbose=False
            )

            # Convert result to parameter dict
            optimal_params = dict(zip(sorted(self.PARAM_SPACE.keys()), result.x))

            logger.info(f"  Optimal Sharpe: {-result.fun:.3f}")
            logger.info(f"  Optimal params: {optimal_params}")

            return optimal_params

        except Exception as e:
            logger.error(f"Error optimizing parameters: {e}", exc_info=True)
            return self._get_default_params()

    async def _get_regime_trades(self, regime: int, lookback_days: int):
        """Get historical trades for a specific regime"""
        try:
            with SessionLocal() as db:
                cutoff = datetime.now() - timedelta(days=lookback_days)

                query = select(MLTradeFeature).where(
                    and_(
                        MLTradeFeature.market_regime == regime,
                        MLTradeFeature.timestamp >= cutoff,
                        MLTradeFeature.outcome.isnot(None)
                    )
                )

                results = db.execute(query).scalars().all()

                if not results:
                    return []

                # Convert to list of dicts
                trades = []
                for r in results:
                    trades.append({
                        'outcome': r.outcome,
                        'pnl_pct': r.pnl_pct,
                        'rsi_1m': r.rsi_1m,
                        'adx_1m': r.adx_1m,
                        'volume_ratio': r.volume_ratio,
                    })

                import pandas as pd
                return pd.DataFrame(trades)

        except Exception as e:
            logger.error(f"Error getting regime trades: {e}")
            return []

    def _backtest_with_params(self, trades_df, params: Dict) -> float:
        """
        Simulate performance with given parameters
        Returns Sharpe ratio
        """
        try:
            # Filter trades based on parameters
            filtered = trades_df.copy()

            # Apply filters (simplified - in reality would use full signal logic)
            if 'rsi_oversold' in params and 'rsi_overbought' in params:
                # Keep trades with RSI in acceptable range
                filtered = filtered[
                    (filtered['rsi_1m'] >= params['rsi_oversold']) &
                    (filtered['rsi_1m'] <= params['rsi_overbought'])
                ]

            if 'adx_min' in params:
                filtered = filtered[filtered['adx_1m'] >= params['adx_min']]

            if 'volume_threshold_pct' in params:
                vol_threshold = params['volume_threshold_pct'] / 100.0
                filtered = filtered[filtered['volume_ratio'] >= vol_threshold]

            if len(filtered) < 10:
                return 0.0  # Insufficient trades after filtering

            # Calculate Sharpe ratio
            returns = filtered['pnl_pct'].values
            sharpe = returns.mean() / returns.std() if returns.std() > 0 else 0.0

            # Penalize if win rate is too low
            win_rate = (filtered['outcome'] == 'WIN').sum() / len(filtered)
            if win_rate < 0.4:
                sharpe *= 0.5  # Heavy penalty

            return sharpe

        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            return 0.0

    async def calculate_recent_metrics(self, days: int = 7) -> Dict:
        """
        Calculate performance metrics for recent period

        Args:
            days: Number of days to look back

        Returns:
            Dict with sharpe_ratio, max_drawdown, win_rate, etc.
        """
        try:
            with SessionLocal() as db:
                cutoff = datetime.now() - timedelta(days=days)

                query = select(MLTradeFeature).where(
                    and_(
                        MLTradeFeature.timestamp >= cutoff,
                        MLTradeFeature.outcome.isnot(None)
                    )
                )

                results = db.execute(query).scalars().all()

                if not results:
                    return {
                        'sharpe_ratio_7d': 0.0,
                        'max_drawdown_7d': 0.0,
                        'win_rate_7d': 0.0,
                        'n_trades': 0,
                    }

                # Convert to arrays
                pnls = np.array([r.pnl_pct for r in results if r.pnl_pct is not None])
                outcomes = [r.outcome for r in results]

                # Calculate metrics
                sharpe = pnls.mean() / pnls.std() if len(pnls) > 0 and pnls.std() > 0 else 0.0

                # Max drawdown
                cumulative = np.cumsum(pnls)
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / 100.0  # Convert to percentage
                max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0

                # Win rate
                wins = outcomes.count('WIN')
                win_rate = wins / len(outcomes) if len(outcomes) > 0 else 0.0

                return {
                    'sharpe_ratio_7d': sharpe,
                    'max_drawdown_7d': max_drawdown,
                    'win_rate_7d': win_rate,
                    'avg_pnl_pct': pnls.mean() if len(pnls) > 0 else 0.0,
                    'n_trades': len(results),
                }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                'sharpe_ratio_7d': 0.0,
                'max_drawdown_7d': 0.0,
                'win_rate_7d': 0.0,
                'n_trades': 0,
            }


# Singleton instance
adaptive_controller = AdaptiveParameterController()
