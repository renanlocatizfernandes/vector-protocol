"""
Trade Journal System
Comprehensive trade tracking with tags, notes, and export capabilities
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from io import StringIO

from utils.logger import setup_logger

logger = setup_logger("trade_journal")


class TradeOutcome(str, Enum):
    """Trade outcome categories"""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    ONGOING = "ongoing"


class TradeJournal:
    """
    Trade Journal System

    Features:
    - Track all trades with detailed metadata
    - Add tags and notes
    - Search and filter
    - Export to CSV/JSON
    - Performance insights
    """

    def __init__(self):
        self.journal_entries: List[Dict] = []
        self.max_entries = 10000
        self.tags_index: Dict[str, List[int]] = {}  # tag -> entry indices

    async def add_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        leverage: int,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        strategy: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add trade to journal

        Args:
            symbol: Trading pair
            side: LONG or SHORT
            entry_price: Entry price
            quantity: Position quantity
            leverage: Leverage used
            exit_price: Exit price (if closed)
            pnl: Profit/Loss in USD
            pnl_pct: Profit/Loss percentage
            tags: List of tags
            notes: User notes
            strategy: Strategy name
            metadata: Additional metadata

        Returns:
            Journal entry
        """
        try:
            entry_id = len(self.journal_entries)

            # Determine outcome
            outcome = TradeOutcome.ONGOING
            if exit_price is not None and pnl is not None:
                if pnl > 1:
                    outcome = TradeOutcome.WIN
                elif pnl < -1:
                    outcome = TradeOutcome.LOSS
                else:
                    outcome = TradeOutcome.BREAKEVEN

            entry = {
                'id': entry_id,
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'leverage': leverage,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'outcome': outcome.value,
                'tags': tags or [],
                'notes': notes,
                'strategy': strategy,
                'metadata': metadata or {},
                'entry_time': datetime.now().isoformat(),
                'exit_time': None
            }

            # Add to journal
            self.journal_entries.append(entry)

            # Update tags index
            if tags:
                for tag in tags:
                    if tag not in self.tags_index:
                        self.tags_index[tag] = []
                    self.tags_index[tag].append(entry_id)

            # Trim if needed
            if len(self.journal_entries) > self.max_entries:
                removed = self.journal_entries.pop(0)
                self._remove_from_tags_index(removed)

            logger.info(f"Added journal entry: {symbol} {side}")

            return entry

        except Exception as e:
            logger.error(f"Error adding journal entry: {e}")
            return {}

    async def update_entry(
        self,
        entry_id: int,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Update existing journal entry"""
        try:
            if entry_id >= len(self.journal_entries):
                return {'success': False, 'message': 'Entry not found'}

            entry = self.journal_entries[entry_id]

            # Update fields
            if exit_price is not None:
                entry['exit_price'] = exit_price
                entry['exit_time'] = datetime.now().isoformat()

            if pnl is not None:
                entry['pnl'] = pnl

                # Update outcome
                if pnl > 1:
                    entry['outcome'] = TradeOutcome.WIN.value
                elif pnl < -1:
                    entry['outcome'] = TradeOutcome.LOSS.value
                else:
                    entry['outcome'] = TradeOutcome.BREAKEVEN.value

            if pnl_pct is not None:
                entry['pnl_pct'] = pnl_pct

            if tags is not None:
                # Remove old tags from index
                old_tags = entry.get('tags', [])
                for tag in old_tags:
                    if tag in self.tags_index and entry_id in self.tags_index[tag]:
                        self.tags_index[tag].remove(entry_id)

                # Add new tags
                entry['tags'] = tags
                for tag in tags:
                    if tag not in self.tags_index:
                        self.tags_index[tag] = []
                    if entry_id not in self.tags_index[tag]:
                        self.tags_index[tag].append(entry_id)

            if notes is not None:
                entry['notes'] = notes

            if metadata is not None:
                entry['metadata'].update(metadata)

            logger.info(f"Updated journal entry: {entry_id}")

            return {'success': True, 'entry': entry}

        except Exception as e:
            logger.error(f"Error updating journal entry: {e}")
            return {'success': False, 'message': str(e)}

    async def search_entries(
        self,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        outcome: Optional[TradeOutcome] = None,
        tags: Optional[List[str]] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search journal entries with filters

        Args:
            symbol: Filter by symbol
            side: Filter by side (LONG/SHORT)
            outcome: Filter by outcome
            tags: Filter by tags (entries must have ALL tags)
            strategy: Filter by strategy name
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            Filtered entries
        """
        try:
            filtered = []

            for entry in reversed(self.journal_entries):
                # Apply filters
                if symbol and entry['symbol'] != symbol:
                    continue

                if side and entry['side'] != side:
                    continue

                if outcome and entry['outcome'] != outcome.value:
                    continue

                if strategy and entry.get('strategy') != strategy:
                    continue

                if tags:
                    entry_tags = set(entry.get('tags', []))
                    if not all(tag in entry_tags for tag in tags):
                        continue

                if start_date or end_date:
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    if start_date and entry_time < start_date:
                        continue
                    if end_date and entry_time > end_date:
                        continue

                filtered.append(entry)

                if len(filtered) >= limit:
                    break

            return filtered

        except Exception as e:
            logger.error(f"Error searching journal entries: {e}")
            return []

    async def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """Get journal entry by ID"""
        if 0 <= entry_id < len(self.journal_entries):
            return self.journal_entries[entry_id]
        return None

    async def get_all_tags(self) -> List[str]:
        """Get all unique tags"""
        return sorted(self.tags_index.keys())

    async def get_statistics(self) -> Dict:
        """Get journal statistics"""
        try:
            total = len(self.journal_entries)

            if total == 0:
                return {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'breakeven': 0,
                    'ongoing': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'largest_win': 0,
                    'largest_loss': 0
                }

            # Count outcomes
            wins = sum(1 for e in self.journal_entries if e['outcome'] == TradeOutcome.WIN.value)
            losses = sum(1 for e in self.journal_entries if e['outcome'] == TradeOutcome.LOSS.value)
            breakeven = sum(1 for e in self.journal_entries if e['outcome'] == TradeOutcome.BREAKEVEN.value)
            ongoing = sum(1 for e in self.journal_entries if e['outcome'] == TradeOutcome.ONGOING.value)

            # Calculate P&L
            total_pnl = sum(e.get('pnl', 0) for e in self.journal_entries if e.get('pnl') is not None)

            # Win/loss stats
            win_pnls = [e['pnl'] for e in self.journal_entries if e.get('pnl') and e['pnl'] > 0]
            loss_pnls = [e['pnl'] for e in self.journal_entries if e.get('pnl') and e['pnl'] < 0]

            avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
            avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
            largest_win = max(win_pnls) if win_pnls else 0
            largest_loss = min(loss_pnls) if loss_pnls else 0

            # Win rate
            completed_trades = wins + losses + breakeven
            win_rate = (wins / completed_trades * 100) if completed_trades > 0 else 0

            return {
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'breakeven': breakeven,
                'ongoing': ongoing,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'largest_win': round(largest_win, 2),
                'largest_loss': round(largest_loss, 2)
            }

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}

    async def export_csv(self, filename: Optional[str] = None) -> str:
        """
        Export journal to CSV

        Args:
            filename: Optional filename

        Returns:
            CSV content as string
        """
        try:
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'id', 'timestamp', 'symbol', 'side', 'entry_price', 'exit_price',
                'quantity', 'leverage', 'pnl', 'pnl_pct', 'outcome', 'strategy',
                'tags', 'notes'
            ])

            writer.writeheader()

            for entry in self.journal_entries:
                row = {
                    'id': entry['id'],
                    'timestamp': entry['timestamp'],
                    'symbol': entry['symbol'],
                    'side': entry['side'],
                    'entry_price': entry['entry_price'],
                    'exit_price': entry.get('exit_price', ''),
                    'quantity': entry['quantity'],
                    'leverage': entry['leverage'],
                    'pnl': entry.get('pnl', ''),
                    'pnl_pct': entry.get('pnl_pct', ''),
                    'outcome': entry['outcome'],
                    'strategy': entry.get('strategy', ''),
                    'tags': ','.join(entry.get('tags', [])),
                    'notes': entry.get('notes', '')
                }
                writer.writerow(row)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return ""

    async def export_json(self) -> str:
        """Export journal to JSON"""
        try:
            return json.dumps(self.journal_entries, indent=2)
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return ""

    def _remove_from_tags_index(self, entry: Dict):
        """Remove entry from tags index"""
        entry_id = entry['id']
        for tag in entry.get('tags', []):
            if tag in self.tags_index and entry_id in self.tags_index[tag]:
                self.tags_index[tag].remove(entry_id)


# Singleton instance
trade_journal = TradeJournal()
