"""
Order Book Depth Analysis & Whale Wall Detection
Analyzes order book to detect support/resistance from large orders
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("orderbook_analyzer")


class OrderBookLevel:
    """Represents a significant price level in the order book"""

    def __init__(self, price: float, quantity: float, side: str, strength: int):
        self.price = price
        self.quantity = quantity
        self.side = side  # 'bid' or 'ask'
        self.strength = strength  # 0-100 score
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'price': self.price,
            'quantity': self.quantity,
            'side': self.side,
            'strength': self.strength,
            'type': 'support' if self.side == 'bid' else 'resistance',
            'timestamp': self.timestamp.isoformat()
        }


class OrderBookAnalyzer:
    """
    Analyzes order book depth to detect:
    - Whale walls (large orders that act as support/resistance)
    - Bid/Ask imbalance
    - Spoofing detection
    - Dynamic support/resistance levels
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 10  # 10 seconds (order book changes fast)
        self.depth_limit = 500  # Number of levels to analyze

    async def get_order_book(self, symbol: str, limit: int = 500) -> Optional[Dict]:
        """
        Get order book depth from Binance

        Args:
            symbol: Trading pair
            limit: Number of levels (5, 10, 20, 50, 100, 500, 1000)

        Returns:
            Order book data with bids and asks
        """
        try:
            order_book = await binance_client.futures_order_book(
                symbol=symbol,
                limit=limit
            )

            return {
                'bids': [[float(price), float(qty)] for price, qty in order_book.get('bids', [])],
                'asks': [[float(price), float(qty)] for price, qty in order_book.get('asks', [])],
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return None

    async def analyze_order_book(self, symbol: str) -> Dict:
        """
        Complete order book analysis

        Returns:
            Analysis with whale walls, imbalance, and trading signals
        """
        cache_key = f"{symbol}_orderbook"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Get order book
            order_book = await self.get_order_book(symbol, self.depth_limit)

            if not order_book:
                return {}

            bids = order_book['bids']
            asks = order_book['asks']

            # Get current price
            mark_price = await binance_client.futures_mark_price(symbol=symbol)
            current_price = float(mark_price.get('markPrice', 0))

            # Detect whale walls
            whale_bids = self._detect_whale_walls(bids, 'bid', current_price)
            whale_asks = self._detect_whale_walls(asks, 'ask', current_price)

            # Calculate bid/ask imbalance
            imbalance = self._calculate_imbalance(bids, asks, current_price)

            # Detect spoofing patterns
            spoofing_detected = self._detect_spoofing(whale_bids, whale_asks, current_price)

            # Generate support/resistance levels
            support_levels = [w.to_dict() for w in whale_bids[:5]]  # Top 5
            resistance_levels = [w.to_dict() for w in whale_asks[:5]]

            # Calculate depth score (0-100)
            depth_score = self._calculate_depth_score(bids, asks, imbalance)

            # Generate trading signals
            signals = self._generate_signals(
                current_price,
                whale_bids,
                whale_asks,
                imbalance,
                spoofing_detected
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'current_price': current_price,

                # Whale walls
                'whale_bids': support_levels,
                'whale_asks': resistance_levels,

                # Imbalance
                'bid_ask_imbalance': imbalance['ratio'],
                'imbalance_pct': imbalance['pct'],
                'dominant_side': imbalance['dominant_side'],

                # Depth metrics
                'total_bid_volume': imbalance['total_bid_volume'],
                'total_ask_volume': imbalance['total_ask_volume'],
                'depth_score': depth_score,

                # Detection
                'spoofing_detected': spoofing_detected,

                # Signals
                **signals
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing order book for {symbol}: {e}")
            return {}

    def _detect_whale_walls(
        self,
        levels: List[List[float]],
        side: str,
        current_price: float
    ) -> List[OrderBookLevel]:
        """
        Detect significant whale walls (large orders)

        Args:
            levels: List of [price, quantity] from order book
            side: 'bid' or 'ask'
            current_price: Current market price

        Returns:
            List of OrderBookLevel objects sorted by strength
        """
        if not levels:
            return []

        # Calculate statistics
        quantities = [qty for _, qty in levels]
        avg_qty = sum(quantities) / len(quantities) if quantities else 0

        whale_walls = []

        for price, qty in levels:
            # Distance from current price
            distance_pct = abs(price - current_price) / current_price * 100

            # Skip if too far (beyond 2%)
            if distance_pct > 2.0:
                continue

            # Whale threshold: 3x average size
            if qty >= avg_qty * 3:
                # Calculate strength (0-100)
                size_score = min(100, (qty / avg_qty) * 20)  # Size component
                proximity_score = max(0, 100 - (distance_pct * 50))  # Proximity component

                strength = int((size_score * 0.7) + (proximity_score * 0.3))

                whale_wall = OrderBookLevel(
                    price=price,
                    quantity=qty,
                    side=side,
                    strength=strength
                )

                whale_walls.append(whale_wall)

        # Sort by strength
        whale_walls.sort(key=lambda x: x.strength, reverse=True)

        return whale_walls

    def _calculate_imbalance(
        self,
        bids: List[List[float]],
        asks: List[List[float]],
        current_price: float,
        range_pct: float = 0.5
    ) -> Dict:
        """
        Calculate bid/ask imbalance near current price

        Args:
            bids: Bid levels
            asks: Ask levels
            current_price: Current price
            range_pct: Price range to consider (% from current)

        Returns:
            Imbalance metrics
        """
        # Define range
        lower_bound = current_price * (1 - range_pct / 100)
        upper_bound = current_price * (1 + range_pct / 100)

        # Sum volumes in range
        bid_volume = sum(qty for price, qty in bids if price >= lower_bound)
        ask_volume = sum(qty for price, qty in asks if price <= upper_bound)

        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return {
                'ratio': 1.0,
                'pct': 0,
                'dominant_side': 'NEUTRAL',
                'total_bid_volume': 0,
                'total_ask_volume': 0
            }

        # Calculate ratio (bid/ask)
        ratio = bid_volume / ask_volume if ask_volume > 0 else 10.0

        # Imbalance percentage
        imbalance_pct = ((bid_volume - ask_volume) / total_volume) * 100

        # Determine dominant side
        if imbalance_pct > 20:
            dominant = 'BID'  # Buy pressure
        elif imbalance_pct < -20:
            dominant = 'ASK'  # Sell pressure
        else:
            dominant = 'NEUTRAL'

        return {
            'ratio': ratio,
            'pct': imbalance_pct,
            'dominant_side': dominant,
            'total_bid_volume': bid_volume,
            'total_ask_volume': ask_volume
        }

    def _detect_spoofing(
        self,
        whale_bids: List[OrderBookLevel],
        whale_asks: List[OrderBookLevel],
        current_price: float
    ) -> bool:
        """
        Detect potential spoofing (fake walls to manipulate price)

        Spoofing characteristics:
        - Very large orders far from price
        - Asymmetric walls (one side only)
        - Walls that disappear quickly (tracked over time)

        Returns:
            True if spoofing pattern detected
        """
        # Simple heuristic: massive wall on one side only
        if not whale_bids and not whale_asks:
            return False

        bid_strength = sum(w.strength for w in whale_bids[:3])
        ask_strength = sum(w.strength for w in whale_asks[:3])

        # One side has 3x more strength than other
        if bid_strength > 0 and ask_strength > 0:
            ratio = max(bid_strength / ask_strength, ask_strength / bid_strength)
            if ratio >= 3.0:
                logger.warning(f"Potential spoofing detected: strength ratio {ratio:.1f}")
                return True

        return False

    def _calculate_depth_score(
        self,
        bids: List[List[float]],
        asks: List[List[float]],
        imbalance: Dict
    ) -> int:
        """
        Calculate order book depth score (0-100)

        Higher score = more liquid, better for trading

        Factors:
        - Total volume
        - Number of levels
        - Imbalance (closer to neutral is better)
        - Spread tightness
        """
        score = 0

        # Volume score (0-40 points)
        total_volume = imbalance['total_bid_volume'] + imbalance['total_ask_volume']
        if total_volume > 1000:
            score += 40
        elif total_volume > 500:
            score += 30
        elif total_volume > 100:
            score += 20
        else:
            score += 10

        # Level count score (0-30 points)
        total_levels = len(bids) + len(asks)
        if total_levels >= 1000:
            score += 30
        elif total_levels >= 500:
            score += 20
        else:
            score += 10

        # Imbalance score (0-20 points) - closer to neutral is better
        imbalance_abs = abs(imbalance['pct'])
        if imbalance_abs < 10:
            score += 20
        elif imbalance_abs < 30:
            score += 15
        elif imbalance_abs < 50:
            score += 10
        else:
            score += 5

        # Spread score (0-10 points)
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread_pct = ((best_ask - best_bid) / best_bid) * 100

            if spread_pct < 0.01:  # < 0.01%
                score += 10
            elif spread_pct < 0.05:
                score += 7
            elif spread_pct < 0.1:
                score += 5
            else:
                score += 2

        return min(100, score)

    def _generate_signals(
        self,
        current_price: float,
        whale_bids: List[OrderBookLevel],
        whale_asks: List[OrderBookLevel],
        imbalance: Dict,
        spoofing_detected: bool
    ) -> Dict:
        """
        Generate trading signals from order book analysis

        Returns:
            Dict with bias, entry zones, and stop suggestions
        """
        signals = {
            'bias': 'NEUTRAL',
            'confidence': 0,
            'reasoning': [],
            'entry_zones': [],
            'stop_suggestions': []
        }

        # Skip if spoofing detected
        if spoofing_detected:
            signals['reasoning'].append("Spoofing detected - waiting for genuine walls")
            return signals

        # BID PRESSURE (bullish bias)
        if imbalance['dominant_side'] == 'BID':
            signals['bias'] = 'LONG'
            signals['confidence'] = min(70, int(abs(imbalance['pct'])))
            signals['reasoning'].append(
                f"Strong bid pressure ({imbalance['pct']:.1f}% imbalance)"
            )

            # Entry zones: near whale bid walls
            if whale_bids:
                strongest_support = whale_bids[0]
                signals['entry_zones'].append({
                    'price': strongest_support.price,
                    'type': 'support',
                    'strength': strongest_support.strength
                })

                # Stop below support
                stop_distance = (current_price - strongest_support.price) * 1.2
                signals['stop_suggestions'].append({
                    'price': current_price - stop_distance,
                    'reason': f"Below support wall at {strongest_support.price:.2f}"
                })

        # ASK PRESSURE (bearish bias)
        elif imbalance['dominant_side'] == 'ASK':
            signals['bias'] = 'SHORT'
            signals['confidence'] = min(70, int(abs(imbalance['pct'])))
            signals['reasoning'].append(
                f"Strong ask pressure ({imbalance['pct']:.1f}% imbalance)"
            )

            # Entry zones: near whale ask walls
            if whale_asks:
                strongest_resistance = whale_asks[0]
                signals['entry_zones'].append({
                    'price': strongest_resistance.price,
                    'type': 'resistance',
                    'strength': strongest_resistance.strength
                })

                # Stop above resistance
                stop_distance = (strongest_resistance.price - current_price) * 1.2
                signals['stop_suggestions'].append({
                    'price': current_price + stop_distance,
                    'reason': f"Above resistance wall at {strongest_resistance.price:.2f}"
                })

        # NEUTRAL - range trading opportunity
        else:
            signals['bias'] = 'NEUTRAL'
            signals['confidence'] = 30
            signals['reasoning'].append("Balanced order book - range trading")

            # Use whale walls as range boundaries
            if whale_bids and whale_asks:
                signals['entry_zones'].append({
                    'price': whale_bids[0].price,
                    'type': 'support',
                    'strength': whale_bids[0].strength,
                    'action': 'BUY_SUPPORT'
                })
                signals['entry_zones'].append({
                    'price': whale_asks[0].price,
                    'type': 'resistance',
                    'strength': whale_asks[0].strength,
                    'action': 'SELL_RESISTANCE'
                })

        # WHALE WALL CONFLUENCE
        if whale_bids and whale_asks:
            nearest_support = min(whale_bids, key=lambda w: abs(w.price - current_price))
            nearest_resistance = min(whale_asks, key=lambda w: abs(w.price - current_price))

            support_dist = ((current_price - nearest_support.price) / current_price) * 100
            resistance_dist = ((nearest_resistance.price - current_price) / current_price) * 100

            # Price squeezed between walls
            if support_dist < 0.3 and resistance_dist < 0.3:
                signals['reasoning'].append(
                    f"Price squeezed between walls (±{min(support_dist, resistance_dist):.2f}%) - expect breakout"
                )
                signals['confidence'] += 10

        # Cap confidence
        signals['confidence'] = min(100, signals['confidence'])

        return signals

    async def get_support_resistance_levels(
        self,
        symbol: str,
        num_levels: int = 3
    ) -> Dict:
        """
        Get dynamic support/resistance levels from order book

        Args:
            symbol: Trading pair
            num_levels: Number of levels to return per side

        Returns:
            Support and resistance price levels
        """
        try:
            analysis = await self.analyze_order_book(symbol)

            if not analysis:
                return {'support': [], 'resistance': []}

            support = analysis.get('whale_bids', [])[:num_levels]
            resistance = analysis.get('whale_asks', [])[:num_levels]

            return {
                'symbol': symbol,
                'current_price': analysis.get('current_price'),
                'support': support,
                'resistance': resistance,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting support/resistance for {symbol}: {e}")
            return {'support': [], 'resistance': []}


# Singleton instance
orderbook_analyzer = OrderBookAnalyzer()
