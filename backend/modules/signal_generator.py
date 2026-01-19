"""
Signal Generator - ADAPTIVE INTELLIGENCE VERSION v6.0
🔴 CORREÇÃO CRÍTICA #4: Score mínimo 70 (antes 60)
✅ Volume threshold 50% (antes 30%)
✅ RSI 30/70 clássico (antes 35/65)
✅ Confirmação de trend com múltiplos timeframes
✅ Filtro de momentum (evita reversões falsas)
✅ v4.0: MACD e Bollinger Bands para melhor detecção
✅ v4.0: Detecção de padrões de candlestick (reversão/continuação)
✅ v4.0: Aproveitamento otimizado de quedas e altas extremas
✅ v4.0: Detecção de oversold/overbought mais precisa
✅ v5.0: RSI Divergence Detection (Regular & Hidden)
✅ v5.0: ADX Trend Strength Filter (evita ranging markets)
✅ v5.0: VWAP Integration (institutional-grade support/resistance)
✅ NOVO v6.0: ADAPTIVE INTELLIGENCE ENGINE 🧠
    - Regime-based parameter adaptation
    - ML ensemble scoring (XGBoost + RandomForest + Logistic)
    - Dynamic indicator weighting
    - Anomaly detection & loss pattern filtering
    - PID-controlled risk management
    - Continuous learning from trade outcomes
"""
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from utils.logger import setup_logger
from modules.risk_calculator import risk_calculator
from utils.binance_client import binance_client
from config.settings import get_settings

# Adaptive Intelligence Engine (optional)
try:
    from modules.ml.adaptive_engine import adaptive_engine
    ML_AVAILABLE = True
    logger_ml = setup_logger("signal_generator_ml")
    logger_ml.info("🧠 Adaptive Intelligence Engine AVAILABLE")
except ImportError as e:
    ML_AVAILABLE = False
    logger_ml = None

logger = setup_logger("signal_generator")


