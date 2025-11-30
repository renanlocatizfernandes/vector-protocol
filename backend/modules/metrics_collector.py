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
        """Retorna um resumo dos ciclos de trading."""
        with self._lock:
            total_cycles = len(self._metrics["cycles"])
            if total_cycles == 0:
                return {"total_cycles": 0}

            total_signals = sum(c.get("signals_generated", 0) for c in self._metrics["cycles"])
            total_executed = sum(c.get("signals_executed", 0) for c in self._metrics["cycles"])
            
            latencies = {
                "scan_time_sec": [],
                "signal_generation_time_sec": [],
                "filter_time_sec": [],
                "execution_time_sec": [],
                "total_cycle_time_sec": []
            }

            for cycle in self._metrics["cycles"]:
                for key, value in cycle.get("latencies", {}).items():
                    if key in latencies:
                        latencies[key].append(value)
            
            avg_latencies = {
                f"avg_{key}": sum(values) / len(values) if values else 0
                for key, values in latencies.items()
            }

            return {
                "total_cycles": total_cycles,
                "total_signals_generated": total_signals,
                "total_trades_executed": total_executed,
                "avg_latencies": avg_latencies
            }

metrics_collector = MetricsCollector()
