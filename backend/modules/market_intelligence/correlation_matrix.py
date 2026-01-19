"""
Correlation Matrix & Pairs Trading Analyzer
Analyzes price correlations between pairs for hedging and pairs trading opportunities
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("correlation_matrix")


class PairOpportunity:
    """Represents a pairs trading opportunity"""

    def __init__(
        self,
        pair1: str,
        pair2: str,
        correlation: float,
        zscore: float,
        opportunity_type: str,
        confidence: int
    ):
        self.pair1 = pair1
        self.pair2 = pair2
        self.correlation = correlation
        self.zscore = zscore
        self.opportunity_type = opportunity_type  # 'pairs_trade', 'hedge', 'divergence'
        self.confidence = confidence  # 0-100
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'pair1': self.pair1,
            'pair2': self.pair2,
            'correlation': round(self.correlation, 3),
            'zscore': round(self.zscore, 2),
            'opportunity_type': self.opportunity_type,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


class CorrelationMatrix:
    """
    Analyzes correlations between cryptocurrency pairs

    Use cases:
    - Portfolio diversification (low correlation)
    - Hedging (high positive correlation)
    - Pairs trading (high correlation with temporary divergence)
    - Risk management (identify correlated positions)
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.lookback_periods = {
            '1h': {'interval': '1m', 'limit': 60},
            '4h': {'interval': '5m', 'limit': 48},
            '1d': {'interval': '15m', 'limit': 96},
            '1w': {'interval': '1h', 'limit': 168},
        }

    async def calculate_correlation_matrix(
        self,
        symbols: List[str],
        period: str = '1d'
    ) -> Dict:
        """
        Calculate correlation matrix for list of symbols

        Args:
            symbols: List of trading pairs (e.g., ['BTCUSDT', 'ETHUSDT'])
            period: Time period ('1h', '4h', '1d', '1w')

        Returns:
            Correlation matrix and analysis
        """
        cache_key = f"corr_matrix_{'_'.join(sorted(symbols))}_{period}"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            if period not in self.lookback_periods:
                period = '1d'

            config = self.lookback_periods[period]

            # Fetch price data for all symbols in parallel
            tasks = [
                self._get_price_series(symbol, config['interval'], config['limit'])
                for symbol in symbols
            ]

            price_series = await asyncio.gather(*tasks)

            # Filter out failed fetches
            valid_data = {}
            for i, symbol in enumerate(symbols):
                if price_series[i] is not None:
                    valid_data[symbol] = price_series[i]

            if len(valid_data) < 2:
                logger.warning("Not enough valid data to calculate correlations")
                return {}

            # Calculate returns
            returns_data = {}
            for symbol, prices in valid_data.items():
                returns = np.diff(prices) / prices[:-1]
                returns_data[symbol] = returns

            # Build correlation matrix
            symbols_list = list(returns_data.keys())
            n = len(symbols_list)
            corr_matrix = np.zeros((n, n))

            for i in range(n):
                for j in range(n):
                    if i == j:
                        corr_matrix[i][j] = 1.0
                    else:
                        corr, _ = stats.pearsonr(
                            returns_data[symbols_list[i]],
                            returns_data[symbols_list[j]]
                        )
                        corr_matrix[i][j] = corr

            # Convert to dict format
            matrix_dict = {}
            for i, symbol1 in enumerate(symbols_list):
                matrix_dict[symbol1] = {}
                for j, symbol2 in enumerate(symbols_list):
                    matrix_dict[symbol1][symbol2] = round(corr_matrix[i][j], 3)

            # Identify opportunities
            opportunities = self._identify_opportunities(
                symbols_list,
                corr_matrix,
                returns_data,
                valid_data
            )

            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics(
                symbols_list,
                corr_matrix
            )

            result = {
                'period': period,
                'timestamp': datetime.now(),
                'symbols': symbols_list,

                # Correlation matrix
                'correlation_matrix': matrix_dict,

                # Opportunities
                'pairs_trading_opportunities': [o.to_dict() for o in opportunities['pairs_trade']],
                'hedge_opportunities': [o.to_dict() for o in opportunities['hedge']],
                'divergence_opportunities': [o.to_dict() for o in opportunities['divergence']],

                # Portfolio metrics
                **portfolio_metrics
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {}

    async def _get_price_series(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> Optional[np.ndarray]:
        """
        Get price series for symbol

        Returns:
            Numpy array of closing prices
        """
        try:
            klines = await binance_client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            if not klines:
                return None

            closes = np.array([float(k[4]) for k in klines])
            return closes

        except Exception as e:
            logger.error(f"Error fetching price series for {symbol}: {e}")
            return None

    def _identify_opportunities(
        self,
        symbols: List[str],
        corr_matrix: np.ndarray,
        returns_data: Dict[str, np.ndarray],
        price_data: Dict[str, np.ndarray]
    ) -> Dict[str, List[PairOpportunity]]:
        """
        Identify trading opportunities from correlation analysis

        Returns:
            Dict with opportunities by type
        """
        opportunities = {
            'pairs_trade': [],
            'hedge': [],
            'divergence': []
        }

        n = len(symbols)

        for i in range(n):
            for j in range(i + 1, n):
                symbol1 = symbols[i]
                symbol2 = symbols[j]
                correlation = corr_matrix[i][j]

                # Calculate spread z-score for pairs trading
                returns1 = returns_data[symbol1]
                returns2 = returns_data[symbol2]

                spread = returns1 - returns2
                zscore = (spread[-1] - np.mean(spread)) / (np.std(spread) + 1e-10)

                # HIGH POSITIVE CORRELATION (> 0.7) - Pairs trading or hedging
                if correlation > 0.7:
                    # Divergence check (high correlation but currently diverging)
                    if abs(zscore) > 2.0:
                        # Pairs trading opportunity
                        opportunity = PairOpportunity(
                            pair1=symbol1,
                            pair2=symbol2,
                            correlation=correlation,
                            zscore=zscore,
                            opportunity_type='pairs_trade',
                            confidence=min(100, int(abs(zscore) * 30 + correlation * 30))
                        )
                        opportunities['pairs_trade'].append(opportunity)

                    else:
                        # Hedge opportunity (move together reliably)
                        opportunity = PairOpportunity(
                            pair1=symbol1,
                            pair2=symbol2,
                            correlation=correlation,
                            zscore=zscore,
                            opportunity_type='hedge',
                            confidence=int(correlation * 100)
                        )
                        opportunities['hedge'].append(opportunity)

                # NEGATIVE CORRELATION (< -0.5) - Diversification/divergence
                elif correlation < -0.5:
                    opportunity = PairOpportunity(
                        pair1=symbol1,
                        pair2=symbol2,
                        correlation=correlation,
                        zscore=zscore,
                        opportunity_type='divergence',
                        confidence=int(abs(correlation) * 80)
                    )
                    opportunities['divergence'].append(opportunity)

        # Sort by confidence
        for opp_type in opportunities:
            opportunities[opp_type].sort(key=lambda x: x.confidence, reverse=True)

        return opportunities

    def _calculate_portfolio_metrics(
        self,
        symbols: List[str],
        corr_matrix: np.ndarray
    ) -> Dict:
        """
        Calculate portfolio diversification metrics

        Returns:
            Portfolio metrics
        """
        n = len(symbols)

        if n < 2:
            return {
                'avg_correlation': 0.0,
                'diversification_score': 100,
                'max_correlation': 0.0,
                'min_correlation': 0.0,
                'highly_correlated_pairs': []
            }

        # Get upper triangle (exclude diagonal)
        upper_triangle = []
        highly_correlated = []

        for i in range(n):
            for j in range(i + 1, n):
                corr = corr_matrix[i][j]
                upper_triangle.append(corr)

                if abs(corr) > 0.8:
                    highly_correlated.append({
                        'pair1': symbols[i],
                        'pair2': symbols[j],
                        'correlation': round(corr, 3)
                    })

        avg_correlation = np.mean(upper_triangle)
        max_correlation = np.max(upper_triangle)
        min_correlation = np.min(upper_triangle)

        # Diversification score (0-100)
        # Lower average correlation = higher diversification
        diversification_score = int(max(0, 100 - (abs(avg_correlation) * 100)))

        return {
            'avg_correlation': round(avg_correlation, 3),
            'max_correlation': round(max_correlation, 3),
            'min_correlation': round(min_correlation, 3),
            'diversification_score': diversification_score,
            'highly_correlated_pairs': highly_correlated,
            'total_pairs_analyzed': len(upper_triangle)
        }

    async def get_hedge_recommendation(
        self,
        symbol: str,
        candidates: List[str],
        period: str = '1d'
    ) -> Dict:
        """
        Find best hedge for a given symbol

        Args:
            symbol: Symbol to hedge
            candidates: List of potential hedge candidates
            period: Time period for correlation

        Returns:
            Best hedge recommendations
        """
        try:
            # Calculate correlations
            all_symbols = [symbol] + candidates
            matrix_result = await self.calculate_correlation_matrix(all_symbols, period)

            if not matrix_result:
                return {}

            # Extract correlations with target symbol
            corr_matrix = matrix_result['correlation_matrix']
            symbol_correlations = corr_matrix.get(symbol, {})

            # Sort by absolute correlation (closest to +1.0)
            hedges = []
            for candidate in candidates:
                if candidate in symbol_correlations:
                    corr = symbol_correlations[candidate]
                    hedges.append({
                        'symbol': candidate,
                        'correlation': corr,
                        'effectiveness': int(max(0, corr * 100)),  # Higher = better hedge
                        'hedge_ratio': round(corr, 2)  # Simplified (should use beta)
                    })

            # Sort by effectiveness
            hedges.sort(key=lambda x: x['effectiveness'], reverse=True)

            return {
                'target_symbol': symbol,
                'period': period,
                'timestamp': datetime.now().isoformat(),
                'recommendations': hedges[:5],  # Top 5
                'best_hedge': hedges[0] if hedges else None
            }

        except Exception as e:
            logger.error(f"Error getting hedge recommendation: {e}")
            return {}

    async def get_pairs_trade_signal(
        self,
        pair1: str,
        pair2: str,
        period: str = '1d'
    ) -> Dict:
        """
        Get pairs trading signal for two symbols

        Args:
            pair1: First symbol
            pair2: Second symbol
            period: Time period

        Returns:
            Pairs trading signal
        """
        try:
            config = self.lookback_periods.get(period, self.lookback_periods['1d'])

            # Get price series
            prices1 = await self._get_price_series(pair1, config['interval'], config['limit'])
            prices2 = await self._get_price_series(pair2, config['interval'], config['limit'])

            if prices1 is None or prices2 is None:
                return {}

            # Calculate returns
            returns1 = np.diff(prices1) / prices1[:-1]
            returns2 = np.diff(prices2) / prices2[:-1]

            # Correlation
            correlation, p_value = stats.pearsonr(returns1, returns2)

            # Calculate spread
            spread = returns1 - returns2
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            current_spread = spread[-1]

            # Z-score
            zscore = (current_spread - spread_mean) / (spread_std + 1e-10)

            # Generate signal
            signal = 'NEUTRAL'
            confidence = 0
            action = None

            if correlation > 0.7:  # High correlation required
                if zscore > 2.0:
                    # Spread too high - pair1 outperforming
                    signal = 'MEAN_REVERSION'
                    action = f"SHORT {pair1}, LONG {pair2}"
                    confidence = min(100, int(abs(zscore) * 30))

                elif zscore < -2.0:
                    # Spread too low - pair2 outperforming
                    signal = 'MEAN_REVERSION'
                    action = f"LONG {pair1}, SHORT {pair2}"
                    confidence = min(100, int(abs(zscore) * 30))

                elif abs(zscore) < 0.5:
                    signal = 'NO_OPPORTUNITY'
                    confidence = 20

            return {
                'pair1': pair1,
                'pair2': pair2,
                'period': period,
                'timestamp': datetime.now().isoformat(),

                # Metrics
                'correlation': round(correlation, 3),
                'p_value': round(p_value, 4),
                'zscore': round(zscore, 2),
                'spread_mean': round(spread_mean, 6),
                'spread_std': round(spread_std, 6),

                # Signal
                'signal': signal,
                'confidence': confidence,
                'action': action,

                # Entry/Exit levels
                'entry_zscore_threshold': 2.0,
                'exit_zscore_threshold': 0.5,
                'current_spread': round(current_spread, 6)
            }

        except Exception as e:
            logger.error(f"Error getting pairs trade signal: {e}")
            return {}

    async def analyze_portfolio_correlation(
        self,
        positions: List[Dict],
        period: str = '1d'
    ) -> Dict:
        """
        Analyze correlation risk in current portfolio

        Args:
            positions: List of current positions with 'symbol' and 'size'
            period: Time period

        Returns:
            Portfolio correlation analysis
        """
        try:
            if not positions:
                return {}

            symbols = [p['symbol'] for p in positions]

            # Calculate correlation matrix
            matrix_result = await self.calculate_correlation_matrix(symbols, period)

            if not matrix_result:
                return {}

            # Calculate weighted correlation
            # Positions with larger sizes contribute more to correlation risk

            total_exposure = sum(abs(p.get('size', 0)) for p in positions)

            weighted_corr = 0
            max_pair_correlation = 0
            risky_pairs = []

            for i, pos1 in enumerate(positions):
                for j, pos2 in enumerate(positions):
                    if i >= j:
                        continue

                    symbol1 = pos1['symbol']
                    symbol2 = pos2['symbol']

                    corr = matrix_result['correlation_matrix'].get(symbol1, {}).get(symbol2, 0)

                    # Weight by position sizes
                    weight1 = abs(pos1.get('size', 0)) / total_exposure if total_exposure > 0 else 0
                    weight2 = abs(pos2.get('size', 0)) / total_exposure if total_exposure > 0 else 0

                    weighted_corr += abs(corr) * weight1 * weight2

                    if abs(corr) > max_pair_correlation:
                        max_pair_correlation = abs(corr)

                    # Identify risky pairs (high correlation + same direction)
                    if abs(corr) > 0.8:
                        # Same direction (both long or both short)
                        same_direction = (
                            (pos1.get('side') == pos2.get('side')) or
                            (np.sign(pos1.get('size', 0)) == np.sign(pos2.get('size', 0)))
                        )

                        if same_direction:
                            risky_pairs.append({
                                'pair1': symbol1,
                                'pair2': symbol2,
                                'correlation': round(corr, 3),
                                'risk': 'High - same direction, high correlation'
                            })

            # Portfolio risk score (0-100)
            # Higher = more correlated = more risk
            portfolio_risk = int(min(100, weighted_corr * 150))

            return {
                'timestamp': datetime.now().isoformat(),
                'period': period,
                'num_positions': len(positions),

                # Correlation metrics
                'weighted_avg_correlation': round(weighted_corr, 3),
                'max_pair_correlation': round(max_pair_correlation, 3),
                'portfolio_correlation_risk': portfolio_risk,

                # Risk assessment
                'risk_level': 'HIGH' if portfolio_risk > 70 else 'MEDIUM' if portfolio_risk > 40 else 'LOW',
                'risky_pairs': risky_pairs,

                # Recommendations
                'diversification_score': matrix_result.get('diversification_score', 0),
                'recommendation': self._get_portfolio_recommendation(portfolio_risk, risky_pairs)
            }

        except Exception as e:
            logger.error(f"Error analyzing portfolio correlation: {e}")
            return {}

    def _get_portfolio_recommendation(
        self,
        risk_score: int,
        risky_pairs: List[Dict]
    ) -> str:
        """Generate recommendation based on portfolio correlation risk"""

        if risk_score > 70:
            return "HIGH RISK: Portfolio highly correlated. Consider reducing correlated positions or adding hedges."

        elif risk_score > 40:
            if risky_pairs:
                return f"MODERATE RISK: {len(risky_pairs)} highly correlated pair(s). Monitor for concentration risk."
            else:
                return "MODERATE RISK: Some correlation present but manageable."

        else:
            return "LOW RISK: Portfolio well diversified with low correlation."


# Singleton instance
correlation_matrix = CorrelationMatrix()
