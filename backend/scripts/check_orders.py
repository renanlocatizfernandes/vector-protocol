import asyncio
import sys
import os

# Adicionar o diretório atual ao path para importar módulos
# Adicionar o diretório raiz e backend ao path para importar módulos
import pathlib
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "backend"))

from backend.utils.binance_client import binance_client

async def check_orders():
    symbols = ["HOTUSDT", "XTZUSDT"] # Add other symbols if needed or fetch from active positions
    print(f"Checking orders for: {symbols}")
    
    total_all = 0
    for symbol in symbols:
        try:
            orders = await binance_client._retry_call(binance_client.client.futures_get_open_orders, symbol=symbol)
            count = len(orders)
            total_all += count
            print(f"\n--- {symbol} ---")
            print(f"Total Open Orders: {count}")
            
            # Group by type
            by_type = {}
            for o in orders:
                t = o['type']
                by_type[t] = by_type.get(t, 0) + 1
            print(f"By Type: {by_type}")

            # Show some details (first 5)
            for o in orders[:5]:
                print(f"  [{o['orderId']}] {o['side']} {o['type']} - Price: {o['price']} - Qty: {o['origQty']} - ReduceOnly: {o['reduceOnly']}")
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
    
    print(f"\nTotal Orders across checked symbols: {total_all}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_orders())
