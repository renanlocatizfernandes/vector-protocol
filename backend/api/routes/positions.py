from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from typing import List, Dict, Optional, Tuple
from utils.binance_client import binance_client
from modules.risk_manager import risk_manager
from api.models.trades import Trade
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("positions_routes")

@router.get("/")
async def get_positions(db: Session = Depends(get_db)):
    """Retorna posições atuais (trades abertos)"""
    positions = db.query(Trade).filter(Trade.status.in_(["open", "OPEN"])).all()
    return {"positions": positions}

@router.get("/trades")
async def get_trades(db: Session = Depends(get_db)):
    """Retorna todos os trades"""
    trades = db.query(Trade).order_by(Trade.opened_at.desc()).limit(50).all()
    return {"trades": trades}

@router.get("/trades/open")
async def get_open_trades(db: Session = Depends(get_db)):
    """Retorna trades abertos"""
    trades = db.query(Trade).filter(Trade.status.in_(["open", "OPEN"])).all()
    return {"trades": trades}

@router.get("/trades/closed")
async def get_closed_trades(db: Session = Depends(get_db)):
    """Retorna trades fechados"""
    trades = db.query(Trade).filter(Trade.status.in_(["closed", "CLOSED"])).order_by(Trade.closed_at.desc()).limit(20).all()
    return {"trades": trades}

@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """Retorna dados completos para dashboard"""
    
    # Obter saldo da conta
    balance_info = await binance_client.get_account_balance()
    account_balance = 0.0
    if balance_info:
        try:
            account_balance = float(balance_info.get("available_balance", 0) or 0)
        except Exception:
            account_balance = 0.0
    
    # Trades abertos (DB)
    open_trades = db.query(Trade).filter(Trade.status.in_(["open", "OPEN"])).all()
    # Coleta modos de margem das posições vivas na corretora (Cross/Isolated)
    try:
        margin_items = await binance_client.get_positions_margin_modes()
        margin_map = {it.get("symbol"): it for it in (margin_items or [])}
    except Exception:
        margin_map = {}
    
    # Métricas do portfólio (DB)
    open_positions_data = [
        {
            'symbol': t.symbol,
            'position_size': float((t.quantity or 0) * (t.entry_price or 0)),
            'unrealized_pnl': float(t.pnl or 0)
        }
        for t in open_trades
    ]

    # Posições vivas da exchange (quando houver)
    exchange_positions = []
    if balance_info:
        for p in balance_info.get("positions", []) or []:
            symbol = p.get("symbol")
            try:
                position_amt = float(p.get("positionAmt", 0) or 0)
            except Exception:
                position_amt = 0.0
            if not symbol or abs(position_amt) <= 0:
                continue

            try:
                entry_price = float(p.get("entryPrice", 0) or 0)
            except Exception:
                entry_price = 0.0
            try:
                mark_price = float(p.get("markPrice", 0) or 0)
            except Exception:
                mark_price = 0.0
            try:
                leverage = float(p.get("leverage", 0) or 0)
            except Exception:
                leverage = 0.0
            try:
                unrealized = float(p.get("unRealizedProfit", p.get("unrealizedProfit", 0) or 0))
            except Exception:
                unrealized = 0.0

            qty = abs(position_amt)
            direction = "LONG" if position_amt > 0 else "SHORT"
            margin_info = margin_map.get(symbol) or {}

            pnl_pct = None
            base_notional = qty * entry_price if entry_price > 0 else 0.0
            if base_notional > 0:
                pnl_pct = (unrealized / base_notional) * 100

            exchange_positions.append({
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry_price,
                "current_price": mark_price or entry_price,
                "quantity": qty,
                "leverage": leverage,
                "pnl": unrealized,
                "pnl_percentage": pnl_pct,
                "opened_at": None,
                "margin_mode": margin_info.get("margin_mode"),
                "isolated": margin_info.get("isolated"),
            })

    use_exchange = len(exchange_positions) > 0
    positions_source = "exchange" if use_exchange else "db"

    if use_exchange:
        positions_for_metrics = [
            {
                "symbol": p["symbol"],
                "position_size": float(p.get("quantity") or 0)
                * float(p.get("current_price") or p.get("entry_price") or 0),
                "unrealized_pnl": float(p.get("pnl") or 0),
            }
            for p in exchange_positions
        ]
    else:
        positions_for_metrics = open_positions_data

    portfolio_metrics = risk_manager.calculate_portfolio_metrics(
        positions_for_metrics,
        account_balance
    )
    
    # Estatísticas de trades
    total_trades = db.query(Trade).count()
    closed_trades = db.query(Trade).filter(Trade.status.in_(["closed", "CLOSED"])).all()
    
    winning_trades = [t for t in closed_trades if t.pnl_percentage > 0]
    losing_trades = [t for t in closed_trades if t.pnl_percentage <= 0]
    
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
    
    avg_win = sum(t.pnl_percentage for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.pnl_percentage for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    return {
        "account": {
            "balance": account_balance,
            "total_wallet": balance_info.get('total_balance', 0) if balance_info else 0
        },
        "portfolio": portfolio_metrics,
        "open_trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "current_price": t.current_price,
                "quantity": t.quantity,
                "leverage": t.leverage,
                "pnl": t.pnl,
                "pnl_percentage": t.pnl_percentage,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                # Enriquecimento com modo de margem observado na corretora
                "margin_mode": (margin_map.get(t.symbol) or {}).get("margin_mode"),
                "isolated": (margin_map.get(t.symbol) or {}).get("isolated"),
            }
            for t in open_trades
        ],
        "exchange_positions": exchange_positions,
        "positions_source": positions_source,
        "statistics": {
            "total_trades": total_trades,
            "open_trades": len(open_trades),
            "closed_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2)
        }
    }


