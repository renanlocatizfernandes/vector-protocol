"""
Position Monitor - PROFESSIONAL VERSION v4.0
🔴 CORREÇÃO CRÍTICA #1: Cálculo de PNL% corrigido
✅ Trailing stop com threshold realista (+3%)
✅ Take profit parcial dinâmico (baseado em volatilidade)
✅ Circuit breaker por símbolo
✅ Kill switch automático em 15% drawdown
✅ Logs otimizados (sem spam)
✅ NOVO v4.0: TSL adaptativo por ATR (respeitando TSL_* min/max)
✅ NOVO v4.0: Métricas por evento (tempo médio, MAE, MFE)
✅ NOVO v4.0: Dashboard de eventos (trailing/partials/ES/SL)
"""
import asyncio
import time
import json
from typing import Dict, List
from datetime import datetime, timedelta, timezone

from utils.binance_client import binance_client
from utils.logger import setup_logger
from api.database import SessionLocal
from api.models.trades import Trade
from utils.telegram_notifier import telegram_notifier
from utils.helpers import round_step_size
from config.settings import get_settings
from modules.risk_calculator import risk_calculator

logger = setup_logger("position_monitor")


class PositionMonitor:
    def __init__(self):
        self.client = binance_client.client
        self.monitoring = False
        self.monitor_interval = 6  # segundos
        
        # Circuit breaker global
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        self.circuit_breaker_active = False
        
        # Circuit breaker por símbolo
        self.symbol_blacklist = {}  # {symbol: until_timestamp}
        
        # 🔴 CORREÇÃO: Limites de perda mais conservadores
        self.max_loss_per_trade = -8.0  # -8% max por trade (antes -10%)
        self.emergency_stop_loss = -15.0  # -15% fecha imediatamente (antes -20%)
        
        # ✅ NOVO: Trailing stop com threshold realista
        self.trailing_stop_activation = 3.0  # Ativar após +3% lucro (antes 1%)
        self.trailing_stop_distance = 0.5  # 50% do lucro máximo
        
        # ✅ NOVO: Take profit parcial dinâmico
        self.partial_tp_threshold = 5.0  # +5% para parcial (antes 3%)
        
        # ✅ NOVO: Kill switch
        self.initial_balance = 0.0
        self.max_drawdown_pct = 15.0  # Kill switch em 15% drawdown
        
        # Cache de warnings (evita spam)
        self.warning_cache = {}
        self.warning_cache_ttl = 300  # 5 minutos
        
        # ✅ NOVO v4.0: Settings para TSL adaptativo
        self.settings = get_settings()
        
        # ✅ NOVO v4.0: Métricas por evento
        self._metrics = {
            "total_positions_monitored": 0,
            "positions_closed": 0,
            "events": {
                "trailing_stop": 0,
                "partial_tp": 0,
                "emergency_stop": 0,
                "max_loss": 0,
                "take_profit": 0,
                "stop_loss": 0
            },
            "position_stats": {
                "average_hold_time_sec": 0.0,
                "total_hold_time_sec": 0.0,
                "positions_with_mae": 0,
                "positions_with_mfe": 0
            },
            "mae_mfe_data": [],  # Últimas 100 posições para análise
            "event_details": []  # Últimos 100 eventos
        }
        
        # ✅ NOVO v4.0: Tracking de MAE/MFE por posição
        self._position_tracking: Dict[str, Dict] = {}  # {symbol: {entry_time, max_adverse, max_favorable, entry_price}}
        
        logger.info("✅ Position Monitor PROFISSIONAL v4.0 inicializado")
        logger.info(f"🛑 Max Loss por Trade: {self.max_loss_per_trade}%")
        logger.info(f"🚨 Emergency Stop: {self.emergency_stop_loss}%")
        logger.info(f"⚡ Circuit Breaker: {self.max_consecutive_losses} perdas consecutivas")
        logger.info(f"📈 Trailing Stop: Ativa após +{self.trailing_stop_activation}%")
        logger.info(f"💰 Take Profit Parcial: +{self.partial_tp_threshold}%")
        logger.info(f"🔴 Kill Switch: {self.max_drawdown_pct}% drawdown")
        logger.info(f"📊 Métricas por evento: ATIVAS")
    
    def start_monitoring(self):
        """Inicia monitoramento de posições"""
        if self.monitoring:
            logger.warning("Monitor já está ativo")
            return
        
        self.monitoring = True
        logger.info("Iniciando monitoramento de posições...")
        asyncio.create_task(self._monitor_loop())
    
    def stop_monitoring(self):
        """Para monitoramento"""
        self.monitoring = False
        logger.info("Monitoramento parado")
    
    async def _monitor_loop(self):
        """Loop principal de monitoramento"""
        
        await asyncio.sleep(5)
        
        # ✅ NOVO: Obter balance inicial para kill switch
        try:
            info = await binance_client.get_account_balance()
            if info:
                self.initial_balance = float(info.get("total_balance", 0) or 0)
                logger.info(f"💰 Balance inicial: {self.initial_balance:.2f} USDT")
        except Exception as e:
            logger.error(f"Erro ao obter balance inicial (async): {e}")
        
        while self.monitoring:
            try:
                # ✅ NOVO: Verificar kill switch
                if await self._check_kill_switch():
                    logger.error("🔴 KILL SWITCH ATIVADO - Parando trading")
                    self.stop_monitoring()
                    break
                
                # Buscar posições da Binance
                binance_positions = await asyncio.to_thread(self.client.futures_position_information)
                open_positions_binance = [
                    p for p in binance_positions
                    if float(p['positionAmt']) != 0
                ]
                
                if not open_positions_binance:
                    await asyncio.sleep(self.monitor_interval)
                    continue
                
                # Buscar posições do DB
                db = SessionLocal()
                
                try:
                    open_positions_db = db.query(Trade).filter(
                        Trade.status == 'open'
                    ).all()
                    
                    # Auto-sync posições faltantes
                    await self._sync_missing_positions(
                        open_positions_binance,
                        open_positions_db,
                        db
                    )
                    
                    # Atualizar posições do DB novamente após sync
                    open_positions_db = db.query(Trade).filter(
                        Trade.status == 'open'
                    ).all()
                    
                    # Monitorar cada posição
                    logger.info(f"📊 Monitorando {len(open_positions_db)} posição(ões)")
                    
                    for trade in open_positions_db:
                        try:
                            # Buscar dados atualizados da Binance
                            binance_data = next(
                                (p for p in open_positions_binance if p['symbol'] == trade.symbol),
                                None
                            )
                            
                            if not binance_data:
                                # Posição no DB mas não na Binance = fechar no DB
                                self._log_once(
                                    f"warning_{trade.symbol}",
                                    f"⚠️ {trade.symbol} no DB mas não na Binance. Fechando no DB..."
                                )
                                
                                trade.status = 'closed'
                                trade.closed_at = datetime.now()
                                db.commit()
                                continue
                            
                            # Atualizar dados
                            current_price = float(binance_data['markPrice'])
                            unrealized_pnl = float(binance_data['unRealizedProfit'])
                            
                            # 🔴 CORREÇÃO CRÍTICA #1: Cálculo de PNL% com proteção contra entry=0
                            # Usa entry do DB; se 0/None, usa entry da exchange; se ainda não houver, evita divisão por zero
                            effective_entry = float(trade.entry_price or 0) or float(binance_data.get('entryPrice') or 0) or current_price
                            qty = float(trade.quantity or 0)
                            base = effective_entry * qty
                            pnl_percentage = (unrealized_pnl / base) * 100 if base > 0 else 0.0
                            
                            # ✅ NOVO v4.0: Tracking de MAE/MFE
                            self._update_mae_mfe(trade.symbol, current_price, effective_entry, trade.direction)
                            
                            trade.current_price = current_price
                            trade.pnl = unrealized_pnl
                            trade.pnl_percentage = pnl_percentage
                            
                            # Log otimizado (apenas mudanças significativas)
                            if abs(pnl_percentage) > 1.0 or unrealized_pnl != 0:
                                logger.info(
                                    f"{trade.symbol} {trade.direction}: "
                                    f"Entry {trade.entry_price:.4f}, Mark {current_price:.4f}, "
                                    f"P&L {unrealized_pnl:+.2f} USDT ({pnl_percentage:+.2f}%)"
                                )
                            
                            # ✅ Trailing Stop e TP Parcial (se campos existirem)
                            has_trailing_fields = hasattr(trade, 'max_pnl_percentage')
                            has_partial_field = hasattr(trade, 'partial_taken')
                            
                            if has_trailing_fields:
                                if await self._check_trailing_stop(trade, current_price, db):
                                    self._track_event("trailing_stop", trade.symbol, pnl_percentage, current_price)
                                    continue
                            
                            if has_partial_field:
                                if await self._check_partial_take_profit(trade, pnl_percentage, current_price, db):
                                    self._track_event("partial_tp", trade.symbol, pnl_percentage, current_price)
                                    continue
                            
                            # Emergency stop loss (-15%)
                            if pnl_percentage <= self.emergency_stop_loss:
                                logger.error(
                                    f"🚨 EMERGENCY STOP: {trade.symbol} "
                                    f"perda {pnl_percentage:.2f}%"
                                )
                                
                                try:
                                    await telegram_notifier.notify_emergency_stop(trade.symbol, pnl_percentage)
                                except:
                                    pass
                                
                                self._track_event("emergency_stop", trade.symbol, pnl_percentage, current_price)
                                await self._close_position(
                                    trade,
                                    current_price,
                                    reason=f"Emergency Stop ({pnl_percentage:.2f}%)",
                                    db=db
                                )
                                continue
                            
                            # Max loss por trade (-8%)
                            if pnl_percentage <= self.max_loss_per_trade:
                                logger.warning(
                                    f"🛑 MAX LOSS: {trade.symbol} "
                                    f"perda {pnl_percentage:.2f}%"
                                )
                                
                                try:
                                    await telegram_notifier.notify_stop_loss_hit(trade.symbol, trade.entry_price, current_price, trade.pnl, pnl_percentage, reason="Max Loss")
                                except:
                                    pass
                                
                                self._track_event("max_loss", trade.symbol, pnl_percentage, current_price)
                                await self._close_position(
                                    trade,
                                    current_price,
                                    reason=f"Max Loss ({pnl_percentage:.2f}%)",
                                    db=db
                                )
                                
                                # Adicionar ao blacklist
                                await self._add_to_symbol_blacklist(trade.symbol)
                                continue
                            
                            db.commit()
                            
                        except Exception as e:
                            logger.error(f"Erro ao monitorar {trade.symbol}: {e}")
                            db.rollback()
                    
                finally:
                    db.close()
                
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                await asyncio.sleep(10)
    
    async def _check_kill_switch(self) -> bool:
        """
        ✅ NOVO: Kill switch automático em drawdown > 15%
        """
        
        if self.initial_balance == 0:
            return False
        
        try:
            info = await binance_client.get_account_balance()
            usdt = {"balance": info.get("total_balance")} if info else None
            
            if not usdt:
                return False
            
            current_balance = float(usdt['balance'])
            drawdown_pct = ((self.initial_balance - current_balance) / self.initial_balance) * 100
            
            if drawdown_pct >= self.max_drawdown_pct:
                logger.error(
                    f"🔴 KILL SWITCH ATIVADO!\n"
                    f"Balance inicial: {self.initial_balance:.2f} USDT\n"
                    f"Balance atual: {current_balance:.2f} USDT\n"
                    f"Drawdown: {drawdown_pct:.2f}%"
                )
                
                try:
                    await telegram_notifier.send_alert(
                        f"🚨 KILL SWITCH ATIVADO\n\n"
                        f"Drawdown: {drawdown_pct:.2f}%\n"
                        f"Balance: {self.initial_balance:.2f} → {current_balance:.2f} USDT\n\n"
                        f"Trading PAUSADO automaticamente.\n"
                        f"Revisar estratégia antes de reativar."
                    )
                except:
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar kill switch: {e}")
            return False
    
    async def _sync_missing_positions(
        self,
        binance_positions: List[Dict],
        db_positions: List[Trade],
        db: SessionLocal
    ):
        """Sincronizar posições "fantasma" automaticamente"""
        
        db_symbols = {trade.symbol for trade in db_positions}
        synced_count = 0
        
        for binance_pos in binance_positions:
            symbol = binance_pos['symbol']
            
            if symbol not in db_symbols:
                self._log_once(
                    f"sync_{symbol}",
                    f"🔄 {symbol} detectado na Binance mas não no DB. Criando registro..."
                )
                
                try:
                    position_amt = float(binance_pos['positionAmt'])
                    entry_price = float(binance_pos['entryPrice'])
                    direction = 'LONG' if position_amt > 0 else 'SHORT'
                    leverage = int(binance_pos.get('leverage', 3))
                    
                    # Calcular stop loss e take profit
                    if direction == 'LONG':
                        stop_loss = entry_price * 0.92
                        tp1 = entry_price * 1.10
                        tp2 = entry_price * 1.20
                        tp3 = entry_price * 1.30
                    else:
                        stop_loss = entry_price * 1.08
                        tp1 = entry_price * 0.90
                        tp2 = entry_price * 0.80
                        tp3 = entry_price * 0.70
                    
                    trade = Trade(
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry_price,
                        current_price=entry_price,
                        quantity=abs(position_amt),
                        leverage=leverage,
                        stop_loss=stop_loss,
                        take_profit_1=tp1,
                        take_profit_2=tp2,
                        take_profit_3=tp3,
                        status='open',
                        pnl=0.0,
                        pnl_percentage=0.0
                    )
                    
                    db.add(trade)
                    db.commit()
                    synced_count += 1
                    
                    logger.info(
                        f"✅ {symbol} sincronizado: {direction} @ {entry_price:.4f}, "
                        f"Qty {abs(position_amt):.4f}, Lev {leverage}x"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar {symbol}: {e}")
                    db.rollback()
        
        if synced_count > 0:
            logger.info(f"✅ {synced_count} posição(ões) sincronizada(s)")
    
    async def _check_trailing_stop(
        self,
        trade: Trade,
        current_price: float,
        db: SessionLocal
    ) -> bool:
        """
        ✅ NOVO v4.0: Trailing Stop adaptativo por ATR (respeitando TSL_* min/max)
        """
        
        pnl_percentage = trade.pnl_percentage
        
        # Atualizar pico de lucro
        if not trade.max_pnl_percentage:
            trade.max_pnl_percentage = 0.0
        
        if pnl_percentage > trade.max_pnl_percentage:
            trade.max_pnl_percentage = pnl_percentage
            trade.trailing_peak_price = current_price
            db.commit()
            
            # Notificar ativação do trailing uma única vez
            try:
                key = f"trail_act_{trade.symbol}"
                if key not in self.warning_cache and trade.max_pnl_percentage > self.trailing_stop_activation:
                    await telegram_notifier.notify_trailing_stop_activated(trade.symbol, trade.max_pnl_percentage)
                    self.warning_cache[key] = time.time()
            except:
                pass
        
        # ✅ CORREÇÃO: Threshold +3% (antes +1%)
        if trade.max_pnl_percentage > self.trailing_stop_activation:
            # ✅ NOVO v4.0: Calcular threshold adaptativo baseado em ATR
            try:
                interval = str(getattr(self.settings, "TSL_ATR_LOOKBACK_INTERVAL", "15m"))
                klines = await binance_client.get_klines(trade.symbol, interval=interval, limit=50)
                atr = risk_calculator.calculate_atr(klines) if klines else 0.0
                atr_pct = (atr / current_price * 100) if current_price > 0 else 0.5
                
                # Aplicar limites min/max do settings
                tsl_min = float(getattr(self.settings, "TSL_CALLBACK_PCT_MIN", 0.4))
                tsl_max = float(getattr(self.settings, "TSL_CALLBACK_PCT_MAX", 1.2))
                
                # Threshold adaptativo: usar ATR% mas respeitar limites
                adaptive_threshold = max(tsl_min, min(tsl_max, atr_pct))
                
                # Usar o maior entre threshold fixo e adaptativo (mais conservador)
                threshold_pct = max(self.trailing_stop_distance * 100, adaptive_threshold)
                
                logger.debug(
                    f"📊 {trade.symbol}: TSL adaptativo - ATR={atr_pct:.2f}%, "
                    f"threshold={threshold_pct:.2f}% (min={tsl_min:.2f}%, max={tsl_max:.2f}%)"
                )
            except Exception as e:
                # Fallback para threshold fixo em caso de erro
                threshold_pct = self.trailing_stop_distance * 100
                logger.debug(f"⚠️ {trade.symbol}: Fallback para TSL fixo ({threshold_pct:.2f}%): {e}")
            
            drawdown_from_peak = ((trade.max_pnl_percentage - pnl_percentage) / 
                                  trade.max_pnl_percentage) * 100 if trade.max_pnl_percentage > 0 else 0
            
            if drawdown_from_peak > threshold_pct:
                logger.info(
                    f"🛑 TRAILING STOP: {trade.symbol}\n"
                    f"  Pico: +{trade.max_pnl_percentage:.2f}%\n"
                    f"  Atual: +{pnl_percentage:.2f}%\n"
                    f"  Queda: {drawdown_from_peak:.1f}% (threshold: {threshold_pct:.1f}%)"
                )
                
                try:
                    await telegram_notifier.notify_trailing_stop_executed(trade.symbol, getattr(trade, 'trailing_peak_price', current_price), current_price, trade.pnl)
                except:
                    pass
                
                await self._close_position(
                    trade,
                    current_price,
                    reason=f"Trailing Stop (pico {trade.max_pnl_percentage:.2f}%)",
                    db=db
                )
                
                return True
        
        return False
    
    async def _check_partial_take_profit(
        self,
        trade: Trade,
        pnl_percentage: float,
        current_price: float,
        db: SessionLocal
    ) -> bool:
        """
        ✅ NOVO: Take Profit Parcial DINÂMICO (baseado em volatilidade)
        """
        
        if trade.partial_taken:
            return False
        
        # ✅ CORREÇÃO: Threshold +5% (antes +3%)
        if pnl_percentage >= self.partial_tp_threshold:
            try:
                # ✅ NOVO: Calcular % parcial baseado em volatilidade
                # Pegar ATR do símbolo para medir volatilidade
                klines = await binance_client.get_klines(
                    symbol=trade.symbol,
                    interval='1h',
                    limit=14
                )
                
                # Calcular volatilidade simplificada
                closes = [float(k[4]) for k in klines]
                volatility = (max(closes) - min(closes)) / min(closes) * 100
                
                # Ajustar parcial baseado em volatilidade
                if volatility > 8:  # Alta volatilidade (altcoins)
                    partial_pct = 0.30  # Fechar apenas 30%
                    logger.info(f"📊 {trade.symbol}: Alta volatilidade ({volatility:.1f}%), parcial 30%")
                elif volatility < 3:  # Baixa volatilidade (BTC/ETH)
                    partial_pct = 0.70  # Fechar 70%
                    logger.info(f"📊 {trade.symbol}: Baixa volatilidade ({volatility:.1f}%), parcial 70%")
                else:
                    partial_pct = 0.50  # Default 50%
                
                logger.info(
                    f"💰 TAKE PROFIT PARCIAL: {trade.symbol} +{pnl_percentage:.2f}%\n"
                    f"  Fechando {partial_pct*100:.0f}% da posição..."
                )
                
                # Calcular quantidade parcial
                partial_qty = trade.quantity * partial_pct
                
                symbol_info = await binance_client.get_symbol_info(trade.symbol)
                partial_qty = round_step_size(partial_qty, symbol_info['step_size'])
                
                side = 'SELL' if trade.direction == 'LONG' else 'BUY'
                
                order = await asyncio.to_thread(
                    self.client.futures_create_order,
                    symbol=trade.symbol,
                    side=side,
                    type='MARKET',
                    quantity=partial_qty,
                    reduceOnly=True
                )
                
                # Atualizar trade
                trade.quantity = trade.quantity - partial_qty
                trade.partial_taken = True
                
                # Mover stop para breakeven
                trade.stop_loss = trade.entry_price
                
                db.commit()
                
                logger.info(
                    f"✅ Parcial executada: {partial_qty} @ {order.get('avgPrice', 0)}\n"
                    f"  Stop movido para breakeven: {trade.entry_price:.4f}"
                )
                
                try:
                    await telegram_notifier.notify_take_profit_hit(trade.symbol, "Parcial", current_price)
                    await telegram_notifier.notify_breakeven_activated(trade.symbol, pnl_percentage, trade.entry_price)
                except:
                    pass
                
                return False
                
            except Exception as e:
                logger.error(f"❌ Erro ao executar parcial: {e}")
                return False
        
        return False
    
    async def _close_position(
        self,
        trade: Trade,
        current_price: float,
        reason: str,
        db: SessionLocal
    ):
        """Fecha uma posição completamente"""
        
        try:
            side = 'SELL' if trade.direction == 'LONG' else 'BUY'
            
            # Ajustar quantidade para step_size (evita erro -1111 de precisão)
            try:
                symbol_info = await binance_client.get_symbol_info(trade.symbol)
                step = symbol_info.get('step_size') if symbol_info else None
            except Exception:
                step = None
            close_qty = round_step_size(float(trade.quantity or 0), step) if step else float(trade.quantity or 0)

            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=trade.symbol,
                side=side,
                type='MARKET',
                quantity=close_qty,
                reduceOnly=True
            )
            
            trade.status = 'closed'
            trade.closed_at = datetime.now()
            trade.pnl = float(order.get('cumQuote', trade.pnl))
            
            # ✅ NOVO v4.0: Finalizar tracking de métricas da posição
            self._finalize_position_tracking(trade.symbol, trade.entry_price, current_price, trade.direction)
            
            db.commit()
            
            logger.info(
                f"✅ Posição fechada: {trade.symbol} {trade.direction}\n"
                f"  Motivo: {reason}\n"
                f"  P&L: {trade.pnl:+.2f} USDT ({trade.pnl_percentage:+.2f}%)"
            )
            
            # Atualizar circuit breaker
            if trade.pnl < 0:
                self.consecutive_losses += 1
                
                if self.consecutive_losses >= self.max_consecutive_losses:
                    self.circuit_breaker_active = True
                    logger.error(f"🚨 CIRCUIT BREAKER ATIVADO: {self.consecutive_losses} perdas consecutivas!")
                    
                    try:
                        await telegram_notifier.send_alert(
                            f"🚨 CIRCUIT BREAKER ATIVADO\n\n"
                            f"{self.consecutive_losses} perdas consecutivas\n"
                            f"Trading pausado por 1 hora"
                        )
                    except:
                        pass
                    
                    asyncio.create_task(self._reset_circuit_breaker())
            else:
                self.consecutive_losses = 0
                self.circuit_breaker_active = False
            
            try:
                await telegram_notifier.notify_trade_closed({
                    'symbol': trade.symbol,
                    'direction': trade.direction,
                    'entry_price': trade.entry_price,
                    'exit_price': current_price,
                    'pnl': trade.pnl,
                    'pnl_percentage': trade.pnl_percentage,
                    'reason': reason
                })
            except:
                pass
            
        except Exception as e:
            logger.error(f"❌ Erro ao fechar posição {trade.symbol}: {e}")
    
    async def _add_to_symbol_blacklist(self, symbol: str):
        """Circuit breaker por símbolo - bloqueia por 2h"""
        
        until = time.time() + (2 * 3600)
        self.symbol_blacklist[symbol] = until
        
        logger.warning(f"🚫 {symbol} bloqueado até {datetime.fromtimestamp(until).strftime('%H:%M')}")
        
        try:
            await telegram_notifier.send_alert(
                f"🚫 SÍMBOLO BLOQUEADO\n\n"
                f"{symbol} bloqueado por 2 horas\n"
                f"Motivo: Perda > {self.max_loss_per_trade}%"
            )
        except:
            pass
    
    def is_symbol_blacklisted(self, symbol: str) -> bool:
        """Verifica se símbolo está no blacklist"""
        
        if symbol not in self.symbol_blacklist:
            return False
        
        if time.time() > self.symbol_blacklist[symbol]:
            del self.symbol_blacklist[symbol]
            logger.info(f"✅ {symbol} removido do blacklist")
            return False
        
        return True
    
    async def _reset_circuit_breaker(self):
        """Reset após 1 hora"""
        
        await asyncio.sleep(3600)
        
        self.circuit_breaker_active = False
        self.consecutive_losses = 0
        
        logger.info("✅ Circuit breaker resetado")
        
        try:
            await telegram_notifier.send_message("✅ Circuit breaker resetado")
        except:
            pass
    
    def _log_once(self, key: str, message: str):
        """Log otimizado (evita spam)"""
        
        current_time = time.time()
        
        if key in self.warning_cache:
            if current_time - self.warning_cache[key] < self.warning_cache_ttl:
                return
        
        logger.warning(message)
        self.warning_cache[key] = current_time


    def _update_mae_mfe(self, symbol: str, current_price: float, entry_price: float, direction: str):
        """✅ NOVO v4.0: Atualiza MAE (Maximum Adverse Excursion) e MFE (Maximum Favorable Excursion)"""
        if symbol not in self._position_tracking:
            self._position_tracking[symbol] = {
                "entry_time": datetime.now(timezone.utc),
                "entry_price": entry_price,
                "direction": direction,
                "max_adverse_pct": 0.0,
                "max_favorable_pct": 0.0
            }
        
        tracking = self._position_tracking[symbol]
        
        # Calcular desvio atual do preço de entrada
        if direction == "LONG":
            deviation_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
        else:  # SHORT
            deviation_pct = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0.0
        
        # Atualizar MAE (pior desvio adverso)
        if deviation_pct < tracking["max_adverse_pct"]:
            tracking["max_adverse_pct"] = deviation_pct
        
        # Atualizar MFE (melhor desvio favorável)
        if deviation_pct > tracking["max_favorable_pct"]:
            tracking["max_favorable_pct"] = deviation_pct
    
    def _finalize_position_tracking(self, symbol: str, entry_price: float, exit_price: float, direction: str):
        """✅ NOVO v4.0: Finaliza tracking e calcula métricas finais"""
        if symbol not in self._position_tracking:
            return
        
        tracking = self._position_tracking[symbol]
        entry_time = tracking["entry_time"]
        hold_time_sec = (datetime.now(timezone.utc) - entry_time).total_seconds()
        
        # Atualizar métricas agregadas
        self._metrics["positions_closed"] += 1
        self._metrics["position_stats"]["total_hold_time_sec"] += hold_time_sec
        
        total_closed = self._metrics["positions_closed"]
        if total_closed > 0:
            self._metrics["position_stats"]["average_hold_time_sec"] = (
                self._metrics["position_stats"]["total_hold_time_sec"] / total_closed
            )
        
        # Registrar MAE/MFE
        if tracking["max_adverse_pct"] < 0:
            self._metrics["position_stats"]["positions_with_mae"] += 1
        if tracking["max_favorable_pct"] > 0:
            self._metrics["position_stats"]["positions_with_mfe"] += 1
        
        mae_mfe_data = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "hold_time_sec": round(hold_time_sec, 2),
            "mae_pct": round(tracking["max_adverse_pct"], 2),
            "mfe_pct": round(tracking["max_favorable_pct"], 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._metrics["mae_mfe_data"].append(mae_mfe_data)
        if len(self._metrics["mae_mfe_data"]) > 100:
            self._metrics["mae_mfe_data"].pop(0)
        
        # Remover do tracking ativo
        del self._position_tracking[symbol]
        
        logger.debug(f"📊 Position tracking finalizado: {json.dumps(mae_mfe_data)}")
    
    def _track_event(self, event_type: str, symbol: str, pnl_percentage: float, price: float):
        """✅ NOVO v4.0: Rastreia eventos de monitoramento"""
        if event_type in self._metrics["events"]:
            self._metrics["events"][event_type] += 1
        
        event_detail = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "symbol": symbol,
            "pnl_percentage": round(pnl_percentage, 2),
            "price": price
        }
        
        self._metrics["event_details"].append(event_detail)
        if len(self._metrics["event_details"]) > 100:
            self._metrics["event_details"].pop(0)
        
        logger.debug(f"📊 Event tracked: {json.dumps(event_detail)}")
    
    def get_metrics(self) -> Dict:
        """✅ NOVO v4.0: Retorna métricas agregadas de monitoramento"""
        return {
            "total_positions_monitored": self._metrics["total_positions_monitored"],
            "positions_closed": self._metrics["positions_closed"],
            "events": self._metrics["events"],
            "position_stats": {
                **self._metrics["position_stats"],
                "average_hold_time_minutes": (
                    self._metrics["position_stats"]["average_hold_time_sec"] / 60
                    if self._metrics["position_stats"]["average_hold_time_sec"] > 0 else 0.0
                )
            },
            "recent_mae_mfe": self._metrics["mae_mfe_data"][-10:],  # Últimas 10
            "recent_events": self._metrics["event_details"][-10:]  # Últimos 10 eventos
        }


# Instância global
position_monitor = PositionMonitor()
