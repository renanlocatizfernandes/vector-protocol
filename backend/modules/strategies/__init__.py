"""
Advanced Trading Strategies Module
"""

from modules.strategies.trailing_stop_manager import (
    trailing_stop_manager,
    TrailingStopMode,
    TrailingStopManager
)
from modules.strategies.execution_strategy import (
    execution_strategy_manager,
    ExecutionMode,
    MarginMode,
    ExecutionStrategy,
    StaticStrategy,
    SniperStrategy,
    PyramidStrategy,
    DCAStrategy,
    StrategyFactory
)

__all__ = [
    # Trailing Stop
    'trailing_stop_manager',
    'TrailingStopMode',
    'TrailingStopManager',

    # Execution Strategies
    'execution_strategy_manager',
    'ExecutionMode',
    'MarginMode',
    'ExecutionStrategy',
    'StaticStrategy',
    'SniperStrategy',
    'PyramidStrategy',
    'DCAStrategy',
    'StrategyFactory',
]