@router.get("/margins")
async def get_positions_margins():
    """
    Lista posições vivas na corretora com indicação do modo de margem por símbolo.
    Útil para auditar se estamos em Cross (CROSSED) ou Isolated (ISOLATED).
    """
    items = await binance_client.get_positions_margin_modes()
    crossed = [i for i in items if not bool(i.get("isolated"))]
    isolated = [i for i in items if bool(i.get("isolated"))]
    return {
        "count": len(items),
        "crossed": len(crossed),
        "isolated": len(isolated),
        "items": items
    }

async def _get_exchange_positions_map() -> Dict[str, float]:
    """Mapa símbolo -> positionAmt (float). positionAmt != 0 indica posição viva."""
    try:
        balance_info = await binance_client.get_account_balance()
    except Exception:
        balance_info = None

    m: Dict[str, float] = {}
    try:
        if balance_info:
            for p in balance_info.get("positions", []):
                s = p.get("symbol")
                try:
                    amt = float(p.get("positionAmt", 0) or 0)
                except Exception:
                    amt = 0.0
                if s:
                    m[s] = amt
    except Exception:
        pass
    return m


def _is_long(direction: Optional[str]) -> Optional[bool]:
    if not direction:
        return None
    d = str(direction).upper()
    if "LONG" in d or "BUY" in d:
        return True
    if "SHORT" in d or "SELL" in d:
        return False
    return None


