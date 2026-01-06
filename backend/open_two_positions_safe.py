#!/usr/bin/env python3
"""Open 2 positions safely with real balance and 10x leverage"""
import asyncio
import sys
sys.path.insert(0, '/app')

from modules.order_executor import order_executor
from utils.binance_client import binance_client
from config.settings import get_settings
from api.models.trades import Trade
from api.database import SessionLocal

# Configuration for 2 pairs with 10x leverage
PAIRS_CONFIG = [
    {
        'symbol': 'HYPERUSDT',
        'direction': 'LONG',
        'rsi': 68,
        'volume_ratio': 1.8,
        'tp_multiplier': [1.04, 1.08, 1.12],  # 4%, 8%, 12%
        'sl_multiplier': 0.96,  # 4% below
    },
    {
        'symbol': 'TURBOUSDT',
        'direction': 'LONG',
        'rsi': 65,
        'volume_ratio': 1.6,
        'tp_multiplier': [1.03, 1.07, 1.11],  # 3%, 7%, 11%
        'sl_multiplier': 0.97,  # 3% below
    },
]

async def open_position(config):
    """Open a single position with all features"""
    symbol = config['symbol']

    try:
        settings = get_settings()
        print(f"\n{'='*70}")
        print(f"OPENING: {symbol}")
        print(f"{'='*70}")

        # Get price
        print(f"\n1️⃣  Getting {symbol} price...")
        price = await binance_client.get_symbol_price(symbol)
        if not price:
            print(f"❌ Could not get {symbol} price")
            return None

        current_price = float(price)
        print(f"   Current Price: ${current_price:.6f}")

        # Get balance
        balance_info = await binance_client.get_account_balance()
        account_balance = balance_info.get('available_balance', 51)
        print(f"   Available Balance: ${account_balance:.2f} USDT (REAL BALANCE)")

        # Get open positions count
        db = SessionLocal()
        open_positions_count = db.query(Trade).filter(Trade.status == 'open').count()
        print(f"   Current Open Positions: {open_positions_count}")
        db.close()

        # Create signal with strategic parameters
        print(f"\n2️⃣  Creating strategic signal for {symbol}...")
        tp_mults = config['tp_multiplier']
        signal = {
            'symbol': symbol,
            'direction': config['direction'],
            'score': 75,  # HIGH CONVICTION
            'entry_price': current_price,
            'take_profit_1': current_price * tp_mults[0],
            'take_profit_2': current_price * tp_mults[1],
            'take_profit_3': current_price * tp_mults[2],
            'stop_loss': current_price * config['sl_multiplier'],
            'rsi': config['rsi'],
            'atr': current_price * 0.02,
            'volume_ratio': config['volume_ratio'],
            'timeframe': '4h',
            'leverage': 10  # 10x leverage (reduce margin requirement)
        }

        print(f"   Entry Price: ${signal['entry_price']:.6f}")
        print(f"   TP1: ${signal['take_profit_1']:.6f}")
        print(f"   TP2: ${signal['take_profit_2']:.6f}")
        print(f"   TP3: ${signal['take_profit_3']:.6f}")
        print(f"   SL: ${signal['stop_loss']:.6f}")
        print(f"   Momentum: RSI={config['rsi']}, Vol={config['volume_ratio']}x")
        print(f"   Leverage: 10x (from $51 real balance)")

        # Execute signal
        print(f"\n3️⃣  Executing trade for {symbol}...")
        result = await order_executor.execute_signal(
            signal=signal,
            account_balance=float(account_balance),
            open_positions=open_positions_count,
            dry_run=False
        )

        if result and result.get('success'):
            print(f"\n✅ {symbol} POSITION OPENED SUCCESSFULLY!")
            print(f"   Order ID: {result.get('order_id', 'N/A')}")
            print(f"   Entry: ${result.get('entry_price', 'N/A')}")
            print(f"   Quantity: {result.get('quantity', 'N/A')}")
            return {
                'success': True,
                'symbol': symbol,
                'order_id': result.get('order_id'),
                'entry_price': result.get('entry_price')
            }
        else:
            print(f"\n❌ {symbol} Trade execution failed: {result}")
            return {
                'success': False,
                'symbol': symbol,
                'reason': result.get('reason') if result else 'Unknown error'
            }

    except Exception as e:
        print(f"❌ Error with {symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'symbol': symbol,
            'reason': str(e)
        }

async def main():
    """Open 2 positions"""
    print("\n" + "="*70)
    print("🚀 OPENING 2 POSITIONS WITH REAL BALANCE ($51)")
    print("   Leverage: 10x | Virtual Balance: DISABLED")
    print("="*70)

    # Open positions sequentially to avoid position count issues
    results = []
    for config in PAIRS_CONFIG:
        result = await open_position(config)
        results.append(result)
        await asyncio.sleep(2)  # Wait between orders

    # Print summary
    print("\n\n" + "="*70)
    print("📊 EXECUTION SUMMARY")
    print("="*70)

    successful = [r for r in results if r and r['success']]
    failed = [r for r in results if r and not r['success']]

    print(f"\n✅ Successful: {len(successful)}/2")
    for r in successful:
        print(f"   - {r['symbol']}: Order {r['order_id']} @ ${r['entry_price']:.6f}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}/2")
        for r in failed:
            print(f"   - {r['symbol']}: {r['reason']}")

    print(f"\n{'='*70}")
    print("📋 POSITIONS READY FOR VALIDATION:")
    print(f"{'='*70}")

    if successful:
        print("\n🎯 FEATURES TO VALIDATE:")
        print("  ✨ Dynamic TP Strategy (CONSERVATIVE/FIBONACCI)")
        print("  🛡️  Breakeven Stop Protection (at +2% profit)")
        print("  💰 Net P&L Tracking with Fee Breakdown")
        print("  📊 Order Book Depth Validation")
        print("  🎯 Stop Loss & Take Profit Orders (Binance)")
        print("  📈 Position Monitoring in Real-time")
        print(f"\n⏳ Monitor until positions reach +2% or close on TP")
        print(f"{'='*70}\n")

    return len(successful) == 2

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
