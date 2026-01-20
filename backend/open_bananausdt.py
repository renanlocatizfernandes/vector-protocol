#!/usr/bin/env python3
"""Open BANANAUSDT position (3rd position for comprehensive feature validation)"""
import asyncio
import sys
import os

# Add backend directory to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from modules.order_executor import order_executor
from utils.binance_client import binance_client
from config.settings import get_settings
from api.models.trades import Trade
from api.database import SessionLocal

# Configuration for BANANAUSDT
PAIR_CONFIG = {
    'symbol': 'BANANAUSDT',
    'direction': 'LONG',
    'rsi': 70,
    'volume_ratio': 1.9,
    'tp_multiplier': [1.05, 1.10, 1.15],  # 5%, 10%, 15%
    'sl_multiplier': 0.95,  # 5% below
}

async def open_position():
    """Open BANANAUSDT position with all features"""
    symbol = PAIR_CONFIG['symbol']

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
        tp_mults = PAIR_CONFIG['tp_multiplier']
        signal = {
            'symbol': symbol,
            'direction': PAIR_CONFIG['direction'],
            'score': 75,  # HIGH CONVICTION
            'entry_price': current_price,
            'take_profit_1': current_price * tp_mults[0],
            'take_profit_2': current_price * tp_mults[1],
            'take_profit_3': current_price * tp_mults[2],
            'stop_loss': current_price * PAIR_CONFIG['sl_multiplier'],
            'rsi': PAIR_CONFIG['rsi'],
            'atr': current_price * 0.02,
            'volume_ratio': PAIR_CONFIG['volume_ratio'],
            'timeframe': '4h',
            'leverage': 10  # 10x leverage (reduce margin requirement)
        }

        print(f"   Entry Price: ${signal['entry_price']:.6f}")
        print(f"   TP1: ${signal['take_profit_1']:.6f}")
        print(f"   TP2: ${signal['take_profit_2']:.6f}")
        print(f"   TP3: ${signal['take_profit_3']:.6f}")
        print(f"   SL: ${signal['stop_loss']:.6f}")
        print(f"   Momentum: RSI={PAIR_CONFIG['rsi']}, Vol={PAIR_CONFIG['volume_ratio']}x")
        print(f"   Leverage: 10x (from ${account_balance:.2f} real balance)")

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
    """Open BANANAUSDT position"""
    print("\n" + "="*70)
    print("🚀 OPENING 3RD POSITION - BANANAUSDT")
    print("   Leverage: 10x | Real Balance: ENABLED")
    print("="*70)

    result = await open_position()

    # Print summary
    print("\n\n" + "="*70)
    print("📊 EXECUTION SUMMARY")
    print("="*70)

    if result and result['success']:
        print("\n✅ BANANAUSDT Position Opened")
        print(f"   Order ID: {result['order_id']}")
        print(f"   Entry: ${result['entry_price']:.6f}")

        print(f"\n{'='*70}")
        print("📋 3 POSITIONS NOW ACTIVE FOR VALIDATION:")
        print(f"{'='*70}")
        print("\n🎯 FEATURES TO VALIDATE:")
        print("  ✨ Dynamic TP Strategy (CONSERVATIVE/FIBONACCI)")
        print("  🛡️  Breakeven Stop Protection (at +2% profit)")
        print("  💰 Net P&L Tracking with Fee Breakdown")
        print("  📊 Order Book Depth Validation")
        print("  🎯 Stop Loss & Take Profit Orders (Binance)")
        print("  📈 Position Monitoring in Real-time")
        print("\n⏳ Monitor all 3 positions until they reach +2% or close on TP")
        print(f"{'='*70}\n")
        return True
    else:
        print("\n❌ BANANAUSDT Position Failed")
        if result:
            print(f"   Reason: {result['reason']}")
        print(f"{'='*70}\n")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
