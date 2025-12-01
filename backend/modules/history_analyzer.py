import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.settings import get_settings
from models.database import get_db
from api.models.trades import Trade
from utils.logger import setup_logger
from utils.binance_client import binance_client

logger = setup_logger("history_analyzer")
settings = get_settings()

class HistoryAnalyzer:
    def __init__(self):
        self.settings = settings
        self.blacklist_recommendations = set()

    async def analyze_performance_by_symbol(self, days: int = 7) -> List[Dict]:
        """Analisa performance por símbolo nos últimos X dias"""
        try:
            # Usar uma sessão de banco de dados temporária
            db = next(get_db())
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query agregada
            stats = db.query(
                Trade.symbol,
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.pnl).label('total_pnl'),
                func.sum(func.case((Trade.pnl > 0, 1), else_=0)).label('wins')
            ).filter(
                Trade.status == 'closed',
                Trade.closed_at >= cutoff_date
            ).group_by(Trade.symbol).all()
            
            results = []
            for s in stats:
                win_rate = (s.wins / s.total_trades * 100) if s.total_trades > 0 else 0
                results.append({
                    "symbol": s.symbol,
                    "total_trades": s.total_trades,
                    "total_pnl": float(s.total_pnl or 0),
                    "win_rate": win_rate
                })
                
            # Identificar candidatos a blacklist (ex: Win Rate < 30% e PnL negativo com min 5 trades)
            self.blacklist_recommendations = {
                r['symbol'] for r in results 
                if r['win_rate'] < 30 and r['total_pnl'] < 0 and r['total_trades'] >= 5
            }
            
            if self.blacklist_recommendations:
                logger.warning(f"🚫 Recomendação de Blacklist (Win Rate < 30%): {self.blacklist_recommendations}")
                
            return sorted(results, key=lambda x: x['total_pnl'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao analisar performance por símbolo: {e}")
            return []
        finally:
            if 'db' in locals():
                db.close()

    async def get_realized_pnl_from_binance(self, days: int = 30) -> float:
        """Busca PnL realizado direto da Binance (inclui taxas e funding)"""
        try:
            # Income history retorna array de dicts com 'incomeType': 'REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE'
            # Limite de 1000, talvez precise paginar se for muito ativo
            # Binance Futures API: GET /fapi/v1/income
            
            # Precisamos converter days para start_time em ms
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            income_history = await binance_client.client.futures_income_history(
                startTime=start_time,
                limit=1000
            )
            
            total_pnl = 0.0
            total_commission = 0.0
            total_funding = 0.0
            
            for item in income_history:
                amount = float(item['income'])
                if item['incomeType'] == 'REALIZED_PNL':
                    total_pnl += amount
                elif item['incomeType'] == 'COMMISSION':
                    total_commission += amount
                elif item['incomeType'] == 'FUNDING_FEE':
                    total_funding += amount
                    
            net_pnl = total_pnl + total_commission + total_funding
            
            logger.info(f"💰 Binance Realized PnL ({days}d): {net_pnl:.2f} USDT (PnL: {total_pnl:.2f}, Taxas: {total_commission:.2f}, Funding: {total_funding:.2f})")
            
            return {
                "net_pnl": net_pnl,
                "gross_pnl": total_pnl,
                "fees": total_commission,
                "funding": total_funding
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar PnL da Binance: {e}")
            return {"net_pnl": 0.0, "gross_pnl": 0.0, "fees": 0.0, "funding": 0.0}

    async def run_analysis_cycle(self):
        """Roda ciclo completo de análise"""
        logger.info("🔍 Iniciando análise de histórico...")
        
        # 1. Performance por Símbolo
        symbol_stats = await self.analyze_performance_by_symbol(days=7)
        
        # 2. PnL Realizado (Binance)
        binance_pnl = await self.get_realized_pnl_from_binance(days=1) # Últimas 24h para monitoramento rápido
        
        return {
            "symbol_stats": symbol_stats,
            "blacklist_recommendations": list(self.blacklist_recommendations),
            "binance_pnl_24h": binance_pnl
        }

# Singleton
history_analyzer = HistoryAnalyzer()
