import asyncio
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Optional
from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("supervisor")

class Supervisor:
    def __init__(self):
        self.settings = get_settings()
        self.heartbeats: Dict[str, float] = {}
        self.thresholds: Dict[str, int] = {
            "trading_loop": 120,      # 2 minutos sem heartbeat = freeze
            "sniper_loop": 300,       # 5 minutos
            "dca_loop": 300,          # 5 minutos
            "position_monitor": 60    # 1 minuto
        }
        self.bot_instance = None  # Referência ao bot para restart
        self.restart_count = 0
        self.last_restart_time = 0
        self.is_monitoring = False

    def register_bot(self, bot):
        """Registra a instância do bot para controle"""
        self.bot_instance = bot

    def heartbeat(self, component: str):
        """Recebe 'pulso' de um componente"""
        self.heartbeats[component] = time.time()
        # logger.debug(f"💓 Heartbeat: {component}")

    async def start_monitoring(self):
        """Inicia loop de monitoramento"""
        if self.is_monitoring: return
        self.is_monitoring = True
        logger.info("🛡️ Supervisor iniciado: Monitorando heartbeats e recursos...")
        
        while self.is_monitoring:
            try:
                await self._check_health()
                await self._monitor_resources()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Erro no loop do Supervisor: {e}")
                await asyncio.sleep(10)

    async def stop_monitoring(self):
        self.is_monitoring = False
        logger.info("🛡️ Supervisor parado")

    async def _check_health(self):
        """Verifica se algum componente parou de responder"""
        now = time.time()
        for component, last_beat in self.heartbeats.items():
            threshold = self.thresholds.get(component, 120)
            if now - last_beat > threshold:
                logger.error(f"💀 COMPONENTE MORTO: {component} (sem heartbeat há {int(now - last_beat)}s)")
                await self._trigger_auto_heal(reason=f"{component} frozen")

    async def _monitor_resources(self):
        """Monitora uso de RAM/CPU"""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            
            if mem_mb > 1024:  # 1GB Limit
                logger.warning(f"⚠️ Uso de RAM alto: {mem_mb:.1f}MB")
                # Poderia reiniciar se crítico, por enquanto só loga
                
        except Exception as e:
            logger.error(f"Erro ao monitorar recursos: {e}")

    async def _trigger_auto_heal(self, reason: str):
        """Reinicia o bot em caso de falha crítica"""
        now = time.time()
        # Evitar loop de restarts (max 3 por hora)
        if now - self.last_restart_time < 3600 and self.restart_count >= 3:
            logger.critical(f"🚨 FALHA CRÍTICA: {reason}. Limite de restarts atingido. Intervenção manual necessária.")
            return

        logger.warning(f"🚑 AUTO-HEAL ATIVADO: {reason}. Reiniciando bot...")
        
        if self.bot_instance:
            try:
                self.bot_instance.stop()
                await asyncio.sleep(5)
                await self.bot_instance.start(dry_run=self.bot_instance.dry_run)
                
                self.restart_count += 1
                self.last_restart_time = now
                self.heartbeats.clear() # Reset heartbeats
                logger.info(f"✅ Bot reiniciado com sucesso (Restart #{self.restart_count})")
            except Exception as e:
                logger.error(f"❌ Falha ao reiniciar bot: {e}")

    def get_status(self) -> Dict:
        """Retorna relatório de saúde"""
        now = time.time()
        status = {}
        for comp, last in self.heartbeats.items():
            age = now - last
            status[comp] = {
                "status": "ok" if age < self.thresholds.get(comp, 120) else "frozen",
                "last_heartbeat_ago": f"{age:.1f}s"
            }
            
        return {
            "monitoring": self.is_monitoring,
            "restarts": self.restart_count,
            "components": status,
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            }
        }

# Singleton
supervisor = Supervisor()
