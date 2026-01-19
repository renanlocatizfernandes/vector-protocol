"""
Performance Analytics API
Advanced performance metrics: Sharpe, Sortino, Win Rate, Profit Factor, etc.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from utils.logger import setup_logger

logger = setup_logger("performance_analytics")


class PerformanceAnalytics:
    """
    Performance Analytics System

    Calculates advanced trading metrics:
    - Sharpe Ratio
    - Sortino Ratio
    - Maximum Drawdown
    - Win Rate
    - Profit Factor
    - Risk-Reward Ratio
    - Average Win/Loss
    - Expectancy
    - Recovery Factor
    - Calmar Ratio
    """

    def __init__(self):
        self.trade_history: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.risk_free_rate = 0.02  # 2% annual risk-free rate

    async def add_trade_result(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_pct: float,
        entry_price: float,
        exit_price: float,
        quantity: float,
        leverage: int,
        duration_minutes: Optional[int] = None
    ):
        """Add completed trade for analysis"""
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'leverage': leverage,
            'duration_minutes': duration_minutes
        }

        self.trade_history.append(trade)

        # Update equity curve
        current_equity = self.equity_curve[-1]['equity'] if self.equity_curve else 0
        new_equity = current_equity + pnl

        self.equity_curve.append({
            'timestamp': datetime.now(),
            'equity': new_equity,
            'pnl': pnl
        })

    async def calculate_sharpe_ratio(
        self,
        period_days: int = 30,
        annualize: bool = True
    ) -> float:
        """
        Calculate Sharpe Ratio

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns

        Args:
            period_days: Period to analyze
            annualize: Whether to annualize the ratio

        Returns:
            Sharpe Ratio
        """
        try:
            # Get trades from period
            cutoff = datetime.now() - timedelta(days=period_days)
            period_trades = [
                t for t in self.trade_history
                if t['timestamp'] >= cutoff
            ]

            if len(period_trades) < 2:
                return 0.0

            # Get returns
            returns = np.array([t['pnl_pct'] / 100 for t in period_trades])

            # Calculate metrics
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return == 0:
                return 0.0

            # Daily risk-free rate
            daily_rf = (1 + self.risk_free_rate) ** (1/365) - 1

            # Sharpe ratio
            sharpe = (mean_return - daily_rf) / std_return

            # Annualize if requested
            if annualize:
                # Assuming ~252 trading days per year
                sharpe = sharpe * np.sqrt(252)

            return round(float(sharpe), 3)

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0

    async def calculate_sortino_ratio(
        self,
        period_days: int = 30,
        annualize: bool = True
    ) -> float:
        """
        Calculate Sortino Ratio

        Sortino = (Mean Return - Risk Free Rate) / Downside Deviation

        Only considers downside volatility (losses)

        Args:
            period_days: Period to analyze
            annualize: Whether to annualize the ratio

        Returns:
            Sortino Ratio
        """
        try:
            # Get trades from period
            cutoff = datetime.now() - timedelta(days=period_days)
            period_trades = [
                t for t in self.trade_history
                if t['timestamp'] >= cutoff
            ]

            if len(period_trades) < 2:
                return 0.0

            # Get returns
            returns = np.array([t['pnl_pct'] / 100 for t in period_trades])

            # Calculate metrics
            mean_return = np.mean(returns)

            # Downside returns (only negative)
            downside_returns = returns[returns < 0]

            if len(downside_returns) == 0:
                return float('inf')

            downside_std = np.std(downside_returns)

            if downside_std == 0:
                return 0.0

            # Daily risk-free rate
            daily_rf = (1 + self.risk_free_rate) ** (1/365) - 1

            # Sortino ratio
            sortino = (mean_return - daily_rf) / downside_std

            # Annualize if requested
            if annualize:
                sortino = sortino * np.sqrt(252)

            return round(float(sortino), 3)

        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0

    async def calculate_max_drawdown(self) -> Dict:
        """
        Calculate Maximum Drawdown

        Returns:
            Dict with max drawdown %, duration, etc.
        """
        try:
            if len(self.equity_curve) < 2:
                return {
                    'max_drawdown_pct': 0.0,
                    'max_drawdown_usd': 0.0,
                    'drawdown_duration_days': 0,
                    'current_drawdown_pct': 0.0
                }

            # Calculate drawdown at each point
            equity_values = np.array([e['equity'] for e in self.equity_curve])
            running_max = np.maximum.accumulate(equity_values)
            drawdowns = (equity_values - running_max) / running_max * 100

            # Find max drawdown
            max_dd_pct = abs(float(np.min(drawdowns)))
            max_dd_idx = int(np.argmin(drawdowns))
            max_dd_usd = abs(equity_values[max_dd_idx] - running_max[max_dd_idx])

            # Calculate drawdown duration
            # Find when drawdown started and ended
            dd_start_idx = max_dd_idx
            while dd_start_idx > 0 and equity_values[dd_start_idx] < running_max[dd_start_idx]:
                dd_start_idx -= 1

            dd_start_time = self.equity_curve[dd_start_idx]['timestamp']
            dd_end_time = self.equity_curve[max_dd_idx]['timestamp']
            dd_duration_days = (dd_end_time - dd_start_time).days

            # Current drawdown
            current_dd_pct = abs(float(drawdowns[-1]))

            return {
                'max_drawdown_pct': round(max_dd_pct, 2),
                'max_drawdown_usd': round(max_dd_usd, 2),
                'drawdown_duration_days': dd_duration_days,
                'current_drawdown_pct': round(current_dd_pct, 2),
                'peak_equity': round(float(running_max[-1]), 2),
                'current_equity': round(float(equity_values[-1]), 2)
            }

        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return {}

    async def calculate_win_rate(self, period_days: Optional[int] = None) -> Dict:
        """
        Calculate Win Rate

        Args:
            period_days: Period to analyze (None = all time)

        Returns:
            Win rate metrics
        """
        try:
            trades = self.trade_history

            if period_days:
                cutoff = datetime.now() - timedelta(days=period_days)
                trades = [t for t in trades if t['timestamp'] >= cutoff]

            if len(trades) == 0:
                return {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate_pct': 0.0
                }

            wins = sum(1 for t in trades if t['pnl'] > 0)
            losses = sum(1 for t in trades if t['pnl'] < 0)
            breakeven = len(trades) - wins - losses

            win_rate = (wins / len(trades) * 100) if len(trades) > 0 else 0

            return {
                'total_trades': len(trades),
                'wins': wins,
                'losses': losses,
                'breakeven': breakeven,
                'win_rate_pct': round(win_rate, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return {}

    async def calculate_profit_factor(self, period_days: Optional[int] = None) -> float:
        """
        Calculate Profit Factor

        Profit Factor = Gross Profit / Gross Loss

        Args:
            period_days: Period to analyze (None = all time)

        Returns:
            Profit factor
        """
        try:
            trades = self.trade_history

            if period_days:
                cutoff = datetime.now() - timedelta(days=period_days)
                trades = [t for t in trades if t['timestamp'] >= cutoff]

            if len(trades) == 0:
                return 0.0

            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))

            if gross_loss == 0:
                return float('inf') if gross_profit > 0 else 0.0

            profit_factor = gross_profit / gross_loss

            return round(profit_factor, 3)

        except Exception as e:
            logger.error(f"Error calculating profit factor: {e}")
            return 0.0

    async def calculate_expectancy(self) -> Dict:
        """
        Calculate Trade Expectancy

        Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

        Returns:
            Expectancy metrics
        """
        try:
            if len(self.trade_history) == 0:
                return {
                    'expectancy': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'avg_win_pct': 0.0,
                    'avg_loss_pct': 0.0
                }

            # Separate wins and losses
            wins = [t for t in self.trade_history if t['pnl'] > 0]
            losses = [t for t in self.trade_history if t['pnl'] < 0]

            # Calculate averages
            avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
            avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses)) if losses else 0

            avg_win_pct = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
            avg_loss_pct = abs(sum(t['pnl_pct'] for t in losses) / len(losses)) if losses else 0

            # Win/loss rates
            win_rate = len(wins) / len(self.trade_history)
            loss_rate = len(losses) / len(self.trade_history)

            # Expectancy
            expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

            return {
                'expectancy': round(expectancy, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_win_pct': round(avg_win_pct, 2),
                'avg_loss_pct': round(avg_loss_pct, 2),
                'reward_risk_ratio': round(avg_win / avg_loss, 2) if avg_loss > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error calculating expectancy: {e}")
            return {}

    async def get_symbol_performance(self) -> List[Dict]:
        """Get performance breakdown by symbol"""
        try:
            symbol_stats = defaultdict(lambda: {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'win_rate': 0.0
            })

            for trade in self.trade_history:
                symbol = trade['symbol']
                stats = symbol_stats[symbol]

                stats['total_trades'] += 1
                stats['total_pnl'] += trade['pnl']

                if trade['pnl'] > 0:
                    stats['wins'] += 1
                elif trade['pnl'] < 0:
                    stats['losses'] += 1

            # Calculate derived metrics
            for symbol, stats in symbol_stats.items():
                stats['avg_pnl'] = stats['total_pnl'] / stats['total_trades']
                stats['win_rate'] = (stats['wins'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0

            # Convert to list and sort by total P&L
            result = [
                {'symbol': symbol, **stats}
                for symbol, stats in symbol_stats.items()
            ]

            result.sort(key=lambda x: x['total_pnl'], reverse=True)

            return result

        except Exception as e:
            logger.error(f"Error getting symbol performance: {e}")
            return []

    async def get_complete_analytics(self) -> Dict:
        """Get complete performance analytics"""
        try:
            return {
                'sharpe_ratio': await self.calculate_sharpe_ratio(period_days=30),
                'sortino_ratio': await self.calculate_sortino_ratio(period_days=30),
                'max_drawdown': await self.calculate_max_drawdown(),
                'win_rate': await self.calculate_win_rate(),
                'profit_factor': await self.calculate_profit_factor(),
                'expectancy': await self.calculate_expectancy(),
                'symbol_performance': await self.get_symbol_performance(),
                'total_trades': len(self.trade_history),
                'period': '30_days'
            }

        except Exception as e:
            logger.error(f"Error getting complete analytics: {e}")
            return {}


# Singleton instance
performance_analytics = PerformanceAnalytics()
