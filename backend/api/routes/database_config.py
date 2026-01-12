"""
Database Configuration Routes - API para gerenciar configurações do sistema
Endpoints para CRUD, histórico e batch update de configurações
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from modules.config_manager import ConfigManager
from modules.autonomous_bot import autonomous_bot
from models.database import SessionLocal
from config.settings import get_settings
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("database_config_routes")


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConfigValue(BaseModel):
    """Modelo para atualização de configuração"""
    key: str
    value: Any
    reason: Optional[str] = None


class ConfigUpdateResponse(BaseModel):
    """Resposta de atualização de configuração"""
    success: bool
    key: str
    old_value: Any
    new_value: Any
    message: str


class BatchUpdateResponse(BaseModel):
    """Resposta de batch update"""
    results: List[dict]
    total: int
    success_count: int


@router.get("/health")
async def config_health_check(db: SessionLocal = Depends(get_db)):
    """
    Health check para o sistema de configurações
    Verifica se database está acessível e ConfigManager funcionando
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        # Testar leitura
        test_value = await config_manager.get('BOT_MIN_SCORE', None)
        
        # Contar configurações no database
        all_configs = await config_manager.get_all()
        db_count = len(all_configs)
        
        # Verificar se .env está acessível
        env_value = getattr(get_settings(), 'BOT_MIN_SCORE', None)
        
        return {
            'status': 'healthy',
            'database_accessible': True,
            'database_config_count': db_count,
            'test_config_value': test_value,
            'env_fallback_working': env_value is not None,
            'cache_enabled': len(config_manager._cache) > 0,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@router.get("/")
async def get_all_configs(db: SessionLocal = Depends(get_db)):
    """
    Retorna todas as configurações do database
    
    Inclui metadados como categoria, descrição, versão, etc.
    """
    try:
        # Criar ConfigManager
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        # Buscar todas as configurações
        configs = await config_manager.get_all()
        
        logger.info(f"Retornando {len(configs)} configurações")
        return {
            'configs': configs,
            'count': len(configs),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao buscar todas as configurações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_config_categories(db: SessionLocal = Depends(get_db)):
    """
    Retorna todas as categorias de configurações disponíveis
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        configs = await config_manager.get_all()
        
        # Extrair categorias únicas
        categories = sorted(list(set(
            c['category'] for c in configs if c['category']
        )))
        
        return {
            'categories': categories,
            'count': len(categories)
        }
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}")
async def get_configs_by_category(category: str, db: SessionLocal = Depends(get_db)):
    """
    Retorna configurações de uma categoria específica
    
    Args:
        category: Nome da categoria (bot, sniper, risk, scanner, general)
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        configs = await config_manager.get_all()
        
        # Filtrar por categoria
        filtered = [c for c in configs if c.get('category') == category]
        
        return {
            'category': category,
            'configs': filtered,
            'count': len(filtered)
        }
    except Exception as e:
        logger.error(f"Erro ao buscar configurações da categoria {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}")
async def get_config(key: str, db: SessionLocal = Depends(get_db)):
    """
    Retorna uma configuração específica
    
    Busca com prioridade: Database -> .env -> Default
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        value = await config_manager.get(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
        
        logger.debug(f"Config '{key}' retornada: {value}")
        return {'key': key, 'value': value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar configuração {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}", response_model=ConfigUpdateResponse)
async def update_config(key: str, config: ConfigValue, db: SessionLocal = Depends(get_db)):
    """
    Atualiza configuração e recarrega bot automaticamente
    
    Args:
        key: Nome da configuração
        config: Objeto com novo valor e motivo (opcional)
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        # Buscar valor atual
        old_value = await config_manager.get(key)
        
        # Atualizar no database
        success = await config_manager.set(
            key, config.value, 
            changed_by='api',
            reason=config.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Failed to update config - validation failed or other error"
            )
        
        # Recarregar bot para aplicar mudanças
        try:
            autonomous_bot.reload_settings()
            logger.info("Bot recarregado após atualização de configuração")
        except Exception as e:
            logger.warning(f"Bot não pôde ser recarregado: {e}")
        
        return ConfigUpdateResponse(
            success=True,
            key=key,
            old_value=old_value,
            new_value=config.value,
            message=f"Configuration '{key}' updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload-from-env")
async def reload_from_env(db: SessionLocal = Depends(get_db)):
    """
    Recarrega configurações do .env para o database
    
    Útil para reset ou migração inicial
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        # Recarregar configurações do .env
        updated = await config_manager.reload_from_env()
        
        # Recarregar bot para aplicar mudanças
        try:
            autonomous_bot.reload_settings()
        except Exception as e:
            logger.warning(f"Bot não pôde ser recarregado: {e}")
        
        return {
            'success': True,
            'message': f'Reloaded {updated} configurations from .env',
            'count': updated,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao recarregar do .env: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{key}")
async def reset_config(key: str, db: SessionLocal = Depends(get_db)):
    """
    Reseta configuração para valor padrão do .env
    
    Args:
        key: Nome da configuração a resetar
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        success = await config_manager.reset_to_default(key)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Config '{key}' not found or has no default value"
            )
        
        # Recarregar bot
        try:
            autonomous_bot.reload_settings()
        except Exception as e:
            logger.warning(f"Bot não pôde ser recarregado: {e}")
        
        return {
            'success': True,
            'key': key,
            'message': f"Configuration '{key}' reset to default value",
            'timestamp': datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao resetar configuração {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{key}")
async def get_config_history(key: str, limit: int = 50, db: SessionLocal = Depends(get_db)):
    """
    Retorna histórico de mudanças de uma configuração
    
    Args:
        key: Nome da configuração
        limit: Número máximo de registros (default 50)
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        history = await config_manager.get_history(key, limit)
        
        logger.debug(f"Histórico de {key}: {len(history)} registros")
        return {
            'key': key,
            'history': history,
            'count': len(history)
        }
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-update", response_model=BatchUpdateResponse)
async def batch_update_configs(configs: List[ConfigValue], db: SessionLocal = Depends(get_db)):
    """
    Atualiza múltiplas configurações em uma única transação
    
    Útil para mudanças em massa. Bot é recarregado após todas as mudanças.
    
    Args:
        configs: Lista de configurações a atualizar
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        results = []
        for config in configs:
            old_value = await config_manager.get(config.key)
            success = await config_manager.set(
                config.key, config.value,
                changed_by='api',
                reason=config.reason
            )
            results.append({
                'key': config.key,
                'success': success,
                'old_value': old_value,
                'new_value': config.value
            })
        
        # Recarregar bot após todas as mudanças
        try:
            autonomous_bot.reload_settings()
            logger.info("Bot recarregado após batch update")
        except Exception as e:
            logger.warning(f"Bot não pôde ser recarregado: {e}")
        
        success_count = sum(1 for r in results if r['success'])
        
        return BatchUpdateResponse(
            results=results,
            total=len(results),
            success_count=success_count
        )
    except Exception as e:
        logger.error(f"Erro no batch update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invalidate-cache")
async def invalidate_cache(key: Optional[str] = None, db: SessionLocal = Depends(get_db)):
    """
    Invalida cache de configurações
    
    Args:
        key: Chave específica para invalidar (opcional). Se não informado, invalida todo o cache.
    """
    try:
        config_manager = ConfigManager(
            db_session=db,
            env_settings=get_settings()
        )
        
        if key:
            config_manager.invalidate_cache(key)
            message = f"Cache invalidado para configuração '{key}'"
        else:
            config_manager.invalidate_cache()
            message = "Todo o cache de configurações invalidado"
        
        logger.info(message)
        return {
            'success': True,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao invalidar cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