async def reconcile_positions(db: Session, strict: bool = False) -> Dict[str, object]:
    """
    Core de sincronização de posições:
    - Modo normal: fecha trades 'open' cujo símbolo NÃO esteja aberto na exchange.
    - Modo estrito: além do normal, garante que:
        * Apenas o lado (LONG/SHORT) da posição líquida permaneça aberto
        * A soma de quantities no DB não exceda a quantity líquida da exchange (fecha excedentes mais antigos)
    Nunca envia ordens para a corretora.
    """
    from datetime import datetime

    positions_map = await _get_exchange_positions_map()
    exchange_symbols_nonzero = {s for s, amt in positions_map.items() if abs(amt) > 0}

    open_db_trades: List[Trade] = db.query(Trade).filter(Trade.status.in_(["open", "OPEN"])).all()

    closed_stale = 0
    closed_strict = 0

    def _close_trade(t: Trade):
        nonlocal closed_stale, closed_strict
        t.status = "closed"
        try:
            if hasattr(t, "exit_price") and t.current_price is not None:
                setattr(t, "exit_price", float(t.current_price))
        except Exception:
            pass
        if hasattr(t, "closed_at"):
            setattr(t, "closed_at", datetime.now())

    # Passo 1: modo normal — fecha símbolos que não estão abertos na exchange
    for t in open_db_trades:
        if t.symbol not in exchange_symbols_nonzero:
            _close_trade(t)
            closed_stale += 1

    if strict:
        # Recarregar a lista corrente (alguns podem ter sido fechados acima)
        current_open = [t for t in open_db_trades if str(t.status).lower() == "open"]

        # Iterar por símbolo presente no DB (mesmo que exchange 0 → fechar todos)
        symbols_in_db = {t.symbol for t in current_open}
        for sym in symbols_in_db:
            exchange_amt = float(positions_map.get(sym, 0.0) or 0.0)
            desired_exists = abs(exchange_amt) > 0
            desired_long = exchange_amt > 0

            sym_trades = [t for t in current_open if t.symbol == sym and str(t.status).lower() == "open"]

            if not desired_exists:
                # Não deveria haver nada aberto: fechar todos do símbolo
                for t in sym_trades:
                    _close_trade(t)
                    closed_strict += 1
                continue

            # Fechar os que estão no lado oposto da posição líquida
            for t in sym_trades:
                side = _is_long(t.direction)
                if side is not None and side != desired_long:
                    _close_trade(t)
                    closed_strict += 1

            # Filtrar os que sobraram no lado correto
            remaining = [t for t in sym_trades if str(t.status).lower() == "open" and _is_long(t.direction) == desired_long]

            # Se quantity no DB excede a líquida, fechar excedentes (mais antigos primeiro)
            try:
                total_qty = sum(abs(float(t.quantity or 0)) for t in remaining)
                desired_qty = abs(exchange_amt)
            except Exception:
                total_qty = 0.0
                desired_qty = 0.0

            eps = 1e-12
            if total_qty - desired_qty > eps:
                remaining_sorted = sorted(remaining, key=lambda x: x.opened_at or 0)
                for t in remaining_sorted:
                    if total_qty - desired_qty > eps:
                        _close_trade(t)
                        try:
                            total_qty -= abs(float(t.quantity or 0))
                        except Exception:
                            pass
                        closed_strict += 1
                    else:
                        break

    db.commit()

    return {
        "db_open_before": len(open_db_trades),
        "exchange_open": len(exchange_symbols_nonzero),
        "closed_stale": closed_stale,
        "closed_strict": closed_strict,
        "exchange_symbols": sorted(list(exchange_symbols_nonzero))
    }


@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Returns current sync health status (Phase 4).

    Compares DB positions vs Exchange positions and reports divergences.
    """
    try:
        import redis
        from config.settings import get_settings
        from datetime import datetime

        settings = get_settings()

        # Get last auto-sync time from Redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        last_sync = redis_client.get("positions:last_sync_time")
        last_sync_dt = datetime.fromisoformat(last_sync) if last_sync else None

        # Compare DB vs Exchange positions
        exchange_positions = await _get_exchange_positions_map()
        db_positions = db.query(Trade).filter(Trade.status == 'open').all()

        db_symbols = {
            t.symbol: float(t.quantity) * (1 if t.direction == 'LONG' else -1)
            for t in db_positions
        }

        # Find divergences
        divergences = []
        all_symbols = set(list(exchange_positions.keys()) + list(db_symbols.keys()))

        for symbol in all_symbols:
            exchange_qty = exchange_positions.get(symbol, 0)
            db_qty = db_symbols.get(symbol, 0)

            # Allow tiny float differences
            if abs(exchange_qty - db_qty) > 0.0001:
                divergences.append({
                    "symbol": symbol,
                    "exchange_qty": exchange_qty,
                    "db_qty": db_qty,
                    "delta": round(exchange_qty - db_qty, 4)
                })

        # Calculate time since last sync
        last_sync_ago_seconds = None
        if last_sync_dt:
            last_sync_ago_seconds = (datetime.utcnow() - last_sync_dt).total_seconds()

        status = "ok" if len(divergences) == 0 else "warning"

        return {
            "last_sync": last_sync_dt.isoformat() if last_sync_dt else None,
            "last_sync_ago_seconds": last_sync_ago_seconds,
            "auto_sync_enabled": settings.POSITIONS_AUTO_SYNC_ENABLED,
            "auto_sync_interval_minutes": settings.POSITIONS_AUTO_SYNC_MINUTES,
            "divergences": divergences,
            "divergence_count": len(divergences),
            "status": status,
            "db_positions_count": len(db_positions),
            "exchange_positions_count": len([q for q in exchange_positions.values() if q != 0])
        }

    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_positions(
    mode: Optional[str] = Query(default=None, description="normal|strict"),
    strict: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Sincroniza os trades 'abertos' no DB com as posições reais da corretora.
    - normal (padrão): fecha trades cujo símbolo não está aberto na exchange.
    - strict: aplica reconciliação forte (lado líquido e quantidade não excedente).
    """
    use_strict = bool(strict) or (str(mode).lower() == "strict" if mode else False)
    return await reconcile_positions(db, strict=use_strict)


