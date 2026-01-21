import asyncio
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("supervisor")

# ✅ PR1.3: Validação de Estado do Sistema

class SystemStateError(Exception):
    """Exceção para erros de estado do sistema"""
    def __init__(self, component: str, reason: str, severity: str = "warning"):
        self.component = component
        self.reason = reason
        self.severity = severity  # warning, error, critical
        super().__init__(f"[{severity.upper()}] {component}: {reason}")

class Supervisor:
    def __init__(self):
        self.settings = get_settings()
        self.heartbeats: Dict[str, float] = {}
        self.thresholds: Dict[str, int] = {
            "trading_loop": 120,      # 2 minutos sem heartbeat = freeze
            "sniper_loop": 300,       # 5 minutos
            "dca_loop": 300,          # 5 minutos
            "pyramiding_loop": 240,   # 4 minutos
            "time_exit_loop": 400,    # 6.5 minutos
            "position_monitor": 60    # 1 minuto
        }
        self.bot_instance = None  # Referência ao bot para restart
        self.restart_count = 0
        self.last_restart_time = 0
        self.is_monitoring = False
        
        # ✅ PR1.3: Estado do sistema e validações
        self.system_state = {
            'circuit_breaker_active': False,
            'circuit_breaker_triggered_at': None,
            'circuit_breaker_reason': None,
            'circuit_breaker_cooldown_until': None,
            'last_validation_time': None,
            'validation_errors': [],
            'health_status': 'unknown'  # unknown, healthy, degraded, critical
        }
        
        # Thresholds de recursos
        self.resource_thresholds = {
            'memory_warning_mb': 1024,     # 1GB
            'memory_critical_mb': 2048,    # 2GB
            'cpu_warning_pct': 70,          # 70%
            'cpu_critical_pct': 90,         # 90%
            'disk_warning_pct': 80,         # 80%
            'disk_critical_pct': 90,        # 90%
        }
        
        # Histórico de estados para tendências
        self.state_history: List[Dict] = []
        self.max_history = 100  # Manter últimos 100 estados

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
        logger.info("🛡️ Supervisor iniciado: Monitorando heartbeats, recursos e circuit breaker...")
        
        while self.is_monitoring:
            try:
                await self._check_health()
                await self._monitor_resources()
                await self._check_circuit_breaker()
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
        
        # ✅ PR1.3: Validar health de todos os componentes
        health_issues = []
        
        for component, last_beat in list(self.heartbeats.items()):
            threshold = self.thresholds.get(component, 120)
            age = now - last_beat
            
            if age > threshold:
                error_msg = f"💀 COMPONENTE MORTO: {component} (sem heartbeat há {int(age)}s)"
                logger.error(error_msg)
                health_issues.append(SystemStateError(
                    component,
                    f"sem heartbeat há {int(age)}s (threshold={threshold}s)",
                    "critical"
                ))
                await self._trigger_auto_heal(reason=f"{component} frozen")
            elif age > threshold * 0.7:
                # Alerta pré-falha
                warning_msg = f"⚠️ COMPONENTE LENTO: {component} (último heartbeat há {int(age)}s)"
                logger.warning(warning_msg)
                health_issues.append(SystemStateError(
                    component,
                    f"último heartbeat há {int(age)}s (threshold={threshold}s)",
                    "warning"
                ))
        
        # Atualizar status de saúde
        if health_issues:
            critical = any(h.severity == "critical" for h in health_issues)
            self.system_state['health_status'] = 'critical' if critical else 'degraded'
            self.system_state['validation_errors'] = [
                {'component': h.component, 'reason': h.reason, 'severity': h.severity}
                for h in health_issues
            ]
        else:
            self.system_state['health_status'] = 'healthy'
            self.system_state['validation_errors'] = []
        
        self.system_state['last_validation_time'] = datetime.utcnow().isoformat()
        
        # Salvar no histórico
        self._save_state_to_history()

    async def _monitor_resources(self):
        """Monitora uso de RAM/CPU com validações e alertas"""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            cpu_pct = process.cpu_percent(interval=1)
            
            # ✅ PR1.3: Validar memória
            if mem_mb > self.resource_thresholds['memory_critical_mb']:
                logger.critical(f"🚨 RAM CRÍTICA: {mem_mb:.1f}MB (threshold={self.resource_thresholds['memory_critical_mb']}MB)")
                await self._trigger_auto_heal(reason=f"RAM crítica: {mem_mb:.1f}MB")
            elif mem_mb > self.resource_thresholds['memory_warning_mb']:
                logger.warning(f"⚠️ RAM ALTA: {mem_mb:.1f}MB (threshold={self.resource_thresholds['memory_warning_mb']}MB)")
            
            # ✅ PR1.3: Validar CPU
            if cpu_pct > self.resource_thresholds['cpu_critical_pct']:
                logger.critical(f"🚨 CPU CRÍTICA: {cpu_pct:.1f}% (threshold={self.resource_thresholds['cpu_critical_pct']}%)")
                await self._trigger_auto_heal(reason=f"CPU crítica: {cpu_pct:.1f}%")
            elif cpu_pct > self.resource_thresholds['cpu_warning_pct']:
                logger.warning(f"⚠️ CPU ALTA: {cpu_pct:.1f}% (threshold={self.resource_thresholds['cpu_warning_pct']}%)")
            
            # ✅ PR1.3: Validar disco
            try:
                disk = psutil.disk_usage('/')
                disk_pct = disk.percent
                
                if disk_pct > self.resource_thresholds['disk_critical_pct']:
                    logger.critical(f"🚨 DISCO CRÍTICO: {disk_pct:.1f}% (threshold={self.resource_thresholds['disk_critical_pct']}%)")
                elif disk_pct > self.resource_thresholds['disk_warning_pct']:
                    logger.warning(f"⚠️ DISCO ALTO: {disk_pct:.1f}% (threshold={self.resource_thresholds['disk_warning_pct']}%)")
            except Exception:
                pass  # Falha silenciosa ao verificar disco
                
        except Exception as e:
            logger.error(f"Erro ao monitorar recursos: {e}")

    async def _check_circuit_breaker(self):
        """✅ PR1.3: Verifica e gerencia circuit breaker"""
        if not self.system_state['circuit_breaker_active']:
            return  # Circuit breaker não está ativo
        
        # Verificar se cooldown expirou
        if self.system_state['circuit_breaker_cooldown_until']:
            cooldown_until = datetime.fromisoformat(self.system_state['circuit_breaker_cooldown_until'])
            if datetime.utcnow() >= cooldown_until:
                logger.info("✅ Circuit breaker cooldown expirado. Bot pode retomar operações.")
                self.system_state['circuit_breaker_active'] = False
                self.system_state['circuit_breaker_cooldown_until'] = None
                # Notificar bot para retomar operações
                if self.bot_instance and hasattr(self.bot_instance, 'resume_after_circuit_breaker'):
                    try:
                        await self.bot_instance.resume_after_circuit_breaker()
                    except Exception as e:
                        logger.error(f"Erro ao retomar bot após circuit breaker: {e}")

    async def trigger_circuit_breaker(self, reason: str, cooldown_hours: int = 2):
        """✅ PR1.3: Ativa circuit breaker para parar operações"""
        logger.warning(f"🚨 CIRCUIT BREAKER ATIVADO: {reason}")
        
        self.system_state['circuit_breaker_active'] = True
        self.system_state['circuit_breaker_triggered_at'] = datetime.utcnow().isoformat()
        self.system_state['circuit_breaker_reason'] = reason
        self.system_state['circuit_breaker_cooldown_until'] = (
            datetime.utcnow() + timedelta(hours=cooldown_hours)
        ).isoformat()
        
        # Notificar bot para parar novas operações
        if self.bot_instance and hasattr(self.bot_instance, 'activate_circuit_breaker'):
            try:
                await self.bot_instance.activate_circuit_breaker(reason)
            except Exception as e:
                logger.error(f"Erro ao notificar bot sobre circuit breaker: {e}")

    def reset_circuit_breaker(self):
        """✅ PR1.3: Reseta manualmente o circuit breaker"""
        logger.info("🔄 Circuit breaker resetado manualmente.")
        self.system_state['circuit_breaker_active'] = False
        self.system_state['circuit_breaker_triggered_at'] = None
        self.system_state['circuit_breaker_reason'] = None
        self.system_state['circuit_breaker_cooldown_until'] = None

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

    def _save_state_to_history(self):
        """✅ PR1.3: Salva estado atual no histórico"""
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            cpu_pct = process.cpu_percent(interval=0.1)
            
            state = {
                'timestamp': datetime.utcnow().isoformat(),
                'health_status': self.system_state['health_status'],
                'memory_mb': mem_info.rss / 1024 / 1024,
                'cpu_percent': cpu_pct,
                'validation_errors_count': len(self.system_state.get('validation_errors', [])),
                'circuit_breaker_active': self.system_state['circuit_breaker_active']
            }
            
            self.state_history.append(state)
            
            # Manter apenas últimos N estados
            if len(self.state_history) > self.max_history:
                self.state_history = self.state_history[-self.max_history:]
        except Exception as e:
            logger.error(f"Erro ao salvar estado no histórico: {e}")

    def get_status(self) -> Dict:
        """Retorna relatório de saúde completo com estado do sistema"""
        now = time.time()
        
        # Status dos componentes
        component_status = {}
        for comp, last in self.heartbeats.items():
            age = now - last
            threshold = self.thresholds.get(comp, 120)
            if age > threshold:
                status = "frozen"
            elif age > threshold * 0.7:
                status = "slow"
            else:
                status = "ok"
            
            component_status[comp] = {
                "status": status,
                "last_heartbeat_ago": f"{age:.1f}s",
                "threshold": threshold
            }
        
        # ✅ PR1.3: Status de recursos detalhado
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            cpu_pct = process.cpu_percent(interval=0.1)
            
            # Validar memória
            mem_mb = mem_info.rss / 1024 / 1024
            if mem_mb > self.resource_thresholds['memory_critical_mb']:
                mem_status = "critical"
            elif mem_mb > self.resource_thresholds['memory_warning_mb']:
                mem_status = "warning"
            else:
                mem_status = "ok"
            
            # Validar CPU
            if cpu_pct > self.resource_thresholds['cpu_critical_pct']:
                cpu_status = "critical"
            elif cpu_pct > self.resource_thresholds['cpu_warning_pct']:
                cpu_status = "warning"
            else:
                cpu_status = "ok"
            
            # Validar disco
            disk_pct = 0
            disk_status = "unknown"
            try:
                disk = psutil.disk_usage('/')
                disk_pct = disk.percent
                if disk_pct > self.resource_thresholds['disk_critical_pct']:
                    disk_status = "critical"
                elif disk_pct > self.resource_thresholds['disk_warning_pct']:
                    disk_status = "warning"
                else:
                    disk_status = "ok"
            except Exception:
                pass
            
            system_status = {
                "cpu_percent": cpu_pct,
                "cpu_status": cpu_status,
                "memory_mb": mem_mb,
                "memory_status": mem_status,
                "disk_percent": disk_pct,
                "disk_status": disk_status
            }
        except Exception as e:
            logger.error(f"Erro ao obter status de recursos: {e}")
            system_status = {
                "cpu_percent": 0,
                "cpu_status": "error",
                "memory_mb": 0,
                "memory_status": "error",
                "disk_percent": 0,
                "disk_status": "error"
            }
        
        # ✅ PR1.3: Status do circuit breaker
        circuit_breaker = {
            "active": self.system_state['circuit_breaker_active'],
            "triggered_at": self.system_state['circuit_breaker_triggered_at'],
            "reason": self.system_state['circuit_breaker_reason'],
            "cooldown_until": self.system_state['circuit_breaker_cooldown_until']
        }
        
        # ✅ PR1.3: Histórico recente de estados (últimos 10)
        recent_history = self.state_history[-10:] if self.state_history else []
        
        return {
            "monitoring": self.is_monitoring,
            "restarts": self.restart_count,
            "last_restart": self.last_restart_time,
            "components": component_status,
            "system": system_status,
            "circuit_breaker": circuit_breaker,
            "health_status": self.system_state['health_status'],
            "last_validation": self.system_state['last_validation_time'],
            "validation_errors": self.system_state.get('validation_errors', []),
            "recent_state_history": recent_history
        }

# Singleton
supervisor = Supervisor()
