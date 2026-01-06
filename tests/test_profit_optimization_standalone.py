"""
Profit Optimization - Standalone Testnet Validation

Tests all new features without requiring Redis/PostgreSQL
Focuses on module initialization and configuration validation
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("\n" + "="*80)
print("PROFIT OPTIMIZATION STANDALONE VALIDATION".center(80))
print("="*80 + "\n")

# Test results
tests_passed = 0
tests_failed = 0
tests_warnings = 0

def test_result(name: str, passed: bool, message: str = ""):
    global tests_passed, tests_failed, tests_warnings

    if passed:
        tests_passed += 1
        status = "✅ PASS"
    else:
        tests_failed += 1
        status = "❌ FAIL"

    msg = f"{message}" if message else ""
    print(f"{status:8} | {name:40} | {msg}")


def test_warning(name: str, message: str = ""):
    global tests_warnings
    tests_warnings += 1
    msg = f"{message}" if message else ""
    print(f"{'⚠️  WARN':8} | {name:40} | {msg}")


# ============================================================================
# TEST 1: Module Imports
# ============================================================================
print("\n" + "-"*80)
print("TEST 1: Module Imports & Initialization")
print("-"*80 + "\n")

try:
    from config.settings import get_settings
    settings = get_settings()
    test_result("settings.py", True, "Loaded successfully")
except Exception as e:
    test_result("settings.py", False, f"Error: {str(e)[:40]}")

try:
    from modules.market_intelligence import MarketIntelligence
    mi = MarketIntelligence()
    test_result("market_intelligence.py", True, "Initialized successfully")
except Exception as e:
    test_result("market_intelligence.py", False, f"Error: {str(e)[:40]}")

try:
    from modules.profit_optimizer import ProfitOptimizer
    po = ProfitOptimizer()
    test_result("profit_optimizer.py", True, "Initialized successfully")
except Exception as e:
    test_result("profit_optimizer.py", False, f"Error: {str(e)[:40]}")

try:
    from api.models.trades import Trade, Base
    test_result("trades.py model", True, "Loaded successfully")
except Exception as e:
    test_result("trades.py model", False, f"Error: {str(e)[:40]}")

# ============================================================================
# TEST 2: Configuration Validation
# ============================================================================
print("\n" + "-"*80)
print("TEST 2: Configuration Validation")
print("-"*80 + "\n")

try:
    settings = get_settings()

    # Feature flags
    feature_flags = {
        "ENABLE_PROFIT_OPTIMIZER": getattr(settings, "ENABLE_PROFIT_OPTIMIZER", False),
        "ENABLE_MARKET_INTELLIGENCE": getattr(settings, "ENABLE_MARKET_INTELLIGENCE", False),
        "ENABLE_BREAKEVEN_STOP": getattr(settings, "ENABLE_BREAKEVEN_STOP", False),
        "ENABLE_FUNDING_EXITS": getattr(settings, "ENABLE_FUNDING_EXITS", False),
        "ENABLE_DYNAMIC_TP": getattr(settings, "ENABLE_DYNAMIC_TP", False),
        "ENABLE_ORDER_BOOK_FILTER": getattr(settings, "ENABLE_ORDER_BOOK_FILTER", False),
    }

    for flag, enabled in feature_flags.items():
        test_result(f"Flag: {flag}", enabled, f"Status: {'ENABLED' if enabled else 'DISABLED'}")

    # Thresholds
    thresholds = {
        "BREAKEVEN_ACTIVATION_PCT": (getattr(settings, "BREAKEVEN_ACTIVATION_PCT", 0), 0.5, 10.0),
        "FUNDING_EXIT_THRESHOLD": (getattr(settings, "FUNDING_EXIT_THRESHOLD", 0), 0.0001, 0.01),
        "FUNDING_EXIT_TIME_WINDOW_MIN": (getattr(settings, "FUNDING_EXIT_TIME_WINDOW_MIN", 0), 10, 120),
        "FUNDING_EXIT_MIN_PROFIT": (getattr(settings, "FUNDING_EXIT_MIN_PROFIT", 0), 0.1, 5.0),
        "MIN_LIQUIDITY_DEPTH_USDT": (getattr(settings, "MIN_LIQUIDITY_DEPTH_USDT", 0), 50000, 1000000),
        "ESTIMATE_TAKER_FEE": (getattr(settings, "ESTIMATE_TAKER_FEE", 0), 0.0001, 0.001),
        "ESTIMATE_MAKER_FEE": (getattr(settings, "ESTIMATE_MAKER_FEE", 0), 0.00001, 0.0005),
    }

    for threshold_name, (value, min_val, max_val) in thresholds.items():
        is_valid = min_val <= value <= max_val
        range_str = f"({min_val:.6f}-{max_val:.6f})" if max_val < 1 else f"({min_val:,}-{max_val:,})"
        msg = f"Value: {value} {range_str}"
        test_result(f"Threshold: {threshold_name}", is_valid, msg)

except Exception as e:
    test_result("Configuration Validation", False, f"Error: {str(e)[:40]}")

# ============================================================================
# TEST 3: Trade Model Columns
# ============================================================================
print("\n" + "-"*80)
print("TEST 3: Trade Model - New Columns Validation")
print("-"*80 + "\n")

try:
    from api.models.trades import Trade
    import sqlalchemy
    from sqlalchemy import inspect

    # Check if Trade model has all required columns
    required_columns = {
        # Fee tracking
        'entry_fee': float,
        'exit_fee': float,
        'funding_cost': float,
        'net_pnl': float,
        'is_maker_entry': bool,
        'is_maker_exit': bool,
        # Breakeven protection
        'breakeven_price': float,
        'breakeven_stop_activated': bool,
        # Market intelligence
        'market_sentiment_score': int,
        'top_trader_ratio': float,
        'liquidation_proximity': str,
        # Funding tracking
        'funding_periods_held': int,
        'entry_time': object,  # DateTime
    }

    # Get model columns
    mapper = inspect(Trade)
    model_columns = {c.name: c.type for c in mapper.columns}

    for col_name in required_columns.keys():
        exists = col_name in model_columns
        test_result(f"Column: {col_name}", exists, f"Type: {model_columns.get(col_name, 'MISSING')}")

except Exception as e:
    test_result("Trade Model Inspection", False, f"Error: {str(e)[:40]}")

# ============================================================================
# TEST 4: Market Intelligence Methods
# ============================================================================
print("\n" + "-"*80)
print("TEST 4: Market Intelligence - Method Signatures")
print("-"*80 + "\n")

try:
    from modules.market_intelligence import MarketIntelligence
    import inspect

    mi = MarketIntelligence()

    required_methods = [
        'get_top_trader_ratios',
        'detect_liquidation_zones',
        'get_funding_rate_history',
        'analyze_oi_price_correlation',
        'get_order_book_depth',
        'get_market_sentiment_score',
    ]

    for method_name in required_methods:
        has_method = hasattr(mi, method_name)
        if has_method:
            method = getattr(mi, method_name)
            is_async = inspect.iscoroutinefunction(method)
            test_result(f"Method: {method_name}", is_async, f"Type: {'async' if is_async else 'sync'}")
        else:
            test_result(f"Method: {method_name}", False, "Method not found")

except Exception as e:
    test_result("Market Intelligence Methods", False, f"Error: {str(e)[:40]}")

# ============================================================================
# TEST 5: Profit Optimizer Methods
# ============================================================================
print("\n" + "-"*80)
print("TEST 5: Profit Optimizer - Method Signatures")
print("-"*80 + "\n")

try:
    from modules.profit_optimizer import ProfitOptimizer
    import inspect

    po = ProfitOptimizer()

    required_methods = [
        'calculate_net_pnl',
        'calculate_breakeven_price',
        'optimize_take_profit_levels',
        'should_exit_for_funding',
    ]

    for method_name in required_methods:
        has_method = hasattr(po, method_name)
        if has_method:
            method = getattr(po, method_name)
            is_async = inspect.iscoroutinefunction(method)
            test_result(f"Method: {method_name}", is_async, f"Type: {'async' if is_async else 'sync'}")
        else:
            test_result(f"Method: {method_name}", False, "Method not found")

except Exception as e:
    test_result("Profit Optimizer Methods", False, f"Error: {str(e)[:40]}")

# ============================================================================
# TEST 6: Code Quality - Import Check
# ============================================================================
print("\n" + "-"*80)
print("TEST 6: Code Quality - Integration Points")
print("-"*80 + "\n")

try:
    # Check order_executor imports
    with open("backend/modules/order_executor.py", "r") as f:
        executor_code = f.read()

    has_dynamic_tp = "ENABLE_DYNAMIC_TP" in executor_code and "optimize_take_profit_levels" in executor_code
    test_result("order_executor.py", has_dynamic_tp, "Dynamic TP integration found")

    has_ob_filter = "_validate_order_book_depth" in executor_code
    test_result("order_executor.py", has_ob_filter, "Order book filter integration found")

except Exception as e:
    test_result("order_executor.py", False, f"Error reading file: {str(e)[:40]}")

try:
    # Check position_monitor imports
    with open("backend/modules/position_monitor.py", "r") as f:
        monitor_code = f.read()

    has_breakeven = "_check_breakeven_stop" in monitor_code
    test_result("position_monitor.py", has_breakeven, "Breakeven stop integration found")

    has_funding = "_check_funding_exit" in monitor_code
    test_result("position_monitor.py", has_funding, "Funding exit integration found")

    has_net_pnl = "calculate_net_pnl" in monitor_code
    test_result("position_monitor.py", has_net_pnl, "Net P&L tracking integration found")

except Exception as e:
    test_result("position_monitor.py", False, f"Error reading file: {str(e)[:40]}")

try:
    # Check signal_generator imports
    with open("backend/modules/signal_generator.py", "r") as f:
        signal_code = f.read()

    has_mi = "market_sentiment_score" in signal_code and "get_market_sentiment_score" in signal_code
    test_result("signal_generator.py", has_mi, "Market intelligence integration found")

except Exception as e:
    test_result("signal_generator.py", False, f"Error reading file: {str(e)[:40]}")

# ============================================================================
# TEST 7: Documentation Check
# ============================================================================
print("\n" + "-"*80)
print("TEST 7: Documentation & Comments")
print("-"*80 + "\n")

try:
    with open("backend/modules/market_intelligence.py", "r") as f:
        mi_code = f.read()

    has_docstrings = '"""' in mi_code and 'async def' in mi_code
    test_result("market_intelligence.py docs", has_docstrings, "Docstrings present")

