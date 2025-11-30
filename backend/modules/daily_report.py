import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from utils.logger import setup_logger
from utils.telegram_notifier import telegram_notifier
from models.database import SessionLocal
from api.models.trades import Trade
from utils.binance_client import binance_client

logger = setup_logger("daily_report")

class DailyReport:
    def __init__(self):
        self.running = False
        logger.info("Daily Report inicializado")
    
    async def start_scheduler(self):
        """Inicia agendador de relatórios diários"""
        
        if self.running:
            logger.warning("Scheduler já está rodando")
            return
        
        self.running = True
        logger.info("📊 Scheduler de relatórios diários iniciado")
        
        while self.running:
            try:
                # Verificar se é 23h
                now = datetime.now()
                
                if now.hour == 23 and now.minute == 0:
                    logger.info("⏰ Horário do relatório diário! Gerando...")
                    await self.generate_and_send_daily_report()
                    
                    # Aguardar 60s para não enviar múltiplas vezes
                    await asyncio.sleep(60)
                else:
                    # Verificar a cada 30 segundos
                    await asyncio.sleep(30)
                    
            except Exception as e:
                logger.error(f"Erro no scheduler: {e}")
                await asyncio.sleep(60)
    
    def stop_scheduler(self):
        """Para o scheduler"""
        self.running = False
        logger.info("Scheduler parado")
    
    async def generate_and_send_daily_report(self):
        """Gera e envia relatório diário"""
        
        try:
            stats = await self.get_daily_stats()
            
            if stats:
                await telegram_notifier.send_daily_summary(stats)
                logger.info("✅ Relatório diário enviado com sucesso")
            else:
                logger.warning("Nenhum dado para relatório diário")
                
        except Exception as e:
            logger.error(f"Erro ao gerar relatório diário: {e}")
    
    async def get_daily_stats(self) -> Dict:
        """Obtém estatísticas do dia"""
        
        db = SessionLocal()
        try:
            # Pegar trades de hoje
            today = datetime.now().date()
            trades = db.query(Trade).filter(
                Trade.created_at >= today
            ).all()
            
            if not trades:
                return None
            
            # Filtrar trades fechados
            closed_trades = [t for t in trades if t.status == 'CLOSED']
            
            if not closed_trades:
                # Se não tiver fechados, retornar dados das abertas
                total_pnl = sum(t.pnl or 0 for t in trades if t.status == 'OPEN')
                
                # Pegar saldo atual
                balance_info = await binance_client.get_account_balance()
                
                return {
                    'total_pnl': total_pnl,
                    'trades_count': len(trades),
                    'closed_count': 0,
                    'win_rate': 0,
                    'best_trade': {},
                    'worst_trade': {},
                    'balance': balance_info['total_balance'],
                    'open_positions': len([t for t in trades if t.status == 'OPEN'])
                }
            
            # Calcular estatísticas
            total_pnl = sum(t.pnl or 0 for t in closed_trades)
            winning_trades = [t for t in closed_trades if (t.pnl or 0) > 0]
            win_rate = (len(winning_trades) / len(closed_trades)) * 100 if closed_trades else 0
            
            best_trade = max(closed_trades, key=lambda t: t.pnl or 0)
            worst_trade = min(closed_trades, key=lambda t: t.pnl or 0)
            
            # Pegar saldo atual
            balance_info = await binance_client.get_account_balance()
            
            return {
                'total_pnl': total_pnl,
                'trades_count': len(trades),
                'closed_count': len(closed_trades),
                'win_rate': win_rate,
                'best_trade': {
                    'symbol': best_trade.symbol,
                    'pnl': best_trade.pnl or 0,
                    'pnl_pct': best_trade.pnl_percentage or 0
                },
                'worst_trade': {
                    'symbol': worst_trade.symbol,
                    'pnl': worst_trade.pnl or 0,
                    'pnl_pct': worst_trade.pnl_percentage or 0
                },
                'balance': balance_info['total_balance'],
                'open_positions': len([t for t in trades if t.status == 'OPEN'])
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter stats diárias: {e}")
            return None
        finally:
            db.close()
    
    async def send_manual_report(self):
        """Envia relatório manualmente (para testes)"""
        await self.generate_and_send_daily_report()

# Instância global
daily_report = DailyReport()
