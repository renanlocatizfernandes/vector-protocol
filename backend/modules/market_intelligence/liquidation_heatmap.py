"""
Liquidation Heatmap Calculator
Estimates liquidation zones based on open interest, leverage, and positioning
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("liquidation_heatmap")


class LiquidationZone:
    """Represents a price zone with high liquidation risk"""

    def __init__(
        self,
        price: float,
        liquidation_value: float,
        side: str,
        leverage: int,
        density: int
    ):
        self.price = price
        self.liquidation_value = liquidation_value  # USD value
        self.side = side  # 'LONG' or 'SHORT'
        self.leverage = leverage
        self.density = density  # 0-100 score
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'price': self.price,
            'liquidation_value_usd': self.liquidation_value,
            'side': self.side,
            'leverage': f"{self.leverage}x",
            'density': self.density,
            'timestamp': self.timestamp.isoformat()
        }


class LiquidationHeatmap:
    """
    Calculates liquidation heatmap to identify:
    - Liquidation clusters (zones with many liquidations)
    - Cascade risk (where liquidations trigger more liquidations)
    - Safe entry zones (far from liquidation clusters)
    - Target zones (near liquidations for momentum plays)
    """

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 60  # 1 minute
        self.common_leverages = [5, 10, 20, 25, 50, 75, 100, 125]  # Binance futures leverage levels

    async def calculate_heatmap(self, symbol: str) -> Dict:
        """
        Calculate liquidation heatmap for symbol

        Returns:
            Heatmap with liquidation zones and trading signals
        """
        cache_key = f"{symbol}_liq_heatmap"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_ttl:
                return cached

        try:
            # Get market data
            mark_price_data = await binance_client.futures_mark_price(symbol=symbol)
            current_price = float(mark_price_data.get('markPrice', 0))

            # Get open interest
            oi = await binance_client.futures_open_interest(symbol=symbol)
            open_interest = float(oi.get('openInterest', 0))
            oi_value = open_interest * current_price

            # Get long/short ratios
            account_ratio = await binance_client.futures_global_long_short_ratio(
                symbol=symbol,
                period='5m',
                limit=1
            )

            if account_ratio and len(account_ratio) > 0:
                long_short_ratio = float(account_ratio[0].get('longShortRatio', 1.0))
            else:
                long_short_ratio = 1.0

            # Estimate long/short distribution
            total_positions = oi_value
            long_pct = long_short_ratio / (long_short_ratio + 1)
            short_pct = 1 - long_pct

            long_value = total_positions * long_pct
            short_value = total_positions * short_pct

            # Calculate liquidation zones
            long_liq_zones = self._calculate_liquidation_zones(
                current_price,
                long_value,
                'LONG',
                self.common_leverages
            )

            short_liq_zones = self._calculate_liquidation_zones(
                current_price,
                short_value,
                'SHORT',
                self.common_leverages
            )

            # Merge and sort all zones by price
            all_zones = long_liq_zones + short_liq_zones
            all_zones.sort(key=lambda z: z.price)

            # Identify high-density clusters
            clusters = self._identify_clusters(all_zones, current_price)

            # Calculate cascade risk
            cascade_risk = self._calculate_cascade_risk(clusters, current_price)

            # Generate signals
            signals = self._generate_signals(
                current_price,
                long_liq_zones,
                short_liq_zones,
                clusters,
                cascade_risk
            )

            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'current_price': current_price,

                # Market data
                'open_interest': open_interest,
                'oi_value_usd': oi_value,
                'long_short_ratio': long_short_ratio,
                'long_pct': long_pct * 100,
                'short_pct': short_pct * 100,

                # Liquidation zones
                'long_liquidation_zones': [z.to_dict() for z in long_liq_zones],
                'short_liquidation_zones': [z.to_dict() for z in short_liq_zones],

                # Clusters
                'high_density_clusters': clusters,
                'cascade_risk_score': cascade_risk,

                # Signals
                **signals
            }

            # Cache
            self.cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error calculating liquidation heatmap for {symbol}: {e}")
            return {}

    def _calculate_liquidation_zones(
        self,
        current_price: float,
        position_value: float,
        side: str,
        leverages: List[int]
    ) -> List[LiquidationZone]:
        """
        Calculate liquidation price zones for different leverage levels

        Liquidation formula (simplified):
        - LONG: liq_price = entry_price * (1 - 1/leverage - maintenance_margin_rate)
        - SHORT: liq_price = entry_price * (1 + 1/leverage + maintenance_margin_rate)

        Args:
            current_price: Current market price (assumed entry)
            position_value: Total USD value of positions
            side: 'LONG' or 'SHORT'
            leverages: List of leverage levels to calculate

        Returns:
            List of LiquidationZone objects
        """
        zones = []
        maintenance_margin_rate = 0.004  # 0.4% for most pairs (varies by tier)

        for leverage in leverages:
            # Calculate liquidation price
            if side == 'LONG':
                # Long liquidation is below entry
                liq_price = current_price * (1 - (1 / leverage) - maintenance_margin_rate)
            else:
                # Short liquidation is above entry
                liq_price = current_price * (1 + (1 / leverage) + maintenance_margin_rate)

            # Estimate value at this leverage (higher leverage = more popular)
            # Distribution: more positions at 10x, 20x than 100x
            leverage_popularity = {
                5: 0.05,
                10: 0.20,
                20: 0.30,
                25: 0.15,
                50: 0.15,
                75: 0.08,
                100: 0.05,
                125: 0.02
            }

            popularity = leverage_popularity.get(leverage, 0.05)
            liq_value = position_value * popularity

            # Calculate density score (0-100)
            # Higher leverage = higher density (more traders)
            density = int(min(100, popularity * 500))

            zone = LiquidationZone(
                price=liq_price,
                liquidation_value=liq_value,
                side=side,
                leverage=leverage,
                density=density
            )

            zones.append(zone)

        return zones

    def _identify_clusters(
        self,
        zones: List[LiquidationZone],
        current_price: float,
        cluster_threshold_pct: float = 0.5
    ) -> List[Dict]:
        """
        Identify high-density liquidation clusters

        Clusters are areas where multiple liquidation zones overlap

        Args:
            zones: All liquidation zones
            current_price: Current price
            cluster_threshold_pct: Price range to consider as cluster (%)

        Returns:
            List of cluster dictionaries
        """
        if not zones:
            return []

        clusters = []

        # Group zones within threshold range
        sorted_zones = sorted(zones, key=lambda z: z.price)

        i = 0
        while i < len(sorted_zones):
            cluster_zones = [sorted_zones[i]]
            cluster_price = sorted_zones[i].price

            # Find nearby zones
            j = i + 1
            while j < len(sorted_zones):
                zone = sorted_zones[j]
                distance_pct = abs(zone.price - cluster_price) / cluster_price * 100

                if distance_pct <= cluster_threshold_pct:
                    cluster_zones.append(zone)
                    j += 1
                else:
                    break

            # If cluster has multiple zones, add it
            if len(cluster_zones) >= 2:
                total_value = sum(z.liquidation_value for z in cluster_zones)
                avg_price = sum(z.price for z in cluster_zones) / len(cluster_zones)
                total_density = sum(z.density for z in cluster_zones)

                # Determine dominant side
                long_value = sum(z.liquidation_value for z in cluster_zones if z.side == 'LONG')
                short_value = sum(z.liquidation_value for z in cluster_zones if z.side == 'SHORT')

                dominant_side = 'LONG' if long_value > short_value else 'SHORT'

                # Distance from current price
                distance_pct = abs(avg_price - current_price) / current_price * 100

                clusters.append({
                    'price': avg_price,
                    'total_liquidation_value': total_value,
                    'num_zones': len(cluster_zones),
                    'density_score': min(100, total_density),
                    'dominant_side': dominant_side,
                    'distance_from_current_pct': distance_pct,
                    'direction': 'below' if avg_price < current_price else 'above'
                })

            i = j if j > i else i + 1

        # Sort by density
        clusters.sort(key=lambda c: c['density_score'], reverse=True)

        return clusters[:10]  # Top 10 clusters

    def _calculate_cascade_risk(
        self,
        clusters: List[Dict],
        current_price: float
    ) -> int:
        """
        Calculate cascade liquidation risk (0-100)

        High risk when:
        - Multiple large clusters close to current price
        - Clusters on both sides (whipsaw risk)
        - High total liquidation value

        Returns:
            Risk score 0-100
        """
        if not clusters:
            return 0

        risk = 0

        # Nearby clusters (within 2%)
        nearby_clusters = [c for c in clusters if c['distance_from_current_pct'] < 2.0]

        if nearby_clusters:
            # Proximity risk (0-40 points)
            min_distance = min(c['distance_from_current_pct'] for c in nearby_clusters)
            proximity_risk = max(0, 40 - int(min_distance * 20))
            risk += proximity_risk

            # Density risk (0-30 points)
            max_density = max(c['density_score'] for c in nearby_clusters)
            density_risk = int(max_density * 0.3)
            risk += density_risk

            # Value risk (0-20 points)
            total_value = sum(c['total_liquidation_value'] for c in nearby_clusters)
            if total_value > 100_000_000:  # $100M+
                risk += 20
            elif total_value > 50_000_000:
                risk += 15
            elif total_value > 10_000_000:
                risk += 10
            else:
                risk += 5

            # Whipsaw risk (0-10 points) - clusters on both sides
            above = any(c['direction'] == 'above' for c in nearby_clusters)
            below = any(c['direction'] == 'below' for c in nearby_clusters)
            if above and below:
                risk += 10

        return min(100, risk)

    def _generate_signals(
        self,
        current_price: float,
        long_liq_zones: List[LiquidationZone],
        short_liq_zones: List[LiquidationZone],
        clusters: List[Dict],
        cascade_risk: int
    ) -> Dict:
        """
        Generate trading signals from liquidation heatmap

        Strategy:
        - Avoid entering near high-density clusters (liquidation risk)
        - Target zones just past clusters (liquidation hunt)
        - Use clusters as invalidation levels

        Returns:
            Dict with signals and recommendations
        """
        signals = {
            'bias': 'NEUTRAL',
            'confidence': 0,
            'reasoning': [],
            'safe_entry_zones': [],
            'target_zones': [],  # For liquidation hunts
            'avoid_zones': []
        }

        # HIGH CASCADE RISK - avoid trading
        if cascade_risk > 70:
            signals['reasoning'].append(
                f"High cascade risk ({cascade_risk}/100) - avoid trading near price"
            )
            signals['confidence'] = 0
            return signals

        # Find nearest clusters above/below
        nearby_clusters = [c for c in clusters if c['distance_from_current_pct'] < 5.0]

        if not nearby_clusters:
            signals['reasoning'].append("No major liquidation clusters nearby - safe to trade")
            signals['confidence'] = 40
            return signals

        # Separate by direction
        clusters_below = [c for c in nearby_clusters if c['direction'] == 'below']
        clusters_above = [c for c in nearby_clusters if c['direction'] == 'above']

        # LONG LIQUIDATION CLUSTER BELOW - bearish signal
        if clusters_below:
            strongest_below = max(clusters_below, key=lambda c: c['density_score'])

            if strongest_below['dominant_side'] == 'LONG':
                signals['bias'] = 'SHORT'
                signals['confidence'] = min(70, strongest_below['density_score'])
                signals['reasoning'].append(
                    f"Large long liquidation cluster at {strongest_below['price']:.2f} "
                    f"(-{strongest_below['distance_from_current_pct']:.1f}%) - price may hunt stops"
                )

                # Target zone just past cluster
                signals['target_zones'].append({
                    'price': strongest_below['price'] * 0.995,  # 0.5% below
                    'reason': 'Liquidation hunt target',
                    'confidence': strongest_below['density_score']
                })

                # Avoid zone at cluster
                signals['avoid_zones'].append({
                    'price': strongest_below['price'],
                    'reason': 'High long liquidation density',
                    'risk': 'Stop loss may get hit by liquidation cascade'
                })

        # SHORT LIQUIDATION CLUSTER ABOVE - bullish signal
        if clusters_above:
            strongest_above = max(clusters_above, key=lambda c: c['density_score'])

            if strongest_above['dominant_side'] == 'SHORT':
                # Override if stronger than below signal
                if strongest_above['density_score'] > signals.get('confidence', 0):
                    signals['bias'] = 'LONG'
                    signals['confidence'] = min(70, strongest_above['density_score'])
                    signals['reasoning'] = [
                        f"Large short liquidation cluster at {strongest_above['price']:.2f} "
                        f"(+{strongest_above['distance_from_current_pct']:.1f}%) - price may hunt stops"
                    ]

                    # Target zone just past cluster
                    signals['target_zones'].append({
                        'price': strongest_above['price'] * 1.005,  # 0.5% above
                        'reason': 'Liquidation hunt target',
                        'confidence': strongest_above['density_score']
                    })

                    # Avoid zone at cluster
                    signals['avoid_zones'].append({
                        'price': strongest_above['price'],
                        'reason': 'High short liquidation density',
                        'risk': 'Stop loss may get hit by liquidation cascade'
                    })

        # SAFE ENTRY ZONES - far from clusters
        if clusters_below and clusters_above:
            # Mid-range between clusters is safest
            lowest_above = min(c['price'] for c in clusters_above)
            highest_below = max(c['price'] for c in clusters_below)

            mid_price = (lowest_above + highest_below) / 2

            if abs(mid_price - current_price) / current_price * 100 < 1.0:
                signals['safe_entry_zones'].append({
                    'price': mid_price,
                    'reason': 'Between liquidation clusters',
                    'range': f"{highest_below:.2f} - {lowest_above:.2f}"
                })

        return signals

    async def get_nearest_liquidation_levels(
        self,
        symbol: str,
        num_levels: int = 5
    ) -> Dict:
        """
        Get nearest liquidation levels above/below current price

        Args:
            symbol: Trading pair
            num_levels: Number of levels per side

        Returns:
            Nearest liquidation zones
        """
        try:
            heatmap = await self.calculate_heatmap(symbol)

            if not heatmap:
                return {'above': [], 'below': []}

            current_price = heatmap['current_price']

            # Get all zones
            long_zones = heatmap.get('long_liquidation_zones', [])
            short_zones = heatmap.get('short_liquidation_zones', [])

            all_zones = long_zones + short_zones

            # Separate by direction
            above = [z for z in all_zones if z['price'] > current_price]
            below = [z for z in all_zones if z['price'] < current_price]

            # Sort by distance
            above.sort(key=lambda z: z['price'])
            below.sort(key=lambda z: z['price'], reverse=True)

            return {
                'symbol': symbol,
                'current_price': current_price,
                'above': above[:num_levels],
                'below': below[:num_levels],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting liquidation levels for {symbol}: {e}")
            return {'above': [], 'below': []}


# Singleton instance
liquidation_heatmap = LiquidationHeatmap()
