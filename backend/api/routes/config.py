from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from config.settings import get_settings, reload_settings
from modules.autonomous_bot import autonomous_bot

router = APIRouter()

class ConfigUpdate(BaseModel):
    max_positions: Optional[int] = None
    risk_per_trade: Optional[float] = None
    max_portfolio_risk: Optional[float] = None
    default_leverage: Optional[int] = None
    bot_min_score: Optional[int] = None
    bot_scan_interval_minutes: Optional[int] = None

@router.get("/")
async def get_config():
    settings = get_settings()
    return {
        "max_positions": settings.MAX_POSITIONS,
        "risk_per_trade": settings.RISK_PER_TRADE,
        "max_portfolio_risk": settings.MAX_PORTFOLIO_RISK,
        "default_leverage": settings.DEFAULT_LEVERAGE,
        "bot_min_score": settings.BOT_MIN_SCORE,
        "bot_scan_interval_minutes": settings.BOT_SCAN_INTERVAL_MINUTES,
        "testnet": settings.BINANCE_TESTNET
    }

@router.patch("/")
async def update_config(config: ConfigUpdate):
    """
    Atualiza configurações dinamicamente.
    Nota: Isso atualiza as variáveis de ambiente do processo atual e recarrega o bot.
    Para persistência entre restarts, seria necessário escrever no .env (não implementado aqui por segurança/complexidade Docker).
    """
    try:
        # Atualizar env vars (afeta get_settings na próxima leitura)
        if config.max_positions is not None:
            os.environ["MAX_POSITIONS"] = str(config.max_positions)
            os.environ["BOT_MAX_POSITIONS"] = str(config.max_positions)
        if config.risk_per_trade is not None:
            os.environ["RISK_PER_TRADE"] = str(config.risk_per_trade)
        if config.max_portfolio_risk is not None:
            os.environ["MAX_PORTFOLIO_RISK"] = str(config.max_portfolio_risk)
        if config.default_leverage is not None:
            os.environ["DEFAULT_LEVERAGE"] = str(config.default_leverage)
        if config.bot_min_score is not None:
            os.environ["BOT_MIN_SCORE"] = str(config.bot_min_score)
        if config.bot_scan_interval_minutes is not None:
            os.environ["BOT_SCAN_INTERVAL_MINUTES"] = str(config.bot_scan_interval_minutes)
            
        # Recarregar settings (limpar cache)
        new_settings = reload_settings()
        
        # Notificar bot para recarregar suas cópias locais
        autonomous_bot.reload_settings()
        
        return {"status": "success", "message": "Configurações atualizadas", "config": config.dict(exclude_unset=True)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar config: {e}")
