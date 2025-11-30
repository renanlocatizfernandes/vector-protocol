#!/usr/bin/env python3
import argparse
import json
import math
import sys
import time

from pathlib import Path

# Garantir que o diretório raiz do backend esteja no PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Importa o client já configurado (testnet/prod) pelas settings
from utils.binance_client import binance_client
client = binance_client.client


def load_exchange_info_map():
    info = client.futures_exchange_info()
    return {s["symbol"]: s for s in info.get("symbols", [])}


def get_filters(symbol: str, info_map: dict):
    s = info_map.get(symbol)
    if not s:
        raise ValueError(f"Symbol {symbol} not found in exchange_info")

    lot = next((f for f in s.get("filters", []) if f.get("filterType") in ("LOT_SIZE", "MARKET_LOT_SIZE")), {})
    pricef = next((f for f in s.get("filters", []) if f.get("filterType") == "PRICE_FILTER"), {})

    min_qty = float(lot.get("minQty") or 0.0)
    step_size = float(lot.get("stepSize") or 0.001)
    tick_size = float(pricef.get("tickSize") or 0.0001)
    return min_qty, step_size, tick_size


def round_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.floor(x / step) * step


def place_market_order(symbol: str, direction: str, notional: float, leverage: int, info_map: dict) -> dict:
    price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
    min_qty, step, tick = get_filters(symbol, info_map)

    # Ajusta leverage (ignora erro)
    try:
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
    except Exception:
        pass

    # Quantidade alvo por valor nocional
    qty = max(min_qty, notional / price)
    qty = round_step(qty, step)
    if qty <= 0:
        qty = min_qty if min_qty > 0 else (step if step > 0 else 0.001)

    side = "BUY" if direction.upper() in ("LONG", "BUY") else "SELL"

    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        type="MARKET",
        quantity=qty
    )

    avg_price = 0.0
    try:
        avg_price = float(order.get("avgPrice") or 0.0)
    except Exception:
        avg_price = 0.0

    return {
        "symbol": symbol,
        "direction": direction.upper(),
        "qty": float(f"{qty:.8f}"),
        "orderId": order.get("orderId"),
        "avgPrice": avg_price
    }


def parse_symbols(arg: str):
    out = []
    for chunk in (arg or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            sym, side = chunk.split(":", 1)
            out.append((sym.strip().upper(), side.strip().upper()))
        else:
            out.append((chunk.strip().upper(), "LONG"))
    return out


def main():
    parser = argparse.ArgumentParser(description="Place simple MARKET orders on Binance Futures (Testnet/Prod via settings).")
    parser.add_argument("--symbols", default="DOGEUSDT:LONG,XRPUSDT:LONG,ETHUSDT:SHORT",
                        help="Lista separada por vírgula no formato SYMBOL:SIDE (ex: BTCUSDT:LONG,ETHUSDT:SHORT)")
    parser.add_argument("--notional", type=float, default=10.0, help="Valor nocional alvo em USDT por ordem (ex.: 10)")
    parser.add_argument("--leverage", type=int, default=6, help="Alavancagem alvo (default: 6)")
    parser.add_argument("--delay", type=float, default=0.3, help="Atraso entre ordens em segundos (default: 0.3s)")

    args = parser.parse_args()

    pairs = parse_symbols(args.symbols)
    info_map = load_exchange_info_map()

    placed = []
    for sym, side in pairs:
        try:
            if sym not in info_map:
                placed.append({"symbol": sym, "direction": side, "error": "symbol not found in exchange_info"})
                continue

            result = place_market_order(sym, side, args.notional, args.leverage, info_map)
            placed.append(result)
            time.sleep(args.delay)
        except Exception as e:
            placed.append({"symbol": sym, "direction": side, "error": str(e)})

    print(json.dumps({"placed": placed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
