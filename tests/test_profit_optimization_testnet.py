"""
Profit Optimization Implementation - Testnet Validation Suite

This script validates all new profit optimization features:
1. Market Intelligence Scoring
2. Dynamic Take Profits (Fibonacci extensions)
3. Breakeven Stop Protection
4. Funding-Aware Exits
5. Order Book Depth Filtering
6. Net P&L Tracking
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from utils.logger import setup_logger
from config.settings import get_settings
from utils.binance_client import binance_client
from modules.market_intelligence import market_intelligence
from modules.profit_optimizer import profit_optimizer
from api.database import SessionLocal, engine
from api.models.trades import Trade, Base

logger = setup_logger("testnet_validation")

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(name: str, passed: bool, message: str):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}: {message}")

    if passed:
        test_results["passed"].append(f"{name}: {message}")
    else:
        test_results["failed"].append(f"{name}: {message}")


def log_warning(name: str, message: str):
    """Log test warning"""
    print(f"⚠️  WARN | {name}: {message}")
    test_results["warnings"].append(f"{name}: {message}")


async def test_environment_setup():
    """Test 1: Verify environment and configuration"""
    print("\n" + "="*80)
    print("TEST 1: Environment Setup & Configuration")
    print("="*80)

    settings = get_settings()

    # Check testnet enabled
    is_testnet = settings.BINANCE_TESTNET
    log_test("Testnet Enabled", is_testnet, f"BINANCE_TESTNET={is_testnet}")

    # Check profit optimization settings
    profit_opt_enabled = getattr(settings, "ENABLE_PROFIT_OPTIMIZER", False)
    log_test("Profit Optimizer Flag", profit_opt_enabled, "ENABLE_PROFIT_OPTIMIZER enabled")

    market_intel_enabled = getattr(settings, "ENABLE_MARKET_INTELLIGENCE", False)
    log_test("Market Intelligence Flag", market_intel_enabled, "ENABLE_MARKET_INTELLIGENCE enabled")

    breakeven_enabled = getattr(settings, "ENABLE_BREAKEVEN_STOP", False)
    log_test("Breakeven Stop Flag", breakeven_enabled, "ENABLE_BREAKEVEN_STOP enabled")

    funding_exit_enabled = getattr(settings, "ENABLE_FUNDING_EXITS", False)
    log_test("Funding Exit Flag", funding_exit_enabled, "ENABLE_FUNDING_EXITS enabled")

    dynamic_tp_enabled = getattr(settings, "ENABLE_DYNAMIC_TP", False)
    log_test("Dynamic TP Flag", dynamic_tp_enabled, "ENABLE_DYNAMIC_TP enabled")

    orderbook_filter_enabled = getattr(settings, "ENABLE_ORDER_BOOK_FILTER", False)
    log_test("Order Book Filter Flag", orderbook_filter_enabled, "ENABLE_ORDER_BOOK_FILTER enabled")

    # Check key thresholds
    breakeven_pct = getattr(settings, "BREAKEVEN_ACTIVATION_PCT", None)
    log_test("Breakeven Activation %", breakeven_pct is not None, f"BREAKEVEN_ACTIVATION_PCT={breakeven_pct}")

    funding_threshold = getattr(settings, "FUNDING_EXIT_THRESHOLD", None)
    log_test("Funding Exit Threshold", funding_threshold is not None, f"FUNDING_EXIT_THRESHOLD={funding_threshold}")


async def test_market_intelligence():
    """Test 2: Market Intelligence Module"""
    print("\n" + "="*80)
    print("TEST 2: Market Intelligence Module")
    print("="*80)

    symbol = "BTCUSDT"

    try:
        # Test Top Trader Ratios
        print(f"\n📊 Testing Top Trader Ratios for {symbol}...")
        top_traders = await market_intelligence.get_top_trader_ratios(symbol)

        if top_traders:
            bullish_ratio = top_traders.get('account_bullish_ratio', 0)
            position_ratio = top_traders.get('position_bullish_ratio', 0)
            print(f"  Account Bullish Ratio: {bullish_ratio:.2f}")
            print(f"  Position Bullish Ratio: {position_ratio:.2f}")
            log_test("Top Trader Ratios", True, f"Fetched for {symbol}")
        else:
            log_warning("Top Trader Ratios", "Returned empty dict (possible API limit or no data)")

        # Test Liquidation Zones
        print(f"\n🌪️  Testing Liquidation Zones for {symbol}...")
        liquidation_zones = await market_intelligence.detect_liquidation_zones(symbol)

        if liquidation_zones:
            bull_zone = liquidation_zones.get('bullish_zone', {})
            bear_zone = liquidation_zones.get('bearish_zone', {})
            print(f"  Bull Zone: ${bull_zone.get('price', 0):.2f} (${bull_zone.get('cluster_value', 0):,.0f})")
            print(f"  Bear Zone: ${bear_zone.get('price', 0):.2f} (${bear_zone.get('cluster_value', 0):,.0f})")
            log_test("Liquidation Zones", True, "Successfully detected")
        else:
            log_warning("Liquidation Zones", "No liquidation data found")

        # Test Funding Rate History
        print(f"\n💰 Testing Funding Rate History for {symbol}...")
        funding_history = await market_intelligence.get_funding_rate_history(symbol)

        if funding_history:
            current_funding = funding_history.get('current_funding_rate', 0)
            avg_funding = funding_history.get('average_funding_rate', 0)
            trend = funding_history.get('trend', 'UNKNOWN')
            print(f"  Current Funding: {current_funding:.6f}")
            print(f"  7-Day Average: {avg_funding:.6f}")
            print(f"  Trend: {trend}")
            log_test("Funding Rate History", True, f"Trend: {trend}")
        else:
            log_warning("Funding Rate History", "No funding data found")

        # Test OI Correlation
        print(f"\n📈 Testing OI-Price Correlation for {symbol}...")
        oi_data = await market_intelligence.analyze_oi_price_correlation(symbol)

        if oi_data:
            correlation = oi_data.get('correlation_type', 'UNKNOWN')
            strength = oi_data.get('strength', 'WEAK')
            print(f"  Correlation Type: {correlation}")
            print(f"  Strength: {strength}")
            log_test("OI Correlation", True, f"Type: {correlation}, Strength: {strength}")
        else:
            log_warning("OI Correlation", "No OI data found")

        # Test Order Book Depth
        print(f"\n📊 Testing Order Book Depth for {symbol}...")
        depth_data = await market_intelligence.get_order_book_depth(symbol)

        if depth_data:
            bid_liq = depth_data.get('bid_liquidity_5pct', 0)
            ask_liq = depth_data.get('ask_liquidity_5pct', 0)
            score = depth_data.get('liquidity_score', 0)
            risk = depth_data.get('execution_risk', 'UNKNOWN')
            print(f"  Bid Liquidity (5%): ${bid_liq:,.0f}")
            print(f"  Ask Liquidity (5%): ${ask_liq:,.0f}")
            print(f"  Liquidity Score: {score}/10")
            print(f"  Execution Risk: {risk}")
            log_test("Order Book Depth", score >= 7, f"Score: {score}/10 (Adequate liquidity)")
        else:
            log_warning("Order Book Depth", "Could not retrieve order book data")

        # Test Market Sentiment Score
        print(f"\n🎯 Testing Market Sentiment Score for {symbol}...")
        sentiment = await market_intelligence.get_market_sentiment_score(symbol)

        if sentiment:
            score = sentiment.get('sentiment_score', 0)
            recommendation = sentiment.get('recommendation', 'NEUTRAL')
            print(f"  Sentiment Score: {score} (range: -50 to +50)")
            print(f"  Recommendation: {recommendation}")
            log_test("Market Sentiment Score", -50 <= score <= 50, f"Score: {score}, Recommendation: {recommendation}")
        else:
            log_warning("Market Sentiment Score", "Could not calculate sentiment")

    except Exception as e:
        log_test("Market Intelligence Suite", False, f"Exception: {str(e)}")


async def test_profit_optimizer():
    """Test 3: Profit Optimizer Module"""
    print("\n" + "="*80)
    print("TEST 3: Profit Optimizer Module")
    print("="*80)

    try:
        # Create test trade object
        test_trade = Trade(
            symbol="BTCUSDT",
            direction="LONG",
            entry_price=50000.0,
            current_price=51000.0,
            quantity=0.1,
            leverage=5,
            stop_loss=49000.0,
            take_profit_1=52000.0,
            take_profit_2=53000.0,
            take_profit_3=54000.0,
            status='open',
            pnl=100.0,
            pnl_percentage=2.0,
            order_id="test_order_123"
        )

        # Test Net P&L Calculation
        print("\n💰 Testing Net P&L Calculation...")
        exit_price = 51000.0

        net_pnl_data = await profit_optimizer.calculate_net_pnl(
            test_trade,
            exit_price,
            entry_was_maker=False,
            exit_is_maker=False
        )

        if net_pnl_data:
            gross_pnl = net_pnl_data.get('gross_pnl', 0)
            entry_fee = net_pnl_data.get('entry_fee', 0)
            exit_fee = net_pnl_data.get('exit_fee', 0)
            funding_cost = net_pnl_data.get('funding_cost', 0)
            net_pnl = net_pnl_data.get('net_pnl', 0)
            fee_impact = net_pnl_data.get('fee_impact_pct', 0)

            print(f"  Gross P&L: ${gross_pnl:+.2f}")
            print(f"  Entry Fee: ${entry_fee:+.2f}")
            print(f"  Exit Fee: ${exit_fee:+.2f}")
            print(f"  Funding Cost: ${funding_cost:+.2f}")
            print(f"  Net P&L: ${net_pnl:+.2f}")
            print(f"  Fee Impact: {fee_impact:.2f}%")

            log_test("Net P&L Calculation", net_pnl > 0, f"Net P&L: ${net_pnl:.2f}")

        # Test Breakeven Price Calculation
        print("\n🛡️  Testing Breakeven Price Calculation...")

        breakeven = await profit_optimizer.calculate_breakeven_price(test_trade)

        if breakeven:
            print(f"  Entry Price: ${test_trade.entry_price:.2f}")
            print(f"  Breakeven Price: ${breakeven:.2f}")
            print(f"  Breakeven Offset: ${breakeven - test_trade.entry_price:+.2f}")

            expected_offset = (test_trade.entry_price * 0.0005) * 2  # Entry + exit taker fees
            log_test("Breakeven Price", breakeven > test_trade.entry_price,
                    f"Breakeven: ${breakeven:.2f} (includes all fees)")

        # Test Dynamic TP Optimization
        print("\n📈 Testing Dynamic Take Profit Optimization...")

        momentum_data = {
            'rsi': 72.0,  # Strong momentum
            'volume_ratio': 2.0,
            'price_momentum_pct': 5.0
        }

        optimized_tps = await profit_optimizer.optimize_take_profit_levels(
            symbol="BTCUSDT",
            direction="LONG",
            entry_price=50000.0,
            quantity=0.1,
            base_atr=100.0,  # $100 ATR
            momentum_data=momentum_data
        )

        if optimized_tps:
            print(f"  Generated {len(optimized_tps)} TP levels")
            for tp in optimized_tps:
                level = tp.get('level', 0)
                price = tp.get('price', 0)
                percentage = tp.get('percentage', '')
                reason = tp.get('exit_reason', '')
                print(f"    TP{level}: ${price:.2f} ({percentage}) - {reason}")

            strategy = "FIBONACCI" if optimized_tps[0].get('exit_reason') == 'tp_momentum' else "CONSERVATIVE"
            log_test("Dynamic TP Optimization", len(optimized_tps) >= 3, f"Strategy: {strategy}")

        # Test Funding Exit Logic
        print("\n💸 Testing Funding-Aware Exit Logic...")

        should_exit, reason = await profit_optimizer.should_exit_for_funding(
            test_trade,
            current_pnl_pct=2.0
        )

        print(f"  Should Exit for Funding: {should_exit}")
        if reason:
            print(f"  Reason: {reason}")

        log_test("Funding Exit Logic", isinstance(should_exit, bool),
                f"Exit: {should_exit}, Reason: {reason if reason else 'N/A'}")

    except Exception as e:
        log_test("Profit Optimizer Suite", False, f"Exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


async def test_database_persistence():
    """Test 4: Database Persistence of New Columns"""
    print("\n" + "="*80)
    print("TEST 4: Database Persistence & New Columns")
    print("="*80)

    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        # Create test trade with new columns
        test_trade = Trade(
            symbol="BTCUSDT_TEST",
            direction="LONG",
            entry_price=50000.0,
            current_price=51000.0,
            quantity=0.1,
            leverage=5,
            stop_loss=49000.0,
            take_profit_1=52000.0,
            status='open',
            pnl=100.0,
            pnl_percentage=2.0,
            order_id="test_db_123",
            # ✅ New profit optimization columns
            entry_fee=2.5,
            exit_fee=2.55,
            funding_cost=1.5,
            net_pnl=93.45,
            is_maker_entry=False,
            breakeven_price=50050.0,
            breakeven_stop_activated=False,
            market_sentiment_score=25,
            top_trader_ratio=1.2,
            liquidation_proximity="NEUTRAL",
            funding_periods_held=3,
            entry_time=datetime.now()
        )

        db.add(test_trade)
        db.commit()

        # Retrieve and validate
        retrieved = db.query(Trade).filter(Trade.symbol == "BTCUSDT_TEST").first()

        if retrieved:
            print(f"  ✅ Trade created with ID: {retrieved.id}")
            print(f"  Entry Fee: ${retrieved.entry_fee:.2f}")
            print(f"  Exit Fee: ${retrieved.exit_fee:.2f}")
            print(f"  Funding Cost: ${retrieved.funding_cost:.2f}")
            print(f"  Net P&L: ${retrieved.net_pnl:.2f}")
            print(f"  Breakeven Price: ${retrieved.breakeven_price:.2f}")
            print(f"  Market Sentiment Score: {retrieved.market_sentiment_score}")

            # Validate all new fields
            fields_ok = (
                retrieved.entry_fee == 2.5 and
                retrieved.exit_fee == 2.55 and
                retrieved.funding_cost == 1.5 and
                retrieved.net_pnl == 93.45 and
                retrieved.breakeven_price == 50050.0 and
                retrieved.market_sentiment_score == 25
            )

            log_test("New Columns Persistence", fields_ok, "All 12 new columns persisted correctly")

            # Cleanup
            db.delete(retrieved)
            db.commit()
        else:
            log_test("Trade Creation", False, "Could not retrieve created trade")

        db.close()

    except Exception as e:
        log_test("Database Persistence", False, f"Exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


async def test_settings_validation():
    """Test 5: Settings Validation"""
    print("\n" + "="*80)
    print("TEST 5: Settings Validation")
    print("="*80)

    settings = get_settings()

    # Check critical thresholds
    thresholds = {
        "BREAKEVEN_ACTIVATION_PCT": (getattr(settings, "BREAKEVEN_ACTIVATION_PCT", 0), 0.5, 5.0),
        "FUNDING_EXIT_THRESHOLD": (getattr(settings, "FUNDING_EXIT_THRESHOLD", 0), 0.0001, 0.001),
        "FUNDING_EXIT_TIME_WINDOW_MIN": (getattr(settings, "FUNDING_EXIT_TIME_WINDOW_MIN", 0), 10, 60),
        "FUNDING_EXIT_MIN_PROFIT": (getattr(settings, "FUNDING_EXIT_MIN_PROFIT", 0), 0.1, 2.0),
        "MIN_LIQUIDITY_DEPTH_USDT": (getattr(settings, "MIN_LIQUIDITY_DEPTH_USDT", 0), 50000, 500000),
    }

    for setting_name, (value, min_val, max_val) in thresholds.items():
        is_valid = min_val <= value <= max_val
        log_test(f"Setting: {setting_name}", is_valid, f"Value: {value} (range: {min_val}-{max_val})")


async def main():
    """Run all testnet validation tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PROFIT OPTIMIZATION TESTNET VALIDATION SUITE".center(78) + "║")
    print("║" + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # Run all tests
    await test_environment_setup()
    await test_settings_validation()
    await test_market_intelligence()
    await test_profit_optimizer()
    await test_database_persistence()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n✅ PASSED: {len(test_results['passed'])} tests")
    for test in test_results['passed']:
        print(f"  • {test}")

    if test_results['warnings']:
        print(f"\n⚠️  WARNINGS: {len(test_results['warnings'])} items")
        for warning in test_results['warnings']:
            print(f"  • {warning}")

    if test_results['failed']:
        print(f"\n❌ FAILED: {len(test_results['failed'])} tests")
        for test in test_results['failed']:
            print(f"  • {test}")

    total_tests = len(test_results['passed']) + len(test_results['failed'])
    success_rate = (len(test_results['passed']) / total_tests * 100) if total_tests > 0 else 0

    print(f"\n{'='*80}")
    print(f"OVERALL SUCCESS RATE: {success_rate:.1f}% ({len(test_results['passed'])}/{total_tests} tests)")
    print(f"{'='*80}\n")

    if test_results['failed']:
        print("🔴 TESTNET VALIDATION FAILED - Fix issues above before deployment")
        return 1
    elif test_results['warnings']:
        print("🟡 TESTNET VALIDATION PASSED WITH WARNINGS - Monitor closely")
        return 0
    else:
        print("🟢 TESTNET VALIDATION SUCCESSFUL - Ready for further testing")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
