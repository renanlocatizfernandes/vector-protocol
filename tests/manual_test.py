import requests
import json

API_URL = "http://localhost:8000/api/trading/manual"

def test_manual_trade(symbol, direction, amount, amount_type, leverage=10):
    payload = {
        "symbol": symbol,
        "direction": direction,
        "amount": amount,
        "amount_type": amount_type,
        "leverage": leverage
    }
    print(f"Testing {direction} {symbol} with {amount} {amount_type} (x{leverage})...")
    try:
        response = requests.post(API_URL, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 40)

if __name__ == "__main__":
    # Test 1: Quantity (Legacy/Direct)
    # BTC price approx 90k. 0.001 BTC is approx $90.
    # test_manual_trade("BTCUSDT", "LONG", 0.001, "quantity")

    # Test 2: USDT Total (Notional)
    # $100 position size.
    # test_manual_trade("ETHUSDT", "SHORT", 100, "usdt_total")

    # Test 3: USDT Margin (Cost)
    # $10 margin * 10x leverage = $100 position size.
    # test_manual_trade("SOLUSDT", "LONG", 10, "usdt_margin", leverage=10)
    
    print("Skipping actual execution to avoid opening real positions during automated test generation.")
    print("Run this script manually if needed, or rely on frontend verification.")
