import asyncio
from datetime import datetime, timezone

from api.database import SessionLocal
from api.models.trades import Trade
from config.settings import get_settings
from utils.binance_client import binance_client
from utils.logger import setup_logger

logger = setup_logger("pnl_reconciler")


async def check_pnl_divergence() -> dict:
    """
    Compara PnL realizado no DB vs Exchange e retorna status de divergencia.
    """
    settings = get_settings()
    db = SessionLocal()
    try:
        if not binance_client.client:
            return {
                "warning": False,
                "reason": "binance_client_unavailable",
                "realized_delta": 0.0,
                "pct_delta": 0.0
            }
        today_start_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        trades = db.query(Trade).filter(
            Trade.closed_at >= today_start_utc,
            Trade.status == "closed"
        ).all()

        total_pnl = sum(t.pnl or 0 for t in trades) if trades else 0.0

        realized_pnl = 0.0
        commission = 0.0
        funding = 0.0
        try:
            start_time = int(today_start_utc.timestamp() * 1000)
            income_history = await asyncio.to_thread(
                binance_client.client.futures_income_history,
                startTime=start_time,
                limit=1000
            )
            for item in income_history or []:
                try:
                    amount = float(item.get("income", 0) or 0)
                except Exception:
                    amount = 0.0
                income_type = item.get("incomeType")
                if income_type == "REALIZED_PNL":
                    realized_pnl += amount
                elif income_type == "COMMISSION":
                    commission += amount
                elif income_type == "FUNDING_FEE":
                    funding += amount
        except Exception as e:
            logger.warning(f"PnL divergence check failed to fetch income history: {e}")
            return {
                "warning": False,
                "reason": "income_history_unavailable",
                "realized_delta": 0.0,
                "pct_delta": 0.0
            }

        realized_delta = abs(realized_pnl - total_pnl)
        denom = max(abs(total_pnl), abs(realized_pnl), 1.0)
        pct_delta = (realized_delta / denom) * 100.0
        threshold = float(getattr(settings, "PNL_DIVERGENCE_THRESHOLD_PCT", 5.0))
        warning = pct_delta > threshold

        return {
            "warning": warning,
            "realized_delta": round(realized_delta, 2),
            "pct_delta": round(pct_delta, 2),
            "db_realized": round(total_pnl, 2),
            "exchange_realized": round(realized_pnl, 2),
            "exchange_fees": round(commission, 2),
            "exchange_funding": round(funding, 2)
        }
    finally:
        db.close()
