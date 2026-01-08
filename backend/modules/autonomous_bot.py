"""
Autonomous Bot - PROFESSIONAL VERSION v5.0
✅ Refatorado para melhor organização e manutenibilidade
"""
import asyncio
import time
import pandas as pd
import redis
import json
from typing import List, Dict
from datetime import datetime, timezone

from utils.logger import setup_logger
from api.database import SessionLocal
from api.models.trades import Trade
from utils.binance_client import binance_client
from utils.telegram_notifier import telegram_notifier
from utils.helpers import round_step_size
from config.settings import get_settings
from modules.position_monitor import position_monitor
from modules.telegram_bot import telegram_bot
from modules.bot.bot_config import BotConfig
from modules.bot.position_manager import PositionManager
from modules.bot.trading_loop import TradingLoop
from modules.bot.loops import BotLoops
from modules.bot.strategies import BotStrategies
from modules.bot.actions import BotActions
from modules.risk_calculator import risk_calculator
from modules.correlation_filter import correlation_filter
from modules.market_filter import market_filter
from modules.market_scanner import market_scanner
from modules.order_executor import order_executor
from modules.signal_generator import signal_generator
from modules.metrics_collector import metrics_collector
from modules.history_analyzer import history_analyzer
from modules.supervisor import supervisor  # ✅ NOVO
from utils.redis_client import redis_client

logger = setup_logger("autonomous_bot")

