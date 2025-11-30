import asyncio
from utils.logger import setup_logger
from api.database import SessionLocal
from api.models.trades import Trade
from datetime import datetime
from modules.risk_calculator import risk_calculator

logger = setup_logger("bot_loops")

class BotLoops:
    def __init__(self, bot):
        self.bot = bot
        self.running = False

    def start(self):
        self.running = True
        asyncio.create_task(self._metrics_loop())
        asyncio.create_task(self.bot.trading_loop.start())
        asyncio.create_task(self.bot._pyramiding_loop())
        asyncio.create_task(self.bot._sniper_loop())
        asyncio.create_task(self.bot._dca_loop())
        asyncio.create_task(self.bot._time_based_exit_loop())

    def stop(self):
        self.running = False
        self.bot.trading_loop.stop()

    async def _metrics_loop(self):
        """Loop de métricas de performance"""
        await asyncio.sleep(600)
        while self.running:
            try:
                db = SessionLocal()
                try:
                    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    trades_today = db.query(Trade).filter(Trade.opened_at >= today_start).all()
                    if trades_today:
                        total_trades = len(trades_today)
                        closed_trades = [t for t in trades_today if t.status == 'closed']
                        if closed_trades:
                            total_pnl = sum(t.pnl for t in closed_trades)
                            winning_trades = [t for t in closed_trades if t.pnl > 0]
                            win_rate = (len(winning_trades) / len(closed_trades)) * 100
                            
                            self.bot.total_trades = len(closed_trades)
                            self.bot.winning_trades = len(winning_trades)
                            self.bot.win_rate = win_rate / 100
                            
                            for trade in closed_trades[-5:]:
                                risk_calculator.update_performance(trade.pnl > 0)
                            
                            avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
                            losing_trades = [t for t in closed_trades if t.pnl < 0]
                            avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
                            
                            logger.info("=" * 60)
                            logger.info("📊 PERFORMANCE HOJE")
                            logger.info(f"  Total Trades: {total_trades} ({len(closed_trades)} fechados)")
                            logger.info(f"  P&L: {total_pnl:+.2f} USDT")
                            logger.info(f"  Win Rate: {win_rate:.1f}% ({len(winning_trades)}/{len(closed_trades)})")
                            logger.info(f"  Avg Win: +{avg_win:.2f} USDT")
                            logger.info(f"  Avg Loss: {avg_loss:.2f} USDT")
                            logger.info("=" * 60)
                        else:
                            logger.info(f"📊 {total_trades} posição(ões) aberta(s), nenhuma fechada ainda")
                finally:
                    db.close()
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Erro no loop de métricas: {e}")
                await asyncio.sleep(1800)
