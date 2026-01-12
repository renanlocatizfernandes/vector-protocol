"""
Configuration Manager - Gerencia configurações do database com fallback para .env
Implementação híbrida que permite migração gradual sem downtime
"""
import json
from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session
from modules.config_database import Configuration, ConfigurationHistory
from utils.logger import setup_logger

logger = setup_logger("config_manager")


class ConfigManager:
    """
    Gerenciador de configurações com prioridade: Database -> .env -> Default
    
    Features:
    - Cache em memória para performance
    - Fallback automático para .env
    - Validação de valores
    - Histórico de mudanças
    - Suporte a múltiplos tipos (int, float, bool, json)
    """
    
    def __init__(self, db_session: Session, env_settings):
        self.db = db_session
        self.env_settings = env_settings
        self._cache: Dict[str, Any] = {}  # Cache em memória
        logger.info("ConfigManager inicializado com fallback para .env")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Busca configuração com prioridade: Cache -> Database -> .env -> Default
        
        Args:
            key: Nome da configuração
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da configuração (tipado corretamente)
        """
        # 1. Verificar cache primeiro
        if key in self._cache:
            return self._cache[key]
        
        # 2. Tentar database primeiro
        try:
            config = self.db.query(Configuration).filter(
                Configuration.key == key
            ).first()
            
            if config:
                value = self._parse_value(config.value, config.value_type)
                self._cache[key] = value
                logger.debug(f"Config '{key}' carregado do DB: {value}")
                return value
        except Exception as e:
            logger.warning(f"Erro ao buscar {key} do DB: {e}")
        
        # 3. Fallback para .env
        env_value = getattr(self.env_settings, key, None)
        if env_value is not None:
            self._cache[key] = env_value
            logger.debug(f"Config '{key}' carregado do .env: {env_value}")
            return env_value
        
        # 4. Fallback para default
        logger.debug(f"Config '{key}' usando default: {default}")
        return default
    
    def get_sync(self, key: str, default: Any = None) -> Any:
        """
        Versao sincrona para compatibilidade com codigo existente
        """
        # Evita uso de loop asyncio em contexto sync (pode estar rodando).
        if key in self._cache:
            return self._cache[key]

        try:
            config = self.db.query(Configuration).filter(
                Configuration.key == key
            ).first()
            if config:
                value = self._parse_value(config.value, config.value_type)
                self._cache[key] = value
                logger.debug(f"Config '{key}' carregado do DB (sync): {value}")
                return value
        except Exception as e:
            logger.warning(f"Erro ao buscar {key} do DB (sync): {e}")

        env_value = getattr(self.env_settings, key, None)
        if env_value is not None:
            self._cache[key] = env_value
            logger.debug(f"Config '{key}' carregado do .env (sync): {env_value}")
            return env_value

        logger.debug(f"Config '{key}' usando default (sync): {default}")
        return default

    async def set(self, key: str, value: Any, changed_by: str = 'api', reason: str = None) -> bool:
        """
        Atualiza configuração no database e registra histórico
        
        Args:
            key: Nome da configuração
            value: Novo valor
            changed_by: Quem está fazendo a mudança (api, admin, migration, etc.)
            reason: Motivo da mudança (opcional)
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Buscar configuração existente
            config = self.db.query(Configuration).filter(
                Configuration.key == key
            ).first()
            
            old_value = config.value if config else None
            new_value_str = self._serialize_value(value)
            
            # Validar antes de atualizar (se existir config com regras)
            if config:
                if not self._validate_value(value, config):
                    logger.error(f"Valor invalido para {key}: {value} (violou regras de validação)")
                    return False
            
            # Criar ou atualizar registro
            if config:
                # Atualizar existente
                config.value = new_value_str
                config.value_type = self._get_value_type(value)
                config.updated_by = changed_by
                config.version += 1
                logger.debug(f"Atualizando config existente: {key}")
            else:
                # Criar nova configuração
                config = Configuration(
                    key=key,
                    value=new_value_str,
                    value_type=self._get_value_type(value),
                    updated_by=changed_by,
                    category=self._infer_category(key)
                )
                self.db.add(config)
                logger.debug(f"Criando nova config: {key}")
            
            # Registrar histórico (apenas se valor mudou)
            if old_value != new_value_str:
                history = ConfigurationHistory(
                    config_key=key,
                    old_value=old_value,
                    new_value=new_value_str,
                    changed_by=changed_by,
                    reason=reason
                )
                self.db.add(history)
                logger.info(f"Histórico registrado para {key}: {old_value} -> {new_value_str}")
            
            # Commit e atualizar cache
            self.db.commit()
            self._cache[key] = value
            
            logger.info(f"✅ Configuração atualizada: {key} = {value} (por {changed_by})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar configuração {key}: {e}")
            self.db.rollback()
            return False
    
    async def set_batch(self, configs: Dict[str, Any], changed_by: str = 'api', reason: str = None) -> Dict[str, bool]:
        """
        Atualiza múltiplas configurações em uma única transação
        
        Args:
            configs: Dicionário {key: value}
            changed_by: Quem está fazendo as mudanças
            reason: Motivo das mudanças
            
        Returns:
            Dicionário {key: success}
        """
        results = {}
        try:
            for key, value in configs.items():
                results[key] = await self.set(key, value, changed_by=changed_by, reason=reason)
            
            logger.info(f"✅ Batch update concluído: {sum(results.values())}/{len(results)} atualizados")
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro no batch update: {e}")
            return results
    
    async def reload_from_env(self) -> int:
        """
        Recarrega configurações do .env para o database
        Útil para migração inicial ou reset para valores padrão
        
        Returns:
            Número de configurações atualizadas
        """
        from config.settings import get_settings
        settings = get_settings()
        
        updated = 0
        
        # Lista de chaves importantes para migrar
        important_keys = [
            # Bot Settings
            'BOT_MIN_SCORE',
            'BOT_SCAN_INTERVAL_MINUTES',
            'BOT_MAX_POSITIONS',
            'AUTOSTART_BOT',
            'BOT_DRY_RUN',
            
            # Risk Management
            'RISK_PER_TRADE',
            'MAX_PORTFOLIO_RISK',
            'DEFAULT_LEVERAGE',
            'DAILY_MAX_LOSS_PCT',
            'INTRADAY_DRAWDOWN_HARD_STOP_PCT',
            
            # Sniper Settings
            'SNIPER_EXTRA_SLOTS',
            'SNIPER_TP_PCT',
            'SNIPER_SL_PCT',
            'SNIPER_RISK_PER_TRADE',
            'SNIPER_DEFAULT_LEVERAGE',
            
            # Scanner Settings
            'SCANNER_MIN_VOLUME_24H',
            'SCANNER_MAX_SYMBOLS',
            'SCANNER_STRICT_WHITELIST',
            'SYMBOL_WHITELIST',
            
            # Stop Loss & Take Profit
            'ENABLE_TRAILING_STOP',
            'TSL_CALLBACK_PCT_MIN',
            'TSL_CALLBACK_PCT_MAX',
            'TSL_ATR_LOOKBACK_INTERVAL',
            
            # DCA Settings
            'DCA_ENABLED',
            'MAX_DCA_COUNT',
            'DCA_THRESHOLD_PCT',
            'DCA_MULTIPLIER',
            
            # Time-Based Exit
            'TIME_EXIT_HOURS',
            'TIME_EXIT_MIN_PROFIT_PCT',
            
            # Virtual Balance
            'VIRTUAL_BALANCE_ENABLED',
            'VIRTUAL_BALANCE_USDT',
            
            # Telegram
            'TELEGRAM_ENABLED',
        ]
        
        logger.info(f"🔄 Recarregando {len(important_keys)} configurações do .env...")
        
        for key in important_keys:
            value = getattr(settings, key, None)
            if value is not None:
                result = await self.set(key, value, changed_by='migration', 
                                     reason='Migração inicial de .env para DB')
                if result:
                    updated += 1
        
        logger.info(f"✅ {updated} configurações importadas do .env para o database")
        return updated
    
    async def get_all(self) -> List[Dict]:
        """
        Retorna todas as configurações do database
        
        Returns:
            Lista de dicionários com metadados
        """
        try:
            configs = self.db.query(Configuration).all()
            
            result = []
            for config in configs:
                result.append({
                    'key': config.key,
                    'value': self._parse_value(config.value, config.value_type),
                    'description': config.description,
                    'category': config.category,
                    'is_sensitive': config.is_sensitive,
                    'updated_at': config.updated_at.isoformat(),
                    'updated_by': config.updated_by,
                    'version': config.version,
                    'min_value': config.min_value,
                    'max_value': config.max_value,
                    'allowed_values': config.allowed_values
                })
            
            return result
        except Exception as e:
            logger.error(f"Erro ao buscar todas as configurações: {e}")
            return []
    
    async def get_history(self, key: str, limit: int = 50) -> List[Dict]:
        """
        Retorna histórico de mudanças de uma configuração
        
        Args:
            key: Nome da configuração
            limit: Número máximo de registros
            
        Returns:
            Lista de dicionários com histórico
        """
        try:
            history = self.db.query(ConfigurationHistory).filter(
                ConfigurationHistory.config_key == key
            ).order_by(ConfigurationHistory.changed_at.desc()).limit(limit).all()
            
            result = []
            for h in history:
                result.append({
                    'id': h.id,
                    'old_value': self._parse_value(h.old_value, 'string') if h.old_value else None,
                    'new_value': self._parse_value(h.new_value, 'string') if h.new_value else None,
                    'changed_at': h.changed_at.isoformat(),
                    'changed_by': h.changed_by,
                    'reason': h.reason
                })
            
            return result
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de {key}: {e}")
            return []
    
    async def reset_to_default(self, key: str) -> bool:
        """
        Reseta configuração para valor padrão do .env
        
        Args:
            key: Nome da configuração
            
        Returns:
            True se resetado com sucesso
        """
        try:
            from config.settings import get_settings
            settings = get_settings()
            default_value = getattr(settings, key, None)
            
            if default_value is None:
                logger.warning(f"Configuração {key} não tem valor padrão no .env")
                return False
            
            return await self.set(key, default_value, changed_by='reset', 
                               reason='Reset para valor padrão do .env')
            
        except Exception as e:
            logger.error(f"Erro ao resetar {key}: {e}")
            return False
    
    def invalidate_cache(self, key: str = None):
        """
        Invalida cache (total ou de uma chave específica)
        """
        if key:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache invalidado para {key}")
        else:
            self._cache.clear()
            logger.debug("Cache totalmente invalidado")
    
    # ================================
    # Métodos Helper (Privados)
    # ================================
    
    def _parse_value(self, value: str, value_type: str) -> Any:
        """Converte string do database para o tipo correto"""
        if value is None:
            return None
        
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'bool':
                return value.lower() in ['true', '1', 'yes', 'on']
            elif value_type == 'json':
                return json.loads(value)
            return value  # string
        except Exception as e:
            logger.warning(f"Erro ao parsear valor '{value}' como {value_type}: {e}")
            return value
    
    def _serialize_value(self, value: Any) -> str:
        """Converte valor para string para armazenamento"""
        if value is None:
            return ''
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return str(value)
    
    def _get_value_type(self, value: Any) -> str:
        """Identifica o tipo do valor"""
        if value is None:
            return 'string'
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, int):
            return 'int'
        if isinstance(value, float):
            return 'float'
        if isinstance(value, (list, dict)):
            return 'json'
        return 'string'
    
    def _validate_value(self, value: Any, config: Configuration) -> bool:
        """
        Valida valor contra restrições definidas na configuração
        
        Args:
            value: Valor a validar
            config: Objeto Configuration com regras de validação
            
        Returns:
            True se válido, False se inválido
        """
        try:
            # Converter para float para comparações numéricas
            float_value = float(value)
            
            # Validar min_value
            if config.min_value is not None and float_value < config.min_value:
                logger.warning(f"Valor {value} < min_value {config.min_value}")
                return False
            
            # Validar max_value
            if config.max_value is not None and float_value > config.max_value:
                logger.warning(f"Valor {value} > max_value {config.max_value}")
                return False
            
            # Validar allowed_values (enum)
            if config.allowed_values is not None and value not in config.allowed_values:
                logger.warning(f"Valor {value} não está em allowed_values {config.allowed_values}")
                return False
            
            return True
        except (ValueError, TypeError):
            # Se não for número, validar apenas allowed_values
            if config.allowed_values is not None and value not in config.allowed_values:
                return False
            return True
    
    def _infer_category(self, key: str) -> str:
        """Infere categoria da configuração pelo nome da chave"""
        key_upper = key.upper()
        
        if 'SNIPER' in key_upper:
            return 'sniper'
        elif 'RISK' in key_upper or 'POSITION' in key_upper or 'LEVERAGE' in key_upper:
            return 'risk'
        elif 'SCANNER' in key_upper or 'WHITELIST' in key_upper:
            return 'scanner'
        elif 'BOT' in key_upper:
            return 'bot'
        elif 'STOP' in key_upper or 'TAKE_PROFIT' in key_upper or 'TP' in key_upper:
            return 'risk'
        elif 'DCA' in key_upper:
            return 'risk'
        elif 'TELEGRAM' in key_upper:
            return 'general'
        elif 'VIRTUAL' in key_upper:
            return 'general'
        
        return 'general'