class AutonomousBot:
    def __init__(self):
        self.bot_config = BotConfig()
        # ... (rest of init)
        
        # Registrar no Supervisor
        supervisor.register_bot(self)
        settings = get_settings()
        self.base_scan_interval = int(getattr(settings, "BOT_SCAN_INTERVAL_MINUTES", 1)) * 60
        self.base_max_positions = int(getattr(settings, "BOT_MAX_POSITIONS", getattr(settings, "MAX_POSITIONS", 15)))
        self.base_max_new_per_cycle = 5
        self.pyramiding_enabled = True
        self.pyramiding_threshold = 5.0
        self.pyramiding_multiplier = 0.5
        self.sniper_enabled = True
        self.total_trades = 0
        self.win_rate = 0.0
        self.winning_trades = 0
        self.client = binance_client.client
        self.bot_config = BotConfig()
        self.position_manager = PositionManager(self.bot_config)
        self.trading_loop = TradingLoop(self.bot_config, self.position_manager)
        self.loops = BotLoops(self)
        self.strategies = BotStrategies(self)
        self.actions = BotActions(self)
        self.running = False
        self.dry_run = True
        self.max_positions = self.base_max_positions
        self.max_new_positions_per_cycle = self.base_max_new_per_cycle
        self._whitelist_block_cache = {}
        self._whitelist_block_cache_ttl = 300

    def _whitelist_allows(self, symbol: str) -> bool:
        settings = get_settings()
        wl = [str(x).upper() for x in (getattr(settings, "SYMBOL_WHITELIST", []) or []) if str(x).strip()]
        if not wl:
            return True
        if not bool(getattr(settings, "SCANNER_STRICT_WHITELIST", False)):
            return True
        return str(symbol).upper() in wl

    def _log_whitelist_block(self, symbol: str, action: str) -> None:
        now = time.time()
        key = f"wl_{action}_{symbol}"
        if key in self._whitelist_block_cache:
            if now - self._whitelist_block_cache[key] < self._whitelist_block_cache_ttl:
                return
        logger.warning(f"Whitelist block: {symbol} action {action} skipped")
        self._whitelist_block_cache[key] = now

    # Propriedades de conveniência para a API
    @property
    def scan_interval(self):
        """Delega para bot_config.scan_interval"""
        return self.bot_config.scan_interval
    
    @scan_interval.setter
    def scan_interval(self, value):
        self.bot_config.scan_interval = value
    
    @property
    def min_score(self):
        """Delega para bot_config.min_score"""
        return self.bot_config.min_score
    
    @min_score.setter
    def min_score(self, value):
        self.bot_config.min_score = value

    def reload_settings(self):
        self.bot_config.reload_settings()
        logger.info("🔄 Configurações do AutonomousBot recarregadas dinamicamente")

    async def start(self, dry_run: bool = True):
        """Inicia o bot autônomo"""
        if self.running:
            logger.warning("Bot já está rodando")
            return

        self.running = True
        self.dry_run = dry_run
        self.bot_config.dry_run = dry_run

        logger.info("🤖 BOT AUTÔNOMO INICIADO!")
        logger.info("Configurações:")
        logger.info(f"  - Scan interval: {self.bot_config.scan_interval}s")
        logger.info(f"  - Score mínimo: {self.bot_config.min_score}")
        logger.info(f"  - Trades simultâneos: {self.bot_config.max_positions}")
        logger.info("=" * 60)

        position_monitor.start_monitoring()
        self.loops.start()
        asyncio.create_task(telegram_bot.start())
        asyncio.create_task(supervisor.start_monitoring()) # ✅ Iniciar Supervisor
        await self._sync_positions_with_binance()

    def stop(self):
        """Para o bot"""
        self.running = False
        self.loops.stop()
        position_monitor.stop_monitoring()
        asyncio.create_task(supervisor.stop_monitoring()) # ✅ Parar Supervisor
        logger.info("🛑 Bot parado")

    def get_metrics(self) -> Dict:
        """Retorna métricas agregadas de KPIs por ciclo"""
        from modules.metrics_collector import metrics_collector
        return metrics_collector.get_cycle_summary()
    
    async def _pyramiding_loop(self):
        """
        ✅ NOVO: Loop de pyramiding
        Adiciona à posições vencedoras
        """
        if not self.pyramiding_enabled:
            return
      
        await asyncio.sleep(30)
        logger.info("📈 Loop de pyramiding iniciado")
        
        while self.running:
            supervisor.heartbeat("pyramiding_loop")
            try:
                db = SessionLocal()
                try:
                    open_trades = db.query(Trade).filter(
                        Trade.status == 'open',
                        Trade.pnl_percentage >= self.pyramiding_threshold
                    ).all()
                    
                    for trade in open_trades:
                        if hasattr(trade, 'pyramided') and trade.pyramided:
                            continue
                        if not self._whitelist_allows(trade.symbol):
                            self._log_whitelist_block(trade.symbol, "pyramiding")
                            continue
                        
                        logger.info(f"📈 PYRAMIDING: {trade.symbol} +{trade.pnl_percentage:.2f}%\n"
                                    f"  Adicionando {self.pyramiding_multiplier*100:.0f}% à posição...")
                        
                        try:
                            additional_qty = trade.quantity * self.pyramiding_multiplier
                            symbol_info = await binance_client.get_symbol_info(trade.symbol)
                            additional_qty = round_step_size(additional_qty, symbol_info['step_size'])
                            
                            side = 'BUY' if trade.direction == 'LONG' else 'SELL'
                            
                            if not self.dry_run:
                                position_side = None
                                try:
                                    position_side = await binance_client.get_position_side(trade.direction)
                                except Exception as e:
                                    logger.debug(f"Position side lookup failed: {e}")

                                order_params = {
                                    "symbol": trade.symbol,
                                    "side": side,
                                    "type": "MARKET",
                                    "quantity": additional_qty
                                }
                                if position_side:
                                    order_params["positionSide"] = position_side
                                order = await asyncio.to_thread(
                                    self.client.futures_create_order,
                                    **order_params
                                )
                                new_avg_price = ((trade.entry_price * trade.quantity + float(order['avgPrice']) * additional_qty) /
                                                 (trade.quantity + additional_qty))
                                
                                trade.quantity += additional_qty
                                trade.entry_price = new_avg_price
                                
                                if hasattr(trade, 'pyramided'):
                                    trade.pyramided = True
                                
                                if trade.direction == 'LONG':
                                    trade.stop_loss = max(trade.stop_loss, trade.entry_price)
                                else:
                                    trade.stop_loss = min(trade.stop_loss, trade.entry_price)
                                
                                db.commit()
                                logger.info(f"✅ Pyramiding executado: Qty adicional: {additional_qty:.4f}, Novo avg price: {new_avg_price:.4f}")
                                
                                await telegram_notifier.send_message(
                                    f"📈 PYRAMIDING\n\n"
                                    f"{trade.symbol} {trade.direction}\n"
                                    f"P&L: +{trade.pnl_percentage:.2f}%\n"
                                    f"Adicionado: {self.pyramiding_multiplier*100:.0f}%\n"
                                    f"Stop → breakeven"
                                )
                            else:
                                logger.info(f"🎯 DRY RUN: Pyramiding simulado para {trade.symbol}")
                        except Exception as e:
                            logger.error(f"❌ Erro ao executar pyramiding para {trade.symbol}: {e}")
                finally:
                    db.close()
                await asyncio.sleep(120)
            except Exception as e:
                logger.error(f"Erro no loop de pyramiding: {e}")
                await asyncio.sleep(120)

    async def _sniper_loop(self):
        """Loop automático para abrir posições sniper quando houver espaço."""
        await asyncio.sleep(45)
        settings = get_settings()

        while self.running:
            supervisor.heartbeat("sniper_loop")
            try:
                if not self.sniper_enabled:
                    await asyncio.sleep(60)
                    continue

                open_positions_exch = await self._get_open_positions_from_binance()
                current_count = len(open_positions_exch)

                core_max = int(getattr(settings, "MAX_POSITIONS", 15))
                extra_slots = int(getattr(settings, "SNIPER_EXTRA_SLOTS", 0))
                max_total_positions = core_max + max(0, extra_slots)
                
                if current_count >= max_total_positions:
                    await asyncio.sleep(90)
                    continue

                missing = max_total_positions - current_count
                if missing > 0:
                    logger.info(f"🎯 Sniper loop: {current_count}/{max_total_positions} posições. Tentando abrir até {missing} snipers...")
                    await self._open_sniper_batch(count=missing, open_positions_exch=open_positions_exch)

                await asyncio.sleep(120)
            except Exception as e:
                logger.error(f"Erro no loop sniper: {e}")
                await asyncio.sleep(120)

    async def _dca_loop(self):
        """✅ NOVO v5.0: Smart DCA Logic"""
        await asyncio.sleep(60)
        logger.info("📉 Smart DCA loop iniciado")
        
        while self.running:
            supervisor.heartbeat("dca_loop")
            try:
                dca_enabled = bool(getattr(get_settings(), "DCA_ENABLED", True))
                if not dca_enabled:
                    await asyncio.sleep(300)
                    continue
                    
                max_dca_count = int(getattr(get_settings(), "MAX_DCA_COUNT", 2))
                dca_threshold_pct = float(getattr(get_settings(), "DCA_THRESHOLD_PCT", -2.5))
                dca_multiplier = float(getattr(get_settings(), "DCA_MULTIPLIER", 1.5))
                
                db = SessionLocal()
                try:
                    open_trades = db.query(Trade).filter(Trade.status == 'open').all()
                    for trade in open_trades:
                        if not self._whitelist_allows(trade.symbol):
                            self._log_whitelist_block(trade.symbol, "dca")
                            continue
                        if trade.pnl_percentage > dca_threshold_pct:
                            continue
                            
                        redis_key = f"dca_count:{trade.symbol}"
                        current_dca_count = 0
                        if redis_client and redis_client.client:
                            val = redis_client.client.get(redis_key)
                            if val:
                                current_dca_count = int(val)
                        if current_dca_count >= max_dca_count:
                            continue
                            
                        logger.info(f"📉 Analisando DCA para {trade.symbol} (PnL: {trade.pnl_percentage:.2f}%)")
                        
                        klines = await binance_client.get_klines(trade.symbol, interval='1h', limit=50)
                        if not klines: continue
                            
                        closes = [float(k[4]) for k in klines]
                        df = pd.DataFrame({'close': closes})
                        rsi = self._calculate_rsi_quick(df)
                        
                        should_dca = False
                        reason = ""
                        if trade.direction == 'LONG' and rsi < 35:
                            should_dca = True
                            reason = f"RSI Oversold ({rsi:.1f})"
                        elif trade.direction == 'SHORT' and rsi > 65:
                            should_dca = True
                            reason = f"RSI Overbought ({rsi:.1f})"
                                
                        if should_dca:
                            logger.info(f"📉 EXECUTANDO DCA #{current_dca_count + 1} para {trade.symbol}: {reason}")
                            
                            dca_qty = trade.quantity * dca_multiplier
                            symbol_info = await binance_client.get_symbol_info(trade.symbol)
                            dca_qty = round_step_size(dca_qty, symbol_info['step_size'])
                            
                            side = 'BUY' if trade.direction == 'LONG' else 'SELL'
                            
                            if not self.dry_run:
                                position_side = None
                                try:
                                    position_side = await binance_client.get_position_side(trade.direction)
                                except Exception as e:
                                    logger.debug(f"Position side lookup failed: {e}")

                                order_params = {
                                    "symbol": trade.symbol,
                                    "side": side,
                                    "type": "MARKET",
                                    "quantity": dca_qty
                                }
                                if position_side:
                                    order_params["positionSide"] = position_side
                                order = await asyncio.to_thread(
                                    self.client.futures_create_order,
                                    **order_params
                                )
                                
                                avg_price = float(order['avgPrice'])
                                new_total_qty = trade.quantity + dca_qty
                                new_avg_entry = ((trade.entry_price * trade.quantity) + (avg_price * dca_qty)) / new_total_qty
                                
                                trade.quantity = new_total_qty
                                trade.entry_price = new_avg_entry
                                db.commit()
                                
                                if redis_client and redis_client.client:
                                    redis_client.client.set(redis_key, str(current_dca_count + 1), ex=86400*7)
                                
                                await telegram_notifier.send_message(f"📉 SMART DCA #{current_dca_count + 1}\n\n{trade.symbol} {trade.direction}\nMotivo: {reason}\nNovo Preço Médio: {new_avg_entry:.4f}")
                            else:
                                logger.info(f"🎯 DRY RUN: DCA simulado para {trade.symbol}")
                        
                        await asyncio.sleep(2)
                finally:
                    db.close()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Erro no loop DCA: {e}")
                await asyncio.sleep(60)

    async def _run_periodic_tasks(self):
        """Executa tarefas periódicas (limpeza, sync, análise)"""
        while self.running:
            try:
                # 1. Sync de posições (a cada 10 min)
                if self.config.positions_auto_sync_enabled:
                    await self.position_manager.sync_positions_with_binance()
                
                # 2. Análise de Histórico (a cada 4 horas)
                # Usar um contador ou timestamp seria melhor, mas sleep longo bloqueia
                # Vamos rodar a análise em background sem bloquear
                asyncio.create_task(self._run_history_analysis())

                await asyncio.sleep(self.config.positions_auto_sync_minutes * 60)
            except Exception as e:
                logger.error(f"Erro nas tarefas periódicas: {e}")
                await asyncio.sleep(60)

    async def _run_history_analysis(self):
        """Roda análise de histórico e aplica blacklist"""
        try:
            logger.info("📜 Rodando análise de histórico...")
            analysis = await history_analyzer.run_analysis_cycle()
            
            # Aplicar blacklist
            if analysis['blacklist_recommendations']:
                for symbol in analysis['blacklist_recommendations']:
                    await position_monitor._add_to_symbol_blacklist(symbol)
                    logger.warning(f"🚫 {symbol} adicionado ao blacklist por baixa performance")
                    
        except Exception as e:
            logger.error(f"Erro na análise de histórico: {e}")

    async def _time_based_exit_loop(self):
        """✅ NOVO v5.0: Time-Based Exit Strategy"""
        await asyncio.sleep(120)
        logger.info("⏱️ Time-Based Exit loop iniciado")
        
        while self.running:
            supervisor.heartbeat("time_exit_loop")
            try:
                max_hold_hours = int(getattr(get_settings(), "TIME_EXIT_HOURS", 6))
                min_profit_pct = float(getattr(get_settings(), "TIME_EXIT_MIN_PROFIT_PCT", 0.5))
                
                db = SessionLocal()
                try:
                    open_trades = db.query(Trade).filter(Trade.status == 'open').all()
                    now = datetime.now(timezone.utc)
                    
                    for trade in open_trades:
                        if not self._whitelist_allows(trade.symbol):
                            self._log_whitelist_block(trade.symbol, "time_exit")
                            continue
                        entry_time = trade.opened_at
                        if entry_time.tzinfo is None:
                            entry_time = entry_time.replace(tzinfo=timezone.utc)
                            
                        hold_duration = now - entry_time
                        hold_hours = hold_duration.total_seconds() / 3600
                        
                        if hold_hours > max_hold_hours and trade.pnl_percentage < min_profit_pct:
                            logger.info(f"⏱️ TIME EXIT: {trade.symbol} hold {hold_hours:.1f}h > {max_hold_hours}h com PnL {trade.pnl_percentage:.2f}% < {min_profit_pct}%")
                            
                            if not self.dry_run:
                                await position_monitor._close_position(trade, trade.current_price, reason=f"Time Exit ({hold_hours:.1f}h)", db=db)
                            else:
                                logger.info(f"🎯 DRY RUN: Time Exit simulado para {trade.symbol}")
                        await asyncio.sleep(1)
                finally:
                    db.close()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Erro no loop Time Exit: {e}")
                await asyncio.sleep(300)

    def _calculate_rsi_quick(self, df, period=14):
        """Cálculo rápido de RSI para o loop de DCA"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]

    async def _open_sniper_batch(self, count: int, open_positions_exch: List[Dict]):
        """Abre até `count` posições sniper usando lógica interna."""
        settings = get_settings()
        target = max(1, int(count))
        account_balance = await self._get_account_balance()
        
        try:
            candidate_symbols = await market_scanner.get_sniper_candidates()
            if not candidate_symbols: raise ValueError("No candidates")
        except Exception:
            logger.warning("⚠️ Nenhum candidato Sniper encontrado. Usando fallback.")
            fallback = list(getattr(settings, "SYMBOL_WHITELIST", [])) or list(getattr(settings, "TESTNET_WHITELIST", []))
            candidate_symbols = [s.upper() for s in fallback if str(s).strip()] or ["BTCUSDT","ETHUSDT","BNBUSDT"]

        opened = 0
        for sym in candidate_symbols:
            if opened >= target: break
            
            try:
                tp_pct = float(getattr(settings, "SNIPER_TP_PCT", 0.6)) / 100.0
                sl_pct = float(getattr(settings, "SNIPER_SL_PCT", 0.3)) / 100.0
                lev_default = int(getattr(settings, "SNIPER_DEFAULT_LEVERAGE", 10))
                price = await binance_client.get_symbol_price(sym)
                if not price:
                    logger.warning(f"⚠️ Preço não disponível para {sym}, pulando.")
                    continue
                
                direction = "LONG"

                stop = price * (1.0 - sl_pct) if direction == "LONG" else price * (1.0 + sl_pct)
                tp = price * (1.0 + tp_pct) if direction == "LONG" else price * (1.0 - tp_pct)

                signal = {"symbol": sym, "direction": direction, "entry_price": price, "stop_loss": float(stop), "take_profit_1": float(tp), "leverage": lev_default, "score": 99, "sniper": True, "risk_pct": 1.0, "force": True}

                exec_res = await order_executor.execute_signal(signal=signal, account_balance=account_balance, open_positions=len(open_positions_exch) + opened, dry_run=self.dry_run)
                if bool(exec_res.get("success")):
                    opened += 1
                    logger.info(f"✅ Sniper aberto: {sym} {direction} @ {exec_res.get('entry_price') or exec_res.get('avg_price')}")
                else:
                    logger.warning(f"❌ Sniper rejeitado {sym}: {exec_res.get('reason')}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Erro ao executar sniper {sym}: {e}")
        
        if opened > 0:
            await telegram_notifier.send_message(f"🎯 Sniper loop concluído\nAlvo: {target} | Abertas: {opened}")
        logger.info(f"🎯 Sniper batch: alvo={target} | executadas={opened}")

    def _get_symbol_profile(self, symbol: str) -> Dict:
        """Perfil histórico por símbolo (P&L, win rate, etc.)"""
        db = SessionLocal()
        try:
            trades = db.query(Trade).filter(Trade.symbol == symbol, Trade.status == 'closed').order_by(Trade.closed_at.desc()).limit(50).all()
            if not trades: return {"trades": 0, "win_rate": 0.0, "roi_pct": 0.0}

            total = len(trades)
            roi_usdt = sum(float(t.pnl or 0.0) for t in trades)
            notional_sum = sum(float((t.entry_price or 0.0) * (t.quantity or 0.0)) for t in trades)
            roi_pct = (roi_usdt / notional_sum * 100.0) if notional_sum > 0 else 0.0
            win_rate = len([t for t in trades if (t.pnl or 0.0) > 0]) / total
            
            return {"trades": total, "roi_pct": roi_pct, "win_rate": win_rate}
        finally:
            db.close()

    def _adjust_signal_for_symbol_profile(self, signal: Dict) -> Dict:
        """Ajusta risco e alavancagem com base no histórico do símbolo."""
        try:
            symbol = signal.get("symbol")
            if not symbol: return signal

            profile = self._get_symbol_profile(symbol)
            if profile["trades"] < 10: return signal

            adjusted = dict(signal)
            risk_pct = float(adjusted.get("risk_pct", 2.0))
            lev_default = int(getattr(get_settings(), "DEFAULT_LEVERAGE", 3))
            leverage = int(adjusted.get("leverage", lev_default))

            if profile["roi_pct"] <= -5.0 or profile["win_rate"] < 0.45:
                adjusted["risk_pct"] = min(risk_pct, 0.5)
                adjusted["leverage"] = max(2, int(leverage * 0.5))
                logger.info(f"⚠️ Ajuste conservador para {symbol}: WR={profile['win_rate']:.1%}, ROI={profile['roi_pct']:.1f}%. Risco: {risk_pct:.2f}%→{adjusted['risk_pct']:.2f}%, Alav.: {leverage}→{adjusted['leverage']}")
            elif profile["roi_pct"] >= 5.0 and profile["win_rate"] > 0.60:
                adjusted["risk_pct"] = min(risk_pct * 1.2, 2.0)
                adjusted["leverage"] = min(leverage + 1, 15)
                logger.info(f"🚀 Ajuste agressivo para {symbol}: WR={profile['win_rate']:.1%}, ROI={profile['roi_pct']:.1f}%. Risco: {risk_pct:.2f}%→{adjusted['risk_pct']:.2f}%, Alav.: {leverage}→{adjusted['leverage']}")
            
            return adjusted
        except Exception as e:
            logger.error(f"Erro ao ajustar sinal por perfil: {e}")
            return signal

    async def _calculate_scan_interval(self) -> int:
        """Calcula scan interval dinâmico baseado em volatilidade"""
        try:
            klines = await binance_client.get_klines(symbol='BTCUSDT', interval='1h', limit=24)
            if not klines: return self.base_scan_interval
            
            closes = [float(k[4]) for k in klines]
            volatility_pct = ((max(closes) - min(closes)) / min(closes)) * 100
            
            if volatility_pct > 5: interval = 300  # 5 min
            elif volatility_pct < 2: interval = 900  # 15 min
            else: interval = self.base_scan_interval # 10 min
            
            logger.info(f"📊 Volatilidade BTC 24h: {volatility_pct:.2f}%. Intervalo de scan: {interval/60:.0f} min")
            return interval
        except Exception as e:
            logger.error(f"Erro ao calcular scan interval: {e}")
            return self.base_scan_interval
    
    async def _adjust_position_limits(self):
        """Ajusta limites de posição baseado em win rate recente"""
        db = SessionLocal()
        try:
            recent_trades = db.query(Trade).filter(Trade.status == 'closed').order_by(Trade.closed_at.desc()).limit(20).all()
            if len(recent_trades) < 10: return

            recent_win_rate = sum(1 for t in recent_trades if t.pnl > 0) / len(recent_trades)
            self.win_rate = recent_win_rate
            risk_calculator.update_win_rate(recent_win_rate)
            
            if recent_win_rate > 0.65:
                self.max_positions = min(20, self.base_max_positions + 5)
                self.max_new_positions_per_cycle = min(8, self.base_max_new_per_cycle + 3)
                logger.info(f"🚀 Win Rate {recent_win_rate:.1%} → Limites aumentados para {self.max_positions} posições")
            elif recent_win_rate < 0.50:
                self.max_positions = max(10, self.base_max_positions - 5)
                self.max_new_positions_per_cycle = max(2, self.base_max_new_per_cycle - 2)
                logger.warning(f"⚠️ Win Rate {recent_win_rate:.1%} → Limites reduzidos para {self.max_positions} posições")
            else:
                self.max_positions = self.base_max_positions
                self.max_new_positions_per_cycle = self.base_max_new_per_cycle
        finally:
            db.close()
    
    async def _sync_positions_with_binance(self):
        """Sincroniza posições da Binance com o banco de dados"""
        logger.info("🔄 Sincronizando posições da Binance com DB...")
        try:
            positions = await asyncio.to_thread(self.client.futures_position_information)
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            if not open_positions:
                logger.info("✅ Nenhuma posição aberta na Binance")
                return

            db = SessionLocal()
            try:
                synced = 0
                for pos in open_positions:
                    symbol = pos['symbol']
                    if not db.query(Trade).filter(Trade.symbol == symbol, Trade.status == 'open').first():
                        logger.info(f"🔄 Sincronizando {symbol}...")
                        position_amt = float(pos['positionAmt'])
                        entry_price = float(pos['entryPrice'])
                        direction = 'LONG' if position_amt > 0 else 'SHORT'
                        if direction == 'LONG':
                            stop_loss = entry_price * 0.92
                        else:
                            stop_loss = entry_price * 1.08
                        trade = Trade(
                            symbol=symbol,
                            direction=direction,
                            entry_price=entry_price,
                            current_price=entry_price,
                            quantity=abs(position_amt),
                            leverage=int(pos.get('leverage', 3)),
                            stop_loss=stop_loss,
                            status='open'
                        )
                        db.add(trade)
                        synced += 1
                if synced > 0:
                    db.commit()
                    logger.info(f"✅ {synced} posição(ões) sincronizada(s)")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro ao sincronizar posições: {e}")
    
    async def _get_account_balance(self) -> float:
        """Retorna saldo disponível em USDT."""
        try:
            info = await binance_client.get_account_balance()
            if info and info.get("available_balance") is not None:
                return float(info["available_balance"])
            account = await asyncio.to_thread(self.client.futures_account_balance)
            usdt = next((b for b in account if b.get('asset') == 'USDT'), None)
            return float(usdt.get('availableBalance', 0) or 0)
        except Exception as e:
            logger.error(f"Erro ao obter saldo (async): {e}")
            return 0.0
    
    async def _get_open_positions_count(self) -> int:
        """Retorna número de posições abertas no DB"""
        db = SessionLocal()
        try:
            return db.query(Trade).filter(Trade.status == 'open').count()
        finally:
            db.close()
    
    async def _get_open_positions_from_binance(self) -> List[Dict]:
        """Retorna posições abertas da Binance"""
        try:
            positions = await asyncio.to_thread(self.client.futures_position_information)
            return [p for p in positions if float(p['positionAmt']) != 0]
        except Exception as e:
            logger.error(f"Erro ao buscar posições da Binance: {e}")
            return []

    async def add_strategic_positions(self, count: int) -> dict:
        """Abre novas posições utilizando o pipeline estratégico."""
        try:
            # Track latency for health monitoring
            latency = {}
            cycle_start = time.time()

            target = max(1, int(count))
            account_balance = await self._get_account_balance()
            open_positions_exch = await self._get_open_positions_from_binance()
            available_slots = min(target, max(0, self.max_positions - len(open_positions_exch)), self.max_new_positions_per_cycle)

            if available_slots <= 0:
                return {"success": False, "message": "Sem slots disponíveis", "opened": 0}

            # Track scan latency
            scan_start = time.time()
            market_sentiment = await market_filter.check_market_sentiment()
            scan_results = await market_scanner.scan_market()
            latency['scan'] = round(time.time() - scan_start, 3)

            # Track signal generation latency
            signal_start = time.time()
            signals = await signal_generator.generate_signal(scan_results)
            latency['signal'] = round(time.time() - signal_start, 3)

            if not signals:
                return {"success": False, "message": "Nenhum sinal gerado", "opened": 0}

            approved_signals = [s for s in signals if await market_filter.should_trade_symbol(s, market_sentiment)]
            filtered_signals = await correlation_filter.filter_correlated_signals(approved_signals, open_positions_exch, max_correlation=0.7)

            # Track execution latency
            exec_start = time.time()
            final_signals = filtered_signals[:available_slots]
            opened = 0
            for sig in final_signals:
                exec_res = await order_executor.execute_signal(signal=sig, account_balance=account_balance, open_positions=len(open_positions_exch) + opened, dry_run=self.dry_run)
                if exec_res.get("success"):
                    opened += 1
                    logger.info(f"✅ Executado {sig['symbol']} {sig['direction']}")
                else:
                    logger.warning(f"❌ Rejeitado {sig['symbol']}: {exec_res.get('reason')}")
                await asyncio.sleep(1)
            latency['execution'] = round(time.time() - exec_start, 3)

            # Calculate total latency
            latency['total'] = round(time.time() - cycle_start, 3)

            # Store latency in Redis for health monitoring
            try:
                settings = get_settings()
                redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=0,
                    decode_responses=True
                )
                redis_client.setex("latency:last_cycle", 300, json.dumps(latency))
                logger.debug(f"Latency tracked: {latency}")
            except Exception as redis_err:
                logger.debug(f"Failed to store latency in Redis: {redis_err}")

            if opened > 0:
                await telegram_notifier.send_message(f"🚀 Abertura estratégica concluída\nAlvo: {target} | Abertas: {opened}")

            return {"success": True, "opened": opened}
        except Exception as e:
            logger.error(f"Erro na abertura estratégica: {e}")
            return {"success": False, "message": str(e), "opened": 0}

autonomous_bot = AutonomousBot()
