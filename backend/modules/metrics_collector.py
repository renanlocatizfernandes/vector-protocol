"""
Metrics Collector

Este módulo é responsável por coletar e agregar métricas de todos os outros módulos do bot.
Ele fornece uma interface centralizada para registrar e consultar métricas de performance,
latência, e outros KPIs importantes.
"""

import time
from typing import Dict, Any, List
import threading

class MetricsCollector:
    def __init__(self):
        self._metrics = {
            "cycles": [],
            "signals": [],
            "orders": [],
            "positions": [],
            "performance": {
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
            }
        }
        self._lock = threading.Lock()

    def record_cycle(self, cycle_data: Dict[str, Any]):
        """Registra as métricas de um ciclo de trading."""
        print(f"DEBUG: record_cycle called with {cycle_data.keys()}")
        with self._lock:
            self._metrics["cycles"].append(cycle_data)
            # Manter apenas os últimos 100 ciclos para não consumir muita memória
            if len(self._metrics["cycles"]) > 100:
                self._metrics["cycles"].pop(0)

    def record_signal(self, signal_data: Dict[str, Any]):
        """Registra um sinal gerado."""
        with self._lock:
            self._metrics["signals"].append(signal_data)
            if len(self._metrics["signals"]) > 500:
                self._metrics["signals"].pop(0)

    def record_order(self, order_data: Dict[str, Any]):
        """Registra uma ordem executada."""
        with self._lock:
            self._metrics["orders"].append(order_data)
            if len(self._metrics["orders"]) > 1000:
                self._metrics["orders"].pop(0)

    def update_performance(self, performance_data: Dict[str, Any]):
        """Atualiza as métricas de performance geral."""
        with self._lock:
            self._metrics["performance"].update(performance_data)

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna um snapshot das métricas atuais."""
        with self._lock:
            # Retorna uma cópia para evitar modificações externas
            return self._metrics.copy()

    def get_cycle_summary(self) -> Dict[str, Any]:
        """Retorna um resumo detalhado dos ciclos de trading compatível com o frontend."""
        with self._lock:
            total_cycles = len(self._metrics["cycles"])
            if total_cycles == 0:
                return {
                    "total_cycles": 0,
                    "cycles_with_trades": 0,
                    "cycles_without_trades": 0,
                    "signals": {
                        "total_generated": 0,
                        "total_approved": 0,
                        "total_rejected": 0,
                        "approval_rate_pct": 0.0
                    },
                    "rejection_reasons": {
                        "market_filter": 0,
                        "correlation_filter": 0,
                        "blacklist": 0,
                        "risk_manager": 0,
                        "execution_failed": 0
                    },
                    "latencies": {
                        "avg_scan_time_sec": 0, "max_scan_time_sec": 0, "min_scan_time_sec": 0,
                        "avg_signal_generation_time_sec": 0, "max_signal_generation_time_sec": 0, "min_signal_generation_time_sec": 0,
                        "avg_filter_time_sec": 0, "max_filter_time_sec": 0, "min_filter_time_sec": 0,
                        "avg_execution_time_sec": 0, "max_execution_time_sec": 0, "min_execution_time_sec": 0,
                        "avg_total_cycle_time_sec": 0, "max_total_cycle_time_sec": 0, "min_total_cycle_time_sec": 0
                    },
                    "execution": {
                        "total_attempted": 0,
                        "total_successful": 0,
                        "total_failed": 0,
                        "success_rate_pct": 0.0
                    },
                    "recent_cycles": []
                }

            # Aggregations
            cycles_with_trades = sum(1 for c in self._metrics["cycles"] if c.get("signals_executed", 0) > 0)
            cycles_without_trades = total_cycles - cycles_with_trades
            
            total_generated = sum(c.get("signals_generated", 0) for c in self._metrics["cycles"])
            total_executed = sum(c.get("signals_executed", 0) for c in self._metrics["cycles"])
            # Assuming approved ~= executed for now if not tracked separately
            total_approved = total_executed 
            total_rejected = total_generated - total_approved
            approval_rate = (total_approved / total_generated * 100) if total_generated > 0 else 0.0

            # Latencies
            lat_keys = [
                "scan_time_sec", "signal_generation_time_sec", "filter_time_sec", 
                "execution_time_sec", "total_cycle_time_sec"
            ]
            lat_stats = {}
            for key in lat_keys:
                values = [c.get("latencies", {}).get(key, 0) for c in self._metrics["cycles"] if c.get("latencies", {}).get(key) is not None]
                if values:
                    lat_stats[f"avg_{key}"] = sum(values) / len(values)
                    lat_stats[f"max_{key}"] = max(values)
                    lat_stats[f"min_{key}"] = min(values)
                else:
                    lat_stats[f"avg_{key}"] = 0
                    lat_stats[f"max_{key}"] = 0
                    lat_stats[f"min_{key}"] = 0

            # Execution
            # Assuming attempted = executed for now
            total_attempted = total_executed
            total_successful = total_executed # Simplified
            total_failed = 0 # Simplified
            success_rate = 100.0 if total_attempted > 0 else 0.0

            return {
                "total_cycles": total_cycles,
                "cycles_with_trades": cycles_with_trades,
                "cycles_without_trades": cycles_without_trades,
                "signals": {
                    "total_generated": total_generated,
                    "total_approved": total_approved,
                    "total_rejected": total_rejected,
                    "approval_rate_pct": approval_rate
                },
                "rejection_reasons": {
                    "market_filter": 0, # Placeholder
                    "correlation_filter": 0, # Placeholder
                    "blacklist": 0, # Placeholder
                    "risk_manager": 0, # Placeholder
                    "execution_failed": 0 # Placeholder
                },
                "latencies": lat_stats,
                "execution": {
                    "total_attempted": total_attempted,
                    "total_successful": total_successful,
                    "total_failed": total_failed,
                    "success_rate_pct": success_rate
                },
                "recent_cycles": self._metrics["cycles"][-10:] # Last 10 cycles
            }

metrics_collector = MetricsCollector()
