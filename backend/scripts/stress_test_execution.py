"""
✅ PASSO 5: STRESS TEST - 100+ SINAIS/HORA

Este script simula alto volume de sinais para testar a eficiência do motor de execução:
- Gera sinais sintéticos em alta velocidade
- Testa latência de processamento
- Verifica estabilidade sob carga
- Mede throughput de sinais por segundo
"""

import asyncio
import time
import random
import sys
import os
from datetime import datetime
from typing import Dict, List

# Adiciona o diretório backend ao PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.metrics_dashboard import metrics_dashboard
from utils.logger import setup_logger

logger = setup_logger("stress_test")

class StressTestExecutor:
    """Executor de stress test para o motor de trading"""
    
    def __init__(self, signals_per_hour: int = 120):
        """
        Args:
            signals_per_hour: Número de sinais a gerar por hora (padrão: 120 = 2 por minuto)
        """
        self.signals_per_hour = signals_per_hour
        self.interval_seconds = 3600 / signals_per_hour
        self.running = False
        self.signals_processed = 0
        self.signals_failed = 0
        self.start_time = None
        self.concurrent_signals = 0
        self.max_concurrent = 0
        
        logger.info(f"✅ StressTestExecutor inicializado: {signals_per_hour} sinais/hora")
    
    def generate_synthetic_signal(self, index: int) -> Dict:
        """Gera sinal sintético para teste"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        sides = ["LONG", "SHORT"]
        
        return {
            "signal_id": f"STRESS_{index}",
            "symbol": random.choice(symbols),
            "side": random.choice(sides),
            "score": random.randint(70, 100),
            "entry_price": random.uniform(100, 50000),
            "stop_loss": random.uniform(95, 49500),
            "take_profit": random.uniform(105, 50500),
            "leverage": random.randint(1, 20),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def process_signal(self, signal: Dict) -> bool:
        """Processa um sinal (simula execução real)"""
        try:
            # Registra sinal recebido
            metrics_dashboard.record_signal_received()
            
            # Simula latência de processamento (10-100ms)
            start_time = time.time()
            self.concurrent_signals += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent_signals)
            
            await asyncio.sleep(random.uniform(0.01, 0.1))  # 10-100ms
            
            # Simula sucesso/falha (95% sucesso)
            success = random.random() < 0.95
            
            if success:
                metrics_dashboard.record_signal_processed()
                metrics_dashboard.record_signal_latency((time.time() - start_time) * 1000)
                self.signals_processed += 1
                
                # Simula ordem preenchida
                metrics_dashboard.record_order_placed()
                metrics_dashboard.record_order_filled()
                metrics_dashboard.record_execution_latency(random.uniform(50, 200))
                
                # Simula trade resultado
                if random.random() < 0.6:  # 60% win rate
                    metrics_dashboard.record_trade_won(random.uniform(10, 100))
                else:
                    metrics_dashboard.record_trade_lost(random.uniform(-50, -10))
                
                logger.debug(f"✅ Sinal {signal['signal_id']} processado")
            else:
                metrics_dashboard.record_signal_rejected()
                metrics_dashboard.record_order_rejected()
                self.signals_failed += 1
                logger.debug(f"❌ Sinal {signal['signal_id']} rejeitado")
            
            # Registra stress test metric
            metrics_dashboard.record_stress_signal(self.concurrent_signals)
            
            self.concurrent_signals -= 1
            return success
            
        except Exception as e:
            logger.error(f"Erro ao processar sinal {signal['signal_id']}: {e}")
            self.signals_failed += 1
            metrics_dashboard.record_signal_rejected()
            self.concurrent_signals -= 1
            return False
    
    async def run_stress_test(self, duration_minutes: int = 5):
        """
        Executa stress test por um período específico
        
        Args:
            duration_minutes: Duração do teste em minutos
        """
        logger.info(f"🚀 Iniciando stress test: {self.signals_per_hour} sinais/hora por {duration_minutes} minutos")
        
        self.running = True
        self.start_time = time.time()
        self.signals_processed = 0
        self.signals_failed = 0
        self.max_concurrent = 0
        
        # Inicia stress test no dashboard
        metrics_dashboard.start_stress_test()
        
        # Cria tasks para processar sinais
        signal_index = 0
        tasks = []
        
        try:
            while self.running and (time.time() - self.start_time) < duration_minutes * 60:
                # Gera novo sinal
                signal = self.generate_synthetic_signal(signal_index)
                signal_index += 1
                
                # Processa sinal em background
                task = asyncio.create_task(self.process_signal(signal))
                tasks.append(task)
                
                # Aguarda intervalo até próximo sinal
                await asyncio.sleep(self.interval_seconds)
                
                # Limpa tasks completadas
                tasks = [t for t in tasks if not t.done()]
            
            # Aguarda todas as tasks completarem
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            logger.info("Stress test cancelado")
        except Exception as e:
            logger.error(f"Erro no stress test: {e}")
        finally:
            self.running = False
            metrics_dashboard.stop_stress_test()
            
            # Imprime resumo
            self.print_summary()
    
    def print_summary(self):
        """Imprime resumo do stress test"""
        duration = time.time() - self.start_time if self.start_time else 0
        total_signals = self.signals_processed + self.signals_failed
        
        print("\n" + "="*60)
        print("🔥 STRESS TEST SUMMARY")
        print("="*60)
        print(f"⏱️  Duration: {duration:.2f}s ({duration/60:.2f}min)")
        print(f"📊 Target Rate: {self.signals_per_hour} signals/hour")
        print(f"📈 Actual Rate: {total_signals / max(1, duration) * 3600:.1f} signals/hour")
        print(f"✅ Processed: {self.signals_processed}")
        print(f"❌ Failed: {self.signals_failed}")
        print(f"📊 Success Rate: {self.signals_processed / max(1, total_signals) * 100:.1f}%")
        print(f"🔀 Peak Concurrent: {self.max_concurrent}")
        print("="*60 + "\n")
    
    def stop(self):
        """Para o stress test"""
        self.running = False
        logger.info("🛑 Parando stress test...")


async def run_burst_test(num_signals: int = 100, max_concurrent: int = 20):
    """
    Teste de burst: processa N sinais simultâneos
    
    Args:
        num_signals: Número de sinais a processar
        max_concurrent: Máximo de sinais processados em paralelo
    """
    logger.info(f"💥 Iniciando BURST test: {num_signals} sinais, max_concurrent={max_concurrent}")
    
    executor = StressTestExecutor(signals_per_hour=1000)  # Alta taxa
    executor.running = True
    executor.start_time = time.time()
    
    metrics_dashboard.start_stress_test()
    
    # Gera sinais
    signals = [executor.generate_synthetic_signal(i) for i in range(num_signals)]
    
    # Processa com limite de concorrência
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(signal):
        async with semaphore:
            return await executor.process_signal(signal)
    
    try:
        # Executa todas as tasks
        start_time = time.time()
        results = await asyncio.gather(*[process_with_limit(s) for s in signals])
        duration = time.time() - start_time
        
        # Estatísticas
        successful = sum(1 for r in results if r)
        failed = len(results) - successful
        
        print("\n" + "="*60)
        print("💥 BURST TEST SUMMARY")
        print("="*60)
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"📊 Signals: {num_signals}")
        print(f"🔀 Max Concurrent: {max_concurrent}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Throughput: {num_signals / duration:.2f} signals/s")
        print(f"📊 Success Rate: {successful / num_signals * 100:.1f}%")
        print("="*60 + "\n")
        
    finally:
        metrics_dashboard.stop_stress_test()


async def main():
    """Função principal para executar testes de stress"""
    import sys
    
    print("\n🎯 STRESS TEST EXECUTION ENGINE")
    print("="*60)
    print("Escolha o tipo de teste:")
    print("1. Continuous Load (100 signals/hour for 5 minutes)")
    print("2. Burst Test (100 signals, max 20 concurrent)")
    print("3. High Load (500 signals/hour for 10 minutes)")
    print("4. Extreme Load (1000 signals/hour for 5 minutes)")
    print("="*60)
    
    try:
        choice = input("\nDigite sua escolha (1-4): ").strip()
        
        if choice == "1":
            # Teste contínuo moderado
            executor = StressTestExecutor(signals_per_hour=100)
            await executor.run_stress_test(duration_minutes=5)
            
        elif choice == "2":
            # Teste de burst
            await run_burst_test(num_signals=100, max_concurrent=20)
            
        elif choice == "3":
            # Carga alta
            executor = StressTestExecutor(signals_per_hour=500)
            await executor.run_stress_test(duration_minutes=10)
            
        elif choice == "4":
            # Carga extrema
            executor = StressTestExecutor(signals_per_hour=1000)
            await executor.run_stress_test(duration_minutes=5)
            
        else:
            print("❌ Opção inválida!")
            sys.exit(1)
        
        # Imprime dashboard final
        print("\n📊 FINAL DASHBOARD:")
        metrics_dashboard.print_dashboard()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Teste interrompido pelo usuário")
        metrics_dashboard.stop_stress_test()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
