import asyncio
import os
import sys

# Adicionar o diretório raiz e backend ao path para importar módulos
import pathlib
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "backend"))

try:
    from backend.utils.binance_client import binance_client
    from backend.api.database import SessionLocal
    from backend.api.models.trades import Trade
    from backend.utils.helpers import round_step_size
except ImportError:
    from utils.binance_client import binance_client
    from api.database import SessionLocal
    from api.models.trades import Trade
    from utils.helpers import round_step_size

async def fix_orders():
    print("Initializing Binance Client...")
    # Force init if needed (though binance_client auto-inits on first call usually)
    # But we need to be in an async loop
    
    db = SessionLocal()
    try:
        positions = db.query(Trade).filter(Trade.status == 'open').all()
        print(f"Found {len(positions)} open positions in DB.")
        
        for trade in positions:
            symbol = trade.symbol
            print(f"\nProcessing {symbol}...")
            
            # 1. Get current position from Binance to be sure of quantity
            try:
                risk_info = await binance_client._retry_call(binance_client.client.futures_position_information, symbol=symbol)
                # risk_info is a list if no symbol passed, but with symbol it might be a list of 1
                if isinstance(risk_info, list):
                    risk_info = risk_info[0]
                
                amt = float(risk_info['positionAmt'])
                if amt == 0:
                    print(f"  No position on Binance for {symbol}. Skipping.")
                    continue
                
                total_qty = abs(amt)
                print(f"  Binance Position: {amt} (Qty: {total_qty})")
                
                # 2. Cancel all open orders
                print("  Cancelling existing orders...")
                await binance_client._retry_call(binance_client.client.futures_cancel_all_open_orders, symbol=symbol)
                
                # 3. Place new Stop Loss
                sl_price = trade.stop_loss
                if not sl_price:
                    print("  No Stop Loss in DB! Skipping SL placement.")
                    continue
                
                # Get symbol info for precision and limits
                info = await binance_client.get_symbol_info(symbol)
                tick_size = info['tick_size']
                step_size = info['step_size']
                
                # Check maxQty
                max_qty = float(info.get('max_quantity', float('inf')))
                
                sl_price = round_step_size(sl_price, tick_size)
                side = 'SELL' if amt > 0 else 'BUY'
                
                remaining_qty = total_qty
                
                while remaining_qty > 0:
                    qty_chunk = min(remaining_qty, max_qty)
                    qty_chunk = round_step_size(qty_chunk, step_size)
                    
                    if qty_chunk <= 0:
                        break
                        
                    print(f"  Placing NEW Stop Loss Chunk: {side} {qty_chunk} @ {sl_price}")
                    
                    await binance_client._retry_call(
                        binance_client.client.futures_create_order,
                        symbol=symbol,
                        side=side,
                        type='STOP_MARKET',
                        stopPrice=sl_price,
                        quantity=qty_chunk,
                        reduceOnly=True,
                        workingType='MARK_PRICE'
                    )
                    remaining_qty -= qty_chunk
                    remaining_qty = max(0, remaining_qty) # avoid float precision issues
                
                print("  ✅ Success.")
                
            except Exception as e:
                print(f"  ❌ Error processing {symbol}: {e}")
                
    finally:
        db.close()
        print("\nDone.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(fix_orders())
