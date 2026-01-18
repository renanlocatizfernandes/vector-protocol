"""
Smart Order Routing (SOR)
Advanced order execution with TWAP, Iceberg, and adaptive algorithms
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from enum import Enum

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("smart_order_routing")


class ExecutionAlgorithm(str, Enum):
    """Order execution algorithms"""
    MARKET = "market"  # Immediate execution at market price
    LIMIT = "limit"  # Simple limit order
    TWAP = "twap"  # Time-Weighted Average Price
    ICEBERG = "iceberg"  # Hidden size orders
    ADAPTIVE = "adaptive"  # ML-driven adaptive execution
    VWAP = "vwap"  # Volume-Weighted Average Price


class OrderSlice:
    """Represents a slice of a parent order"""

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float],
        slice_num: int,
        total_slices: int
    ):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.slice_num = slice_num
        self.total_slices = total_slices
        self.order_id = None
        self.filled_qty = 0
        self.avg_price = 0
        self.status = 'PENDING'
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'slice_num': self.slice_num,
            'total_slices': self.total_slices,
            'quantity': self.quantity,
            'price': self.price,
            'filled_qty': self.filled_qty,
            'avg_price': self.avg_price,
            'status': self.status,
            'order_id': self.order_id
        }


class SmartOrderRouter:
    """
    Smart Order Routing with advanced execution algorithms

    Algorithms:
    - TWAP: Splits order evenly over time (minimizes timing risk)
    - Iceberg: Shows small visible size, hides bulk (minimizes market impact)
    - Adaptive: Adjusts based on order book depth and volatility
    - VWAP: Matches volume profile (minimizes price impact)
    """

    def __init__(self):
        self.active_parent_orders = {}  # Track multi-slice orders

    async def execute_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        duration_seconds: int = 300,
        num_slices: int = 10,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Execute Time-Weighted Average Price strategy

        Splits order into equal slices over time

        Args:
            symbol: Trading pair
            side: BUY or SELL
            total_quantity: Total quantity to trade
            duration_seconds: Time to spread execution (default 5 min)
            num_slices: Number of order slices
            limit_price: Optional limit price (None = market orders)

        Returns:
            Execution report
        """
        try:
            logger.info(
                f"TWAP: {side} {total_quantity} {symbol} over {duration_seconds}s in {num_slices} slices"
            )

            # Calculate slice parameters
            slice_qty = total_quantity / num_slices
            interval_seconds = duration_seconds / num_slices

            # Create slices
            slices = []
            for i in range(num_slices):
                slice_obj = OrderSlice(
                    symbol=symbol,
                    side=side,
                    quantity=slice_qty,
                    price=limit_price,
                    slice_num=i + 1,
                    total_slices=num_slices
                )
                slices.append(slice_obj)

            # Execute slices with time delay
            execution_results = []

            for i, slice_obj in enumerate(slices):
                try:
                    # Place order
                    if limit_price:
                        result = await self._place_limit_order(
                            symbol, side, slice_obj.quantity, limit_price
                        )
                    else:
                        result = await self._place_market_order(
                            symbol, side, slice_obj.quantity
                        )

                    if result:
                        slice_obj.order_id = result.get('orderId')
                        slice_obj.filled_qty = float(result.get('executedQty', 0))
                        slice_obj.avg_price = float(result.get('avgPrice', 0))
                        slice_obj.status = result.get('status', 'UNKNOWN')

                    execution_results.append(slice_obj.to_dict())

                    # Wait before next slice (except last one)
                    if i < num_slices - 1:
                        await asyncio.sleep(interval_seconds)

                except Exception as e:
                    logger.error(f"Error executing TWAP slice {i+1}: {e}")
                    slice_obj.status = 'FAILED'
                    execution_results.append(slice_obj.to_dict())

            # Calculate overall execution metrics
            total_filled = sum(s['filled_qty'] for s in execution_results)
            total_value = sum(s['filled_qty'] * s['avg_price'] for s in execution_results)
            avg_execution_price = total_value / total_filled if total_filled > 0 else 0

            return {
                'algorithm': 'TWAP',
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'total_filled': total_filled,
                'fill_rate_pct': (total_filled / total_quantity * 100) if total_quantity > 0 else 0,
                'avg_execution_price': avg_execution_price,
                'num_slices': num_slices,
                'slices': execution_results,
                'duration_seconds': duration_seconds,
                'completed_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error executing TWAP: {e}")
            return {'error': str(e)}

    async def execute_iceberg(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        visible_quantity: float,
        limit_price: float,
        timeout_seconds: int = 300
    ) -> Dict:
        """
        Execute Iceberg order strategy

        Shows only small visible quantity, replenishes as filled

        Args:
            symbol: Trading pair
            side: BUY or SELL
            total_quantity: Total quantity to trade
            visible_quantity: Quantity visible in order book
            limit_price: Limit price
            timeout_seconds: Max time to complete

        Returns:
            Execution report
        """
        try:
            logger.info(
                f"Iceberg: {side} {total_quantity} {symbol} (visible: {visible_quantity}) @ {limit_price}"
            )

            remaining_qty = total_quantity
            filled_qty = 0
            execution_slices = []
            slice_num = 0

            start_time = datetime.now()

            while remaining_qty > 0:
                # Check timeout
                elapsed = (datetime.now() - start_time).seconds
                if elapsed > timeout_seconds:
                    logger.warning(f"Iceberg timeout after {elapsed}s")
                    break

                # Determine slice size
                current_slice_qty = min(visible_quantity, remaining_qty)

                slice_num += 1

                try:
                    # Place limit order for visible quantity
                    result = await self._place_limit_order(
                        symbol, side, current_slice_qty, limit_price
                    )

                    if result:
                        order_id = result.get('orderId')
                        slice_filled = float(result.get('executedQty', 0))
                        slice_avg_price = float(result.get('avgPrice', 0))
                        status = result.get('status')

                        execution_slices.append({
                            'slice_num': slice_num,
                            'quantity': current_slice_qty,
                            'filled_qty': slice_filled,
                            'avg_price': slice_avg_price,
                            'status': status,
                            'order_id': order_id
                        })

                        filled_qty += slice_filled
                        remaining_qty -= slice_filled

                        # If not fully filled, wait and check
                        if status != 'FILLED':
                            await asyncio.sleep(10)  # Wait 10s before next slice

                            # Check if order got filled during wait
                            order_status = await binance_client.futures_get_order(
                                symbol=symbol,
                                orderId=order_id
                            )

                            updated_filled = float(order_status.get('executedQty', 0))
                            if updated_filled > slice_filled:
                                additional_filled = updated_filled - slice_filled
                                filled_qty += additional_filled
                                remaining_qty -= additional_filled

                            # Cancel if still open
                            if order_status.get('status') not in ['FILLED', 'CANCELED']:
                                await binance_client.futures_cancel_order(
                                    symbol=symbol,
                                    orderId=order_id
                                )

                except Exception as e:
                    logger.error(f"Error executing iceberg slice {slice_num}: {e}")
                    break

            # Calculate metrics
            total_value = sum(s['filled_qty'] * s['avg_price'] for s in execution_slices)
            avg_price = total_value / filled_qty if filled_qty > 0 else 0

            return {
                'algorithm': 'ICEBERG',
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'visible_quantity': visible_quantity,
                'total_filled': filled_qty,
                'fill_rate_pct': (filled_qty / total_quantity * 100) if total_quantity > 0 else 0,
                'avg_execution_price': avg_price,
                'limit_price': limit_price,
                'num_slices': len(execution_slices),
                'slices': execution_slices,
                'duration_seconds': (datetime.now() - start_time).seconds,
                'completed_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error executing Iceberg: {e}")
            return {'error': str(e)}

    async def execute_adaptive(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        urgency: str = 'NORMAL',  # LOW, NORMAL, HIGH
        max_duration_seconds: int = 300
    ) -> Dict:
        """
        Execute Adaptive algorithm

        Adjusts execution based on:
        - Order book depth
        - Volatility
        - Spread
        - Urgency level

        Args:
            symbol: Trading pair
            side: BUY or SELL
            total_quantity: Total quantity
            urgency: Execution urgency level
            max_duration_seconds: Max execution time

        Returns:
            Execution report
        """
        try:
            logger.info(f"Adaptive: {side} {total_quantity} {symbol} (urgency: {urgency})")

            # Analyze market conditions
            conditions = await self._analyze_market_conditions(symbol, side, total_quantity)

            # Determine optimal strategy based on conditions
            if conditions['spread_bps'] > 10 or conditions['depth_score'] < 30:
                # Wide spread or low depth - use TWAP
                logger.info("Adaptive choosing TWAP (low liquidity)")
                num_slices = 15 if urgency == 'LOW' else 10 if urgency == 'NORMAL' else 5

                return await self.execute_twap(
                    symbol, side, total_quantity,
                    duration_seconds=max_duration_seconds,
                    num_slices=num_slices
                )

            elif conditions['order_impact_pct'] > 0.5:
                # High market impact - use Iceberg
                logger.info("Adaptive choosing Iceberg (high impact)")
                visible_qty = total_quantity * 0.2  # Show 20%

                # Get current best price
                if side == 'BUY':
                    limit_price = conditions['best_ask'] * 1.001  # 0.1% above
                else:
                    limit_price = conditions['best_bid'] * 0.999  # 0.1% below

                return await self.execute_iceberg(
                    symbol, side, total_quantity,
                    visible_quantity=visible_qty,
                    limit_price=limit_price,
                    timeout_seconds=max_duration_seconds
                )

            else:
                # Good liquidity - use simple limit or market
                logger.info("Adaptive choosing limit order (good liquidity)")

                if urgency == 'HIGH':
                    # Market order
                    result = await self._place_market_order(symbol, side, total_quantity)
                else:
                    # Limit order at best price
                    limit_price = conditions['best_ask'] if side == 'BUY' else conditions['best_bid']
                    result = await self._place_limit_order(symbol, side, total_quantity, limit_price)

                return {
                    'algorithm': 'ADAPTIVE_LIMIT',
                    'symbol': symbol,
                    'side': side,
                    'total_quantity': total_quantity,
                    'result': result
                }

        except Exception as e:
            logger.error(f"Error executing Adaptive: {e}")
            return {'error': str(e)}

    async def _analyze_market_conditions(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Dict:
        """
        Analyze market conditions for adaptive execution

        Returns:
            Market condition metrics
        """
        try:
            # Get order book
            order_book = await binance_client.futures_order_book(symbol=symbol, limit=20)

            bids = [[float(p), float(q)] for p, q in order_book.get('bids', [])]
            asks = [[float(p), float(q)] for p, q in order_book.get('asks', [])]

            if not bids or not asks:
                return self._default_conditions()

            best_bid = bids[0][0]
            best_ask = asks[0][0]

            # Calculate spread
            spread = best_ask - best_bid
            spread_bps = (spread / best_bid) * 10000  # Basis points

            # Calculate available depth
            if side == 'BUY':
                available_depth = sum(q for p, q in asks[:5])
            else:
                available_depth = sum(q for p, q in bids[:5])

            depth_ratio = available_depth / quantity if quantity > 0 else 0

            # Depth score (0-100)
            if depth_ratio >= 3.0:
                depth_score = 100
            elif depth_ratio >= 2.0:
                depth_score = 80
            elif depth_ratio >= 1.0:
                depth_score = 60
            else:
                depth_score = int(depth_ratio * 60)

            # Estimate market impact
            if side == 'BUY':
                levels = asks[:10]
            else:
                levels = bids[:10]

            cumulative_qty = 0
            total_cost = 0
            for price, qty in levels:
                take_qty = min(qty, quantity - cumulative_qty)
                total_cost += price * take_qty
                cumulative_qty += take_qty

                if cumulative_qty >= quantity:
                    break

            avg_impact_price = total_cost / cumulative_qty if cumulative_qty > 0 else best_bid
            impact_pct = abs(avg_impact_price - best_bid) / best_bid * 100

            return {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread_bps': spread_bps,
                'available_depth': available_depth,
                'depth_ratio': depth_ratio,
                'depth_score': depth_score,
                'order_impact_pct': impact_pct
            }

        except Exception as e:
            logger.error(f"Error analyzing market conditions: {e}")
            return self._default_conditions()

    def _default_conditions(self) -> Dict:
        """Return default market conditions"""
        return {
            'best_bid': 0,
            'best_ask': 0,
            'spread_bps': 5.0,
            'available_depth': 0,
            'depth_ratio': 0,
            'depth_score': 50,
            'order_impact_pct': 0.1
        }

    async def _place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Optional[Dict]:
        """Place limit order"""
        try:
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce='GTC'
            )

            return order

        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None

    async def _place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict]:
        """Place market order"""
        try:
            order = await binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )

            return order

        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None

    async def calculate_optimal_execution_params(
        self,
        symbol: str,
        side: str,
        quantity: float,
        target_duration_minutes: int = 5
    ) -> Dict:
        """
        Calculate optimal execution parameters without executing

        Useful for planning

        Returns:
            Recommended execution parameters
        """
        try:
            # Analyze conditions
            conditions = await self._analyze_market_conditions(symbol, side, quantity)

            # Recommend algorithm
            if conditions['order_impact_pct'] > 1.0:
                recommended_algo = 'TWAP'
                params = {
                    'num_slices': 20,
                    'duration_seconds': target_duration_minutes * 60,
                    'reason': f"High market impact ({conditions['order_impact_pct']:.2f}%)"
                }

            elif conditions['depth_score'] < 50:
                recommended_algo = 'ICEBERG'
                params = {
                    'visible_quantity': quantity * 0.15,
                    'reason': f"Low order book depth (score: {conditions['depth_score']})"
                }

            else:
                recommended_algo = 'LIMIT'
                params = {
                    'limit_price': conditions['best_ask'] if side == 'BUY' else conditions['best_bid'],
                    'reason': f"Good liquidity (depth score: {conditions['depth_score']})"
                }

            return {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'recommended_algorithm': recommended_algo,
                'parameters': params,
                'market_conditions': conditions,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating execution params: {e}")
            return {'error': str(e)}


# Singleton instance
smart_order_router = SmartOrderRouter()
