from datetime import datetime, timedelta, timezone
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.models.trades import Trade, TradeArchive  # noqa: E402
from models.database import SessionLocal  # noqa: E402


def _trade_dt(trade):
    dt = trade.closed_at or trade.exit_time or trade.opened_at
    if dt and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def archive_closed_trades(days: int = 1, reason: str = "cleanup"):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db = SessionLocal()
    try:
        closed_trades = db.query(Trade).filter(Trade.status == "closed").all()
        to_archive = [t for t in closed_trades if _trade_dt(t) and _trade_dt(t) < cutoff]

        for t in to_archive:
            archived = TradeArchive(
                id=t.id,
                symbol=t.symbol,
                direction=t.direction,
                entry_price=t.entry_price,
                current_price=t.current_price,
                quantity=t.quantity,
                leverage=t.leverage,
                stop_loss=t.stop_loss,
                take_profit_1=t.take_profit_1,
                take_profit_2=t.take_profit_2,
                take_profit_3=t.take_profit_3,
                status=t.status,
                pnl=t.pnl,
                pnl_percentage=t.pnl_percentage,
                opened_at=t.opened_at,
                closed_at=t.closed_at,
                order_id=t.order_id,
                max_pnl_percentage=t.max_pnl_percentage,
                trailing_peak_price=t.trailing_peak_price,
                pyramided=t.pyramided,
                partial_taken=t.partial_taken,
                dca_count=t.dca_count,
                entry_fee=t.entry_fee,
                exit_fee=t.exit_fee,
                funding_cost=t.funding_cost,
                net_pnl=t.net_pnl,
                is_maker_entry=t.is_maker_entry,
                is_maker_exit=t.is_maker_exit,
                breakeven_price=t.breakeven_price,
                breakeven_stop_activated=t.breakeven_stop_activated,
                market_sentiment_score=t.market_sentiment_score,
                top_trader_ratio=t.top_trader_ratio,
                liquidation_proximity=t.liquidation_proximity,
                funding_periods_held=t.funding_periods_held,
                entry_time=t.entry_time,
                is_sniper=t.is_sniper,
                exit_price=t.exit_price,
                exit_time=t.exit_time,
                archived_at=datetime.now(timezone.utc),
                archive_reason=reason,
            )
            db.add(archived)
            db.delete(t)

        db.commit()
        print(f"archived={len(to_archive)} cutoff={cutoff.isoformat()}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Default: archive closed trades older than 1 day.
    archive_closed_trades(days=1)
