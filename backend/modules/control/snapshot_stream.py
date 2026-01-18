"""
Real-Time Snapshot Stream Manager
Streams real-time updates of capital, positions, and bot status via WebSocket
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("snapshot_stream")


class SnapshotStreamManager:
    """
    Real-Time Snapshot Stream Manager

    Provides 1-second updates of:
    - Capital state (wallet, margin, P&L)
    - Open positions (real-time prices, P&L)
    - Bot status (running, paused, last action)
    - Market data (selected symbols)
    """

    def __init__(self):
        self.is_running = False
        self.stream_task = None
        self.subscribers = []  # WebSocket connections
        self.update_interval = 1.0  # 1 second

        # Snapshot history (last 60 snapshots = 1 minute)
        self.snapshot_history = deque(maxlen=60)

        # Configuration
        self.enabled_modules = {
            'capital': True,
            'positions': True,
            'bot_status': True,
            'market_data': False  # Disabled by default (high bandwidth)
        }

        # Watched symbols for market data
        self.watched_symbols = set()

    async def start_stream(self):
        """Start the real-time snapshot stream"""
        if self.is_running:
            logger.warning("Snapshot stream already running")
            return

        self.is_running = True
        self.stream_task = asyncio.create_task(self._stream_loop())
        logger.info("Real-time snapshot stream started")

    async def stop_stream(self):
        """Stop the real-time snapshot stream"""
        if not self.is_running:
            return

        self.is_running = False

        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass

        logger.info("Real-time snapshot stream stopped")

    async def _stream_loop(self):
        """Main streaming loop - runs every second"""
        try:
            while self.is_running:
                try:
                    # Generate snapshot
                    snapshot = await self._generate_snapshot()

                    # Save to history
                    self.snapshot_history.append(snapshot)

                    # Broadcast to subscribers (will be handled by WebSocket manager)
                    await self._broadcast_snapshot(snapshot)

                except Exception as e:
                    logger.error(f"Error in snapshot stream loop: {e}")

                # Wait for next interval
                await asyncio.sleep(self.update_interval)

        except asyncio.CancelledError:
            logger.info("Snapshot stream loop cancelled")

    async def _generate_snapshot(self) -> Dict:
        """Generate complete snapshot of current state"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'type': 'snapshot',
            'data': {}
        }

        # Capital state
        if self.enabled_modules['capital']:
            snapshot['data']['capital'] = await self._get_capital_snapshot()

        # Positions
        if self.enabled_modules['positions']:
            snapshot['data']['positions'] = await self._get_positions_snapshot()

        # Bot status
        if self.enabled_modules['bot_status']:
            snapshot['data']['bot_status'] = await self._get_bot_status_snapshot()

        # Market data
        if self.enabled_modules['market_data'] and self.watched_symbols:
            snapshot['data']['market_data'] = await self._get_market_data_snapshot()

        return snapshot

    async def _get_capital_snapshot(self) -> Dict:
        """Get capital state snapshot"""
        try:
            # Import here to avoid circular dependency
            from modules.capital import dynamic_capital_manager

            capital_state = await dynamic_capital_manager.get_capital_state()

            if not capital_state:
                return {}

            return {
                'wallet_balance': capital_state.get('total_wallet_balance', 0),
                'available_balance': capital_state.get('available_balance', 0),
                'margin_used_pct': capital_state.get('margin_used_pct', 0),
                'unrealized_pnl': capital_state.get('unrealized_pnl', 0),
                'unrealized_pnl_pct': capital_state.get('unrealized_pnl_pct', 0),
                'buying_power': capital_state.get('buying_power', 0),
                'num_positions': capital_state.get('num_positions', 0),
                'capital_status': capital_state.get('capital_status', 'unknown')
            }

        except Exception as e:
            logger.error(f"Error getting capital snapshot: {e}")
            return {}

    async def _get_positions_snapshot(self) -> List[Dict]:
        """Get open positions snapshot"""
        try:
            positions = await binance_client.futures_position_information()

            active_positions = []

            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))

                if abs(position_amt) == 0:
                    continue

                # Get current mark price
                mark_price = float(pos.get('markPrice', 0))
                entry_price = float(pos.get('entryPrice', 0))
                unrealized_profit = float(pos.get('unRealizedProfit', 0))
                leverage = int(pos.get('leverage', 1))

                # Calculate P&L %
                pnl_pct = 0
                if entry_price > 0:
                    price_change_pct = ((mark_price - entry_price) / entry_price) * 100
                    pnl_pct = price_change_pct * leverage * (1 if position_amt > 0 else -1)

                active_positions.append({
                    'symbol': pos.get('symbol'),
                    'side': 'LONG' if position_amt > 0 else 'SHORT',
                    'size': abs(position_amt),
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'leverage': leverage,
                    'unrealized_pnl': unrealized_profit,
                    'unrealized_pnl_pct': round(pnl_pct, 2),
                    'liquidation_price': float(pos.get('liquidationPrice', 0)),
                    'margin_type': pos.get('marginType', 'cross'),
                    'notional': abs(position_amt) * mark_price
                })

            return active_positions

        except Exception as e:
            logger.error(f"Error getting positions snapshot: {e}")
            return []

    async def _get_bot_status_snapshot(self) -> Dict:
        """Get bot status snapshot"""
        try:
            # Import here to avoid circular dependency
            from modules.autonomous_bot import autonomous_bot

            return {
                'is_running': autonomous_bot.is_running,
                'is_paused': getattr(autonomous_bot, 'is_paused', False),
                'scan_interval_minutes': autonomous_bot.scan_interval_minutes,
                'dry_run': autonomous_bot.dry_run,
                'last_scan_time': autonomous_bot.last_scan_time.isoformat() if autonomous_bot.last_scan_time else None,
                'total_trades': autonomous_bot.total_trades,
                'successful_trades': autonomous_bot.successful_trades,
                'failed_trades': autonomous_bot.failed_trades
            }

        except Exception as e:
            logger.error(f"Error getting bot status snapshot: {e}")
            return {
                'is_running': False,
                'error': str(e)
            }

    async def _get_market_data_snapshot(self) -> Dict:
        """Get market data snapshot for watched symbols"""
        try:
            market_data = {}

            for symbol in self.watched_symbols:
                try:
                    # Get ticker
                    ticker = await binance_client.futures_symbol_ticker(symbol=symbol)

                    if ticker:
                        market_data[symbol] = {
                            'price': float(ticker.get('price', 0)),
                            'timestamp': ticker.get('time', 0)
                        }

                except Exception as e:
                    logger.debug(f"Error getting market data for {symbol}: {e}")

            return market_data

        except Exception as e:
            logger.error(f"Error getting market data snapshot: {e}")
            return {}

    async def _broadcast_snapshot(self, snapshot: Dict):
        """Broadcast snapshot to all subscribers"""
        # This will be called by WebSocket manager
        # For now, we'll use Redis pub/sub
        try:
            from utils.redis_client import get_redis_client

            redis_client = await get_redis_client()

            if redis_client:
                await redis_client.publish(
                    'snapshot_stream',
                    json.dumps(snapshot, default=str)
                )

        except Exception as e:
            logger.debug(f"Error broadcasting snapshot: {e}")

    def configure_modules(self, modules: Dict[str, bool]):
        """Configure which modules to include in snapshots"""
        self.enabled_modules.update(modules)
        logger.info(f"Snapshot modules configured: {self.enabled_modules}")

    def add_watched_symbol(self, symbol: str):
        """Add symbol to market data watch list"""
        self.watched_symbols.add(symbol)
        logger.info(f"Added {symbol} to watch list")

    def remove_watched_symbol(self, symbol: str):
        """Remove symbol from market data watch list"""
        self.watched_symbols.discard(symbol)
        logger.info(f"Removed {symbol} from watch list")

    def set_update_interval(self, interval_seconds: float):
        """Set update interval (minimum 0.1s, maximum 60s)"""
        interval_seconds = max(0.1, min(60.0, interval_seconds))
        self.update_interval = interval_seconds
        logger.info(f"Snapshot update interval set to {interval_seconds}s")

    async def get_snapshot_history(self, count: Optional[int] = None) -> List[Dict]:
        """Get historical snapshots"""
        if count is None:
            return list(self.snapshot_history)
        else:
            return list(self.snapshot_history)[-count:]

    async def get_current_snapshot(self) -> Dict:
        """Get current snapshot immediately"""
        return await self._generate_snapshot()


# Singleton instance
snapshot_stream_manager = SnapshotStreamManager()
