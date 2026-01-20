"""
✅ PASSO 4: DASHBOARD DE MÉTRICAS EM TEMPO REAL

Este módulo coleta e exibe métricas de performance do sistema em tempo real:
- Latência de execução
- Taxa de sucesso de ordens
- Taxa de sinais processados por hora
- Uso de recursos (memória, CPU)
- Status da conexão Binance
- Estatísticas de trades (win rate, PnL, etc.)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import psutil
import time
from utils.logger import setup_logger
from utils.redis_client import redis_client

logger = setup_logger("metrics_dashboard")

class MetricsDashboard:
    """Dashboard de métricas em tempo real para monitoramento do sistema"""
    
    def __init__(self):
        # Métricas de latência (últimas 100 medições)
        self.execution_latencies = deque(maxlen=100)
        self.signal_generation_latencies = deque(maxlen=100)
        self.api_call_latencies = deque(maxlen=100)
        
        # Métricas de ordens
        self.orders_placed = 0
        self.orders_filled = 0
        self.orders_failed = 0
        self.orders_rejected = 0
        
        # Métricas de sinais
        self.signals_received = 0
        self.signals_processed = 0
        self.signals_rejected = 0
        self.signals_per_hour = deque(maxlen=24)  # Últimas 24 horas
        
        # Métricas de trades
        self.trades_won = 0
        self.trades_lost = 0
        self.realized_pnl = 0.0
        
        # Status do sistema
        self.start_time = time.time()
        self.last_api_call = time.time()
        self.api_errors_last_hour = 0
        self.binance_connection_status = "CONNECTED"
        
        # Métricas de recursos
        self.memory_usage_samples = deque(maxlen=60)  # Últimos 60 segundos
        self.cpu_usage_samples = deque(maxlen=60)
        
        # Stress test metrics
        self.stress_test_active = False
        self.stress_test_signals_processed = 0
        self.stress_test_start_time = None
        self.stress_test_peak_concurrent = 0
        
        logger.info("✅ MetricsDashboard inicializado")
    
    def record_execution_latency(self, latency_ms: float):
        """Registra latência de execução de ordem"""
        self.execution_latencies.append(latency_ms)
        logger.debug(f"Latência execução: {latency_ms:.2f}ms")
    
    def record_signal_latency(self, latency_ms: float):
        """Registra latência de geração de sinal"""
        self.signal_generation_latencies.append(latency_ms)
        logger.debug(f"Latência sinal: {latency_ms:.2f}ms")
    
    def record_api_call_latency(self, latency_ms: float):
        """Registra latência de chamada à API"""
        self.api_call_latencies.append(latency_ms)
        self.last_api_call = time.time()
        logger.debug(f"Latência API: {latency_ms:.2f}ms")
    
    def record_order_placed(self):
        """Registra ordem colocada"""
        self.orders_placed += 1
        logger.debug(f"Ordens colocadas: {self.orders_placed}")
    
    def record_order_filled(self):
        """Registra ordem preenchida"""
        self.orders_filled += 1
        logger.debug(f"Ordens preenchidas: {self.orders_filled}")
    
    def record_order_failed(self):
        """Registra ordem falhada"""
        self.orders_failed += 1
        logger.debug(f"Ordens falhadas: {self.orders_failed}")
    
    def record_order_rejected(self):
        """Registra ordem rejeitada"""
        self.orders_rejected += 1
        logger.debug(f"Ordens rejeitadas: {self.orders_rejected}")
    
    def record_signal_received(self):
        """Registra sinal recebido"""
        self.signals_received += 1
        logger.debug(f"Sinais recebidos: {self.signals_received}")
    
    def record_signal_processed(self):
        """Registra sinal processado"""
        self.signals_processed += 1
        logger.debug(f"Sinais processados: {self.signals_processed}")
    
    def record_signal_rejected(self):
        """Registra sinal rejeitado"""
        self.signals_rejected += 1
        logger.debug(f"Sinais rejeitados: {self.signals_rejected}")
    
    def record_trade_won(self, pnl: float):
        """Registra trade vencedor"""
        self.trades_won += 1
        self.realized_pnl += pnl
        logger.debug(f"Trades ganhos: {self.trades_won}, PnL: {self.realized_pnl:.2f}")
    
    def record_trade_lost(self, pnl: float):
        """Registra trade perdedor"""
        self.trades_lost += 1
        self.realized_pnl += pnl
        logger.debug(f"Trades perdidos: {self.trades_lost}, PnL: {self.realized_pnl:.2f}")
    
    def record_api_error(self):
        """Registra erro de API"""
        self.api_errors_last_hour += 1
        logger.debug(f"Erros API (última hora): {self.api_errors_last_hour}")
    
    def update_binance_status(self, status: str):
        """Atualiza status da conexão Binance"""
        self.binance_connection_status = status
        logger.info(f"Status Binance: {status}")
    
    def collect_system_metrics(self):
        """Coleta métricas de recursos do sistema"""
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            
            self.memory_usage_samples.append(mem.percent)
            self.cpu_usage_samples.append(cpu)
            
            logger.debug(f"Memória: {mem.percent:.1f}%, CPU: {cpu:.1f}%")
        except Exception as e:
            logger.warning(f"Erro ao coletar métricas do sistema: {e}")
    
    def calculate_signals_per_hour(self) -> float:
        """Calcula sinais processados por hora (últimas 24h)"""
        now = time.time()
        hour_ago = now - 3600
        
        # Conta sinais da última hora (simulado - na prática usar Redis)
        return self.signals_processed / max(1, (now - self.start_time) / 3600)
    
    def get_execution_stats(self) -> Dict:
        """Retorna estatísticas de execução"""
        if not self.execution_latencies:
            return {}
        
        latencies = list(self.execution_latencies)
        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p50_latency_ms": sorted(latencies)[len(latencies) // 2],
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "total_orders": self.orders_placed,
            "filled_orders": self.orders_filled,
            "failed_orders": self.orders_failed,
            "rejected_orders": self.orders_rejected,
            "success_rate": self.orders_filled / max(1, self.orders_placed) * 100
        }
    
    def get_signal_stats(self) -> Dict:
        """Retorna estatísticas de sinais"""
        if not self.signal_generation_latencies:
            return {}
        
        latencies = list(self.signal_generation_latencies)
        return {
            "signals_received": self.signals_received,
            "signals_processed": self.signals_processed,
            "signals_rejected": self.signals_rejected,
            "avg_signal_latency_ms": sum(latencies) / len(latencies),
            "min_signal_latency_ms": min(latencies),
            "max_signal_latency_ms": max(latencies),
            "signals_per_hour": self.calculate_signals_per_hour(),
            "rejection_rate": self.signals_rejected / max(1, self.signals_received) * 100
        }
    
    def get_trade_stats(self) -> Dict:
        """Retorna estatísticas de trades"""
        total_trades = self.trades_won + self.trades_lost
        if total_trades == 0:
            return {}
        
        return {
            "total_trades": total_trades,
            "trades_won": self.trades_won,
            "trades_lost": self.trades_lost,
            "win_rate": self.trades_won / total_trades * 100,
            "realized_pnl": self.realized_pnl,
            "avg_pnl_per_trade": self.realized_pnl / total_trades
        }
    
    def get_system_stats(self) -> Dict:
        """Retorna estatísticas do sistema"""
        if not self.memory_usage_samples or not self.cpu_usage_samples:
            return {}
        
        mem = list(self.memory_usage_samples)
        cpu = list(self.cpu_usage_samples)
        
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "memory_usage_avg_percent": sum(mem) / len(mem),
            "memory_usage_max_percent": max(mem),
            "cpu_usage_avg_percent": sum(cpu) / len(cpu),
            "cpu_usage_max_percent": max(cpu),
            "api_errors_last_hour": self.api_errors_last_hour,
            "binance_connection_status": self.binance_connection_status,
            "last_api_call_seconds_ago": time.time() - self.last_api_call
        }
    
    def get_stress_test_stats(self) -> Dict:
        """Retorna estatísticas do stress test"""
        if not self.stress_test_active:
            return {"active": False}
        
        duration = time.time() - self.stress_test_start_time if self.stress_test_start_time else 0
        
        return {
            "active": True,
            "signals_processed": self.stress_test_signals_processed,
            "duration_seconds": duration,
            "signals_per_second": self.stress_test_signals_processed / max(1, duration),
            "peak_concurrent": self.stress_test_peak_concurrent
        }
    
    def start_stress_test(self):
        """Inicia modo de stress test"""
        self.stress_test_active = True
        self.stress_test_start_time = time.time()
        self.stress_test_signals_processed = 0
        self.stress_test_peak_concurrent = 0
        logger.info("🚀 Stress test iniciado")
    
    def stop_stress_test(self):
        """Para modo de stress test"""
        if not self.stress_test_active:
            return
        
        duration = time.time() - self.stress_test_start_time
        logger.info(f"🛑 Stress test finalizado: {self.stress_test_signals_processed} sinais em {duration:.2f}s")
        
        self.stress_test_active = False
        self.stress_test_start_time = None
    
    def record_stress_signal(self, concurrent: int = 0):
        """Registra sinal processado durante stress test"""
        if not self.stress_test_active:
            return
        
        self.stress_test_signals_processed += 1
        self.stress_test_peak_concurrent = max(self.stress_test_peak_concurrent, concurrent)
    
    def get_full_dashboard(self) -> Dict:
        """Retorna dashboard completo de métricas"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "execution": self.get_execution_stats(),
            "signals": self.get_signal_stats(),
            "trades": self.get_trade_stats(),
            "system": self.get_system_stats(),
            "stress_test": self.get_stress_test_stats()
        }
    
    def print_dashboard(self):
        """Imprime dashboard formatado no console"""
        dashboard = self.get_full_dashboard()
        
        print("\n" + "="*60)
        print("📊 METRICS DASHBOARD - VECTOR PROTOCOL")
        print("="*60)
        print(f"⏰ Timestamp: {dashboard['timestamp']}")
        print(f"⏱️  Uptime: {dashboard['system'].get('uptime_hours', 0):.2f}h")
        
        # Execution Stats
        if dashboard['execution']:
            exec_stats = dashboard['execution']
            print("\n📈 EXECUTION STATS:")
            print(f"  Total Orders: {exec_stats['total_orders']}")
            print(f"  Filled: {exec_stats['filled_orders']} ({exec_stats['success_rate']:.1f}%)")
            print(f"  Failed: {exec_stats['failed_orders']}")
            print(f"  Rejected: {exec_stats['rejected_orders']}")
            print(f"  Avg Latency: {exec_stats['avg_latency_ms']:.2f}ms")
            print(f"  P95 Latency: {exec_stats['p95_latency_ms']:.2f}ms")
            print(f"  P99 Latency: {exec_stats['p99_latency_ms']:.2f}ms")
        
        # Signal Stats
        if dashboard['signals']:
            sig_stats = dashboard['signals']
            print("\n📡 SIGNAL STATS:")
            print(f"  Received: {sig_stats['signals_received']}")
            print(f"  Processed: {sig_stats['signals_processed']}")
            print(f"  Rejected: {sig_stats['signals_rejected']} ({sig_stats['rejection_rate']:.1f}%)")
            print(f"  Avg Signal Latency: {sig_stats.get('avg_signal_latency_ms', 0):.2f}ms")
            print(f"  Signals/Hour: {sig_stats['signals_per_hour']:.1f}")
        
        # Trade Stats
        if dashboard['trades']:
            trade_stats = dashboard['trades']
            print("\n💰 TRADE STATS:")
            print(f"  Total Trades: {trade_stats['total_trades']}")
            print(f"  Won: {trade_stats['trades_won']}")
            print(f"  Lost: {trade_stats['trades_lost']}")
            print(f"  Win Rate: {trade_stats['win_rate']:.1f}%")
            print(f"  Realized PnL: ${trade_stats['realized_pnl']:.2f}")
            print(f"  Avg PnL/Trade: ${trade_stats['avg_pnl_per_trade']:.2f}")
        
        # System Stats
        if dashboard['system']:
            sys_stats = dashboard['system']
            print("\n🖥️  SYSTEM STATS:")
            print(f"  Memory: {sys_stats['memory_usage_avg_percent']:.1f}% (max: {sys_stats['memory_usage_max_percent']:.1f}%)")
            print(f"  CPU: {sys_stats['cpu_usage_avg_percent']:.1f}% (max: {sys_stats['cpu_usage_max_percent']:.1f}%)")
            print(f"  API Errors (1h): {sys_stats['api_errors_last_hour']}")
            print(f"  Binance Status: {sys_stats['binance_connection_status']}")
        
        # Stress Test Stats
        if dashboard['stress_test'].get('active'):
            stress_stats = dashboard['stress_test']
            print("\n🔥 STRESS TEST:")
            print("  Active: YES")
            print(f"  Signals: {stress_stats['signals_processed']}")
            print(f"  Duration: {stress_stats['duration_seconds']:.2f}s")
            print(f"  Rate: {stress_stats['signals_per_second']:.1f} signals/s")
            print(f"  Peak Concurrent: {stress_stats['peak_concurrent']}")
        
        print("\n" + "="*60 + "\n")
    
    async def publish_to_redis(self):
        """Publica métricas no Redis para consumo do frontend"""
        if not redis_client.client:
            return
        
        try:
            dashboard = self.get_full_dashboard()
            await redis_client.client.setex(
                "metrics:dashboard",
                5,  # TTL de 5 segundos
                dashboard
            )
            logger.debug("✅ Métricas publicadas no Redis")
        except Exception as e:
            logger.warning(f"Erro ao publicar métricas no Redis: {e}")

# Instância global
metrics_dashboard = MetricsDashboard()
