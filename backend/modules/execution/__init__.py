"""
Advanced Execution Module
Smart order routing and adaptive take profit management
"""

from modules.execution.smart_order_routing import (
    smart_order_router,
    SmartOrderRouter,
    ExecutionAlgorithm,
    OrderSlice
)
from modules.execution.adaptive_tp_ladder import (
    adaptive_tp_ladder,
    AdaptiveTakeProfitLadder,
    TakeProfitLevel
)

__all__ = [
    # Smart Order Routing
    'smart_order_router',
    'SmartOrderRouter',
    'ExecutionAlgorithm',
    'OrderSlice',

    # Adaptive TP Ladder
    'adaptive_tp_ladder',
    'AdaptiveTakeProfitLadder',
    'TakeProfitLevel',
]