except Exception as e:
    test_warning("market_intelligence.py docs", f"Could not verify: {str(e)[:40]}")

# ============================================================================
# FINAL REPORT
# ============================================================================
print("\n" + "="*80)
print("VALIDATION REPORT".center(80))
print("="*80 + "\n")

total_tests = tests_passed + tests_failed
success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"✅ PASSED:  {tests_passed:3} tests")
print(f"❌ FAILED:  {tests_failed:3} tests")
print(f"⚠️  WARNS:   {tests_warnings:3} items")
print(f"\nTOTAL:      {total_tests:3} tests")
print(f"SUCCESS:    {success_rate:5.1f}%\n")

if tests_failed == 0:
    print("🟢 " + "TESTNET VALIDATION SUCCESSFUL".center(76) + " 🟢")
    print("\n✅ All core modules initialized and configured correctly")
    print("✅ All new columns present in Trade model")
    print("✅ All integration points in place")
    print("✅ Feature flags properly configured")
    print("\nReady for testnet trading! Monitor logs carefully during execution.")
    exit_code = 0
else:
    print("🔴 " + "TESTNET VALIDATION FAILED".center(76) + " 🔴")
    print("\n❌ Fix issues above before proceeding with testnet deployment")
    exit_code = 1

print("\n" + "="*80 + "\n")

sys.exit(exit_code)
