from fastapi import APIRouter, Query
import asyncio
import time
import httpx
from utils.binance_client import binance_client
from modules.market_scanner import market_scanner
from modules.signal_generator import signal_generator
from modules.risk_calculator import risk_calculator
from utils.logger import setup_logger
from api.models.trades import Trade

router = APIRouter()
logger = setup_logger("market_routes")

_TICKERS_CACHE = {"ts": 0.0, "data": []}
_TICKERS_TTL_SEC = 15
_FNG_CACHE = {"ts": 0.0, "data": [], "limit": 0}
_FNG_TTL_SEC = 300


@router.get("/balance")
async def get_balance():
    """Retorna saldo da conta Binance Futures"""
    balance = await binance_client.get_account_balance()
    return balance


@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """Retorna preço atual de um símbolo"""
    price = await binance_client.get_symbol_price(symbol.upper())
    return {"symbol": symbol, "price": price}


@router.get("/scan")
async def scan_market(limit: int = Query(default=50, ge=10, le=100)):
    """Escaneia o mercado e retorna análise técnica das top moedas"""
    analysis = await market_scanner.scan_market()
    analysis_limited = analysis[:limit]
    return {
        "count": len(analysis_limited),
        "analysis": analysis_limited,
        "top_10": analysis_limited[:10]
    }


@router.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str):
    """Analisa um símbolo específico"""
    analysis = await market_scanner.analyze_symbol(symbol.upper())
    if analysis:
        return analysis
    return {"error": "Não foi possível analisar o símbolo"}


