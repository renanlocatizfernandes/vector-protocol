"""
Market Filter - PROFESSIONAL VERSION v3.0
✅ Detecção de pump & dump (rejeita +30% em < 2h)
✅ Filtro de horário (reduz agressividade nos finais de semana)
✅ Validação de liquidez mais rigorosa
"""
import asyncio
from typing import Dict
from datetime import datetime, time as dt_time
from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings
from api.database import SessionLocal
from api.models.trades import Trade

logger = setup_logger("market_filter")


class MarketFilter:
    def __init__(self):
        self.client = binance_client.client
        self.settings = get_settings()
        
        # ✅ NOVO: Detecção de pump & dump (parametrizado via settings)
        s = self.settings
        self.pump_threshold = float(getattr(s, "PUMP_THRESHOLD_PCT", 30.0))  # +X% em curto prazo
        self.pump_timeframe_hours = int(getattr(s, "PUMP_TIMEFRAME_HOURS", 2))  # horas
        self.min_sustained_volume = float(getattr(s, "PUMP_MIN_SUSTAINED_VOLUME_X", 2.0))  # Volume mínimo sustentado (x)
        
        # ✅ NOVO: Detecção de dump (simétrica)
        self.dump_threshold = float(getattr(s, "DUMP_THRESHOLD_PCT", 20.0))  # -X% em curto prazo
        self.dump_timeframe_hours = int(getattr(s, "DUMP_TIMEFRAME_HOURS", 2))  # horas
        self.min_sustained_volume_dump = float(getattr(s, "DUMP_MIN_SUSTAINED_VOLUME_X", 2.0))
        
        # ✅ NOVO: Score mínimo em regime lateral
        self.required_score_sideways = int(getattr(s, "REQUIRED_SCORE_SIDEWAYS", 75))
        
        # ✅ NOVO: Filtro de horário
        self.weekend_multiplier = 0.5  # Reduz agressividade 50% no fim de semana
        
        logger.info("✅ Market Filter PROFISSIONAL v3.0 inicializado")
        logger.info(f"🚫 Pump threshold: +{self.pump_threshold}% em {self.pump_timeframe_hours}h | Dump threshold: -{self.dump_threshold}% em {self.dump_timeframe_hours}h")
        logger.info(f"📅 Weekend reduction: {self.weekend_multiplier*100:.0f}% (SIDEWAYS score min: {self.required_score_sideways})")
    
    async def check_market_sentiment(self) -> Dict:
        """Analisa sentimento geral do mercado"""
        
        try:
            # BTC como proxy do mercado
            klines_4h = await binance_client.get_klines(
                symbol='BTCUSDT',
                interval='4h',
                limit=24
            )
            
            klines_1h = await binance_client.get_klines(
                symbol='BTCUSDT',
                interval='1h',
                limit=24
            )
            
            # Calcular mudanças
            btc_current = float(klines_4h[-1][4])
            btc_24h_ago = float(klines_4h[-6][4])
            btc_4h_ago = float(klines_4h[-1][1])
            btc_1h_ago = float(klines_1h[-1][1])
            
            btc_change_24h = ((btc_current - btc_24h_ago) / btc_24h_ago) * 100
            btc_change_4h = ((btc_current - btc_4h_ago) / btc_4h_ago) * 100
            btc_change_1h = ((btc_current - btc_1h_ago) / btc_1h_ago) * 100
            
            # Calcular volume
            volumes = [float(k[5]) for k in klines_4h[-6:]]
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1])
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Determinar trend
            if btc_change_4h > 2:
                trend = 'STRONG_UPTREND'
            elif btc_change_4h > 0.5:
                trend = 'UPTREND'
            elif btc_change_4h < -2:
                trend = 'STRONG_DOWNTREND'
            elif btc_change_4h < -0.5:
                trend = 'DOWNTREND'
            else:
                trend = 'SIDEWAYS'
            
            return {
                'trend': trend,
                'btc_change_24h': btc_change_24h,
                'btc_change_4h': btc_change_4h,
                'btc_change_1h': btc_change_1h,
                'volume_ratio': volume_ratio,
                'btc_price': btc_current
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar sentimento: {e}")
            return {
                'trend': 'UNKNOWN',
                'btc_change_24h': 0,
                'btc_change_4h': 0,
                'btc_change_1h': 0,
                'volume_ratio': 1,
                'btc_price': 0
            }
    
    async def should_trade_symbol(self, signal: Dict, market_sentiment: Dict) -> bool:
        """
        Valida se deve tradear um símbolo baseado em condições de mercado
        """
        
        symbol = signal['symbol']
        direction = signal['direction']
        
        # ✅ NOVO: Verificar pump & dump
        if not await self._validate_not_pump_and_dump(symbol):
            logger.warning(f"🚫 {symbol}: Possível pump & dump detectado")
            return False
        
        # ✅ NOVO: Ajustar baseado em horário
        weekend_adjustment = self._get_weekend_adjustment()
        
        if weekend_adjustment < 1.0:
            # No fim de semana, rejeitar sinais com score abaixo do mínimo configurado
            if signal['score'] < self.required_score_sideways:
                logger.info(f"📅 {symbol}: Score {signal['score']:.0f} < {self.required_score_sideways} (weekend threshold)")
                return False
        
        # Validar baseado em trend do BTC
        trend = market_sentiment['trend']
        # ✅ NOVO: Em regime lateral, exigir score mínimo configurável
        if trend == 'SIDEWAYS' and signal['score'] < self.required_score_sideways:
            logger.info(f"⚖️ {symbol}: Score {signal['score']:.0f} < {self.required_score_sideways} (SIDEWAYS threshold)")
            return False

        # ✅ NOVO: Ajuste extra cruzando PERFIL do símbolo x tendência do BTC
        if not self._validate_symbol_profile_vs_trend(symbol, direction, trend):
            return False
        
        # LONG conditions
        if direction == 'LONG':
            if trend == 'STRONG_DOWNTREND':
                logger.warning(f"❌ {symbol} LONG bloqueado: BTC em STRONG_DOWNTREND")
                return False
            
            if trend == 'DOWNTREND' and signal['score'] < 80:
                logger.warning(f"❌ {symbol} LONG bloqueado: BTC em DOWNTREND (score < 80)")
                return False
        
        # SHORT conditions
        elif direction == 'SHORT':
            if trend == 'STRONG_UPTREND':
                logger.warning(f"❌ {symbol} SHORT bloqueado: BTC em STRONG_UPTREND")
                return False
            
            if trend == 'UPTREND' and signal['score'] < 80:
                logger.warning(f"❌ {symbol} SHORT bloqueado: BTC em UPTREND (score < 80)")
                return False
        
        return True
    
    async def _validate_not_pump_and_dump(self, symbol: str) -> bool:
        """
        ✅ NOVO: Detecta pump & dump schemes
        Rejeita moedas com +30% em < 2h sem volume sustentado
        """
        
        try:
            # Obter klines das últimas 2h
            tf_hours = max(self.pump_timeframe_hours, getattr(self, "dump_timeframe_hours", self.pump_timeframe_hours))
            klines = await binance_client.get_klines(
                symbol=symbol,
                interval='1h',
                limit=tf_hours + 1
            )
            
            if len(klines) < 3:
                return True
            
            # Calcular mudança de preço
            price_start = float(klines[0][1])  # Open da primeira vela
            price_current = float(klines[-1][4])  # Close da última vela
            
            price_change_pct = ((price_current - price_start) / price_start) * 100

            # Calcular volume atual vs média
            volumes = [float(k[5]) for k in klines]
            avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 0.0
            current_volume = volumes[-1] if volumes else 0.0
            volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0.0
            
            # Pump: alta acentuada sem volume sustentado
            if price_change_pct >= self.pump_threshold:
                if volume_ratio < self.min_sustained_volume:
                    logger.warning(
                        f"🚫 {symbol}: Pump detectado!\n"
                        f"  Mudança: {price_change_pct:+.2f}% em {self.pump_timeframe_hours}h\n"
                        f"  Volume ratio: {volume_ratio:.2f}x (< {self.min_sustained_volume}x)"
                    )
                    return False

            # Dump: queda acentuada sem volume sustentado
            if price_change_pct <= -self.dump_threshold:
                if volume_ratio < self.min_sustained_volume_dump:
                    logger.warning(
                        f"🚫 {symbol}: Dump detectado!\n"
                        f"  Mudança: {price_change_pct:+.2f}% em {self.dump_timeframe_hours}h\n"
                        f"  Volume ratio: {volume_ratio:.2f}x (< {self.min_sustained_volume_dump}x)"
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar pump & dump para {symbol}: {e}")
            return True  # Em caso de erro, permitir
    
    def _get_weekend_adjustment(self) -> float:
        """
        ✅ NOVO: Retorna ajuste para finais de semana
        """
        
        now = datetime.now()
        
        # Sábado (5) ou Domingo (6)
        if now.weekday() in [5, 6]:
            logger.info(f"📅 Final de semana detectado - Reduzindo agressividade {self.weekend_multiplier*100:.0f}%")
            return self.weekend_multiplier
        
        return 1.0

    def _get_symbol_profile(self, symbol: str) -> Dict:
        """Perfil simples por símbolo (ROI e win rate) com base em trades fechados."""
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
                    "symbol": symbol,
                    "trades": 0,
                    "roi_pct": 0.0,
                    "win_rate": 0.0,
                }

            roi_usdt = sum(float(t.pnl or 0.0) for t in trades)
            notional_sum = sum(
                float((t.entry_price or 0.0) * (t.quantity or 0.0)) for t in trades
            )
            roi_pct = (roi_usdt / notional_sum * 100.0) if notional_sum > 0 else 0.0
            wins = [t for t in trades if (t.pnl or 0.0) > 0]
            win_rate = len(wins) / total if total > 0 else 0.0

            return {
                "symbol": symbol,
                "trades": total,
                "roi_pct": roi_pct,
                "win_rate": win_rate,
            }
        except Exception as e:
            logger.error(f"Erro ao obter perfil do símbolo {symbol}: {e}")
            return {
                "symbol": symbol,
                "trades": 0,
                "roi_pct": 0.0,
                "win_rate": 0.0,
            }
        finally:
            db.close()

    def _validate_symbol_profile_vs_trend(self, symbol: str, direction: str, trend: str) -> bool:
        """Reforça filtros cruzando perfil do símbolo x tendência do BTC.

        - Símbolos com ROI ruim e win rate baixo são bloqueados de operar contra a tendência.
        """
        profile = self._get_symbol_profile(symbol)
        trades = profile.get("trades", 0)
        if trades < 15:
            # Pouco histórico: não bloquear ainda
            return True

        roi_pct = float(profile.get("roi_pct", 0.0))
        win_rate = float(profile.get("win_rate", 0.0))

        # Perfil ruim: ROI muito negativo ou win rate baixo
        is_bad = (roi_pct <= -5.0) or (win_rate < 0.45)
        if not is_bad:
            return True

        # Regras de bloqueio adicionais
        if direction == 'LONG' and trend in ('DOWNTREND', 'STRONG_DOWNTREND'):
            logger.warning(
                f"🚫 {symbol} LONG bloqueado por perfil ruim em {trend}: "
                f"ROI={roi_pct:.1f}%, WR={win_rate*100:.1f}% (trades={trades})"
            )
            return False

        if direction == 'SHORT' and trend in ('UPTREND', 'STRONG_UPTREND'):
            logger.warning(
                f"🚫 {symbol} SHORT bloqueado por perfil ruim em {trend}: "
                f"ROI={roi_pct:.1f}%, WR={win_rate*100:.1f}% (trades={trades})"
            )
            return False

        return True


# Instância global
market_filter = MarketFilter()
