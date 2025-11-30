from utils.logger import setup_logger
from utils.binance_client import binance_client
from api.database import SessionLocal
from api.models.trades import Trade
from config.settings import get_settings
from typing import Dict
import pandas as pd

logger = setup_logger("bot_strategies")

class BotStrategies:
    def __init__(self, bot):
        self.bot = bot

    def _calculate_rsi_quick(self, df, period=14):
        """Cálculo rápido de RSI para o loop de DCA"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    def _get_symbol_profile(self, symbol: str) -> Dict:
        """Perfil histórico por símbolo (P&L, win rate, etc.) baseado nos trades fechados.
        Usado para ajustar risco/alavancagem dinamicamente.
        """
        db = SessionLocal()
        try:
            trades = (
                db.query(Trade)
                .filter(Trade.symbol == symbol, Trade.status == 'closed')
                .order_by(Trade.closed_at.desc())
                .limit(50)
                .all()
            )
            total = len(trades)
            if total == 0:
                return {
                    "symbol": symbol, "trades": 0, "roi_usdt": 0.0, "roi_pct": 0.0,
                    "win_rate": 0.0, "avg_pnl": 0.0, "avg_pnl_pct": 0.0,
                }

            roi_usdt = sum(float(t.pnl or 0.0) for t in trades)
            notional_sum = sum(float((t.entry_price or 0.0) * (t.quantity or 0.0)) for t in trades)
            roi_pct = (roi_usdt / notional_sum * 100.0) if notional_sum > 0 else 0.0
            wins = [t for t in trades if (t.pnl or 0.0) > 0]
            win_rate = len(wins) / total if total > 0 else 0.0
            avg_pnl = roi_usdt / total if total > 0 else 0.0
            avg_pnl_pct = sum(float(t.pnl_percentage or 0.0) for t in trades) / total

            return {
                "symbol": symbol, "trades": total, "roi_usdt": roi_usdt, "roi_pct": roi_pct,
                "win_rate": win_rate, "avg_pnl": avg_pnl, "avg_pnl_pct": avg_pnl_pct,
            }
        except Exception as e:
            logger.error(f"Erro ao obter perfil do símbolo {symbol}: {e}")
            return {
                "symbol": symbol, "trades": 0, "roi_usdt": 0.0, "roi_pct": 0.0,
                "win_rate": 0.0, "avg_pnl": 0.0, "avg_pnl_pct": 0.0,
            }
        finally:
            db.close()

    def _adjust_signal_for_symbol_profile(self, signal: Dict) -> Dict:
        """Ajusta risk_pct e leverage do sinal com base no histórico do símbolo."""
        try:
            symbol = signal.get("symbol")
            if not symbol:
                return signal

            profile = self._get_symbol_profile(symbol)
            trades = profile.get("trades", 0)
            if trades < 10:
                return signal

            roi_pct = float(profile.get("roi_pct", 0.0))
            win_rate = float(profile.get("win_rate", 0.0))

            adjusted = dict(signal)
            risk_pct = float(adjusted.get("risk_pct", 2.0))
            lev_default = int(get_settings().DEFAULT_LEVERAGE)
            leverage = int(adjusted.get("leverage", lev_default))

            if roi_pct <= -5.0 or win_rate < 0.45:
                old_risk, old_lev = risk_pct, leverage
                risk_pct = min(risk_pct, 0.5)
                leverage = max(2, int(leverage * 0.5))
                logger.info(f"⚠️ Ajuste conservador para {symbol}: trades={trades}, ROI={roi_pct:.1f}%, WR={win_rate*100:.1f}%. risk_pct {old_risk:.2f}%→{risk_pct:.2f}%, lev {old_lev}→{leverage}.")
            elif roi_pct >= 5.0 and win_rate > 0.60:
                old_risk, old_lev = risk_pct, leverage
                risk_pct = min(risk_pct * 1.2, 2.0)
                leverage = min(leverage + 1, 15)
                logger.info(f"🚀 Ajuste agressivo moderado para {symbol}: trades={trades}, ROI={roi_pct:.1f}%, WR={win_rate*100:.1f}%. risk_pct {old_risk:.2f}%→{risk_pct:.2f}%, lev {old_lev}→{leverage}.")
            
            adjusted["risk_pct"] = risk_pct
            adjusted["leverage"] = leverage
            return adjusted
        except Exception as e:
            logger.error(f"Erro ao ajustar sinal por perfil de símbolo: {e}")
            return signal

    async def _calculate_scan_interval(self) -> int:
        """Calcula scan interval dinâmico baseado em volatilidade"""
        try:
            klines = await binance_client.get_klines(symbol='BTCUSDT', interval='1h', limit=24)
            closes = [float(k[4]) for k in klines] if klines else []
            if not closes:
                logger.warning("Falha ao obter klines (async); usando intervalo base.")
                return self.bot.bot_config.base_scan_interval
            
            high_24h, low_24h = max(closes), min(closes)
            volatility_pct = ((high_24h - low_24h) / low_24h) * 100
            
            if volatility_pct > 5:
                interval = 300  # 5 minutos
                logger.info(f"🔥 Alta volatilidade ({volatility_pct:.2f}%) → Scan: 5min")
            elif volatility_pct < 2:
                interval = 900  # 15 minutos
                logger.info(f"💤 Baixa volatilidade ({volatility_pct:.2f}%) → Scan: 15min")
            else:
                interval = self.bot.bot_config.base_scan_interval
                logger.info(f"📊 Volatilidade normal ({volatility_pct:.2f}%) → Scan: 10min")
            
            return interval
        except Exception as e:
            logger.error(f"Erro ao calcular scan interval: {e}")
            return self.bot.bot_config.base_scan_interval
