#!/usr/bin/env python3
"""Force open HYPERUSDT position for testing profit optimization features"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from modules.order_executor import order_executor
from utils.binance_client import binance_client
from config.settings import get_settings
from api.models.trades import Trade
from api.database import SessionLocal

async def main():
    try:
        settings = get_settings()
        print("=" * 60)
        print("OPENING STRATEGIC POSITION FOR FEATURE TESTING")
        print("=" * 60)

        # Get ticker data
        print("\n1. Getting HYPERUSDT price...")
        ticker = await binance_client.get_symbol_price('HYPERUSDT')
        if not ticker:
            print("❌ Could not get ticker data")
            return

        current_price = float(ticker)
        print(f"   Current Price: ${current_price:.4f}")

        # Get balance
        print("\n2. Getting account balance...")
        balance_info = await binance_client.get_account_balance()
        account_balance = balance_info.get('available_balance', 40)
        print(f"   Available Balance: ${account_balance:.2f} USDT")

        # Get current open positions count
        print("\n2.5. Checking current open positions...")
        db = SessionLocal()
        open_positions_count = db.query(Trade).filter(Trade.status == 'open').count()
        print(f"   Current Open Positions: {open_positions_count}")
        db.close()

        # Create strategic signal
        print("\n3. Creating strategic signal...")
        signal = {
            'symbol': 'HYPERUSDT',
            'direction': 'LONG',
            'score': 75,
            'entry_price': current_price,
            'take_profit_1': current_price * 1.04,
            'take_profit_2': current_price * 1.08,
            'take_profit_3': current_price * 1.12,
            'stop_loss': current_price * 0.96,
            'rsi': 68,
            'atr': current_price * 0.02,
            'volume_ratio': 1.8,
            'timeframe': '4h',
            'leverage': 5
        }
        print(f"   Entry Price: ${signal['entry_price']:.4f}")
        print(f"   TP1: ${signal['take_profit_1']:.4f}")
        print(f"   TP2: ${signal['take_profit_2']:.4f}")
        print(f"   TP3: ${signal['take_profit_3']:.4f}")
        print(f"   SL: ${signal['stop_loss']:.4f}")

        # Execute signal
        print("\n4. Executing trade...")
        result = await order_executor.execute_signal(
            signal=signal,
            account_balance=float(account_balance),
            open_positions=open_positions_count,
            dry_run=False
        )

        if result and result.get('success'):
            print("\n" + "=" * 60)
            print("✅ POSITION OPENED SUCCESSFULLY!")
            print("=" * 60)
            print(f"Order ID: {result.get('order_id', 'N/A')}")
            print(f"Entry: ${result.get('entry_price', 'N/A')}")
            print(f"TP1: ${result.get('take_profit_1', 'N/A')}")
            print(f"TP2: ${result.get('take_profit_2', 'N/A')}")
            print(f"TP3: ${result.get('take_profit_3', 'N/A')}")
            print(f"SL: ${result.get('stop_loss', 'N/A')}")
            print("\nFEATURES TO MONITOR:")
            print("  - Dynamic TP Strategy (FIBONACCI vs CONSERVATIVE)")
            print("  - Market Intelligence Scoring")
            print("  - Order Book Depth Validation")
            print("  - Breakeven Stop (at +2% profit)")
            print("  - Funding Exit (before 8h funding)")
            print("  - Net P&L Tracking (all fees)")
            print("=" * 60)
        else:
            print(f"\n❌ Trade execution failed: {result}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