@router.get("/signals")
async def get_signals(min_score: int = Query(default=60, ge=50, le=90)):
    """✅ CORRIGIDO: Trading signals com parâmetros completos"""
    
    try:
        # Escanear mercado
        scan_results = await market_scanner.scan_market()
        
        if not scan_results:
            return {
                "count": 0,
                "signals": [],
                "message": "Nenhum símbolo encontrado no scan"
            }
        
        # Gerar sinais a partir dos resultados do scan
        signals = await signal_generator.generate_signal(scan_results)
        
        # Filtrar por score mínimo
        filtered_signals = [
            s for s in signals 
            if s.get('score', 0) >= min_score
        ]
        
        return {
            "count": len(filtered_signals),
            "signals": filtered_signals,
            "scan_count": len(scan_results)
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar sinais: {e}")
        return {
            "count": 0,
            "signals": [],
            "error": str(e)
        }


@router.get("/signal/{symbol}")
async def generate_signal(symbol: str, risk_profile: str = Query(default="moderate", regex="^(conservative|moderate|aggressive)$")):
    """Gera sinal de trading para um símbolo específico (pipeline completo)."""
    sig = await signal_generator.generate_signal_for_symbol(symbol.upper(), risk_profile)
    if not sig:
        return {"error": "Não foi possível gerar sinal para este símbolo"}
    # Prévia de position sizing com banca fictícia (não envia ordem)
    try:
        sizing = risk_calculator.calculate_position_size(
            symbol=sig["symbol"],
            direction=sig["direction"],
            entry_price=float(sig["entry_price"]),
            stop_loss=float(sig["stop_loss"]),
            leverage=int(sig["leverage"]),
            account_balance=5000.0  # prévia com $5k
        )
    except Exception as e:
        sizing = {"approved": False, "reason": f"preview_failed: {e}"}
    sig["position_preview"] = sizing
    return sig


@router.get("/derivatives/{symbol}")
async def get_derivatives(symbol: str, oi_period: str = Query(default="5m"), oi_lookback: int = Query(default=12)):
    """
    Diagnóstico de derivativos para um símbolo:
    - premium index (mark/index price, lastFundingRate, nextFundingTime)
    - open interest atual e variação percentual (histórico)
    - taker buy/sell ratio (predomínio de agressores)
    """
    symbol = symbol.upper()
    premium_coro = binance_client.get_premium_index(symbol)
    oi_now_coro = binance_client.get_open_interest(symbol)
    oi_ch_coro = binance_client.get_open_interest_change(symbol, period=oi_period, limit=oi_lookback)
    taker_coro = binance_client.get_taker_long_short_ratio(symbol, period=oi_period, limit=oi_lookback)
    premium, oi_now, oi_change, taker = await asyncio.gather(premium_coro, oi_now_coro, oi_ch_coro, taker_coro)
    return {
        "symbol": symbol,
        "premium": premium,
        "open_interest": oi_now,
        "open_interest_change": oi_change,
        "taker_ratio": taker
    }

@router.get("/top100")
async def get_top_100():
    """Retorna top 100 moedas por volume"""
    symbols = await binance_client.get_top_futures_symbols(limit=100)
    return {"count": len(symbols), "symbols": symbols}


@router.get("/tickers")
async def get_tickers(limit: int = Query(default=200, ge=20, le=1000), quote: str = "USDT"):
    """Retorna tickers futuros filtrados por quote (default USDT)."""
    now = time.time()
    if _TICKERS_CACHE["data"] and (now - _TICKERS_CACHE["ts"]) < _TICKERS_TTL_SEC:
        data = _TICKERS_CACHE["data"]
    else:
        try:
            rows = await asyncio.to_thread(binance_client.client.futures_ticker)
        except Exception as e:
            logger.error(f"Erro ao obter tickers: {e}")
            return {"count": 0, "tickers": []}

        quote = str(quote or "USDT").upper()
        data = []
        for t in rows or []:
            symbol = str(t.get("symbol") or "").upper()
            if not symbol.endswith(quote):
                continue
            try:
                last_price = float(t.get("lastPrice", 0) or 0)
            except Exception:
                last_price = 0.0
            try:
                change_pct = float(t.get("priceChangePercent", 0) or 0)
            except Exception:
                change_pct = 0.0
            try:
                quote_volume = float(t.get("quoteVolume", 0) or 0)
            except Exception:
                quote_volume = 0.0

            data.append({
                "symbol": symbol,
                "last_price": last_price,
                "price_change_percent": change_pct,
                "quote_volume": quote_volume
            })

        _TICKERS_CACHE["data"] = data
        _TICKERS_CACHE["ts"] = now

    data_sorted = sorted(data, key=lambda x: x.get("quote_volume", 0), reverse=True)
    limited = data_sorted[:limit]
    return {"count": len(limited), "tickers": limited}


@router.get("/fear-greed")
async def get_fear_greed(limit: int = Query(default=30, ge=1, le=365)):
    """Returns Fear and Greed index series (cached)."""
    now = time.time()
    if (
        _FNG_CACHE["data"]
        and _FNG_CACHE["limit"] == limit
        and (now - _FNG_CACHE["ts"]) < _FNG_TTL_SEC
    ):
        data = _FNG_CACHE["data"]
    else:
        url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                res.raise_for_status()
                payload = res.json()
        except Exception as e:
            logger.error(f"Error fetching fear_greed: {e}")
            return {"count": 0, "data": []}

        rows = payload.get("data") or []
        data = []
        for row in rows:
            try:
                value = int(float(row.get("value", 0) or 0))
            except Exception:
                value = 0
            try:
                ts = int(row.get("timestamp", 0) or 0)
            except Exception:
                ts = 0
            data.append({
                "value": value,
                "classification": row.get("value_classification"),
                "timestamp": ts,
            })

        data = sorted(data, key=lambda x: x["timestamp"])
        _FNG_CACHE["data"] = data
        _FNG_CACHE["ts"] = now
        _FNG_CACHE["limit"] = limit

    latest = data[-1] if data else None
    return {"count": len(data), "data": data, "latest": latest}


@router.get("/klines/{symbol}")
async def get_klines(symbol: str, interval: str = "1h", limit: int = 100):
    """Retorna dados de candlestick"""
    klines = await binance_client.get_klines(
        symbol=symbol.upper(),
        interval=interval,
        limit=limit
    )
    return {"symbol": symbol, "count": len(klines), "klines": klines}
