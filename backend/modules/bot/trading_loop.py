import asyncio
import time
from datetime import datetime, timezone
import json
from typing import List, Dict

from utils.logger import setup_logger
from modules.market_scanner import market_scanner
from modules.signal_generator import signal_generator
from modules.order_executor import order_executor
from modules.position_monitor import position_monitor
from modules.market_filter import market_filter
from modules.correlation_filter import correlation_filter
from modules.metrics_collector import metrics_collector

logger = setup_logger("trading_loop")

class TradingLoop:
    def __init__(self, bot_config, position_manager):
        self.bot_config = bot_config
        self.position_manager = position_manager
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._trading_loop())

    def stop(self):
        self.running = False

    async def _trading_loop(self):
        """Loop principal de trading"""
        await asyncio.sleep(3)
        logger.info("🔄 Executando sync de posições ao iniciar...")
        await self.position_manager.sync_positions_with_binance()
        await asyncio.sleep(3)

        while self.running:
            try:
                cycle_start_time = time.time()
                cycle_metrics = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "signals_generated": 0,
                    "signals_approved_market": 0,
                    "signals_approved_correlation": 0,
                    "signals_final": 0,
                    "signals_executed": 0,
                    "signals_failed": 0,
                    "rejection_reasons": {},
                    "latencies": {},
                    "execution_results": []
                }

                logger.info("🔄 Iniciando novo ciclo de trading...")

                if position_monitor.circuit_breaker_active:
                    logger.warning("⚠️ Circuit breaker ativo. Aguardando reset...")
                    await asyncio.sleep(60)
                    continue

                market_sentiment = await market_filter.check_market_sentiment()
                logger.info(
                    f"📊 BTC: {market_sentiment['trend']} | "
                    f"4h: {market_sentiment['btc_change_4h']:+.2f}% | "
                    f"1h: {market_sentiment['btc_change_1h']:+.2f}% | "
                    f"Vol: {market_sentiment['volume_ratio']:.2f}x"
                )

                account_balance = await self.position_manager.get_account_balance()
                open_positions_count = await self.position_manager.get_open_positions_count()
                logger.info(f"💰 Saldo disponível: {account_balance:.2f} USDT")
                logger.info(f"📊 Posições: {open_positions_count}/{self.bot_config.max_positions}")

                available_slots = self.bot_config.max_positions - open_positions_count
                if available_slots <= 0:
                    logger.warning("❌ Sem slots disponíveis para novas posições")
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                logger.info(f"✅ Slots disponíveis: {available_slots}")
                logger.info(f"🔍 Escaneando {self.bot_config.symbols_to_scan} símbolos...")

                scan_start = time.time()
                scan_results = await market_scanner.scan_market()
                scan_time = time.time() - scan_start
                cycle_metrics["latencies"]["scan_time_sec"] = round(scan_time, 3)
                logger.info(f"📊 {len(scan_results)} símbolos escaneados (tempo: {scan_time:.2f}s)")

                if not scan_results:
                    logger.warning("❌ Nenhum símbolo encontrado no scan")
                    self._finalize_cycle(cycle_metrics, cycle_start_time)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                signal_start = time.time()
                signals = await signal_generator.generate_signal(scan_results)
                signal_time = time.time() - signal_start
                cycle_metrics["latencies"]["signal_generation_time_sec"] = round(signal_time, 3)
                cycle_metrics["signals_generated"] = len(signals)

                if not signals:
                    logger.info("❌ Nenhum sinal gerado")
                    self._finalize_cycle(cycle_metrics, cycle_start_time)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                logger.info(f"🎯 {len(signals)} sinal(is) de alta qualidade (tempo: {signal_time:.2f}s)")

                filter_start = time.time()
                approved_signals = [s for s in signals if await market_filter.should_trade_symbol(s, market_sentiment)]
                market_filter_rejected = len(signals) - len(approved_signals)
                filter_time = time.time() - filter_start
                cycle_metrics["latencies"]["filter_time_sec"] = round(filter_time, 3)
                cycle_metrics["signals_approved_market"] = len(approved_signals)
                cycle_metrics["rejection_reasons"]["market_filter"] = market_filter_rejected

                if not approved_signals:
                    logger.warning("❌ Todos os sinais foram bloqueados pelo market filter")
                    self._finalize_cycle(cycle_metrics, cycle_start_time)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                logger.info(f"📊 {len(approved_signals)} sinal(is) aprovado(s) pelo market filter (rejeitados: {market_filter_rejected})")

                open_positions_binance = await self.position_manager.get_open_positions_from_binance()
                correlation_start = time.time()
                filtered_signals = await correlation_filter.filter_correlated_signals(approved_signals, open_positions=open_positions_binance)
                correlation_time = time.time() - correlation_start
                cycle_metrics["latencies"]["filter_time_sec"] += round(correlation_time, 3)
                cycle_metrics["signals_approved_correlation"] = len(filtered_signals)
                cycle_metrics["rejection_reasons"]["correlation_filter"] = len(approved_signals) - len(filtered_signals)

                if not filtered_signals:
                    logger.warning("❌ Todos os sinais foram filtrados por correlação")
                    self._finalize_cycle(cycle_metrics, cycle_start_time)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                logger.info(f"📊 {len(filtered_signals)} sinal(is) após filtro de correlação")

                final_signals = [s for s in filtered_signals if not position_monitor.is_symbol_blacklisted(s['symbol'])]
                blacklist_rejected = len(filtered_signals) - len(final_signals)
                cycle_metrics["signals_final"] = len(final_signals)
                cycle_metrics["rejection_reasons"]["blacklist"] = blacklist_rejected

                if not final_signals:
                    logger.warning("❌ Todos os sinais estão no blacklist")
                    self._finalize_cycle(cycle_metrics, cycle_start_time)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                signals_to_execute = final_signals[:available_slots]
                logger.info(f"📤 Executando {len(signals_to_execute)} sinal(is) (limite: {available_slots} slots)")

                execution_start = time.time()
                executed_count = 0
                failed_count = 0

                for signal in signals_to_execute:
                    try:
                        result = await order_executor.execute_signal(
                            signal=signal,
                            account_balance=account_balance,
                            open_positions=open_positions_count + executed_count,
                            dry_run=self.bot_config.dry_run
                        )
                        if result['success']:
                            executed_count += 1
                            cycle_metrics["execution_results"].append({"symbol": signal['symbol'], "success": True})
                            logger.info(f"✅ Trade executado: {signal['symbol']} {signal['direction']}")
                        else:
                            failed_count += 1
                            reason = result.get('reason', 'Unknown')
                            cycle_metrics["execution_results"].append({"symbol": signal['symbol'], "success": False, "reason": reason})
                            if "risk" in reason.lower():
                                cycle_metrics["rejection_reasons"]["risk_manager"] = cycle_metrics["rejection_reasons"].get("risk_manager", 0) + 1
                            else:
                                cycle_metrics["rejection_reasons"]["execution_failed"] = cycle_metrics["rejection_reasons"].get("execution_failed", 0) + 1
                            logger.warning(f"❌ Trade rejeitado: {signal['symbol']} - {reason}")
                        await asyncio.sleep(2)
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"❌ Erro ao executar {signal['symbol']}: {e}")
                        cycle_metrics["execution_results"].append({"symbol": signal.get('symbol', 'UNKNOWN'), "success": False, "reason": str(e)})

                execution_time = time.time() - execution_start
                cycle_metrics["latencies"]["execution_time_sec"] = round(execution_time, 3)
                cycle_metrics["signals_executed"] = executed_count
                cycle_metrics["signals_failed"] = failed_count
                logger.info(f"✅ {executed_count} trade(s) executado(s) neste ciclo (falhas: {failed_count}, tempo: {execution_time:.2f}s)")

                self._finalize_cycle(cycle_metrics, cycle_start_time)
                await asyncio.sleep(self.bot_config.scan_interval)

            except Exception as e:
                logger.error(f"Erro no loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                if 'cycle_metrics' in locals():
                    self._finalize_cycle(cycle_metrics, cycle_start_time if 'cycle_start_time' in locals() else time.time())
                await asyncio.sleep(60)

    def _finalize_cycle(self, cycle_metrics: Dict, cycle_start_time: float):
        total_cycle_time = time.time() - cycle_start_time
        cycle_metrics["latencies"]["total_cycle_time_sec"] = round(total_cycle_time, 3)
        if total_cycle_time > 300:
            logger.warning(f"⚠️ Ciclo demorou {total_cycle_time/60:.1f} minutos")
        
        logger.debug(f"📊 Cycle metrics: {json.dumps(cycle_metrics)}")
        metrics_collector.record_cycle(cycle_metrics)
