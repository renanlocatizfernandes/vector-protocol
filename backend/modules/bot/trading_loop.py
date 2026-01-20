import asyncio
import time
import traceback
import uuid
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
from modules.supervisor import supervisor  # ✅ NOVO
from modules.metrics_dashboard import metrics_dashboard  # ✅ PASSO 4: Metrics Dashboard
from modules.pnl_reconciler import check_pnl_divergence
from config.settings import get_settings
from utils.binance_client import binance_client

logger = setup_logger("trading_loop")

# ✅ NOVO PR1: Thresholds de latência máxima por etapa
MAX_SCAN_TIME_SEC = 30
MAX_SIGNAL_TIME_SEC = 30
MAX_FILTER_TIME_SEC = 15
MAX_EXECUTION_TIME_SEC = 60
TOTAL_CYCLE_TIMEOUT_SEC = 180

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
            # ✅ Verificar se estamos banidos da Binance
            if binance_client.is_banned():
                remaining = binance_client.get_ban_remaining()
                logger.warning(f"⏸️ Trading loop pausado - Ban da Binance: {remaining:.0f}s restantes")
                await asyncio.sleep(min(remaining + 5, 60))  # Wait up to 60s, then recheck
                continue

            # ✅ NOVO PR1: Gerar cycle_id único para correlação de eventos
            cycle_id = str(uuid.uuid4())
            supervisor.heartbeat("trading_loop") # ✅ Heartbeat

            try:
                cycle_start_time = time.time()
                
                # ✅ NOVO PR1: Log de início de ciclo com context tracking
                logger.info(
                    json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": "INFO",
                        "component": "trading_loop",
                        "cycle_id": cycle_id,
                        "event": "cycle_start",
                        "data": {
                            "cycle_number": getattr(self, '_cycle_count', 0)
                        }
                    })
                )
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
                settings = get_settings()
                if getattr(settings, "PNL_DIVERGENCE_BLOCK_ENABLED", True):
                    divergence = await check_pnl_divergence()
                    if divergence.get("warning"):
                        logger.warning(
                            "PnL divergence detected. Pausing executions until reconciliation. "
                            f"delta={divergence.get('realized_delta')} "
                            f"pct={divergence.get('pct_delta')}%"
                        )
                        await asyncio.sleep(self.bot_config.scan_interval)
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
                
                # ✅ NOVO PR1: Validação de latência de scan
                if scan_time > MAX_SCAN_TIME_SEC:
                    logger.warning(
                        json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "WARNING",
                            "component": "trading_loop",
                            "cycle_id": cycle_id,
                            "event": "latency_validation_failed",
                            "data": {
                                "stage": "scan",
                                "actual_time_sec": round(scan_time, 3),
                                "max_time_sec": MAX_SCAN_TIME_SEC,
                                "exceeded_by_sec": round(scan_time - MAX_SCAN_TIME_SEC, 3)
                            }
                        })
                    )
                
                logger.info(f"📊 {len(scan_results)} símbolos escaneados (tempo: {scan_time:.2f}s)")

                if not scan_results:
                    logger.warning("❌ Nenhum símbolo encontrado no scan")
                    self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                signal_start = time.time()
                signals = await signal_generator.generate_signal(scan_results)
                signal_time = time.time() - signal_start
                cycle_metrics["latencies"]["signal_generation_time_sec"] = round(signal_time, 3)
                cycle_metrics["signals_generated"] = len(signals)
                
                # ✅ PASSO 4: Registrar sinais gerados no metrics dashboard
                for _ in range(len(signals)):
                    metrics_dashboard.record_signal_received()
                    if signal_time > 0:
                        metrics_dashboard.record_signal_latency(signal_time * 1000)  # Converter para ms
                
                # ✅ NOVO PR1: Validação de latência de geração de sinal
                if signal_time > MAX_SIGNAL_TIME_SEC:
                    logger.warning(
                        json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "WARNING",
                            "component": "trading_loop",
                            "cycle_id": cycle_id,
                            "event": "latency_validation_failed",
                            "data": {
                                "stage": "signal_generation",
                                "actual_time_sec": round(signal_time, 3),
                                "max_time_sec": MAX_SIGNAL_TIME_SEC,
                                "exceeded_by_sec": round(signal_time - MAX_SIGNAL_TIME_SEC, 3),
                                "symbols_scanned": len(scan_results)
                            }
                        })
                    )

                if not signals:
                    logger.info("❌ Nenhum sinal gerado")
                    self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
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
                
                # ✅ NOVO PR1: Validação de latência de filtro
                if filter_time > MAX_FILTER_TIME_SEC:
                    logger.warning(
                        json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "WARNING",
                            "component": "trading_loop",
                            "cycle_id": cycle_id,
                            "event": "latency_validation_failed",
                            "data": {
                                "stage": "market_filter",
                                "actual_time_sec": round(filter_time, 3),
                                "max_time_sec": MAX_FILTER_TIME_SEC,
                                "exceeded_by_sec": round(filter_time - MAX_FILTER_TIME_SEC, 3),
                                "signals_filtered": market_filter_rejected
                            }
                        })
                    )

                if not approved_signals:
                    logger.warning("❌ Todos os sinais foram bloqueados pelo market filter")
                    self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
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
                
                # ✅ NOVO PR1: Validação de latência de filtro de correlação (parte do filter_time_sec)
                total_filter_time = cycle_metrics["latencies"]["filter_time_sec"]
                if total_filter_time > MAX_FILTER_TIME_SEC:
                    logger.warning(
                        json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "WARNING",
                            "component": "trading_loop",
                            "cycle_id": cycle_id,
                            "event": "latency_validation_failed",
                            "data": {
                                "stage": "correlation_filter",
                                "actual_time_sec": round(total_filter_time, 3),
                                "max_time_sec": MAX_FILTER_TIME_SEC,
                                "exceeded_by_sec": round(total_filter_time - MAX_FILTER_TIME_SEC, 3),
                                "correlation_time_sec": round(correlation_time, 3)
                            }
                        })
                    )

                if not filtered_signals:
                    logger.warning("❌ Todos os sinais foram filtrados por correlação")
                    self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                logger.info(f"📊 {len(filtered_signals)} sinal(is) após filtro de correlação")

                final_signals = [s for s in filtered_signals if not position_monitor.is_symbol_blacklisted(s['symbol'])]
                blacklist_rejected = len(filtered_signals) - len(final_signals)
                cycle_metrics["signals_final"] = len(final_signals)
                cycle_metrics["rejection_reasons"]["blacklist"] = blacklist_rejected

                if not final_signals:
                    logger.warning("❌ Todos os sinais estão no blacklist")
                    self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
                    
                    # ✅ PASSO 4: Registrar sinais rejeitados pelo blacklist
                    metrics_dashboard.record_signal_rejected()
                    
                    await asyncio.sleep(self.bot_config.scan_interval)
                    continue

                signals_to_execute = final_signals[:available_slots]
                logger.info(f"📤 Executando {len(signals_to_execute)} sinal(is) (limite: {available_slots} slots)")

                execution_start = time.time()
                executed_count = 0
                failed_count = 0

                for idx, signal in enumerate(signals_to_execute):
                    # ✅ NOVO PR1: Gerar trade_id único para correlação
                    trade_id = str(uuid.uuid4())
                    
                    try:
                        logger.info(
                            json.dumps({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "level": "INFO",
                                "component": "trading_loop",
                                "cycle_id": cycle_id,
                                "trade_id": trade_id,
                                "event": "trade_execution_start",
                                "data": {
                                    "symbol": signal['symbol'],
                                    "direction": signal['direction'],
                                    "score": signal.get('score', 0),
                                    "sequence": idx + 1,
                                    "total_to_execute": len(signals_to_execute)
                                }
                            })
                        )
                        
                        # ✅ PASSO 4: Registrar ordem colocada
                        metrics_dashboard.record_order_placed()
                        
                        trade_execution_start = time.time()
                        result = await order_executor.execute_signal(
                            signal=signal,
                            account_balance=account_balance,
                            open_positions=open_positions_count + executed_count,
                            dry_run=self.bot_config.dry_run
                        )
                        trade_execution_time = time.time() - trade_execution_start
                        if result['success']:
                            # ✅ PASSO 4: Registrar ordem preenchida
                            metrics_dashboard.record_order_filled()
                            metrics_dashboard.record_execution_latency(trade_execution_time * 1000)  # Converter para ms
                            
                            executed_count +=1
                            cycle_metrics["execution_results"].append({
                                "symbol": signal['symbol'], 
                                "success": True,
                                "trade_id": trade_id
                            })
                            logger.info(
                                json.dumps({
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "level": "INFO",
                                    "component": "trading_loop",
                                    "cycle_id": cycle_id,
                                    "trade_id": trade_id,
                                    "event": "trade_execution_success",
                                    "data": {
                                        "symbol": signal['symbol'],
                                        "direction": signal['direction'],
                                        "entry_price": result.get('entry_price'),
                                        "quantity": result.get('quantity')
                                    }
                                })
                            )
                        else:
                            # ✅ PASSO 4: Registrar ordem rejeitada
                            metrics_dashboard.record_order_rejected()
                            
                            failed_count +=1
                            reason = result.get('reason', 'Unknown')
                            cycle_metrics["execution_results"].append({
                                "symbol": signal['symbol'], 
                                "success": False, 
                                "reason": reason,
                                "trade_id": trade_id
                            })
                            if "risk" in reason.lower():
                                cycle_metrics["rejection_reasons"]["risk_manager"] = cycle_metrics["rejection_reasons"].get("risk_manager", 0) + 1
                            else:
                                cycle_metrics["rejection_reasons"]["execution_failed"] = cycle_metrics["rejection_reasons"].get("execution_failed", 0) + 1
                            logger.warning(
                                json.dumps({
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "level": "WARNING",
                                    "component": "trading_loop",
                                    "cycle_id": cycle_id,
                                    "trade_id": trade_id,
                                    "event": "trade_execution_failed",
                                    "data": {
                                        "symbol": signal['symbol'],
                                        "reason": reason
                                    }
                                })
                            )
                        await asyncio.sleep(2)
                    except Exception as e:
                        failed_count += 1
                        logger.error(
                            json.dumps({
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "level": "ERROR",
                                "component": "trading_loop",
                                "cycle_id": cycle_id,
                                "trade_id": trade_id,
                                "event": "trade_execution_error",
                                "data": {
                                    "symbol": signal.get('symbol', 'UNKNOWN'),
                                    "error": str(e)
                                }
                            })
                        )
                        cycle_metrics["execution_results"].append({
                            "symbol": signal.get('symbol', 'UNKNOWN'), 
                            "success": False, 
                            "reason": str(e),
                            "trade_id": trade_id
                        })

                execution_time = time.time() - execution_start
                cycle_metrics["latencies"]["execution_time_sec"] = round(execution_time, 3)
                cycle_metrics["signals_executed"] = executed_count
                cycle_metrics["signals_failed"] = failed_count
                
                # ✅ NOVO PR1: Validação de latência de execução
                if execution_time > MAX_EXECUTION_TIME_SEC:
                    logger.warning(
                        json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "level": "WARNING",
                            "component": "trading_loop",
                            "cycle_id": cycle_id,
                            "event": "latency_validation_failed",
                            "data": {
                                "stage": "execution",
                                "actual_time_sec": round(execution_time, 3),
                                "max_time_sec": MAX_EXECUTION_TIME_SEC,
                                "exceeded_by_sec": round(execution_time - MAX_EXECUTION_TIME_SEC, 3),
                                "signals_to_execute": len(signals_to_execute)
                            }
                        })
                    )
                
                logger.info(f"✅ {executed_count} trade(s) executado(s) neste ciclo (falhas: {failed_count}, tempo: {execution_time:.2f}s)")

                self._finalize_cycle(cycle_metrics, cycle_start_time, cycle_id)
                
                # ✅ NOVO PR1: Incrementar contador de ciclos
                self._cycle_count = getattr(self, '_cycle_count', 0) + 1
                await asyncio.sleep(self.bot_config.scan_interval)

            except Exception as e:
                logger.error(
                    json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": "ERROR",
                        "component": "trading_loop",
                        "cycle_id": cycle_id,
                        "event": "cycle_error",
                        "data": {
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        }
                    })
                )
                if 'cycle_metrics' in locals():
                    self._finalize_cycle(cycle_metrics, cycle_start_time if 'cycle_start_time' in locals() else time.time(), cycle_id)
                await asyncio.sleep(60)

    def _finalize_cycle(self, cycle_metrics: Dict, cycle_start_time: float, cycle_id: str = None):
        """✅ NOVO PR1: Finalizar ciclo com context tracking e validação de tempo total"""
        total_cycle_time = time.time() - cycle_start_time
        cycle_metrics["latencies"]["total_cycle_time_sec"] = round(total_cycle_time, 3)
        cycle_metrics["cycle_id"] = cycle_id  # ✅ Adicionar cycle_id às métricas
        
        # ✅ NOVO PR1: Validação de tempo total do ciclo
        if total_cycle_time > TOTAL_CYCLE_TIMEOUT_SEC:
            logger.error(
                json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "ERROR",
                    "component": "trading_loop",
                    "cycle_id": cycle_id,
                    "event": "cycle_timeout",
                    "data": {
                        "actual_time_sec": round(total_cycle_time, 3),
                        "max_time_sec": TOTAL_CYCLE_TIMEOUT_SEC,
                        "exceeded_by_sec": round(total_cycle_time - TOTAL_CYCLE_TIMEOUT_SEC, 3),
                        "latencies_breakdown": cycle_metrics["latencies"]
                    }
                })
            )
        elif total_cycle_time > 300:
            logger.warning(f"⚠️ Ciclo demorou {total_cycle_time/60:.1f} minutos")
        
        logger.debug(f"📊 Cycle metrics: {json.dumps(cycle_metrics)}")
        metrics_collector.record_cycle(cycle_metrics)
