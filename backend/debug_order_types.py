
import asyncio
import os
from binance.client import AsyncClient

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
TESTNET = os.getenv("BINANCE_TESTNET", "False").lower() == "true"

async def check_order_types():
    client = await AsyncClient.create(API_KEY, API_SECRET, testnet=TESTNET)
    try:
        info = await client.futures_exchange_info()
        symbol = "1000000BOBUSDT" # The one in logs
        
        target = next((s for s in info['symbols'] if s['symbol'] == symbol), None)
        if target:
            print(f"Symbol: {symbol}")
            print(f"Order Types: {target['orderTypes']}")
            
            # Tentar criar ordem de teste STOP_MARKET
            try:
                price = await client.futures_symbol_ticker(symbol=symbol)
                curr_price = float(price['price'])
                stop_price_test = round(curr_price * 0.9, 4) # 10% abaixo
                
                print(f"Testing STOP_MARKET for {symbol} at {stop_price_test}...")
                
                # Teste 1: Full params (como no bot)
                # Nota: test=True não existe no create_order do python-binance, mas existe endpoint create_test_order?
                # O metodo é futures_create_order(..., newOrderRespType='RESULT') não tem flag test explicita facil.
                # Mas python-binance tem futures_create_test_order? SIM.
                
                await client.futures_create_test_order(
                    symbol=symbol,
                    side='SELL',
                    type='STOP_MARKET',
                    stopPrice=stop_price_test,
                    quantity=100, # Valor arbitrario, validade depois
                    reduceOnly=True,
                    workingType='MARK_PRICE'
                )
                print("✅ Test Order 1 (Full Params): SUCCESS")
                
            except Exception as e:
                print(f"❌ Test Order 1 Failed: {e}")
                
                # Teste 2: Sem workingType
                try:
                    print("Testing without workingType...")
                    await client.futures_create_test_order(
                        symbol=symbol,
                        side='SELL',
                        type='STOP_MARKET',
                        stopPrice=stop_price_test,
                        quantity=100,
                        reduceOnly=True
                    )
                    print("✅ Test Order 2 (No WorkingType): SUCCESS")
                except Exception as e2:
                    print(f"❌ Test Order 2 Failed: {e2}")

            # Teste 3: STOP (Limit)
            try:
                print("Testing STOP (Limit)...")
                limit_price = round(stop_price_test * 0.99, 4)
                await client.futures_create_test_order(
                    symbol=symbol,
                    side='SELL',
                    type='STOP',
                    stopPrice=stop_price_test,
                    price=limit_price,
                    quantity=100,
                    reduceOnly=True,
                    workingType='MARK_PRICE'
                )
                print("✅ Test Order 3 (STOP Limit): SUCCESS")
            except Exception as e3:
                print(f"❌ Test Order 3 Failed: {e3}")


        else:
            print(f"Symbol {symbol} not found in exchange info.")

            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(check_order_types())
