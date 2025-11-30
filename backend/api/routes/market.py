from fastapi import APIRouter, Query
import asyncio
from utils.binance_client import binance_client
from modules.market_scanner import market_scanner
from modules.signal_generator import signal_generator
from modules.risk_calculator import risk_calculator
from utils.logger import setup_logger
from api.models.trades import Trade

router = APIRouter()
logger = setup_logger("market_routes")


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


@router.get("/klines/{symbol}")
async def get_klines(symbol: str, interval: str = "1h", limit: int = 100):
    """Retorna dados de candlestick"""
    klines = await binance_client.get_klines(
        symbol=symbol.upper(),
        interval=interval,
        limit=limit
    )
    return {"symbol": symbol, "count": len(klines), "klines": klines}