# =======================
# Exchange Open Orders / Diagnóstico
# =======================
from typing import Any
import asyncio
from modules.autonomous_bot import autonomous_bot

def _trim_order(o: Dict[str, Any]) -> Dict[str, Any]:
    """Reduz tamanho do payload de ordens para inspeção."""
    fields = ("symbol","orderId","clientOrderId","type","side","origQty","executedQty","cumQuote",
              "price","avgPrice","stopPrice","reduceOnly","status","time","updateTime","positionSide","workingType")
    out = {}
    for k in fields:
        if k in o:
            out[k] = o[k]
    return out

@router.get("/open-orders")
async def get_open_orders(symbol: Optional[str] = Query(default=None, description="Símbolo opcional para filtrar")):
    """
    Lista ordens abertas na Binance Futures (USD‑M).
    Retorna total, contagem por símbolo e amostra das ordens (trimmed).
    """
    try:
        if symbol:
            rows = await asyncio.to_thread(binance_client.client.futures_get_open_orders, symbol=symbol.upper())
        else:
            rows = await asyncio.to_thread(binance_client.client.futures_get_open_orders)
    except Exception as e:
        return {"success": False, "error": str(e), "total": 0, "by_symbol": {}}

    rows = rows or []
    by_symbol: Dict[str, int] = {}
    for r in rows:
        s = r.get("symbol")
        by_symbol[s] = by_symbol.get(s, 0) + 1

    sample = [_trim_order(r) for r in rows[:200]]
    return {
        "success": True,
        "total": len(rows),
        "by_symbol": dict(sorted(by_symbol.items(), key=lambda kv: kv[0])),
        "sample_len": len(sample),
        "sample": sample
    }

@router.post("/open-orders/cancel-all")
async def cancel_all_open_orders(
    symbol: Optional[str] = Query(default=None, description="Se informado, cancela apenas deste símbolo"),
    dry_run: bool = Query(default=True, description="true=apenas simulação; false=executa cancelamento"),
):
    """
    Cancela ordens abertas:
    - symbol omitido: carrega lista e cancela por símbolo (allOpenOrders) — cuidado em produção.
    - symbol informado: cancela todas de um símbolo.
    """
    # Carregar conjunto de símbolos a cancelar
    try:
        if symbol:
            symbols = [symbol.upper()]
        else:
            rows = await asyncio.to_thread(binance_client.client.futures_get_open_orders)
            symbols = sorted({r.get("symbol") for r in (rows or []) if r.get("symbol")})
    except Exception as e:
        return {"success": False, "error": str(e)}

    if dry_run:
        return {"success": True, "dry_run": True, "symbols": symbols, "message": f"{len(symbols)} símbolo(s) elegível(is) para cancelamento"}

    results = {}
    ok = 0
    for sym in symbols:
        try:
            res = await asyncio.to_thread(binance_client.client.futures_cancel_all_open_orders, symbol=sym)
            results[sym] = {"canceled": True, "response": res}
            ok += 1
            await asyncio.sleep(0.2)
        except Exception as e:
            results[sym] = {"canceled": False, "error": str(e)}
    return {"success": True, "dry_run": False, "executed_on": ok, "results": results}

@router.get("/diagnostics/exchange")
async def diagnostics_exchange():
    """
    Sumário de estado da exchange: posições vivas, ordens abertas, limites do bot.
    """
    # Posições vivas (exchange)
    exch_map = await _get_exchange_positions_map()
    live_symbols = [s for s, amt in exch_map.items() if abs(amt) > 0]

    # Ordens abertas
    try:
        open_orders = await asyncio.to_thread(binance_client.client.futures_get_open_orders)
    except Exception:
        open_orders = []
    by_symbol: Dict[str, int] = {}
    for r in (open_orders or []):
        s = r.get("symbol")
        by_symbol[s] = by_symbol.get(s, 0) + 1

    return {
        "bot": {
            "running": autonomous_bot.running,
            "dry_run": autonomous_bot.dry_run,
            "max_positions": getattr(autonomous_bot, "max_positions", None),
            "scan_interval": getattr(autonomous_bot, "scan_interval", None),
            "min_score": getattr(autonomous_bot, "min_score", None),
        },
        "exchange": {
            "open_positions_count": len(live_symbols),
            "open_positions_symbols": sorted(live_symbols),
            "open_orders_total": len(open_orders or []),
            "open_orders_by_symbol": dict(sorted(by_symbol.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
    }
