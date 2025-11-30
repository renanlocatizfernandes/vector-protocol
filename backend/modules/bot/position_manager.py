from api.database import SessionLocal
from api.models.trades import Trade
from utils.binance_client import binance_client
from utils.logger import setup_logger
from typing import List, Dict
import asyncio

logger = setup_logger("position_manager")

class PositionManager:
    def __init__(self, bot_config):
        self.client = binance_client.client
        self.bot_config = bot_config

    async def get_open_positions_count(self) -> int:
        """Retorna número de posições abertas"""
        db = SessionLocal()
        try:
            count = db.query(Trade).filter(Trade.status == 'open').count()
            return count
        finally:
            db.close()

    async def get_open_positions_from_binance(self) -> List[Dict]:
        """Retorna posições abertas da Binance"""
        try:
            positions = await asyncio.to_thread(self.client.futures_position_information)
            open_positions = [
                p for p in positions
                if float(p['positionAmt']) != 0
            ]
            return open_positions
        except Exception as e:
            logger.error(f"Erro ao buscar posições da Binance: {e}")
            return []

    async def sync_positions_with_binance(self):
        """Sincroniza posições da Binance com o banco de dados"""
        logger.info("🔄 Sincronizando posições da Binance com DB...")
        try:
            positions = await self.get_open_positions_from_binance()
            if not positions:
                logger.info("✅ Nenhuma posição aberta na Binance")
                return

            db = SessionLocal()
            try:
                synced = 0
                for pos in positions:
                    symbol = pos['symbol']
                    existing = db.query(Trade).filter(
                        Trade.symbol == symbol,
                        Trade.status == 'open'
                    ).first()

                    if existing:
                        continue

                    logger.info(f"🔄 Sincronizando {symbol}...")
                    position_amt = float(pos['positionAmt'])
                    entry_price = float(pos['entryPrice'])
                    direction = 'LONG' if position_amt > 0 else 'SHORT'
                    leverage = int(pos.get('leverage', 3))

                    trade = Trade(
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry_price,
                        current_price=entry_price,
                        quantity=abs(position_amt),
                        leverage=leverage,
                        stop_loss=entry_price * (0.92 if direction == 'LONG' else 1.08),
                        take_profit_1=entry_price * (1.10 if direction == 'LONG' else 0.90),
                        take_profit_2=entry_price * (1.20 if direction == 'LONG' else 0.80),
                        take_profit_3=entry_price * (1.30 if direction == 'LONG' else 0.70),
                        status='open',
                        pnl=0.0,
                        pnl_percentage=0.0
                    )
                    db.add(trade)
                    synced += 1
                db.commit()
                if synced > 0:
                    logger.info(f"✅ {synced} posição(ões) sincronizada(s)")
                else:
                    logger.info("✅ Nenhuma posição para sincronizar")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro ao sincronizar posições: {e}")

    async def get_account_balance(self) -> float:
        """Retorna saldo disponível em USDT (não bloqueia o event loop)."""
        try:
            info = await binance_client.get_account_balance()
            if info and info.get("available_balance") is not None:
                return float(info["available_balance"])
            account = await asyncio.to_thread(self.client.futures_account_balance)
            usdt = next((b for b in account if b.get('asset') == 'USDT'), None)
            if usdt:
                return float(usdt.get('availableBalance', 0) or 0)
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao obter saldo (async): {e}")
            return 0.0
