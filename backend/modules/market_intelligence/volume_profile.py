"""
Volume Profile & Point of Control (POC) Analysis
Analyzes volume distribution at different price levels to identify key support/resistance zones
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("volume_profile")


class VolumeNode:
    """Represents a volume node at a price level"""

    def __init__(self, price: float, volume: float, volume_pct: float):
        self.price = price
        self.volume = volume
        self.volume_pct = volume_pct  # Percentage of total volume
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'price': self.price,
            'volume': self.volume,
            'volume_pct': round(self.volume_pct, 2),
            'timestamp': self.timestamp.isoformat()
        }


class VolumeProfile:
    """
    Volume Profile Analyzer

    Identifies:
    - Point of Control (POC): Price level with highest volume
    - Value Area: Range containing 70% of volume
    - High Volume Nodes (HVN): Strong support/resistance
    - Low Volume Nodes (LVN): Areas price moves through quickly
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # 1 minute
        self.num_price_levels = 50  # Divide price range into 50 levels

    async def analyze_volume_profile(
        self,
        symbol: str,
        interval: str = '5m',
        lookback: int = 200
    ) -> Dict:
        """
        Analyze volume profile for symbol

        Args:
            symbol: Trading pair
            interval: Candle interval
            lookback: Number of candles to analyze

        Returns:
            Volume profile analysis
        """
        cache_key = f"{symbol}_vp_{interval}_{lookback}"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Get candle data
            klines = await binance_client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=lookback
            )

            if not klines or len(klines) < 20:
                return {}

            # Extract data
            highs = np.array([float(k[2]) for k in klines])
            lows = np.array([float(k[3]) for k in klines])
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])

            current_price = closes[-1]
            price_min = np.min(lows)
            price_max = np.max(highs)

            # Build volume profile
            volume_profile = self._build_volume_profile(
                highs, lows, closes, volumes,
                price_min, price_max,
                self.num_price_levels
            )

            # Find POC (Point of Control)
            poc = max(volume_profile, key=lambda x: x.volume)

            # Calculate Value Area (70% of volume)
            value_area_high, value_area_low = self._calculate_value_area(
                volume_profile, 0.70
            )

            # Identify High/Low Volume Nodes
            hvn_nodes, lvn_nodes = self._identify_volume_nodes(volume_profile)

            # Generate trading signals
            signals = self._generate_signals(
                current_price,
                poc,
                value_area_high,
                value_area_low,
                hvn_nodes,
                lvn_nodes
            )

            result = {
                'symbol': symbol,
                'interval': interval,
                'lookback': lookback,
                'timestamp': datetime.now(),
                'current_price': current_price,

                # POC
                'poc': poc.to_dict(),
                'poc_distance_pct': abs(current_price - poc.price) / current_price * 100,

                # Value Area
                'value_area_high': value_area_high.to_dict() if value_area_high else None,
                'value_area_low': value_area_low.to_dict() if value_area_low else None,
                'value_area_range_pct': (
                    (value_area_high.price - value_area_low.price) / current_price * 100
                    if value_area_high and value_area_low else 0
                ),

                # Volume Nodes
                'high_volume_nodes': [n.to_dict() for n in hvn_nodes[:10]],
                'low_volume_nodes': [n.to_dict() for n in lvn_nodes[:10]],

                # Full profile
                'volume_profile': [n.to_dict() for n in volume_profile],

                # Signals
                **signals
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error analyzing volume profile for {symbol}: {e}")
            return {}

    def _build_volume_profile(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        price_min: float,
        price_max: float,
        num_levels: int
    ) -> List[VolumeNode]:
        """
        Build volume profile by distributing volume across price levels

        Args:
            highs, lows, closes, volumes: Candle data
            price_min, price_max: Price range
            num_levels: Number of price levels to divide range into

        Returns:
            List of VolumeNode objects
        """
        # Create price levels
        price_step = (price_max - price_min) / num_levels
        price_levels = np.linspace(price_min, price_max, num_levels)

        # Initialize volume buckets
        volume_at_level = defaultdict(float)

        # Distribute volume
        for i in range(len(highs)):
            high = highs[i]
            low = lows[i]
            volume = volumes[i]

            # Find which price levels this candle touched
            touched_levels = []
            for level in price_levels:
                if low <= level <= high:
                    touched_levels.append(level)

            # Distribute volume equally across touched levels
            if touched_levels:
                volume_per_level = volume / len(touched_levels)
                for level in touched_levels:
                    volume_at_level[level] += volume_per_level

        # Calculate total volume
        total_volume = sum(volume_at_level.values())

        # Create VolumeNode objects
        volume_profile = []
        for level in price_levels:
            vol = volume_at_level.get(level, 0)
            vol_pct = (vol / total_volume * 100) if total_volume > 0 else 0

            node = VolumeNode(
                price=level,
                volume=vol,
                volume_pct=vol_pct
            )
            volume_profile.append(node)

        # Sort by price
        volume_profile.sort(key=lambda x: x.price)

        return volume_profile

    def _calculate_value_area(
        self,
        volume_profile: List[VolumeNode],
        target_pct: float = 0.70
    ) -> Tuple[Optional[VolumeNode], Optional[VolumeNode]]:
        """
        Calculate Value Area (price range containing target % of volume)

        Starts from POC and expands outward

        Args:
            volume_profile: List of VolumeNode objects
            target_pct: Percentage of volume to include (default 70%)

        Returns:
            Tuple of (value_area_high, value_area_low)
        """
        if not volume_profile:
            return None, None

        # Find POC index
        poc_idx = max(range(len(volume_profile)), key=lambda i: volume_profile[i].volume)

        # Total volume to capture
        total_volume = sum(n.volume for n in volume_profile)
        target_volume = total_volume * target_pct

        # Expand from POC
        included_volume = volume_profile[poc_idx].volume
        low_idx = poc_idx
        high_idx = poc_idx

        while included_volume < target_volume:
            # Check volumes at boundaries
            vol_below = volume_profile[low_idx - 1].volume if low_idx > 0 else 0
            vol_above = volume_profile[high_idx + 1].volume if high_idx < len(volume_profile) - 1 else 0

            # Expand to side with more volume
            if vol_above >= vol_below and high_idx < len(volume_profile) - 1:
                high_idx += 1
                included_volume += volume_profile[high_idx].volume
            elif low_idx > 0:
                low_idx -= 1
                included_volume += volume_profile[low_idx].volume
            else:
                break

        return volume_profile[high_idx], volume_profile[low_idx]

    def _identify_volume_nodes(
        self,
        volume_profile: List[VolumeNode]
    ) -> Tuple[List[VolumeNode], List[VolumeNode]]:
        """
        Identify High Volume Nodes (HVN) and Low Volume Nodes (LVN)

        HVN: Volume > 150% of average (strong support/resistance)
        LVN: Volume < 50% of average (price moves quickly)

        Returns:
            Tuple of (hvn_nodes, lvn_nodes)
        """
        if not volume_profile:
            return [], []

        # Calculate average volume
        avg_volume = sum(n.volume for n in volume_profile) / len(volume_profile)

        hvn_nodes = []
        lvn_nodes = []

        for node in volume_profile:
            if node.volume > avg_volume * 1.5:
                hvn_nodes.append(node)
            elif node.volume < avg_volume * 0.5 and node.volume > 0:
                lvn_nodes.append(node)

        # Sort HVN by volume (descending)
        hvn_nodes.sort(key=lambda x: x.volume, reverse=True)

        # Sort LVN by volume (ascending)
        lvn_nodes.sort(key=lambda x: x.volume)

        return hvn_nodes, lvn_nodes

    def _generate_signals(
        self,
        current_price: float,
        poc: VolumeNode,
        vah: Optional[VolumeNode],
        val: Optional[VolumeNode],
        hvn_nodes: List[VolumeNode],
        lvn_nodes: List[VolumeNode]
    ) -> Dict:
        """
        Generate trading signals from volume profile

        Strategy:
        - Price near POC: Wait for breakout
        - Price above VAH: Bullish, look for pullback to VAH
        - Price below VAL: Bearish, look for bounce to VAL
        - HVN nearby: Strong support/resistance
        - LVN nearby: Expect quick moves through

        Returns:
            Dict with signals and recommendations
        """
        signals = {
            'bias': 'NEUTRAL',
            'confidence': 0,
            'reasoning': [],
            'key_levels': [],
            'position_relative_to_value_area': 'UNKNOWN'
        }

        if not vah or not val:
            return signals

        # Determine position relative to value area
        if current_price > vah.price:
            signals['position_relative_to_value_area'] = 'ABOVE_VALUE_AREA'
            signals['bias'] = 'BULLISH'
            signals['confidence'] = 60
            signals['reasoning'].append(
                f"Price above Value Area High ({vah.price:.2f}) - bullish"
            )

            # Look for HVN support above VAH
            support_hvn = [n for n in hvn_nodes if val.price < n.price < current_price]
            if support_hvn:
                nearest = max(support_hvn, key=lambda x: x.price)
                signals['key_levels'].append({
                    'price': nearest.price,
                    'type': 'support',
                    'reason': 'High Volume Node',
                    'volume_pct': nearest.volume_pct
                })
                signals['confidence'] += 10

        elif current_price < val.price:
            signals['position_relative_to_value_area'] = 'BELOW_VALUE_AREA'
            signals['bias'] = 'BEARISH'
            signals['confidence'] = 60
            signals['reasoning'].append(
                f"Price below Value Area Low ({val.price:.2f}) - bearish"
            )

            # Look for HVN resistance below VAL
            resistance_hvn = [n for n in hvn_nodes if current_price < n.price < vah.price]
            if resistance_hvn:
                nearest = min(resistance_hvn, key=lambda x: x.price)
                signals['key_levels'].append({
                    'price': nearest.price,
                    'type': 'resistance',
                    'reason': 'High Volume Node',
                    'volume_pct': nearest.volume_pct
                })
                signals['confidence'] += 10

        else:
            signals['position_relative_to_value_area'] = 'INSIDE_VALUE_AREA'
            signals['bias'] = 'NEUTRAL'
            signals['confidence'] = 40
            signals['reasoning'].append(
                f"Price inside Value Area ({val.price:.2f} - {vah.price:.2f}) - range-bound"
            )

        # POC proximity
        poc_distance_pct = abs(current_price - poc.price) / current_price * 100

        if poc_distance_pct < 0.5:
            signals['reasoning'].append(
                f"Price near POC ({poc.price:.2f}) - expect consolidation or breakout"
            )
            signals['key_levels'].append({
                'price': poc.price,
                'type': 'pivot',
                'reason': 'Point of Control (highest volume)',
                'volume_pct': poc.volume_pct
            })

        elif current_price > poc.price:
            signals['reasoning'].append(
                f"Price above POC ({poc.price:.2f}) - bullish momentum"
            )
            signals['confidence'] += 5
        else:
            signals['reasoning'].append(
                f"Price below POC ({poc.price:.2f}) - bearish momentum"
            )
            signals['confidence'] += 5

        # Check for LVN (gap) nearby
        nearby_lvn = [n for n in lvn_nodes if abs(n.price - current_price) / current_price * 100 < 1.0]

        if nearby_lvn:
            signals['reasoning'].append(
                "Price near Low Volume Node - expect rapid movement"
            )

            for lvn in nearby_lvn[:3]:
                signals['key_levels'].append({
                    'price': lvn.price,
                    'type': 'gap',
                    'reason': 'Low Volume Node - expect quick move through',
                    'volume_pct': lvn.volume_pct
                })

        # Add VAH/VAL as key levels
        signals['key_levels'].insert(0, {
            'price': vah.price,
            'type': 'resistance' if current_price < vah.price else 'support',
            'reason': 'Value Area High',
            'volume_pct': vah.volume_pct
        })

        signals['key_levels'].insert(0, {
            'price': val.price,
            'type': 'support' if current_price > val.price else 'resistance',
            'reason': 'Value Area Low',
            'volume_pct': val.volume_pct
        })

        # Cap confidence
        signals['confidence'] = min(100, signals['confidence'])

        return signals

    async def get_nearest_volume_levels(
        self,
        symbol: str,
        interval: str = '5m',
        lookback: int = 200,
        num_levels: int = 5
    ) -> Dict:
        """
        Get nearest significant volume levels above/below current price

        Args:
            symbol: Trading pair
            interval: Candle interval
            lookback: Number of candles
            num_levels: Number of levels to return per side

        Returns:
            Nearest volume levels
        """
        try:
            analysis = await self.analyze_volume_profile(symbol, interval, lookback)

            if not analysis:
                return {'above': [], 'below': []}

            current_price = analysis['current_price']
            hvn_nodes_data = analysis.get('high_volume_nodes', [])

            # Separate by direction
            above = [n for n in hvn_nodes_data if n['price'] > current_price]
            below = [n for n in hvn_nodes_data if n['price'] < current_price]

            # Sort by distance
            above.sort(key=lambda n: n['price'])
            below.sort(key=lambda n: n['price'], reverse=True)

            return {
                'symbol': symbol,
                'current_price': current_price,
                'above': above[:num_levels],
                'below': below[:num_levels],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting volume levels for {symbol}: {e}")
            return {'above': [], 'below': []}

    async def compare_current_to_historical_profile(
        self,
        symbol: str,
        current_interval: str = '5m',
        historical_interval: str = '1h',
        current_lookback: int = 100,
        historical_lookback: int = 200
    ) -> Dict:
        """
        Compare current session volume profile to historical profile

        Useful for identifying:
        - Acceptance/rejection of price levels
        - Migration of value area
        - Changes in POC

        Returns:
            Comparison analysis
        """
        try:
            # Get both profiles
            current = await self.analyze_volume_profile(
                symbol, current_interval, current_lookback
            )
            historical = await self.analyze_volume_profile(
                symbol, historical_interval, historical_lookback
            )

            if not current or not historical:
                return {}

            current_poc = current.get('poc', {}).get('price', 0)
            historical_poc = historical.get('poc', {}).get('price', 0)

            poc_migration_pct = (
                (current_poc - historical_poc) / historical_poc * 100
                if historical_poc > 0 else 0
            )

            # Value area comparison
            current_vah = current.get('value_area_high', {})
            current_val = current.get('value_area_low', {})
            historical_vah = historical.get('value_area_high', {})
            historical_val = historical.get('value_area_low', {})

            # Determine trend
            if poc_migration_pct > 2:
                trend = 'BULLISH'
                interpretation = "POC migrating higher - buyers in control"
            elif poc_migration_pct < -2:
                trend = 'BEARISH'
                interpretation = "POC migrating lower - sellers in control"
            else:
                trend = 'NEUTRAL'
                interpretation = "POC stable - balanced market"

            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),

                # POC comparison
                'current_poc': current_poc,
                'historical_poc': historical_poc,
                'poc_migration_pct': round(poc_migration_pct, 2),

                # Value area comparison
                'current_value_area': {
                    'high': current_vah.get('price') if current_vah else None,
                    'low': current_val.get('price') if current_val else None
                },
                'historical_value_area': {
                    'high': historical_vah.get('price') if historical_vah else None,
                    'low': historical_val.get('price') if historical_val else None
                },

                # Trend
                'trend': trend,
                'interpretation': interpretation,
                'confidence': min(100, int(abs(poc_migration_pct) * 10))
            }

        except Exception as e:
            logger.error(f"Error comparing volume profiles: {e}")
            return {}


# Singleton instance
volume_profile = VolumeProfile()