class SignalGenerator:
    def __init__(self):
        # Configurações via Settings (presets por ambiente)
        self.settings = get_settings()

        # ✅ FORÇAR MODO PROD (Mesmo em Testnet) para garantir qualidade
        # Usamos os valores de PROD como base, mas permitimos override se explicitamente configurado
        self.min_score = int(getattr(self.settings, "PROD_MIN_SCORE", 70))
        self.volume_threshold = float(getattr(self.settings, "PROD_VOLUME_THRESHOLD", 0.5))
        self.rsi_oversold = int(getattr(self.settings, "PROD_RSI_OVERSOLD", 30))
        self.rsi_overbought = int(getattr(self.settings, "PROD_RSI_OVERBOUGHT", 70))
        self.require_trend_confirmation = bool(getattr(self.settings, "REQUIRE_TREND_CONFIRMATION", True))
        self.min_momentum_threshold = float(getattr(self.settings, "MIN_MOMENTUM_THRESHOLD_PCT", 0.2))

        # Log de aviso se estiver em Testnet
        if self.settings.BINANCE_TESTNET:
            logger.warning("⚠️ RODANDO EM TESTNET COM SETTINGS DE PRODUÇÃO (High Quality Mode) ⚠️")

        self.max_leverage = 20
        self.min_leverage = 3

        # Stop loss e take profit
        self.atr_multiplier = 2.0  # Stop loss 2.0x ATR
        self.tp_multiplier = 4.0  # Take profit 4.0x ATR

        # 🧠 Adaptive Intelligence Engine
        self.ml_enabled = ML_AVAILABLE and getattr(self.settings, "ML_ENABLED", True)
        self.adaptive_engine = adaptive_engine if self.ml_enabled else None

        version = "v6.0 (ADAPTIVE INTELLIGENCE)" if self.ml_enabled else "v5.0 (TRADITIONAL)"
        logger.info(f"✅ Signal Generator {version} inicializado")
        logger.info(f"🎯 Score mínimo: {self.min_score}")
        logger.info(f"📊 Volume threshold: {self.volume_threshold*100:.0f}%")
        logger.info(f"📈 RSI: {self.rsi_oversold}/{self.rsi_overbought}")
        logger.info(f"🔍 Confirmação de trend: {'✅ ATIVA' if self.require_trend_confirmation else '❌'}")
        smart_reversal = getattr(self.settings, 'SMART_REVERSAL_ENABLED', True)
        smart_rsi = getattr(self.settings, 'SMART_REVERSAL_RSI_THRESHOLD', 72)
        logger.info(f"🔄 Smart Reversal: {'✅ ATIVO (RSI>' + str(smart_rsi) + ')' if smart_reversal else '❌'}")
        logger.info(f"📊 Indicadores avançados: MACD, Bollinger Bands, Padrões de Candlestick")

        if self.ml_enabled:
            logger.info("🧠 ML Mode: ENABLED")
            logger.info("   - Regime-based adaptation")
            logger.info("   - Ensemble ML scoring")
            logger.info("   - Anomaly filtering")
            logger.info("   - Continuous learning")
    
    def reload_settings(self):
        """Recarrega configurações dinamicamente"""
        from config.settings import get_settings
        self.settings = get_settings()

        # Atualizar atributos derivados
        self.min_score = int(getattr(self.settings, "PROD_MIN_SCORE", 70))
        self.volume_threshold = float(getattr(self.settings, "PROD_VOLUME_THRESHOLD", 0.5))
        self.rsi_oversold = int(getattr(self.settings, "PROD_RSI_OVERSOLD", 30))
        self.rsi_overbought = int(getattr(self.settings, "PROD_RSI_OVERBOUGHT", 70))

        logger.info(f"🔄 Signal Generator settings reloaded (Min Score: {self.min_score}, Vol Thresh: {self.volume_threshold})")

    async def _apply_adaptive_config(self):
        """
        Aplica configurações adaptativas do ML engine
        """
        if not self.ml_enabled:
            return

        try:
            # Get adaptive config
            config = await self.adaptive_engine.get_adaptive_config()

            # Apply dynamic parameters
            self.min_score = config.get('min_score', self.min_score)
            self.rsi_oversold = config.get('rsi_oversold', self.rsi_oversold)
            self.rsi_overbought = config.get('rsi_overbought', self.rsi_overbought)
            self.volume_threshold = config.get('volume_threshold_pct', 50.0) / 100.0
            self.atr_multiplier = config.get('stop_loss_atr_mult', self.atr_multiplier)

            if logger_ml:
                logger_ml.info(f"🎯 Adaptive config applied: "
                             f"MinScore={self.min_score}, "
                             f"RSI={self.rsi_oversold}/{self.rsi_overbought}, "
                             f"Regime={config.get('regime_name', 'unknown')}")

        except Exception as e:
            logger.error(f"Error applying adaptive config: {e}")

    async def _enhance_signal_with_ml(self, symbol: str, base_signal: Dict) -> Optional[Dict]:
        """
        Enhance traditional signal with ML evaluation

        Args:
            symbol: Trading symbol
            base_signal: Traditional signal analysis

        Returns:
            Enhanced signal with ML scores or None if rejected
        """
        if not self.ml_enabled or not base_signal:
            return base_signal

        try:
            # Evaluate with ML
            ml_evaluation = await self.adaptive_engine.evaluate_trade_opportunity(
                symbol,
                base_signal
            )

            # If ML rejects, return None
            if ml_evaluation['action'] == 'SKIP':
                if logger_ml:
                    logger_ml.info(f"❌ {symbol}: {ml_evaluation['reason']}")
                return None

            # Enhance signal with ML data
            enhanced_signal = base_signal.copy()
            enhanced_signal.update({
                'ml_score': ml_evaluation['ml_score'],
                'traditional_score': ml_evaluation['traditional_score'],
                'final_score': ml_evaluation['final_score'],
                'ml_regime': ml_evaluation['regime'],
                'ml_top_indicators': ml_evaluation.get('top_indicators', []),
                'score': ml_evaluation['final_score'],  # Override score with ML-enhanced version
            })

            if logger_ml:
                logger_ml.info(f"✅ {symbol}: ML={ml_evaluation['ml_score']:.1f}, "
                             f"Trad={ml_evaluation['traditional_score']:.1f}, "
                             f"Final={ml_evaluation['final_score']:.1f}")

            return enhanced_signal

        except Exception as e:
            logger.error(f"Error enhancing signal with ML: {e}")
            return base_signal  # Fallback to traditional signal

    async def generate_signal(self, scan_results: List[Dict]) -> List[Dict]:
        """
        Gera sinais de alta qualidade com filtros rigorosos
        Com suporte para Adaptive Intelligence Engine (v6.0)
        """

        if not scan_results:
            return []

        # Apply adaptive configuration if ML is enabled
        await self._apply_adaptive_config()

        signals = []

        for symbol_data in scan_results:
            try:
                # Traditional analysis
                signal = await self._analyze_symbol(symbol_data)

                if signal and signal['score'] >= self.min_score:
                    # Enhance with ML if enabled
                    if self.ml_enabled:
                        symbol = symbol_data.get('symbol', '')
                        enhanced_signal = await self._enhance_signal_with_ml(symbol, signal)

                        if enhanced_signal:  # ML may reject the signal
                            signals.append(enhanced_signal)
                    else:
                        signals.append(signal)

            except Exception as e:
                logger.error(f"Erro ao analisar {symbol_data.get('symbol', 'Unknown')}: {e}")

        # Ordenar por score (maior primeiro)
        signals.sort(key=lambda x: x['score'], reverse=True)

        if signals:
            ml_suffix = " (ML-enhanced)" if self.ml_enabled else ""
            logger.info(
                f"✅ {len(signals)} sinal(is) gerado(s){ml_suffix}\n"
                f"  Top 3 scores: {[s['score'] for s in signals[:3]]}"
            )

        return signals
    
    async def generate_signals_batch(self, limit: int = 30, min_score: int = 55) -> List[Dict]:
        """
        Gera múltiplos sinais a partir do scan de mercado.
        Compatível com rota /api/trading/execute-batch.
        """
        try:
            # Import local para evitar ciclos
            from modules.market_scanner import market_scanner
            scan_results = await market_scanner.scan_market()
            if not scan_results:
                return []
            signals = await self.generate_signal(scan_results)
            filtered = [s for s in signals if s.get('score', 0) >= min_score]
            return filtered[:limit]
        except Exception as e:
            logger.error(f"Erro em generate_signals_batch: {e}")
            return []
    
    async def generate_signal_for_symbol(self, symbol: str, risk_profile: str = "moderate") -> Optional[Dict]:
        """
        Gera um único sinal para um símbolo específico usando o mesmo pipeline do scan.
        """
        try:
            from modules.market_scanner import market_scanner  # import local para evitar ciclos
            analysis = await market_scanner.analyze_symbol(symbol.upper())
            if not analysis:
                return None
            return await self._analyze_symbol(analysis)
        except Exception as e:
            logger.error(f"Erro em generate_signal_for_symbol({symbol}): {e}")
            return None

    async def _fetch_derivatives(self, symbol: str) -> Dict:
        """
        Coleta métricas de derivativos (funding/mark, open interest e taker ratio).
        Retorna dict com chaves: premium, oi, oi_change, taker.
        """
        try:
            s = self.settings
            period = str(getattr(s, "OI_CHANGE_PERIOD", "5m"))
            lookback = int(getattr(s, "OI_CHANGE_LOOKBACK", 12))
            premium_coro = binance_client.get_premium_index(symbol)
            oi_now_coro = binance_client.get_open_interest(symbol)
            oi_ch_coro = binance_client.get_open_interest_change(symbol, period=period, limit=lookback)
            taker_coro = binance_client.get_taker_long_short_ratio(symbol, period=period, limit=lookback)
            premium, oi_now, oi_change, taker = await asyncio.gather(premium_coro, oi_now_coro, oi_ch_coro, taker_coro)
            return {"premium": premium, "oi": oi_now, "oi_change": oi_change, "taker": taker}
        except Exception as e:
            logger.debug(f"{symbol}: falha ao buscar derivativos ({e})")
            return {}
    
    async def _analyze_symbol(self, symbol_data: Dict) -> Optional[Dict]:
        """
        Analisa um símbolo e gera sinal se critérios forem atendidos
        """
        
        symbol = symbol_data['symbol']
        klines_1h = symbol_data.get('klines_1h', [])
        klines_4h = symbol_data.get('klines_4h', [])
        
        if not klines_1h or not klines_4h:
            return None
        
        # Converter para DataFrame
        df_1h = self._klines_to_dataframe(klines_1h)
        df_4h = self._klines_to_dataframe(klines_4h)
        
        # Calcular indicadores
        df_1h = self._calculate_indicators(df_1h)
        df_4h = self._calculate_indicators(df_4h)
        
        # Obter última linha
        last_1h = df_1h.iloc[-1]
        last_4h = df_4h.iloc[-1]
        
        current_price = last_1h['close']
        # Derivativos (funding/OI/taker): usado para ajustes de score/bloqueios
        der = await self._fetch_derivatives(symbol)
        
        # ================================
        # FILTROS OBRIGATÓRIOS
        # ================================
        
        # 1. Volume
        vol_ma = df_1h['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = (last_1h['volume'] / vol_ma) if (vol_ma and vol_ma > 0) else 1.0
        
        # Filtro de volume (desativável via threshold = 0.0)
        if volume_ratio < self.volume_threshold:
            return None
        
        # 2. EMA Trend
        ema_50 = last_1h['ema_50']
        ema_200 = last_1h['ema_200']
        
        # 3. RSI
        rsi = last_1h['rsi']
        
        # 4. ATR
        atr = last_1h['atr']
        
        if atr == 0 or pd.isna(atr):
            # Definir ATR mínimo para evitar divisão por zero em mercados pouco voláteis de testnet
            atr = max(current_price * 0.001, 1e-6)
        
        # ================================
        # DETECTAR DIREÇÃO
        # ================================
        
        direction = None
        score = 0
        
        # ✅ NOVO v4.0: Detectar padrões de candlestick e indicadores avançados
        candlestick_pattern = self._detect_candlestick_pattern(df_1h)
        macd_signal = self._get_macd_signal(df_1h)
        bb_signal = self._get_bollinger_signal(df_1h)
        
        # ✅ NOVO v5.0: ADX and VWAP signals
        adx = last_1h.get('adx', 0)
        vwap = last_1h.get('vwap', current_price)
        adx_enabled = bool(getattr(self.settings, "ENABLE_ADX_FILTER", True))
        adx_min = float(getattr(self.settings, "ADX_MIN_TREND_STRENGTH", 25))
        
        # ✅ NOVO v5.0: RSI Divergence Detection
        rsi_divergence = self._detect_rsi_divergence(df_1h)
        
        # LONG conditions
        # ✅ CORREÇÃO: RSI < 30 (antes < 35)
        # ✅ NOVO v4.0: Detectar quedas extremas para aproveitar melhor
        is_extreme_dip = rsi < 20 or (rsi < self.rsi_oversold and current_price < ema_200 * 0.95)
        
        if (rsi < self.rsi_oversold) or is_extreme_dip:
            
            direction = 'LONG'
            score = 50  # Base score
            
            # ✅ NOVO v5.0: ADX Filter - Ensure strong trend
            if adx_enabled and adx < adx_min:
                logger.debug(f"{symbol}: ADX {adx:.1f} < {adx_min:.1f} (weak trend), rejeitado")
                return None
            elif adx >= adx_min:
                score += 10  # Bonus for strong trend
            
            # ✅ NOVO v5.0: VWAP positioning (price below VWAP = good buy opportunity)
            if current_price < vwap * 0.99:  # 1% below VWAP
                score += 8
                logger.debug(f"{symbol}: Preço abaixo do VWAP (bom ponto de entrada)")
            
            # ✅ NOVO v5.0: RSI Bullish Divergence (very strong signal)
            if rsi_divergence == 'BULLISH':
                score += 20
                logger.info(f"{symbol}: 🚀 DIVERGÊNCIA BULLISH detectada!")
            elif rsi_divergence == 'HIDDEN_BULLISH':
                score += 15
                logger.info(f"{symbol}: 🚀 DIVERGÊNCIA HIDDEN BULLISH detectada!")
            
            # ✅ NOVO v4.0: Bônus extra para quedas extremas (aproveitar melhor)
            if is_extreme_dip:
                score += 15
                logger.debug(f"{symbol}: 🎯 QUEDA EXTREMA detectada (RSI={rsi:.1f}, abaixo EMA200)")
            
            # ✅ NOVO: Confirmar trend com 4h (Smart Reversal Logic)
            is_reversal_signal = False
            if self.require_trend_confirmation:
                # Permitir Long contra tendência SE for extremo ou divergência
                is_reversal = is_extreme_dip or (rsi_divergence in ['BULLISH', 'HIDDEN_BULLISH']) or rsi < 25
                
                if not await self._confirm_trend_long(df_4h):
                    if is_reversal:
                        logger.info(f"{symbol}: ⚠️ Long contra tendência permitido (Smart Reversal) - RSI={rsi:.1f}, Div={rsi_divergence}")
                        # Penalidade de risco por operar contra tendência
                        score -= 5
                        is_reversal_signal = True
                    else:
                        logger.debug(f"{symbol}: Rejeitado por estar em downtrend no 4h (sem sinal extremo)")
                        return None
                else:
                    score += 10
            
            # ✅ NOVO: Verificar momentum
            momentum_ok, momentum_score = self._check_momentum(df_1h, 'LONG')
            if not momentum_ok:
                return None
            score += momentum_score
            
            # ✅ NOVO v4.0: MACD confirmação
            if macd_signal == 'BULLISH':
                score += 8
            elif macd_signal == 'STRONG_BULLISH':
                score += 15
            
            # ✅ NOVO v4.0: Bollinger Bands (preço próximo da banda inferior = oversold)
            if bb_signal == 'OVERSOLD':
                score += 10
            elif bb_signal == 'EXTREME_OVERSOLD':
                score += 15
            
            # ✅ NOVO v4.0: Padrões de candlestick de reversão
            if candlestick_pattern in ['HAMMER', 'ENGULFING_BULLISH', 'DOJI_BULLISH']:
                score += 12
                logger.debug(f"{symbol}: 📊 Padrão de reversão detectado: {candlestick_pattern}")
            
            # Bônus: Volume muito alto
            if volume_ratio > 1.5:
                score += 10
            
            # Bônus: RSI muito oversold
            if rsi < 25:
                score += 5
            if rsi < 20:
                score += 10  # Bônus extra para RSI extremo
            
            # Bônus: Distância do EMA200 (quanto mais abaixo, melhor oportunidade)
            distance_from_ema200 = ((current_price - ema_200) / ema_200) * 100
            if distance_from_ema200 < -5:  # Mais de 5% abaixo da EMA200
                score += 15  # Grande oportunidade de compra
            elif distance_from_ema200 < -3:
                score += 8
        
        # SHORT conditions
        # ✅ CORREÇÃO: RSI > 70 (antes > 65)
        # ✅ NOVO v4.0: Detectar altas extremas para aproveitar melhor
        elif (rsi > self.rsi_overbought):
            is_extreme_pump = rsi > 80 or (rsi > self.rsi_overbought and current_price > ema_200 * 1.05)
            
            direction = 'SHORT'
            score = 50  # Base score
            
            # ✅ NOVO v5.0: ADX Filter - Ensure strong trend
            if adx_enabled and adx < adx_min:
                logger.debug(f"{symbol}: ADX {adx:.1f} < {adx_min:.1f} (weak trend), rejeitado")
                return None
            elif adx >= adx_min:
                score += 10  # Bonus for strong trend
            
            # ✅ NOVO v5.0: VWAP positioning (price above VWAP = good sell opportunity)
            if current_price > vwap * 1.01:  # 1% above VWAP
                score += 8
                logger.debug(f"{symbol}: Preço acima do VWAP (bom ponto de entrada SHORT)")
            
            # ✅ NOVO v5.0: RSI Bearish Divergence (very strong signal)
            if rsi_divergence == 'BEARISH':
                score += 20
                logger.info(f"{symbol}: 🔻 DIVERGÊNCIA BEARISH detectada!")
            elif rsi_divergence == 'HIDDEN_BEARISH':
                score += 15
                logger.info(f"{symbol}: 🔻 DIVERGÊNCIA HIDDEN BEARISH detectada!")
            
            # ✅ NOVO v4.0: Bônus extra para altas extremas (aproveitar melhor)
            if is_extreme_pump:
                score += 15
                logger.debug(f"{symbol}: 🎯 ALTA EXTREMA detectada (RSI={rsi:.1f}, acima EMA200)")
            
            # ✅ NOVO: Confirmar trend com 4h (Smart Reversal Logic)
            is_reversal_signal = False
            smart_reversal_enabled = getattr(self.settings, 'SMART_REVERSAL_ENABLED', True)
            smart_reversal_rsi = getattr(self.settings, 'SMART_REVERSAL_RSI_THRESHOLD', 72)
            if self.require_trend_confirmation:
                # Permitir Short contra tendência SE for extremo ou divergência (Smart Reversal mais agressivo)
                is_reversal = is_extreme_pump or (rsi_divergence in ['BEARISH', 'HIDDEN_BEARISH']) or (smart_reversal_enabled and rsi > smart_reversal_rsi)
                
                if not await self._confirm_trend_short(df_4h):
                    if is_reversal:
                        logger.info(f"{symbol}: ⚠️ Short contra tendência permitido (Smart Reversal) - RSI={rsi:.1f}, Div={rsi_divergence}")
                        # Penalidade de risco por operar contra tendência
                        score -= 5 
                        is_reversal_signal = True
                    else:
                        logger.debug(f"{symbol}: Rejeitado por estar em uptrend no 4h (sem sinal extremo)")
                        return None
                else:
                    score += 10
            
            # ✅ NOVO: Verificar momentum
            momentum_ok, momentum_score = self._check_momentum(df_1h, 'SHORT')
            if not momentum_ok:
                return None
            score += momentum_score
            
            # ✅ NOVO v4.0: MACD confirmação
            if macd_signal == 'BEARISH':
                score += 8
            elif macd_signal == 'STRONG_BEARISH':
                score += 15
            
            # ✅ NOVO v4.0: Bollinger Bands (preço próximo da banda superior = overbought)
            if bb_signal == 'OVERBOUGHT':
                score += 10
            elif bb_signal == 'EXTREME_OVERBOUGHT':
                score += 15
            
            # ✅ NOVO v4.0: Padrões de candlestick de reversão
            if candlestick_pattern in ['SHOOTING_STAR', 'ENGULFING_BEARISH', 'DOJI_BEARISH']:
                score += 12
                logger.debug(f"{symbol}: 📊 Padrão de reversão detectado: {candlestick_pattern}")
            
            # Bônus: Volume muito alto
            if volume_ratio > 1.5:
                score += 10
            
            # Bônus: RSI muito overbought
            if rsi > 75:
                score += 5
            if rsi > 80:
                score += 10  # Bônus extra para RSI extremo
            
            # Bônus: Distância do EMA200 (quanto mais acima, melhor oportunidade)
            distance_from_ema200 = ((ema_200 - current_price) / ema_200) * 100
            if distance_from_ema200 < -5:  # Preço mais de 5% acima da EMA200
                score += 15  # Grande oportunidade de venda
            elif distance_from_ema200 < -3:
                score += 8
        
        if not direction:
            return None

        # Derivatives-aware: funding/OI/taker ajustes e bloqueio próximo ao funding adverso
        mins_to_funding = None
        try:
            if getattr(self.settings, "ENABLE_FUNDING_AWARE", True):
                fr = float((der.get("premium") or {}).get("lastFundingRate", 0.0))
                nft = int((der.get("premium") or {}).get("nextFundingTime", 0) or 0)
                from datetime import datetime as _dt
                if nft and nft > 0:
                    mins_to_funding = max(0, int((nft - int(_dt.now().timestamp() * 1000)) / 60000))
                # Janela de bloqueio próximo ao funding quando adverso ao lado
                adverse_th = float(getattr(self.settings, "FUNDING_ADVERSE_THRESHOLD", 0.0003))
                adverse_long = fr > adverse_th
                adverse_short = fr < -adverse_th
                near_window = (mins_to_funding is not None) and (mins_to_funding <= int(getattr(self.settings, "FUNDING_BLOCK_WINDOW_MINUTES", 20)))
                if near_window and ((direction == 'LONG' and adverse_long) or (direction == 'SHORT' and adverse_short)):
                    logger.debug(f"{symbol}: bloqueado por funding adverso (fr={fr:.5f}, mins={mins_to_funding})")
                    return None

                # Ajustes de score por Open Interest e taker imbalance
                oi_ch = float((der.get("oi_change") or {}).get("pct_change", 0.0))
                ratio = float((der.get("taker") or {}).get("buySellRatio", 1.0))
                oi_min = float(getattr(self.settings, "OI_CHANGE_MIN_ABS", 0.5))
                long_min = float(getattr(self.settings, "TAKER_RATIO_LONG_MIN", 1.02))
                short_max = float(getattr(self.settings, "TAKER_RATIO_SHORT_MAX", 0.98))

                if direction == 'LONG':
                    if ratio >= long_min:
                        score += 5
                    else:
                        score -= 3
                    if oi_ch >= oi_min:
                        score += 3
                    elif oi_ch <= -oi_min:
                        score -= 3
                else:  # SHORT
                    if ratio <= short_max:
                        score += 5
                    else:
                        score -= 3
                    if oi_ch <= -oi_min:
                        score += 3
                    elif oi_ch >= oi_min:
                        score -= 3
        except Exception as _e:
            logger.debug(f"{symbol}: derivativos indisponíveis para ajuste ({_e})")
        
        # ================================
        # CALCULAR STOP LOSS E TAKE PROFIT
        # ================================
        
        # ✅ NOVO v5.0: Stop Loss via Chandelier Exit (método dedicado)
        # Passamos um DF mínimo com ATR para o método
        df_sl = pd.DataFrame({'atr': [atr]})
        stop_loss = self._calculate_stop_loss(df_sl, direction, current_price)

        if direction == 'LONG':
            take_profit_1 = current_price + (atr * self.tp_multiplier)
            take_profit_2 = current_price + (atr * self.tp_multiplier * 1.5)
            take_profit_3 = current_price + (atr * self.tp_multiplier * 2.0)
        else:  # SHORT
            take_profit_1 = current_price - (atr * self.tp_multiplier)
            take_profit_2 = current_price - (atr * self.tp_multiplier * 1.5)
            take_profit_3 = current_price - (atr * self.tp_multiplier * 2.0)
        
        # ✅ NOVO (P3): Regime de mercado e R:R dinâmico
        # Regime simples: usa ATR% e inclinação da EMA200 (últimos ~5 candles 1h)
        atr_pct_full = (atr / current_price * 100) if current_price else 0.0
        try:
            if len(df_1h) >= 6:
                ema200_now = df_1h['ema_200'].iloc[-1]
                ema200_prev5 = df_1h['ema_200'].iloc[-6]
                ema200_slope_pct = ((ema200_now - ema200_prev5) / ema200_prev5 * 100) if ema200_prev5 else 0.0
            else:
                ema200_slope_pct = 0.0
        except Exception:
            ema200_slope_pct = 0.0

        trending = (abs(ema200_slope_pct) > 0.2 and 0.3 <= atr_pct_full <= 3.0)
        rr_min_trend = float(getattr(self.settings, "RR_MIN_TREND", 1.2))
        rr_min_range = float(getattr(self.settings, "RR_MIN_RANGE", 1.6))
        rr_min = rr_min_trend if trending else rr_min_range

        # ✅ Validar R:R mínimo por regime
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit_1 - current_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        if risk_reward_ratio < rr_min:
            logger.debug(f"{symbol}: R:R {risk_reward_ratio:.2f} < {rr_min:.2f} (regime={'trend' if trending else 'range'}), rejeitado")
            return None
        
        # Bônus por R:R excelente e por regime 'trending'
        if risk_reward_ratio > 3.0:
            score += 5
        if trending:
            score += 5
        
        # ================================
        # CALCULAR LEVERAGE DINÂMICO
        # ================================
        
        leverage = self._calculate_leverage(volume_ratio, rsi, risk_reward_ratio)

        # ================================
        # PROFIT OPTIMIZATION - Market Intelligence Integration (v6.0)
        # ================================

        market_sentiment_score = 0
        top_trader_ratio = None
        liquidation_proximity = None

        if getattr(self.settings, "ENABLE_MARKET_INTELLIGENCE", True):
            try:
                from modules.market_intelligence import market_intelligence

                # Get market sentiment (includes all advanced data)
                mi_data = await market_intelligence.get_market_sentiment_score(symbol)
                sentiment_score = mi_data.get('sentiment_score', 0)
                market_sentiment_score = sentiment_score

                # Get individual components for signal enrichment
                top_trader_data = await market_intelligence.get_top_trader_ratios(symbol)
                top_trader_ratio = top_trader_data.get('account_ratio', 1.0)

                liq_data = await market_intelligence.detect_liquidation_zones(symbol)
                liq_proximity = liq_data.get('current_proximity', {})
                liquidation_proximity = liq_proximity.get('distance_type', 'NEUTRAL')

                # Apply market intelligence adjustments to score
                if direction == 'LONG':
                    if sentiment_score > 20:
                        score += 20
                        logger.info(f"{symbol}: Institutional buying confirmed (+20) - {top_trader_data.get('sentiment')}")
                    elif sentiment_score > 10:
                        score += 10
                    elif sentiment_score < -20:
                        logger.warning(f"{symbol}: Strong institutional selling - BLOCKING")
                        return None
                    elif sentiment_score < -10:
                        score -= 10

                    # Liquidation zone bonus
                    if liquidation_proximity and liq_proximity.get('distance_pct', 100) < 2:
                        score += 15
                        logger.info(f"{symbol}: Near bullish liquidation zone (+15)")

                elif direction == 'SHORT':
                    if sentiment_score < -20:
                        score += 20
                        logger.info(f"{symbol}: Institutional selling confirmed (+20) - {top_trader_data.get('sentiment')}")
                    elif sentiment_score < -10:
                        score += 10
                    elif sentiment_score > 20:
                        logger.warning(f"{symbol}: Strong institutional buying - BLOCKING")
                        return None
                    elif sentiment_score > 10:
                        score -= 10

                    # Liquidation zone bonus
                    if liquidation_proximity and liq_proximity.get('distance_pct', 100) < 2:
                        score += 15
                        logger.info(f"{symbol}: Near bearish liquidation zone (+15)")

                logger.debug(
                    f"{symbol}: Market Intelligence - Sentiment {sentiment_score:+d}, "
                    f"Top Traders {top_trader_ratio:.2f}x, Final Score {min(score, 100):.0f}"
                )

            except Exception as e:
                logger.debug(f"{symbol}: Market Intelligence unavailable ({e})")

        # ================================
        # CONSTRUIR SINAL
        # ================================
        
        signal = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'take_profit_3': take_profit_3,
            'leverage': leverage,
            'score': min(score, 100),  # Cap em 100
            'rsi': rsi,
            'volume_ratio': volume_ratio,
            'atr': atr,
            'risk_reward_ratio': risk_reward_ratio,
            'funding_rate': float((der.get('premium') or {}).get('lastFundingRate', 0.0)) if 'der' in locals() else 0.0,
            'minutes_to_funding': mins_to_funding if 'mins_to_funding' in locals() and mins_to_funding is not None else 0,
            'oi_change_pct': float((der.get('oi_change') or {}).get('pct_change', 0.0)) if 'der' in locals() else 0.0,
            'taker_ratio': float((der.get('taker') or {}).get('buySellRatio', 1.0)) if 'der' in locals() else 1.0,
            # ✅ PROFIT OPTIMIZATION - Market Intelligence Fields
            'market_sentiment_score': market_sentiment_score,
            'top_trader_ratio': top_trader_ratio,
            'liquidation_proximity': liquidation_proximity,
            'is_reversal': is_reversal_signal if 'is_reversal_signal' in locals() else False,
            'timestamp': datetime.now()
        }
        
        logger.info(
            f"🎯 Sinal gerado: {symbol} {direction}\n"
            f"  Score: {signal['score']:.0f}\n"
            f"  Entry: {current_price:.4f}\n"
            f"  Stop: {stop_loss:.4f} ({((stop_loss-current_price)/current_price*100):.2f}%)\n"
            f"  TP1: {take_profit_1:.4f} ({((take_profit_1-current_price)/current_price*100):.2f}%)\n"
            f"  R:R: {risk_reward_ratio:.2f}:1\n"
            f"  Leverage: {leverage}x\n"
            f"  RSI: {rsi:.1f} | Volume: {volume_ratio:.2f}x"
        )
        
        return signal
    
    async def _confirm_trend_long(self, df_4h: pd.DataFrame) -> bool:
        """
        ✅ NOVO: Confirma trend LONG no timeframe 4h
        """
        
        last = df_4h.iloc[-1]
        prev = df_4h.iloc[-2]
        
        # 4h deve estar em uptrend
        if last['ema_50'] <= last['ema_200']:
            return False
        
        # EMA50 deve estar subindo
        if last['ema_50'] <= prev['ema_50']:
            return False
        
        # Preço deve estar acima de EMA50
        if last['close'] < last['ema_50']:
            return False
        
        return True
    
    async def _confirm_trend_short(self, df_4h: pd.DataFrame) -> bool:
        """
        ✅ NOVO: Confirma trend SHORT no timeframe 4h
        """
        
        last = df_4h.iloc[-1]
        prev = df_4h.iloc[-2]
        
        # 4h deve estar em downtrend
        if last['ema_50'] >= last['ema_200']:
            return False
        
        # EMA50 deve estar caindo
        if last['ema_50'] >= prev['ema_50']:
            return False
        
        # Preço deve estar abaixo de EMA50
        if last['close'] > last['ema_50']:
            return False
        
        return True
    
    def _check_momentum(self, df: pd.DataFrame, direction: str) -> tuple[bool, int]:
        """
        ✅ NOVO: Verifica momentum para evitar reversões falsas
        """
        
        # Calcular momentum dos últimos 3 candles
        closes = df['close'].tail(4).values
        
        if len(closes) < 4:
            return False, 0
        
        momentum_pct = ((closes[-1] - closes[-3]) / closes[-3]) * 100
        
        if direction == 'LONG':
            # Para LONG, precisa ter momentum positivo
            if momentum_pct < self.min_momentum_threshold:
                return False, 0
            
            # Bônus por momentum forte
            if momentum_pct > 1.0:
                return True, 10
            elif momentum_pct > 0.5:
                return True, 5
            else:
                return True, 0
        
        else:  # SHORT
            # Para SHORT, precisa ter momentum negativo
            if momentum_pct > -self.min_momentum_threshold:
                return False, 0
            
            # Bônus por momentum forte
            if momentum_pct < -1.0:
                return True, 10
            elif momentum_pct < -0.5:
                return True, 5
            else:
                return True, 0
    
    def _calculate_leverage(self, volume_ratio: float, rsi: float, risk_reward: float) -> int:
        """
        Calcula leverage dinâmico (3x → 20x) considerando:
        - volume_ratio: liquidez/momento
        - r:r (risk_reward): qualidade do setup
        - rsi: extremos aumentam convicção
        Regras conservadoras em baixa qualidade, agressivas em alta qualidade.
        """
        # Base adaptativa
        leverage = 5
        
        # Condições desfavoráveis → mínimo
        if volume_ratio < 0.8 or risk_reward < 1.5:
            return max(self.min_leverage, 3)
        
        # Liquidez/momento
        if volume_ratio >= 3.0:
            leverage += 6
        elif volume_ratio >= 2.0:
            leverage += 4
        elif volume_ratio >= 1.2:
            leverage += 2
        
        # Qualidade do setup (R:R)
        if risk_reward >= 4.0:
            leverage += 5
        elif risk_reward >= 3.0:
            leverage += 3
        elif risk_reward >= 2.0:
            leverage += 1
        
        # RSI extremos
        if rsi <= 20 or rsi >= 80:
            leverage += 2
        elif rsi <= 25 or rsi >= 75:
            leverage += 1
        
        # Clamp final
        leverage = int(max(self.min_leverage, min(leverage, self.max_leverage)))
        return leverage
    
    def _klines_to_dataframe(self, klines: List) -> pd.DataFrame:
        """Converte klines para DataFrame"""
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Converter para float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """✅ NOVO v5.0: Calcula indicadores técnicos incluindo MACD, Bollinger Bands, ADX e VWAP"""
        
        # EMAs
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # ✅ NOVO v4.0: MACD (Moving Average Convergence Divergence)
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # ✅ NOVO v4.0: Bollinger Bands
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = sma_20 + (std_20 * 2)
        df['bb_lower'] = sma_20 - (std_20 * 2)
        df['bb_middle'] = sma_20
        
        # ✅ NOVO v5.0: ADX (Average Directional Index) - Trend Strength
        # Calculate +DM and -DM
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = -df['low'].diff()
        
        df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
        df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
        
        # Smooth DM and TR
        period = 14
        df['plus_dm_smooth'] = df['plus_dm'].rolling(window=period).sum()
        df['minus_dm_smooth'] = df['minus_dm'].rolling(window=period).sum()
        df['atr_smooth'] = df['atr'] * period
        
        # Calculate +DI and -DI
        df['plus_di'] = 100 * (df['plus_dm_smooth'] / df['atr_smooth'])
        df['minus_di'] = 100 * (df['minus_dm_smooth'] / df['atr_smooth'])
        
        # Calculate DX and ADX
        df['dx'] = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        # ✅ NOVO v5.0: VWAP (Volume Weighted Average Price)
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (df['typical_price'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Clean up temporary columns
        df.drop(['high_diff', 'low_diff', 'plus_dm', 'minus_dm', 'plus_dm_smooth', 
                 'minus_dm_smooth', 'atr_smooth', 'plus_di', 'minus_di', 'dx', 'typical_price'], 
                axis=1, inplace=True, errors='ignore')
        
        return df
    
    def _get_macd_signal(self, df: pd.DataFrame) -> str:
        """
        ✅ NOVO v4.0: Analisa sinal MACD
        Retorna: 'BULLISH', 'STRONG_BULLISH', 'BEARISH', 'STRONG_BEARISH', 'NEUTRAL'
        """
        if len(df) < 2:
            return 'NEUTRAL'
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        macd = last.get('macd', 0)
        signal = last.get('macd_signal', 0)
        histogram = last.get('macd_histogram', 0)
        prev_histogram = prev.get('macd_histogram', 0)
        
        # MACD cruzou acima do sinal (bullish)
        if macd > signal and histogram > 0:
            if histogram > prev_histogram and histogram > 0.5:
                return 'STRONG_BULLISH'
            return 'BULLISH'
        
        # MACD cruzou abaixo do sinal (bearish)
        elif macd < signal and histogram < 0:
            if histogram < prev_histogram and histogram < -0.5:
                return 'STRONG_BEARISH'
            return 'BEARISH'
        
        return 'NEUTRAL'
    
    def _get_bollinger_signal(self, df: pd.DataFrame) -> str:
        """
        ✅ NOVO v4.0: Analisa posição do preço em relação às Bollinger Bands
        Retorna: 'OVERSOLD', 'EXTREME_OVERSOLD', 'OVERBOUGHT', 'EXTREME_OVERBOUGHT', 'NORMAL'
        """
        if len(df) < 1:
            return 'NORMAL'
        
        last = df.iloc[-1]
        close = last.get('close', 0)
        bb_upper = last.get('bb_upper', 0)
        bb_lower = last.get('bb_lower', 0)
        bb_middle = last.get('bb_middle', 0)
        
        if bb_upper == 0 or bb_lower == 0:
            return 'NORMAL'
        
        # Calcular distância das bandas
        distance_from_upper = ((close - bb_upper) / bb_upper) * 100
        distance_from_lower = ((bb_lower - close) / bb_lower) * 100
        
        # Preço muito próximo ou abaixo da banda inferior (oversold)
        if close <= bb_lower:
            return 'EXTREME_OVERSOLD'
        elif distance_from_lower < 1.0:  # Dentro de 1% da banda inferior
            return 'OVERSOLD'
        
        # Preço muito próximo ou acima da banda superior (overbought)
        elif close >= bb_upper:
            return 'EXTREME_OVERBOUGHT'
        elif distance_from_upper < 1.0:  # Dentro de 1% da banda superior
            return 'OVERBOUGHT'
        
        return 'NORMAL'
    
    def _detect_candlestick_pattern(self, df: pd.DataFrame) -> Optional[str]:
        """
        ✅ NOVO v5.0: Detecta padrões de candlestick de reversão/continuação COM CONFIRMAÇÃO DE VOLUME
        Retorna: 'HAMMER', 'SHOOTING_STAR', 'ENGULFING_BULLISH', 'ENGULFING_BEARISH', 
                 'DOJI_BULLISH', 'DOJI_BEARISH', None
        """
        if len(df) < 3:  # Need at least 3 candles for volume comparison
            return None
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        open_price = last.get('open', 0)
        close_price = last.get('close', 0)
        high_price = last.get('high', 0)
        low_price = last.get('low', 0)
        volume = last.get('volume', 0)
        
        prev_open = prev.get('open', 0)
        prev_close = prev.get('close', 0)
        prev_volume = prev.get('volume', 0)
        
        # ✅ NOVO v5.0: Volume confirmation
        # Calculate average volume of last 20 candles
        avg_volume = df['volume'].tail(20).mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Require above-average volume for pattern confirmation (at least 80% of average)
        volume_confirmed = volume_ratio >= 0.8
        
        body = abs(close_price - open_price)
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        total_range = high_price - low_price
        
        if total_range == 0:
            return None
        
        body_ratio = body / total_range
        upper_shadow_ratio = upper_shadow / total_range
        lower_shadow_ratio = lower_shadow / total_range
        
        # Hammer (reversão bullish): corpo pequeno, sombra inferior longa
        if body_ratio < 0.3 and lower_shadow_ratio > 0.6 and upper_shadow_ratio < 0.1:
            if volume_confirmed and volume_ratio > 1.2:  # High volume hammer is stronger
                return 'HAMMER'
            elif volume_confirmed:
                return 'HAMMER'
        
        # Shooting Star (reversão bearish): corpo pequeno, sombra superior longa
        if body_ratio < 0.3 and upper_shadow_ratio > 0.6 and lower_shadow_ratio < 0.1:
            if volume_confirmed and volume_ratio > 1.2:
                return 'SHOOTING_STAR'
            elif volume_confirmed:
                return 'SHOOTING_STAR'
        
        # Engulfing Bullish: candle atual engole o anterior (bullish)
        if (prev_close < prev_open and  # Anterior era bearish
            close_price > open_price and  # Atual é bullish
            open_price < prev_close and  # Abertura abaixo do fechamento anterior
            close_price > prev_open):  # Fechamento acima da abertura anterior
            # ✅ v5.0: Require strong volume for engulfing patterns
            if volume_confirmed and volume_ratio > 1.5:  # Engulfing needs higher volume
                return 'ENGULFING_BULLISH'
        
        # Engulfing Bearish: candle atual engole o anterior (bearish)
        if (prev_close > prev_open and  # Anterior era bullish
            close_price < open_price and  # Atual é bearish
            open_price > prev_close and  # Abertura acima do fechamento anterior
            close_price < prev_open):  # Fechamento abaixo da abertura anterior
            if volume_confirmed and volume_ratio > 1.5:
                return 'ENGULFING_BEARISH'
        
        # Doji (indecisão, mas com viés baseado no contexto)
        if body_ratio < 0.1:  # Corpo muito pequeno
            if volume_confirmed:  # Only consider Doji with volume confirmation
                if close_price > prev_close:
                    return 'DOJI_BULLISH'
                else:
                    return 'DOJI_BEARISH'
        
        return None
    
    def _detect_rsi_divergence(self, df: pd.DataFrame, lookback: int = 14) -> Optional[str]:
        """
        ✅ NOVO v5.0: Detecta divergências entre preço e RSI
        Retorna: 'BULLISH', 'BEARISH', 'HIDDEN_BULLISH', 'HIDDEN_BEARISH', None
        
        Regular Bullish Divergence: Preço faz lower low, RSI faz higher low (reversão de baixa para alta)
        Regular Bearish Divergence: Preço faz higher high, RSI faz lower high (reversão de alta para baixa)
        Hidden Bullish Divergence: Preço faz higher low, RSI faz lower low (continuação de alta)
        Hidden Bearish Divergence: Preço faz lower high, RSI faz higher high (continuação de baixa)
        """
        if len(df) < lookback + 5:
            return None
        
        # Get recent data
        recent_df = df.tail(lookback)
        prices = recent_df['close'].values
        rsi_values = recent_df['rsi'].values
        
        if len(prices) < 5 or len(rsi_values) < 5:
            return None
        
        # Find local extrema (peaks and troughs)
        # Simple approach: compare with neighbors
        price_lows = []
        price_highs = []
        rsi_lows = []
        rsi_highs = []
        
        for i in range(2, len(prices) - 2):
            # Price lows
            if prices[i] < prices[i-1] and prices[i] < prices[i+1] and prices[i] < prices[i-2] and prices[i] < prices[i+2]:
                price_lows.append((i, prices[i]))
            # Price highs
            if prices[i] > prices[i-1] and prices[i] > prices[i+1] and prices[i] > prices[i-2] and prices[i] > prices[i+2]:
                price_highs.append((i, prices[i]))
            # RSI lows
            if rsi_values[i] < rsi_values[i-1] and rsi_values[i] < rsi_values[i+1]:
                rsi_lows.append((i, rsi_values[i]))
            # RSI highs
            if rsi_values[i] > rsi_values[i-1] and rsi_values[i] > rsi_values[i+1]:
                rsi_highs.append((i, rsi_values[i]))
        
        # Need at least 2 points to compare
        # Regular Bullish Divergence: Price lower low + RSI higher low
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            last_price_low = price_lows[-1]
            prev_price_low = price_lows[-2]
            last_rsi_low = rsi_lows[-1]
            prev_rsi_low = rsi_lows[-2]
            
            # Check if indices are reasonably close (within lookback window)
            if abs(last_price_low[0] - last_rsi_low[0]) <= 3:  # Allow 3-candle tolerance
                if last_price_low[1] < prev_price_low[1] and last_rsi_low[1] > prev_rsi_low[1]:
                    # Confirm recent (last point should be in last 1/3 of window)
                    if last_price_low[0] >= len(prices) * 0.66:
                        return 'BULLISH'
        
        # Regular Bearish Divergence: Price higher high + RSI lower high
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            last_price_high = price_highs[-1]
            prev_price_high = price_highs[-2]
            last_rsi_high = rsi_highs[-1]
            prev_rsi_high = rsi_highs[-2]
            
            if abs(last_price_high[0] - last_rsi_high[0]) <= 3:
                if last_price_high[1] > prev_price_high[1] and last_rsi_high[1] < prev_rsi_high[1]:
                    if last_price_high[0] >= len(prices) * 0.66:
                        return 'BEARISH'
        
        # Hidden Bullish Divergence: Price higher low + RSI lower low
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            last_price_low = price_lows[-1]
            prev_price_low = price_lows[-2]
            last_rsi_low = rsi_lows[-1]
            prev_rsi_low = rsi_lows[-2]
            
            if abs(last_price_low[0] - last_rsi_low[0]) <= 3:
                if last_price_low[1] > prev_price_low[1] and last_rsi_low[1] < prev_rsi_low[1]:
                    if last_price_low[0] >= len(prices) * 0.66:
                        return 'HIDDEN_BULLISH'
        
        # Hidden Bearish Divergence: Price lower high + RSI higher high
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            last_price_high = price_highs[-1]
            prev_price_high = price_highs[-2]
            last_rsi_high = rsi_highs[-1]
            prev_rsi_high = rsi_highs[-2]
            
            if abs(last_price_high[0] - last_rsi_high[0]) <= 3:
                if last_price_high[1] < prev_price_high[1] and last_rsi_high[1] > prev_rsi_high[1]:
                    if last_price_high[0] >= len(prices) * 0.66:
                        return 'HIDDEN_BEARISH'
        
        return None


    def _calculate_stop_loss(self, df: pd.DataFrame, direction: str, entry_price: float) -> float:
        """
        Calcula Stop Loss dinâmico baseado em ATR (Chandelier Exit)
        ✅ v6.0: Phase 2 - ATR Dinâmico com limites configuráveis
        """
        try:
            last_row = df.iloc[-1]
            atr = float(last_row['atr'])

            # Melhoria #12: SL ATR Dinâmico com configurações Phase 2
            sl_atr_enabled = getattr(self.settings, "SL_ATR_ENABLED", True)

            if sl_atr_enabled:
                # Usar configurações Phase 2
                atr_multiplier = float(getattr(self.settings, "SL_ATR_MULTIPLIER", 2.0))
                min_distance_pct = float(getattr(self.settings, "SL_ATR_MIN_DISTANCE_PCT", 1.0))
                max_distance_pct = float(getattr(self.settings, "SL_ATR_MAX_DISTANCE_PCT", 8.0))
            else:
                # Fallback para configuração legada
                atr_multiplier = float(getattr(self.settings, "ATR_STOP_LOSS_MULTIPLIER", 3.0))
                min_distance_pct = 1.0
                max_distance_pct = 10.0

            if direction == 'LONG':
                # Chandelier Exit Long: Entry - ATR * Multiplier
                stop_loss = entry_price - (atr * atr_multiplier)

                # Guardrails configuráveis (Phase 2)
                min_stop = entry_price * (1 - max_distance_pct / 100)  # Ex: -8%
                max_stop = entry_price * (1 - min_distance_pct / 100)  # Ex: -1%

                if stop_loss < min_stop:
                    stop_loss = min_stop
                    logger.debug(f"SL ajustado para limite mínimo: {min_distance_pct}% = ${stop_loss:.4f}")
                elif stop_loss > max_stop:
                    stop_loss = max_stop
                    logger.debug(f"SL ajustado para limite máximo: {max_distance_pct}% = ${stop_loss:.4f}")

            else:  # SHORT
                # Chandelier Exit Short: Entry + ATR * Multiplier
                stop_loss = entry_price + (atr * atr_multiplier)

                # Guardrails configuráveis (Phase 2)
                max_stop = entry_price * (1 + max_distance_pct / 100)  # Ex: +8%
                min_stop = entry_price * (1 + min_distance_pct / 100)  # Ex: +1%

                if stop_loss > max_stop:
                    stop_loss = max_stop
                    logger.debug(f"SL ajustado para limite máximo: {max_distance_pct}% = ${stop_loss:.4f}")
                elif stop_loss < min_stop:
                    stop_loss = min_stop
                    logger.debug(f"SL ajustado para limite mínimo: {min_distance_pct}% = ${stop_loss:.4f}")

            sl_distance_pct = abs((stop_loss - entry_price) / entry_price * 100)
            logger.info(f"✅ SL ATR calculado: ${stop_loss:.4f} (distância: {sl_distance_pct:.2f}%, ATR: {atr:.4f}, mult: {atr_multiplier}x)")

            return stop_loss

        except Exception as e:
            logger.error(f"Erro ao calcular stop loss: {e}")
            # Fallback seguro
            return entry_price * 0.95 if direction == 'LONG' else entry_price * 1.05


# Instância global
signal_generator = SignalGenerator()
