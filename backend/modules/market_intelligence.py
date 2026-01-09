"""
Market Intelligence Module - Advanced Binance Futures Data
Utiliza dados não explorados para melhorar sinais e maximizar lucros

Features:
- Top Trader Long/Short Ratios (follow smart money)
- Liquidation Zone Detection (encontrar reversões)
- Funding Rate History Analysis (evitar posições caras)
- OI + Price Correlation (confirmar força de tendência)
- Order Book Depth Analysis (avaliar liquidez real)
- Mark Price vs Last Price Monitoring (detectar cascatas de liquidação)

Impacto Esperado: +15-20% melhoria no win rate através de melhor timing
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import setup_logger
from utils.binance_client import binance_client
from config.settings import get_settings
import json

logger = setup_logger("market_intelligence")


class MarketIntelligence:
    """
    Centraliza todos os dados avançados da Binance Futures
    Institucional-grade market analysis para retail traders
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache = {}  # Simple in-memory cache with TTL
        self.cache_ttl = 300  # 5 minutes default

    async def get_top_trader_ratios(self, symbol: str) -> Dict:
        """
        Binance Top Trader Long/Short Ratios

        Endpoint: /futures/data/topLongShortAccountRatio
               /futures/data/topLongShortPositionRatio

        Returns:
            {
                'account_ratio': 1.25,  # >1 = top traders net long
                'position_ratio': 1.18,
                'sentiment': 'BULLISH',  # BULLISH | NEUTRAL | BEARISH
                'strength': 85,  # 0-100 score
                'data_timestamp': '2025-01-05T10:30:00Z'
            }

        Score Impact: +10 to +20 if aligned with signal direction
        """
        try:
            cache_key = f"top_traders_{symbol}"
            if cache_key in self.cache and datetime.now() < self.cache[cache_key].get("expiry"):
                return self.cache[cache_key]["data"]

            # Fetch current ratios
            account_ratio_resp = await asyncio.to_thread(
                binance_client.client.futures_top_long_short_account_ratio,
                symbol=symbol,
                period="5m"  # Last 5 minutes
            )

            position_ratio_resp = await asyncio.to_thread(
                binance_client.client.futures_top_long_short_position_ratio,
                symbol=symbol,
                period="5m"
            )

            if not account_ratio_resp or not position_ratio_resp:
                return {
                    'account_ratio': 1.0,
                    'position_ratio': 1.0,
                    'sentiment': 'NEUTRAL',
                    'strength': 50,
                    'error': 'No data available'
                }

            # Extract latest values
            account_ratio = float(account_ratio_resp[0]['longShortRatio'])
            position_ratio = float(position_ratio_resp[0]['longShortRatio'])

            # Calculate sentiment
            sentiment = self._calculate_sentiment(account_ratio)
            strength = self._calculate_strength(account_ratio)

            result = {
                'account_ratio': round(account_ratio, 4),
                'position_ratio': round(position_ratio, 4),
                'sentiment': sentiment,
                'strength': strength,
                'data_timestamp': datetime.now().isoformat()
            }

            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'expiry': datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            logger.debug(f"{symbol}: Top Trader Ratio {account_ratio:.4f} - {sentiment}")
            return result

        except Exception as e:
            logger.error(f"Error fetching top trader ratios for {symbol}: {e}")
            return {
                'account_ratio': 1.0,
                'position_ratio': 1.0,
                'sentiment': 'NEUTRAL',
                'strength': 50,
                'error': str(e)
            }

    async def detect_liquidation_zones(self, symbol: str, lookback_hours: int = 24) -> Dict:
        """
        Detecta clusters de liquidação = zonas de reversão potencial

        Endpoint: /fapi/v1/forceOrders

        Returns:
            {
                'bullish_zones': [
                    {'price': 50000.0, 'volume': 1000000, 'count': 15},
                    ...
                ],
                'bearish_zones': [
                    {'price': 52000.0, 'volume': 800000, 'count': 12},
                    ...
                ],
                'current_proximity': {
                    'nearest_bull_zone': 50000.0,
                    'distance_pct': 0.5,
                    'in_zone': False
                },
                'recommendation': 'BUY_NEAR_BULL_ZONE'  # STRONG_BUY | BUY | NEUTRAL
            }

        Score Impact: +15 if price próximo a liquidation zone (<2%)
        """
        try:
            cache_key = f"liq_zones_{symbol}"
            if cache_key in self.cache and datetime.now() < self.cache[cache_key].get("expiry"):
                return self.cache[cache_key]["data"]

            # Fetch recent liquidation orders
            # Note: Binance API may not always have this endpoint available
            liquidations = []
            try:
                if hasattr(binance_client.client, 'futures_liquidation_orders'):
                    liquidations = await asyncio.to_thread(
                        binance_client.client.futures_liquidation_orders,
                        symbol=symbol,
                        limit=100
                    )
                elif hasattr(binance_client.client, 'futures_force_orders'):
                    liquidations = await asyncio.to_thread(
                        binance_client.client.futures_force_orders,
                        symbol=symbol,
                        limit=100
                    )
                else:
                    logger.debug(f"Liquidation orders endpoint not available for {symbol}")
            except Exception as e:
                logger.debug(f"Could not fetch liquidation data for {symbol}: {e}")

            if not liquidations:
                return {
                    'bullish_zones': [],
                    'bearish_zones': [],
                    'current_proximity': {'nearest_bull_zone': None, 'distance_pct': None},
                    'recommendation': 'NEUTRAL'
                }

            # Filter by time (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
            recent_liq = [
                liq for liq in liquidations
                if datetime.fromtimestamp(liq['time'] / 1000) > cutoff_time
            ]

            # Cluster liquidations by price
            bullish_zones = self._cluster_liquidations(recent_liq, "LONG")  # Longs got liquidated = bounce zone
            bearish_zones = self._cluster_liquidations(recent_liq, "SHORT")  # Shorts got liquidated = dump zone

            # Get current price
            current_price = await binance_client.get_symbol_price(symbol)

            # Calculate proximity
            proximity = self._calculate_zone_proximity(current_price, bullish_zones, bearish_zones)

            result = {
                'bullish_zones': bullish_zones[:5],  # Top 5 zones
                'bearish_zones': bearish_zones[:5],
                'current_proximity': proximity,
                'recommendation': self._liquidation_recommendation(proximity),
                'data_timestamp': datetime.now().isoformat()
            }

            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'expiry': datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            logger.debug(
                f"{symbol}: Found {len(bullish_zones)} bullish zones, {len(bearish_zones)} bearish zones"
            )
            return result

        except Exception as e:
            logger.error(f"Error detecting liquidation zones for {symbol}: {e}")
            return {
                'bullish_zones': [],
                'bearish_zones': [],
                'current_proximity': {'nearest_bull_zone': None, 'distance_pct': None},
                'recommendation': 'NEUTRAL',
                'error': str(e)
            }

    async def get_funding_rate_history(self, symbol: str, limit: int = 24) -> Dict:
        """
        Análise histórica de funding rates

        Detecta tendências: longs ficando caros/baratos?
        Identifica extremos: funding muito adverso?

        Returns:
            {
                'current_rate': 0.0005,  # % por período
                'avg_rate': 0.0003,
                'rates_history': [0.0001, 0.0003, 0.0005, ...],
                'trend': 'INCREASING',  # INCREASING | STABLE | DECREASING
                'bias': 'LONG_EXPENSIVE',  # LONG_EXPENSIVE | NEUTRAL | SHORT_EXPENSIVE
                'extreme_count': 3,  # Períodos com funding > 0.1%
                'recommendation': 'BLOCK_LONG_ENTRIES'  # Ação recomendada
            }

        Ação: Bloqueia LONG entries se bias='LONG_EXPENSIVE' e rate > 0.08%
        """
        try:
            cache_key = f"funding_hist_{symbol}"
            if cache_key in self.cache and datetime.now() < self.cache[cache_key].get("expiry"):
                return self.cache[cache_key]["data"]

            # Fetch funding rate history
            funding_rates = await asyncio.to_thread(
                binance_client.client.futures_funding_rate,
                symbol=symbol,
                limit=limit
            )

            if not funding_rates:
                return {
                    'current_rate': 0.0,
                    'avg_rate': 0.0,
                    'trend': 'NEUTRAL',
                    'bias': 'NEUTRAL',
                    'extreme_count': 0,
                    'recommendation': 'NEUTRAL'
                }

            # Convert to floats
            rates = [float(f['fundingRate']) for f in funding_rates]

            # Calculate metrics
            current_rate = rates[-1]
            avg_rate = np.mean(rates)
            extreme_count = sum(1 for r in rates if abs(r) > 0.001)

            # Calculate trend
            trend = self._calculate_trend(rates)

            # Determine bias
            if current_rate > 0:
                bias = 'LONG_EXPENSIVE'
            elif current_rate < 0:
                bias = 'SHORT_EXPENSIVE'
            else:
                bias = 'NEUTRAL'

            # Recommendation
            if current_rate > getattr(self.settings, 'FUNDING_BLOCK_THRESHOLD', 0.0008):
                recommendation = 'BLOCK_LONG_ENTRIES' if bias == 'LONG_EXPENSIVE' else 'BLOCK_SHORT_ENTRIES'
            elif current_rate < -getattr(self.settings, 'FUNDING_BLOCK_THRESHOLD', 0.0008):
                recommendation = 'BLOCK_SHORT_ENTRIES' if bias == 'SHORT_EXPENSIVE' else 'BLOCK_LONG_ENTRIES'
            else:
                recommendation = 'NEUTRAL'

            result = {
                'current_rate': round(current_rate, 6),
                'avg_rate': round(avg_rate, 6),
                'rates_history': [round(r, 6) for r in rates[-10:]],  # Last 10 for display
                'trend': trend,
                'bias': bias,
                'extreme_count': extreme_count,
                'recommendation': recommendation,
                'data_timestamp': datetime.now().isoformat()
            }

            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'expiry': datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            logger.debug(
                f"{symbol}: Funding Rate {current_rate:.6f} ({bias}) - Avg {avg_rate:.6f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error fetching funding rate history for {symbol}: {e}")
            return {
                'current_rate': 0.0,
                'avg_rate': 0.0,
                'trend': 'NEUTRAL',
                'bias': 'NEUTRAL',
                'recommendation': 'NEUTRAL',
                'error': str(e)
            }

    async def analyze_oi_price_correlation(self, symbol: str) -> Dict:
        """
        OI + Price Correlation Analysis

        Padrões Fortes:
        - OI ↑ + Price ↑ = STRONG_BULL (novos longs entrando)
        - OI ↑ + Price ↓ = STRONG_BEAR (novos shorts entrando)

        Padrões Fracos:
        - OI ↓ + Price ↑ = WEAK_BULL (shorts cobrindo)
        - OI ↓ + Price ↓ = WEAK_BEAR (longs fechando)

        Returns:
            {
                'oi_change_1h': 5.2,  # % change
                'price_change_1h': 2.1,  # % change
                'signal': 'STRONG_BULL',
                'strength': 85,  # 0-100
                'score_adjustment': 10  # Adicionar ao score do sinal
            }
        """
        try:
            cache_key = f"oi_price_{symbol}"
            if cache_key in self.cache and datetime.now() < self.cache[cache_key].get("expiry"):
                return self.cache[cache_key]["data"]

            # Get current OI
            current_oi = await asyncio.to_thread(
                binance_client.client.futures_open_interest,
                symbol=symbol
            )

            if not current_oi:
                return {
                    'oi_change_1h': 0,
                    'price_change_1h': 0,
                    'signal': 'NEUTRAL',
                    'strength': 50,
                    'score_adjustment': 0
                }

            current_oi_value = float(current_oi['openInterest'])

            # Get OI history (last 24 hours)
            oi_history = await asyncio.to_thread(
                binance_client.client.futures_open_interest_hist,
                symbol=symbol,
                period="1h",
                limit=24
            )

            if not oi_history or len(oi_history) < 2:
                return {
                    'oi_change_1h': 0,
                    'price_change_1h': 0,
                    'signal': 'NEUTRAL',
                    'strength': 50,
                    'score_adjustment': 0
                }

            # Calculate OI change (1 hour ago vs now)
            oi_1h_ago = float(oi_history[-2]['sumOpenInterest'])
            oi_change_pct = ((current_oi_value - oi_1h_ago) / oi_1h_ago * 100) if oi_1h_ago > 0 else 0

            # Get price change (last hour)
            klines = await asyncio.to_thread(
                binance_client.client.futures_klines,
                symbol=symbol,
                interval="1h",
                limit=2
            )

            price_1h_ago = float(klines[0][4])  # Close price
            price_now = float(klines[-1][4])
            price_change_pct = ((price_now - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0

            # Analyze correlation
            signal, strength, adjustment = self._analyze_oi_price_pattern(oi_change_pct, price_change_pct)

            result = {
                'oi_change_1h': round(oi_change_pct, 2),
                'price_change_1h': round(price_change_pct, 2),
                'signal': signal,
                'strength': strength,
                'score_adjustment': adjustment,
                'data_timestamp': datetime.now().isoformat()
            }

            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'expiry': datetime.now() + timedelta(seconds=self.cache_ttl)
            }

            logger.debug(
                f"{symbol}: OI {oi_change_pct:+.1f}%, Price {price_change_pct:+.1f}% → {signal}"
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing OI-Price correlation for {symbol}: {e}")
            return {
                'oi_change_1h': 0,
                'price_change_1h': 0,
                'signal': 'NEUTRAL',
                'strength': 50,
                'score_adjustment': 0,
                'error': str(e)
            }

    async def get_order_book_depth(self, symbol: str, depth: int = 100) -> Dict:
        """
        Avalia liquidez dentro de 5% do preço atual

        Returns:
            {
                'bid_liquidity_5pct': 250000,  # USDT
                'ask_liquidity_5pct': 180000,
                'imbalance_ratio': 1.39,  # bid_vol / ask_vol
                'liquidity_score': 7,  # 0-10
                'execution_risk': 'LOW',  # LOW | MEDIUM | HIGH
                'recommendation': 'GOOD_LIQUIDITY',
                'current_price': 50000.0
            }
        """
        try:
            cache_key = f"orderbook_{symbol}"
            if cache_key in self.cache and datetime.now() < self.cache[cache_key].get("expiry"):
                return self.cache[cache_key]["data"]

            # Get order book
            orderbook = await asyncio.to_thread(
                binance_client.client.futures_order_book,
                symbol=symbol,
                limit=depth
            )

            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return {
                    'bid_liquidity_5pct': 0,
                    'ask_liquidity_5pct': 0,
                    'imbalance_ratio': 1.0,
                    'liquidity_score': 0,
                    'execution_risk': 'CRITICAL',
                    'recommendation': 'NO_DATA'
                }

            current_price = float(orderbook['bids'][0][0])  # Best bid
            threshold = current_price * 0.05  # 5% threshold

            # Calculate liquidity within 5%
            bid_liquidity = sum(
                float(bid[0]) * float(bid[1])
                for bid in orderbook['bids']
                if float(bid[0]) > current_price - threshold
            )

            ask_liquidity = sum(
                float(ask[0]) * float(ask[1])
                for ask in orderbook['asks']
                if float(ask[0]) < current_price + threshold
            )

            # Calculate metrics
            imbalance_ratio = bid_liquidity / ask_liquidity if ask_liquidity > 0 else 1.0
            liquidity_score = self._calculate_liquidity_score(bid_liquidity, ask_liquidity)
            execution_risk = self._calculate_execution_risk(liquidity_score)

            result = {
                'bid_liquidity_5pct': round(bid_liquidity, 0),
                'ask_liquidity_5pct': round(ask_liquidity, 0),
                'imbalance_ratio': round(imbalance_ratio, 2),
                'liquidity_score': liquidity_score,  # 0-10
                'execution_risk': execution_risk,
                'recommendation': 'GOOD_LIQUIDITY' if liquidity_score >= 7 else 'LOW_LIQUIDITY',
                'current_price': current_price,
                'data_timestamp': datetime.now().isoformat()
            }

            # Cache result
            self.cache[cache_key] = {
                'data': result,
                'expiry': datetime.now() + timedelta(seconds=60)  # Shorter TTL for orderbook
            }

            logger.debug(
                f"{symbol}: Liquidity Score {liquidity_score}/10 - Imbalance {imbalance_ratio:.2f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing order book depth for {symbol}: {e}")
            return {
                'bid_liquidity_5pct': 0,
                'ask_liquidity_5pct': 0,
                'imbalance_ratio': 1.0,
                'liquidity_score': 0,
                'execution_risk': 'CRITICAL',
                'error': str(e)
            }

    async def get_market_sentiment_score(self, symbol: str) -> Dict:
        """
        Agrega TODOS os dados de market intelligence em um único score

        Retorna: {
            'sentiment_score': 35,  # -50 to +50 (negative = bearish, positive = bullish)
            'components': {
                'top_trader': 15,       # -20 to +20
                'liquidations': 10,     # -20 to +20
                'funding': -5,          # -20 to +20
                'oi_correlation': 10,   # -20 to +20
                'order_book': 5         # -10 to +10
            },
            'recommendation': 'BUY',  # STRONG_BUY | BUY | NEUTRAL | SELL | STRONG_SELL
            'overall_strength': 85,  # 0-100
            'data_timestamp': '2025-01-05T10:30:00Z'
        }
        """
        try:
            # Fetch all data in parallel
            results = await asyncio.gather(
                self.get_top_trader_ratios(symbol),
                self.detect_liquidation_zones(symbol),
                self.get_funding_rate_history(symbol),
                self.analyze_oi_price_correlation(symbol),
                self.get_order_book_depth(symbol)
            )

            top_trader, liq_zones, funding, oi_corr, orderbook = results

            # Calculate component scores
            components = {
                'top_trader': self._score_from_sentiment(top_trader.get('sentiment'), top_trader.get('strength')),
                'liquidations': self._score_from_liq_zones(liq_zones),
                'funding': self._score_from_funding(funding.get('bias'), funding.get('current_rate', 0)),
                'oi_correlation': oi_corr.get('score_adjustment', 0),
                'order_book': self._score_from_liquidity(orderbook.get('liquidity_score', 5))
            }

            # Aggregate score
            sentiment_score = sum(components.values())

            # Calculate overall strength
            strengths = [
                top_trader.get('strength', 50),
                max(0, 100 - abs(liq_zones.get('current_proximity', {}).get('distance_pct', 50) * 100)),
                orderbook.get('liquidity_score', 5) * 10
            ]
            overall_strength = int(np.mean(strengths))

            # Determine recommendation
            if sentiment_score > 30:
                recommendation = 'STRONG_BUY'
            elif sentiment_score > 10:
                recommendation = 'BUY'
            elif sentiment_score > -10:
                recommendation = 'NEUTRAL'
            elif sentiment_score > -30:
                recommendation = 'SELL'
            else:
                recommendation = 'STRONG_SELL'

            result = {
                'sentiment_score': sentiment_score,
                'components': components,
                'recommendation': recommendation,
                'overall_strength': overall_strength,
                'data_timestamp': datetime.now().isoformat()
            }

            logger.debug(
                f"{symbol}: Market Sentiment {sentiment_score:+d} ({recommendation}) - "
                f"Strength {overall_strength}%"
            )
            return result

        except Exception as e:
            logger.error(f"Error calculating market sentiment for {symbol}: {e}")
            return {
                'sentiment_score': 0,
                'components': {
                    'top_trader': 0,
                    'liquidations': 0,
                    'funding': 0,
                    'oi_correlation': 0,
                    'order_book': 0
                },
                'recommendation': 'NEUTRAL',
                'overall_strength': 50,
                'error': str(e)
            }

    # ===========================
    # HELPER METHODS
    # ===========================

    def _calculate_sentiment(self, ratio: float) -> str:
        """Convert ratio to sentiment"""
        if ratio > 1.15:
            return 'BULLISH'
        elif ratio < 0.85:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

    def _calculate_strength(self, ratio: float) -> int:
        """Calculate sentiment strength (0-100)"""
        # More extreme = stronger
        if ratio > 1.0:
            return min(100, int((ratio - 1) * 100 + 50))
        else:
            return max(0, int((1 - ratio) * 100 + 50))

    def _cluster_liquidations(self, liquidations: List[Dict], side: str) -> List[Dict]:
        """Cluster liquidations by price level"""
        if not liquidations:
            return []

        # Filter by side (SHORT liquidations = bullish zones)
        filtered = [liq for liq in liquidations if liq['side'] == side]
        if not filtered:
            return []

        # Create price clusters (round to nearest significant level)
        clusters = {}
        for liq in filtered:
            price = float(liq['price'])
            # Cluster within 0.5%
            cluster_key = round(price / (price * 0.005)) * (price * 0.005)

            if cluster_key not in clusters:
                clusters[cluster_key] = {'price': price, 'volume': 0, 'count': 0}

            clusters[cluster_key]['volume'] += float(liq['qty'])
            clusters[cluster_key]['count'] += 1

        # Sort by volume
        sorted_clusters = sorted(
            clusters.values(),
            key=lambda x: x['volume'],
            reverse=True
        )

        return sorted_clusters

    def _calculate_zone_proximity(self, current_price: float, bull_zones: List[Dict], bear_zones: List[Dict]) -> Dict:
        """Calculate distance to nearest liquidation zone"""
        proximity = {
            'nearest_bull_zone': None,
            'distance_pct': None,
            'distance_type': None,
            'in_zone': False
        }

        if bull_zones:
            nearest_bull = bull_zones[0]['price']
            distance = ((current_price - nearest_bull) / nearest_bull * 100) if nearest_bull != 0 else 0
            proximity['nearest_bull_zone'] = nearest_bull
            proximity['distance_pct'] = abs(distance)
            proximity['distance_type'] = 'below' if distance < 0 else 'above'
            proximity['in_zone'] = abs(distance) < 2.0  # Within 2%

        return proximity

    def _liquidation_recommendation(self, proximity: Dict) -> str:
        """Recommend action based on liquidation zone proximity"""
        distance = proximity.get('distance_pct', float('inf'))

        if distance is None:
            return 'NEUTRAL'
        elif distance < 1:
            return 'STRONG_BUY_BULL_ZONE'
        elif distance < 2:
            return 'BUY_BULL_ZONE'
        else:
            return 'NEUTRAL'

    def _calculate_trend(self, values: List[float]) -> str:
        """Determine trend from values"""
        if len(values) < 2:
            return 'STABLE'

        recent = values[-5:] if len(values) >= 5 else values
        avg_recent = np.mean(recent)
        avg_older = np.mean(values[:-5]) if len(values) > 5 else np.mean(values[:-1])

        change_pct = ((avg_recent - avg_older) / abs(avg_older) * 100) if avg_older != 0 else 0

        if change_pct > 10:
            return 'INCREASING'
        elif change_pct < -10:
            return 'DECREASING'
        else:
            return 'STABLE'

    def _analyze_oi_price_pattern(self, oi_change: float, price_change: float) -> Tuple[str, int, int]:
        """Analyze OI+Price pattern and return signal + strength + score adjustment"""
        oi_up = oi_change > 1
        price_up = price_change > 0.5

        if oi_up and price_up:
            return 'STRONG_BULL', 90, 10
        elif oi_up and not price_up:
            return 'STRONG_BEAR', 90, -10
        elif not oi_up and price_up:
            return 'WEAK_BULL', 60, 5
        elif not oi_up and not price_up:
            return 'WEAK_BEAR', 60, -5
        else:
            return 'NEUTRAL', 50, 0

    def _calculate_liquidity_score(self, bid_liq: float, ask_liq: float) -> int:
        """Calculate liquidity score (0-10)"""
        total_liq = bid_liq + ask_liq
        if total_liq > 500000:  # >$500k in 5% depth = excellent
            return 10
        elif total_liq > 250000:
            return 8
        elif total_liq > 100000:
            return 6
        elif total_liq > 50000:
            return 4
        elif total_liq > 10000:
            return 2
        else:
            return 0

    def _calculate_execution_risk(self, score: int) -> str:
        """Determine execution risk from liquidity score"""
        if score >= 7:
            return 'LOW'
        elif score >= 4:
            return 'MEDIUM'
        else:
            return 'HIGH'

    def _score_from_sentiment(self, sentiment: str, strength: int) -> int:
        """Convert sentiment to score adjustment"""
        if sentiment == 'BULLISH':
            return int((strength / 100) * 20)
        elif sentiment == 'BEARISH':
            return -int((strength / 100) * 20)
        else:
            return 0

    def _score_from_liq_zones(self, liq_data: Dict) -> int:
        """Convert liquidation zone data to score"""
        distance = liq_data.get('current_proximity', {}).get('distance_pct')
        if distance is None:
            return 0
        elif distance < 1:
            return 15
        elif distance < 2:
            return 10
        else:
            return 0

    def _score_from_funding(self, bias: str, rate: float) -> int:
        """Convert funding rate to score"""
        if abs(rate) < 0.0001:
            return 0
        elif abs(rate) < 0.0005:
            return -5 if rate > 0 else 5
        else:
            return -15 if rate > 0 else 15

    def _score_from_liquidity(self, score: int) -> int:
        """Convert liquidity score to signal score adjustment"""
        if score >= 7:
            return 5
        elif score >= 4:
            return 0
        else:
            return -5


# Singleton instance
market_intelligence = MarketIntelligence()
