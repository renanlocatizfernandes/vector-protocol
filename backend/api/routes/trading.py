"""
Trading Routes - FIXED VERSION
✅ Correção do erro 500 no endpoint /bot/start
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from modules.signal_generator import signal_generator
from modules.order_executor import order_executor
from utils.binance_client import binance_client
from modules.position_monitor import position_monitor
from modules.autonomous_bot import autonomous_bot
from modules.risk_manager import risk_manager
from utils.telegram_notifier import telegram_notifier
from api.models.trades import Trade
from api.database import SessionLocal 
from modules.daily_report import daily_report
from datetime import datetime
from utils.logger import setup_logger
from config.settings import get_settings

router = APIRouter()
logger = setup_logger("trading_routes")


def _to_native(obj):
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None  # type: ignore
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(x) for x in obj]
    if np is not None:
        try:
            # numpy scalar
            import numpy as np  # type: ignore
            if isinstance(obj, np.generic):  # type: ignore
                return obj.item()
        except Exception:
            pass
    return obj


class ExecuteTradeRequest(BaseModel):
    symbol: str
    risk_profile: str = "moderate"
    dry_run: bool = True


@router.post("/execute")
async def execute_trade(request: ExecuteTradeRequest):
    """Executa um trade baseado em sinal gerado"""
    
    balance_info = await binance_client.get_account_balance()
    
    if not balance_info:
        raise HTTPException(status_code=500, detail="Erro ao obter saldo da conta")
    
    account_balance = balance_info['available_balance']
    try:
        account_balance = float(account_balance)
    except Exception:
        pass
    try:
        settings = get_settings()
        if getattr(settings, "VIRTUAL_BALANCE_ENABLED", False):
            account_balance = float(getattr(settings, "VIRTUAL_BALANCE_USDT", 300.0))
    except Exception:
        pass
    
    signal = await signal_generator.generate_signal_for_symbol(request.symbol.upper(), request.risk_profile)
    
    if not signal:
        raise HTTPException(status_code=400, detail=f"Não foi possível gerar sinal para {request.symbol}")
    
    result = await order_executor.execute_signal(
        signal=signal,
        account_balance=account_balance,
        open_positions=0,
        dry_run=request.dry_run
    )
    
    return {
        "signal": _to_native(signal),
        "execution": _to_native(result),
        "account_balance": float(account_balance) if isinstance(account_balance, (int, float)) else account_balance
    }


@router.post("/execute-batch")
async def execute_batch_trades(min_score: int = 70, max_trades: int = 3, dry_run: bool = True):
    """Executa múltiplos trades automaticamente"""
    
    balance_info = await binance_client.get_account_balance()
    
    if not balance_info:
        raise HTTPException(status_code=500, detail="Erro ao obter saldo da conta")
    
    account_balance = balance_info['available_balance']
    try:
        account_balance = float(account_balance)
    except Exception:
        pass
    try:
        settings = get_settings()
        if getattr(settings, "VIRTUAL_BALANCE_ENABLED", False):
            account_balance = float(getattr(settings, "VIRTUAL_BALANCE_USDT", 300.0))
    except Exception:
        pass
    
    signals = await signal_generator.generate_signals_batch(limit=30, min_score=min_score)
    
    if not signals:
        return {"message": "Nenhum sinal gerado", "executed": []}
    
    executed = []
    
    for i, signal in enumerate(signals[:max_trades]):
        result = await order_executor.execute_signal(
            signal=signal,
            account_balance=account_balance,
            open_positions=i,
            dry_run=dry_run
        )
        
        executed.append({
            "signal": signal,
            "execution": result
        })
        
        if result['success'] and not dry_run:
            account_balance -= result.get('margin_required', 0)
    
    return {
        "total_signals": len(signals),
        "executed_count": len(executed),
        "executed": _to_native(executed),
        "remaining_balance": float(account_balance) if isinstance(account_balance, (int, float)) else account_balance
    }


@router.get("/positions")
async def get_open_positions():
    """Retorna posições abertas na Binance"""
    
    balance_info = await binance_client.get_account_balance()
    
    if not balance_info:
        raise HTTPException(status_code=500, detail="Erro ao obter posições")
    
    positions = [p for p in balance_info.get('positions', []) if float(p.get('positionAmt', 0)) != 0]
    
    return {
        "count": len(positions),
        "positions": positions
    }


@router.post("/monitor/start")
async def start_position_monitoring():
    """Inicia monitoramento de posições"""
    position_monitor.start_monitoring()
    
    return {
        "message": "Monitoramento de posições iniciado",
        "status": "monitoring"
    }


@router.post("/monitor/stop")
async def stop_position_monitoring():
    """Para monitoramento de posições"""
    position_monitor.stop_monitoring()
    
    return {
        "message": "Monitoramento de posições parado",
        "status": "stopped"
    }


@router.get("/monitor/status")
async def get_monitoring_status():
    """Retorna status do monitoramento"""
    return {
        "monitoring": position_monitor.monitoring,
        "circuit_breaker_active": position_monitor.circuit_breaker_active,
        "consecutive_losses": position_monitor.consecutive_losses
    }


@router.post("/bot/start")
async def start_autonomous_bot(dry_run: bool = True):
    """
    ✅ CORRIGIDO: Inicia o bot autônomo
    """
    
    if autonomous_bot.running:
        return {
            "success": False,
            "message": "Bot já está rodando",
            "status": "running"
        }
    
    try:
        # ✅ CORREÇÃO: Usar await porque start() é async
        await autonomous_bot.start(dry_run=dry_run)

        # Notificação Telegram (assíncrona)
        try:
            msg = (
                "🤖 BOT AUTÔNOMO INICIADO\n\n"
                f"Modo: {'DRY RUN' if dry_run else 'REAL'}\n"
                f"Scan: {autonomous_bot.scan_interval//60} min\n"
                f"Score mínimo: {autonomous_bot.min_score}\n"
                f"Máx posições: {autonomous_bot.max_positions}\n"
            )
            asyncio.create_task(telegram_notifier.send_message(msg))
        except Exception:
            pass
        
        return {
            "success": True,
            "message": "🤖 Bot autônomo iniciado com sucesso!",
            "status": "running",
            "config": {
                "dry_run": dry_run,
                "scan_interval": autonomous_bot.scan_interval,
                "min_score": autonomous_bot.min_score,
                "max_positions": autonomous_bot.max_positions
            }
        }
    
    except Exception as e:
        logger.error(f"Erro ao iniciar bot: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar bot: {str(e)}")


@router.post("/bot/stop")
async def stop_autonomous_bot():
    """Para o bot autônomo"""
    
    if not autonomous_bot.running:
        return {
            "success": False,
            "message": "Bot não está rodando",
            "status": "stopped"
        }
    
    autonomous_bot.stop()

    # Notificação Telegram (assíncrona)
    try:
        asyncio.create_task(telegram_notifier.send_message("🛑 BOT AUTÔNOMO PARADO"))
    except Exception:
        pass
    
    return {
        "success": True,
        "message": "🛑 Bot autônomo parado",
        "status": "stopped"
    }


@router.get("/bot/status")
async def get_bot_status():
    """Retorna status do bot"""
    
    return {
        "running": autonomous_bot.running,
        "dry_run": autonomous_bot.dry_run,
        "scan_interval": autonomous_bot.scan_interval,
        "min_score": autonomous_bot.min_score,
        "max_positions": autonomous_bot.max_positions,
        "circuit_breaker_active": position_monitor.circuit_breaker_active
    }


@router.get("/bot/metrics")
async def get_bot_metrics():
    """Retorna métricas agregadas do bot autônomo (KPIs por ciclo)"""
    try:
        metrics = autonomous_bot.get_metrics()
        return _to_native(metrics)
    except Exception as e:
        logger.error(f"Erro ao obter métricas do bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


@router.get("/execution/metrics")
async def get_execution_metrics():
    """Retorna métricas agregadas do executor de ordens"""
    try:
        metrics = order_executor.get_metrics()
        return _to_native(metrics)
    except Exception as e:
        logger.error(f"Erro ao obter métricas de execução: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


@router.get("/monitoring/metrics")
async def get_monitoring_metrics():
    """Retorna métricas agregadas do monitor de posições"""
    try:
        metrics = position_monitor.get_metrics()
        return _to_native(metrics)
    except Exception as e:
        logger.error(f"Erro ao obter métricas de monitoramento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


@router.get("/risk/metrics")
async def get_risk_metrics():
    """Retorna métricas agregadas do gerenciador de risco"""
    try:
        metrics = risk_manager.get_metrics()
        return _to_native(metrics)
    except Exception as e:
        logger.error(f"Erro ao obter métricas de risco: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao obter métricas: {str(e)}")


# =========================
# Execução avançada (TSL/Bracket/WorkingType/Margin Policy) - runtime toggles
# =========================
@router.get("/execution/config")
async def get_execution_config():
    """Lê flags de execução avançada em runtime (sem reinício)."""
    s = order_executor.settings
    return {
        "ENABLE_TRAILING_STOP": bool(getattr(s, "ENABLE_TRAILING_STOP", False)),
        "TSL_CALLBACK_PCT_MIN": float(getattr(s, "TSL_CALLBACK_PCT_MIN", 0.4)),
        "TSL_CALLBACK_PCT_MAX": float(getattr(s, "TSL_CALLBACK_PCT_MAX", 1.2)),
        "TSL_ATR_LOOKBACK_INTERVAL": str(getattr(s, "TSL_ATR_LOOKBACK_INTERVAL", "15m")),
        "ENABLE_BRACKET_BATCH": bool(getattr(s, "ENABLE_BRACKET_BATCH", False)),
        "USE_MARK_PRICE_FOR_STOPS": bool(getattr(s, "USE_MARK_PRICE_FOR_STOPS", True)),
        "DEFAULT_MARGIN_CROSSED": bool(getattr(s, "DEFAULT_MARGIN_CROSSED", True)),
        "AUTO_ISOLATE_MIN_LEVERAGE": int(getattr(s, "AUTO_ISOLATE_MIN_LEVERAGE", 10)),
        "ALLOW_MARGIN_MODE_OVERRIDE": bool(getattr(s, "ALLOW_MARGIN_MODE_OVERRIDE", True)),
        "ORDER_TIMEOUT_SEC": int(getattr(s, "ORDER_TIMEOUT_SEC", 3)),
        "USE_POST_ONLY_ENTRIES": bool(getattr(s, "USE_POST_ONLY_ENTRIES", False)),
        "TAKE_PROFIT_PARTS": str(getattr(s, "TAKE_PROFIT_PARTS", "0.5,0.3,0.2")),
        "AUTO_POST_ONLY_ENTRIES": bool(getattr(s, "AUTO_POST_ONLY_ENTRIES", False)),
        "AUTO_MAKER_SPREAD_BPS": float(getattr(s, "AUTO_MAKER_SPREAD_BPS", 3.0)),
        "HEADROOM_MIN_PCT": float(getattr(s, "HEADROOM_MIN_PCT", 35.0)),
        "REDUCE_STEP_PCT": float(getattr(s, "REDUCE_STEP_PCT", 10.0)),
        "ALLOW_RISK_BYPASS_FOR_FORCE": bool(getattr(s, "ALLOW_RISK_BYPASS_FOR_FORCE", False)),
    }


@router.put("/execution/config")
async def update_execution_config(
    enable_trailing_stop: Optional[bool] = None,
    tsl_callback_pct_min: Optional[float] = None,
    tsl_callback_pct_max: Optional[float] = None,
    tsl_atr_lookback_interval: Optional[str] = None,
    enable_bracket_batch: Optional[bool] = None,
    use_mark_price_for_stops: Optional[bool] = None,
    default_margin_crossed: Optional[bool] = None,
    auto_isolate_min_leverage: Optional[int] = None,
    allow_margin_mode_override: Optional[bool] = None,
    order_timeout_sec: Optional[int] = None,
    use_post_only_entries: Optional[bool] = None,
    take_profit_parts: Optional[str] = None,
    auto_post_only_entries: Optional[bool] = None,
    auto_maker_spread_bps: Optional[float] = None,
    headroom_min_pct: Optional[float] = None,
    reduce_step_pct: Optional[float] = None,
    allow_risk_bypass_for_force: Optional[bool] = None
):
    """
    Atualiza flags de execução avançada em memória (efeito imediato, sem reinício).
    """
    s = order_executor.settings

    def _apply(name: str, value):
        if value is None:
            return
        setattr(s, name, value)

    _apply("ENABLE_TRAILING_STOP", enable_trailing_stop)
    _apply("TSL_CALLBACK_PCT_MIN", tsl_callback_pct_min)
    _apply("TSL_CALLBACK_PCT_MAX", tsl_callback_pct_max)
    _apply("TSL_ATR_LOOKBACK_INTERVAL", tsl_atr_lookback_interval)
    _apply("ENABLE_BRACKET_BATCH", enable_bracket_batch)
    _apply("USE_MARK_PRICE_FOR_STOPS", use_mark_price_for_stops)
    _apply("DEFAULT_MARGIN_CROSSED", default_margin_crossed)
    _apply("AUTO_ISOLATE_MIN_LEVERAGE", auto_isolate_min_leverage)
    _apply("ALLOW_MARGIN_MODE_OVERRIDE", allow_margin_mode_override)
    _apply("ORDER_TIMEOUT_SEC", order_timeout_sec)
    _apply("USE_POST_ONLY_ENTRIES", use_post_only_entries)
    _apply("TAKE_PROFIT_PARTS", take_profit_parts)
    _apply("AUTO_POST_ONLY_ENTRIES", auto_post_only_entries)
    _apply("AUTO_MAKER_SPREAD_BPS", auto_maker_spread_bps)
    _apply("HEADROOM_MIN_PCT", headroom_min_pct)
    _apply("REDUCE_STEP_PCT", reduce_step_pct)
    _apply("ALLOW_RISK_BYPASS_FOR_FORCE", allow_risk_bypass_for_force)

    # Sincronizar campos internos do executor usados durante a execução
    if default_margin_crossed is not None:
        order_executor.default_margin_crossed = bool(default_margin_crossed)
    if auto_isolate_min_leverage is not None:
        order_executor.auto_isolate_min_leverage = int(auto_isolate_min_leverage)
    if allow_margin_mode_override is not None:
        order_executor.allow_margin_override = bool(allow_margin_mode_override)
    if order_timeout_sec is not None:
        try:
            order_executor.limit_order_timeout = int(order_timeout_sec)
        except Exception:
            pass

    return await get_execution_config()


@router.get("/execution/leverage-preview")
async def leverage_preview(symbol: str, entry_price: float, quantity: float):
    """
    Mostra a alavancagem máxima permitida pela Binance (leverage brackets)
    para um notional aproximado (entry_price * quantity).
    """
    try:
        notional = float(entry_price) * float(quantity)
        max_allowed = await binance_client.get_max_leverage_for_notional(symbol.upper(), notional)
        return {
            "symbol": symbol.upper(),
            "entry_price": entry_price,
            "quantity": quantity,
            "notional": notional,
            "max_leverage_allowed": int(max_allowed)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na prévia de leverage: {str(e)}")


@router.put("/bot/config")
async def update_bot_config(
    scan_interval_minutes: int = None,
    min_score: int = None,
    max_positions: int = None
):
    """Atualiza configurações do bot"""
    
    if scan_interval_minutes is not None:
        autonomous_bot.scan_interval = scan_interval_minutes * 60
    
    if min_score is not None:
        autonomous_bot.min_score = min_score
    
    if max_positions is not None:
        autonomous_bot.max_positions = max_positions
    
    return {
        "success": True,
        "message": "Configurações atualizadas",
        "config": {
            "scan_interval": autonomous_bot.scan_interval,
            "min_score": autonomous_bot.min_score,
            "max_positions": autonomous_bot.max_positions
        }
    }


@router.post("/test/telegram")
async def test_telegram(text: Optional[str] = None):
    """Testa notificação do Telegram (mensagem customizável via query param ?text=...)"""
    message = text or "🤖 Bot operacional: OK"
    try:
        # Não bloquear a resposta do endpoint: dispara envio em background
        asyncio.create_task(telegram_notifier.send_message(message))
        return {"success": True, "message": "Mensagem enfileirada", "text": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enfileirar mensagem: {str(e)}")


@router.post("/positions/close")
async def close_position_manual(symbol: str):
    """Fecha uma posição manualmente"""
    
    db = SessionLocal()
    
    try:
        trade = db.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == 'open'
        ).first()
        
        if not trade:
            return {
                "success": False,
                "message": f"❌ Posição {symbol} não encontrada ou já fechada"
            }
        
        logger.info(f"🔄 Fechando posição {symbol} manualmente...")
        
        result = await order_executor.close_position(
            symbol=symbol,
            quantity=trade.quantity,
            direction=trade.direction
        )
        
        if result['success']:
            close_price = result['avg_price']
            
            if trade.direction == 'LONG':
                pnl = (close_price - trade.entry_price) * trade.quantity
            else:
                pnl = (trade.entry_price - close_price) * trade.quantity
            
            trade.status = 'closed'
            trade.exit_price = close_price
            trade.pnl = pnl
            trade.pnl_percentage = (pnl / (trade.entry_price * trade.quantity)) * 100
            trade.exit_time = datetime.now()
            
            db.commit()
            
            logger.info(f"✅ {symbol} fechado: P&L = {pnl:.2f} USDT ({trade.pnl_percentage:.2f}%)")
            
            try:
                await telegram_notifier.send_message(
                    f"✅ POSIÇÃO FECHADA\n"
                    f"{symbol} {trade.direction}\n"
                    f"Entry: {trade.entry_price:.4f}\n"
                    f"Exit: {close_price:.4f}\n"
                    f"P&L: {pnl:+.2f} USDT ({trade.pnl_percentage:+.2f}%)\n"
                    f"Razão: Fechamento Manual"
                )
            except Exception as e:
                logger.error(f"Erro ao notificar Telegram: {e}")
            
            return {
                "success": True,
                "message": f"✅ Posição {symbol} fechada com sucesso",
                "close_price": close_price,
                "pnl": pnl,
                "pnl_percentage": trade.pnl_percentage
            }
        
        else:
            return {
                "success": False,
                "message": f"❌ Erro ao fechar: {result.get('reason', 'Erro desconhecido')}"
            }
    
    except Exception as e:
        logger.error(f"Erro ao fechar posição: {e}", exc_info=True)
        db.rollback()
        return {
            "success": False,
            "message": f"❌ Erro: {str(e)}"
        }
    
    finally:
        db.close()


@router.post("/positions/close-all")
async def close_all_positions():
    """Fecha todas as posições abertas"""
    
    db = SessionLocal()
    
    try:
        open_trades = db.query(Trade).filter(Trade.status == 'open').all()
        
        if not open_trades:
            return {
                "success": True,
                "message": "Nenhuma posição aberta",
                "closed_count": 0
            }
        
        results = []
        success_count = 0
        
        for trade in open_trades:
            logger.info(f"🔄 Fechando {trade.symbol}...")
            
            result = await order_executor.close_position(
                symbol=trade.symbol,
                quantity=trade.quantity,
                direction=trade.direction
            )
            
            if result['success']:
                close_price = result['avg_price']
                
                if trade.direction == 'LONG':
                    pnl = (close_price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - close_price) * trade.quantity
                
                trade.status = 'closed'
                trade.exit_price = close_price
                trade.pnl = pnl
                trade.pnl_percentage = (pnl / (trade.entry_price * trade.quantity)) * 100
                trade.exit_time = datetime.now()
                
                success_count += 1
                
                results.append({
                    "symbol": trade.symbol,
                    "success": True,
                    "pnl": pnl,
                    "pnl_percentage": trade.pnl_percentage
                })
                
                try:
                    await telegram_notifier.send_message(
                        f"✅ {trade.symbol} fechado\n"
                        f"P&L: {pnl:+.2f} USDT ({trade.pnl_percentage:+.2f}%)"
                    )
                except:
                    pass
            
            else:
                results.append({
                    "symbol": trade.symbol,
                    "success": False,
                    "reason": result.get('reason', 'Erro desconhecido')
                })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"✅ {success_count}/{len(open_trades)} posições fechadas",
            "closed_count": success_count,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Erro ao fechar posições: {e}", exc_info=True)
        db.rollback()
        return {
            "success": False,
            "message": str(e)
        }
    
    finally:
        db.close()


@router.get("/stats/daily")
async def get_daily_stats():
    """Retorna estatísticas do dia"""
    
    db = SessionLocal()
    
    try:
        from datetime import datetime, timedelta
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        trades = db.query(Trade).filter(
            Trade.closed_at >= today_start,
            Trade.status == 'closed'
        ).all()
        
        if not trades:
            balance_info = await binance_client.get_account_balance()
            return {
                "total_pnl": 0,
                "trades_count": 0,
                "win_rate": 0,
                "best_trade": {},
                "worst_trade": {},
                "balance": balance_info.get('total_balance', 0) if balance_info else 0
            }
        
        total_pnl = sum(t.pnl or 0 for t in trades)
        winning_trades = [t for t in trades if (t.pnl or 0) > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
        
        best_trade = max(trades, key=lambda t: t.pnl or 0)
        worst_trade = min(trades, key=lambda t: t.pnl or 0)
        
        balance_info = await binance_client.get_account_balance()
        
        return {
            "total_pnl": total_pnl,
            "trades_count": len(trades),
            "win_rate": win_rate,
            "best_trade": {
                "symbol": best_trade.symbol,
                "pnl": best_trade.pnl or 0
            },
            "worst_trade": {
                "symbol": worst_trade.symbol,
                "pnl": worst_trade.pnl or 0
            },
            "balance": balance_info.get('total_balance', 0) if balance_info else 0
        }
    
    finally:
        db.close()


@router.post("/report/daily")
async def send_daily_report_manual():
    """Envia relatório diário manualmente"""
    
    try:
        await daily_report.send_manual_report()
        return {"success": True, "message": "Relatório enviado"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== ADMIN: Forçar abertura de múltiplas posições (bypass gerador) ==========
@router.post("/execute/force-many")
async def force_open_many(
    count: int = 15,
    symbols: Optional[str] = None,
    direction: Optional[str] = None,
    leverage: Optional[int] = None
):
    """
    Abre múltiplas posições rapidamente sem depender do gerador de sinais.
    - count: quantidade alvo de posições a abrir
    - symbols: lista CSV opcional (ex: BTCUSDT,ETHUSDT,BNBUSDT). Se omitido, usa uma whitelist padrão.
    - direction: 'LONG' ou 'SHORT'; se omitido alterna LONG/SHORT.
    - leverage: alavancagem alvo (default 10x)
    """
    # Saldo
    balance_info = await binance_client.get_account_balance()
    if not balance_info:
        raise HTTPException(status_code=500, detail="Erro ao obter saldo da conta")

    account_balance = balance_info["available_balance"]
    try:
        account_balance = float(account_balance)
    except Exception:
        pass
    try:
        settings = get_settings()
        if getattr(settings, "VIRTUAL_BALANCE_ENABLED", False):
            account_balance = float(getattr(settings, "VIRTUAL_BALANCE_USDT", 300.0))
    except Exception:
        pass

    # Ajustes de velocidade para entradas (testnet / força de abertura)
    try:
        # Relaxar spread e acelerar timeout de LIMIT para cair em MARKET rápido
        order_executor.max_spread_pct = 1.0
        order_executor.limit_order_timeout = 1
        order_executor.limit_order_buffer_pct = 0.05
    except Exception:
        pass

    # Lista de símbolos alvo
    if symbols:
        candidate_symbols: List[str] = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        candidate_symbols = [
            "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","LTCUSDT",
            "LINKUSDT","DOTUSDT","TRXUSDT","AVAXUSDT","MATICUSDT","BCHUSDT","ATOMUSDT","FILUSDT",
            "NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","FTMUSDT","SANDUSDT","AAVEUSDT","ETCUSDT",
            "XTZUSDT","GALAUSDT","EOSUSDT","APEUSDT","RUNEUSDT","IMXUSDT"
        ]

    results: List[dict] = []
    opened = 0
    attempted = 0

    # Evitar reforçar símbolos já abertos (para aumentar a contagem de posições únicas)
    try:
        _bal = await binance_client.get_account_balance()
        _open_syms = {
            p.get("symbol")
            for p in (_bal.get("positions", []) if _bal else [])
            if abs(float(p.get("positionAmt", 0) or 0)) != 0
        }
    except Exception:
        _open_syms = set()

    # Aux: obter ATR (caindo para 0.5% do preço caso indisponível)
    async def _get_atr(sym: str, price: float):
        """Retorna (atr, volume_ratio, rsi) a partir de klines 1h (fallbacks leves para testnet)."""
        try:
            kl = await binance_client.get_klines(sym, interval="1h", limit=50)
        except Exception:
            kl = []
        # ATR
        try:
            from modules.risk_calculator import risk_calculator as _rc  # import local
            atr_val = _rc.calculate_atr(kl) if kl else 0.0
        except Exception:
            atr_val = 0.0
        if not atr_val or atr_val <= 0:
            atr_val = max(price * 0.005, 1e-6)  # 0.5% como fallback

        # Volume ratio (last / avg20)
        try:
            vols = [float(x[5]) for x in (kl or []) if len(x) > 5]
            if len(vols) >= 21:
                volume_ratio = float(vols[-1]) / (sum(vols[-21:-1]) / 20.0)
            else:
                volume_ratio = 1.0
        except Exception:
            volume_ratio = 1.0

        # RSI(14) simplificado
        try:
            closes = [float(x[4]) for x in (kl or []) if len(x) > 4]
            rsi = 50.0
            if len(closes) >= 15:
                gains = 0.0
                losses = 0.0
                for i in range(-14, 0):
                    diff = closes[i] - closes[i - 1]
                    if diff > 0:
                        gains += diff
                    else:
                        losses -= diff
                avg_gain = gains / 14.0
                avg_loss = losses / 14.0
                if avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100.0 - (100.0 / (1.0 + rs))
        except Exception:
            rsi = 50.0

        return float(atr_val), float(volume_ratio), float(rsi)

    # Loop de abertura
    for i, sym in enumerate(candidate_symbols):
        if opened >= int(count):
            break

        # Pular símbolos já abertos (não aumenta contagem)
        if sym in _open_syms:
            results.append({"symbol": sym, "success": False, "reason": "Já existe posição aberta"})
            continue

        attempted += 1

        # Preço atual
        price = await binance_client.get_symbol_price(sym)
        if not price or float(price) <= 0:
            results.append({"symbol": sym, "success": False, "reason": "Preço indisponível"})
            continue
        price = float(price)

        atr, volume_ratio, rsi = await _get_atr(sym, price)

        # Direção
        dir_used = (direction or ("LONG" if (i % 2 == 0) else "SHORT")).upper()
        if dir_used not in ("LONG", "SHORT"):
            dir_used = "LONG"

        # SL/TP simples baseados em ATR (R:R ~ 2:1)
        if dir_used == "LONG":
            stop = price - 1.5 * atr
            tp1 = price + 3.0 * atr
            tp2 = price + 4.5 * atr
            tp3 = price + 6.0 * atr
        else:
            stop = price + 1.5 * atr
            tp1 = price - 3.0 * atr
            tp2 = price - 4.5 * atr
            tp3 = price - 6.0 * atr

        # Montar sinal mínimo compatível com o executor
        # R:R para alavancagem dinâmica
        risk = abs(price - stop)
        reward = abs(tp1 - price)
        risk_reward = (reward / risk) if risk > 0 else 1.0

        if leverage is None:
            try:
                lev_used = int(signal_generator._calculate_leverage(volume_ratio, rsi, risk_reward))
            except Exception:
                lev_used = 10
        else:
            lev_used = int(leverage)

        signal = {
            "symbol": sym,
            "direction": dir_used,
            "entry_price": price,
            "stop_loss": float(stop),
            "take_profit_1": float(tp1),
            "take_profit_2": float(tp2),
            "take_profit_3": float(tp3),
            "leverage": lev_used,
            "score": 95,  # alto para não ser bloqueado por heurísticas
            "force": True,
        }

        try:
            exec_res = await order_executor.execute_signal(
                signal=signal,
                account_balance=account_balance,
                open_positions=opened,  # aproximação
                dry_run=False
            )
            ok = bool(exec_res.get("success"))
            if ok:
                opened += 1
            results.append({
                "symbol": sym,
                "success": ok,
                "direction": dir_used,
                "entry": exec_res.get("entry_price") or exec_res.get("avg_price"),
                "order_id": exec_res.get("order_id"),
                "reason": None if ok else exec_res.get("reason")
            })
        except Exception as e:
            results.append({"symbol": sym, "success": False, "reason": str(e)})

        # Pequeno espaçamento para evitar rate-limit
        await asyncio.sleep(0.5)

    # Checar contagem na exchange (melhor esforço)
    try:
        balance_info2 = await binance_client.get_account_balance()
        live_positions = [p for p in (balance_info2.get("positions", []) if balance_info2 else []) if abs(float(p.get("positionAmt", 0) or 0)) != 0]
        live_count = len(live_positions)
    except Exception:
        live_count = None

    return {
        "attempted": attempted,
        "opened": opened,
        "target": count,
        "live_count": live_count,
        "results": results
    }


@router.post("/execute/force-many/async")
async def force_open_many_async(
    count: int = 15,
    symbols: Optional[str] = None,
    direction: Optional[str] = None,
    leverage: Optional[int] = 10
):
    """Dispara em background a abertura de múltiplas posições e retorna imediatamente.
    Use /api/trading/positions para acompanhar."""
    try:
        asyncio.create_task(force_open_many(count=count, symbols=symbols, direction=direction, leverage=leverage))
        return {"accepted": True, "target": int(count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Estratégico: Abrir novas posições usando toda a estratégia ==========
@router.post("/positions/add-strategic")
async def positions_add_strategic(count: int = 4):
    """Abre 'count' novas posições utilizando o pipeline completo:
    scanner → signal_generator → market_filter → correlation_filter → order_executor.
    """
    try:
        res = await autonomous_bot.add_strategic_positions(count=count)
        return _to_native(res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar posições estrategicamente: {str(e)}")


@router.post("/positions/add-strategic/async")
async def positions_add_strategic_async(count: int = 4):
    """Dispara em background a abertura estratégica de posições e retorna imediatamente.
    Use /api/trading/positions para acompanhar a evolução."""
    try:
        asyncio.create_task(autonomous_bot.add_strategic_positions(count=count))
        return {"accepted": True, "target": int(count)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enfileirar abertura estratégica: {str(e)}")


# ========== Sniper: 5 slots extras para scalps rápidos ==========
@router.post("/execute/sniper")
async def execute_sniper(
    count: int = 5,
    symbols: Optional[str] = None,
    direction: Optional[str] = None
):
    """Abre rapidamente até 'count' posições do tipo sniper (scalps rápidos),
    usando SL/TP curtos e respeitando SNIPER_EXTRA_SLOTS."""
    settings = get_settings()
    try:
        extra_slots = int(getattr(settings, "SNIPER_EXTRA_SLOTS", 0))
    except Exception:
        extra_slots = 0
    try:
        core_max = int(getattr(settings, "MAX_POSITIONS", 15))
    except Exception:
        core_max = 15

    max_total_positions = core_max + max(0, extra_slots)

    # Saldo
    balance_info = await binance_client.get_account_balance()
    if not balance_info:
        raise HTTPException(status_code=500, detail="Erro ao obter saldo da conta")

    account_balance = balance_info["available_balance"]
    try:
        account_balance = float(account_balance)
    except Exception:
        pass
    try:
        if getattr(settings, "VIRTUAL_BALANCE_ENABLED", False):
            account_balance = float(getattr(settings, "VIRTUAL_BALANCE_USDT", 300.0))
    except Exception:
        pass

    # Posições já abertas na exchange
    existing_positions = [
        p for p in balance_info.get("positions", [])
        if abs(float(p.get("positionAmt", 0) or 0)) != 0
    ]
    base_open = len(existing_positions)

    available_slots = max(0, max_total_positions - base_open)
    if available_slots <= 0:
        return {
            "success": False,
            "message": f"Sem slots sniper disponíveis ({base_open}/{max_total_positions})",
            "opened": 0,
            "target": int(count)
        }

    target = min(int(count), available_slots)

    # Lista de símbolos alvo
    if symbols:
        candidate_symbols: List[str] = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        candidate_symbols = [
            "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT","DOGEUSDT","LTCUSDT",
            "LINKUSDT","DOTUSDT","TRXUSDT","AVAXUSDT","MATICUSDT","BCHUSDT","ATOMUSDT","FILUSDT",
            "NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","FTMUSDT","SANDUSDT","AAVEUSDT","ETCUSDT",
            "XTZUSDT","GALAUSDT","EOSUSDT","APEUSDT","RUNEUSDT","IMXUSDT"
        ]

    # Permitir reforçar símbolos já abertos (sniper pode scalpar em cima de posição core)
    open_symbols = {p.get("symbol") for p in existing_positions}

    tp_pct = float(getattr(settings, "SNIPER_TP_PCT", 0.6)) / 100.0
    sl_pct = float(getattr(settings, "SNIPER_SL_PCT", 0.3)) / 100.0
    lev_default = int(getattr(settings, "SNIPER_DEFAULT_LEVERAGE", 10))

    results: List[dict] = []
    opened = 0
    attempted = 0

    for i, sym in enumerate(candidate_symbols):
        if opened >= target:
            break



        attempted += 1

        price = await binance_client.get_symbol_price(sym)
        if not price or float(price) <= 0:
            results.append({"symbol": sym, "success": False, "reason": "Preço indisponível"})
            continue
        price = float(price)

        dir_used = (direction or ("LONG" if (i % 2 == 0) else "SHORT")).upper()
        if dir_used not in ("LONG", "SHORT"):
            dir_used = "LONG"

        if dir_used == "LONG":
            stop = price * (1.0 - sl_pct)
            tp = price * (1.0 + tp_pct)
        else:
            stop = price * (1.0 + sl_pct)
            tp = price * (1.0 - tp_pct)

        signal = {
            "symbol": sym,
            "direction": dir_used,
            "entry_price": price,
            "stop_loss": float(stop),
            "take_profit_1": float(tp),
            "take_profit_2": None,
            "take_profit_3": None,
            "leverage": lev_default,
            "score": 99,
            "sniper": True,
            "risk_pct": 1.0,
            "force": True,
        }

        try:
            exec_res = await order_executor.execute_signal(
                signal=signal,
                account_balance=account_balance,
                open_positions=base_open + opened,
                dry_run=False
            )
            ok = bool(exec_res.get("success"))
            if ok:
                opened += 1
                open_symbols.add(sym)
            results.append({
                "symbol": sym,
                "success": ok,
                "direction": dir_used,
                "entry": exec_res.get("entry_price") or exec_res.get("avg_price"),
                "order_id": exec_res.get("order_id"),
                "reason": None if ok else exec_res.get("reason")
            })
        except Exception as e:
            results.append({"symbol": sym, "success": False, "reason": str(e)})

        await asyncio.sleep(0.3)

    # Checar contagem final
    try:
        balance_info2 = await binance_client.get_account_balance()
        live_positions = [
            p for p in (balance_info2.get("positions", []) if balance_info2 else [])
            if abs(float(p.get("positionAmt", 0) or 0)) != 0
        ]
        live_count = len(live_positions)
    except Exception:
        live_count = None

    return {
        "success": opened > 0,
        "attempted": attempted,
        "opened": opened,
        "target": target,
        "max_total_positions": max_total_positions,
        "live_count": live_count,
        "results": results,
    }
# =========================
# Manual Trading & History
# =========================

class ManualTradeRequest(BaseModel):
    symbol: str
    direction: str  # LONG or SHORT
    amount: float
    amount_type: str = "quantity" # quantity, usdt_total, usdt_margin
    leverage: int = 10
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@router.post("/manual")
async def execute_manual_trade(request: ManualTradeRequest):
    """
    Executa um trade manual sem passar pelo gerador de sinais.
    Cria um sinal sintético e envia para o executor.
    Suporta cálculo de quantidade baseado em USDT Total ou Margem.
    """
    try:
        # 1. Validar input
        symbol = request.symbol.upper()
        direction = request.direction.upper()
        if direction not in ['LONG', 'SHORT']:
            raise HTTPException(status_code=400, detail="Direction must be LONG or SHORT")
            
        # 2. Obter preço atual
        price = await binance_client.get_symbol_price(symbol)
        if not price:
            raise HTTPException(status_code=400, detail="Symbol price not found")
            
        # 3. Calcular Quantidade Baseada no Tipo
        quantity = 0.0
        if request.amount_type == "quantity":
            quantity = request.amount
        elif request.amount_type == "usdt_total":
            # Valor total da posição em USDT (Notional)
            # Qty = Total / Price
            quantity = request.amount / price
        elif request.amount_type == "usdt_margin":
            # Valor da margem (cost) em USDT
            # Total = Margin * Leverage
            # Qty = (Margin * Leverage) / Price
            quantity = (request.amount * request.leverage) / price
        else:
            raise HTTPException(status_code=400, detail="Invalid amount_type. Use: quantity, usdt_total, usdt_margin")

        # Arredondar quantidade (precisão básica, ideal seria pegar do exchange info)
        # Vamos assumir 4 casas decimais por segurança para a maioria das cryptos, 
        # mas o executor deve tratar a precisão final.
        # O executor tem lógica de step size? Sim, _adjust_quantity_precision
        
        # 4. Construir SL/TP Defaults se necessário
        sl = request.stop_loss
        if not sl:
            if direction == 'LONG':
                sl = price * 0.98
            else:
                sl = price * 1.02
                
        tp = request.take_profit
        if not tp:
            if direction == 'LONG':
                tp = price * 1.04
            else:
                tp = price * 0.96

        synthetic_signal = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": price,
            "stop_loss": sl,
            "take_profit_1": tp,
            "take_profit_2": None,
            "take_profit_3": None,
            "leverage": request.leverage,
            "score": 100,
            "force": True,
            "user_quantity": quantity # Passamos a quantidade calculada
        }
        
        # 5. Executar
        balance_info = await binance_client.get_account_balance()
        account_balance = float(balance_info.get('available_balance', 0))
        
        result = await order_executor.execute_signal(
            signal=synthetic_signal,
            account_balance=account_balance,
            open_positions=0,
            dry_run=False
        )
        
        return result

    except Exception as e:
        logger.error(f"Erro no trade manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Erro no trade manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_trade_history(limit: int = 50):
    """Retorna histórico de trades fechados com PnL"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(
            Trade.status == 'closed'
        ).order_by(Trade.closed_at.desc()).limit(limit).all()
        
        return _to_native([
            {
                "id": t.id,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "pnl_percentage": t.pnl_percentage,
                "opened_at": t.opened_at,
                "closed_at": t.closed_at,
                "leverage": t.leverage
            }
            for t in trades
        ])
    finally:
        db.close()
