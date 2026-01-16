import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from modules.risk_manager import RiskManager

# Mock Redis client
@pytest.fixture
def mock_redis():
    with patch('modules.risk_manager.redis_client') as mock:
        mock.client = MagicMock()
        yield mock

@pytest.fixture
def mock_settings():
    with patch('modules.risk_manager.get_settings') as mock:
        settings = MagicMock()
        # Set default values for settings used in RiskManager
        settings.RISK_PER_TRADE = 0.02
        settings.MAX_PORTFOLIO_RISK = 0.15
        settings.MAX_POSITIONS = 5
        settings.SNIPER_RISK_PER_TRADE = 0.01
        settings.SNIPER_EXTRA_SLOTS = 2
        settings.REVERSAL_EXTRA_SLOTS_PCT = 0.5  # ✅ Added missing mock
        settings.DAILY_MAX_LOSS_PCT = 0.05
        settings.INTRADAY_DRAWDOWN_HARD_STOP_PCT = 0.10
        mock.return_value = settings
        yield settings

@pytest.fixture
def risk_manager(mock_redis, mock_settings):
    # Reset singleton if needed or just instantiate new
    rm = RiskManager()
    # Reset internal state for tests
    rm._daily_date = None
    rm._daily_start_balance = None
    rm._intraday_peak_balance = None
    rm._intraday_trough_balance = None
    return rm

def test_rollover_daily_initialization(risk_manager, mock_redis):
    """Test if rollover initializes balances correctly from scratch"""
    # Setup
    mock_redis.client.get.return_value = None # No data in Redis
    
    # Execute
    risk_manager._rollover_daily(1000.0)
    
    # Verify
    assert risk_manager._daily_start_balance == 1000.0
    assert risk_manager._intraday_peak_balance == 1000.0
    assert risk_manager._intraday_trough_balance == 1000.0
    
    # Verify Redis set calls
    assert mock_redis.client.set.call_count >= 3 # daily, peak, trough

def test_rollover_daily_recovery(risk_manager, mock_redis):
    """Test if rollover recovers balances from Redis"""
    # Setup
    mock_redis.client.get.side_effect = [
        "1000.0", # daily
        "1100.0", # peak
        "900.0"   # trough
    ]
    
    # Execute
    risk_manager._rollover_daily(1050.0) # Current balance
    
    # Verify
    assert risk_manager._daily_start_balance == 1000.0
    assert risk_manager._intraday_peak_balance == 1100.0
    assert risk_manager._intraday_trough_balance == 900.0

def test_update_intraday_extrema_persistence(risk_manager, mock_redis):
    """Test if updates are persisted to Redis"""
    # Setup
    risk_manager._intraday_peak_balance = 1000.0
    risk_manager._intraday_trough_balance = 1000.0
    
    # Execute - New Peak
    risk_manager._update_intraday_extrema(1100.0)
    
    # Verify
    assert risk_manager._intraday_peak_balance == 1100.0
    # Check if set was called for peak
    # We iterate over all calls to find the one for peak
    calls = mock_redis.client.set.call_args_list
    peak_call_found = False
    for call in calls:
        args, _ = call
        if "risk:intraday_peak" in args[0] and args[1] == "1100.0":
            peak_call_found = True
            break
    assert peak_call_found

def test_hard_stop_with_recovered_peak(risk_manager, mock_redis):
    """Test if hard stop works with recovered peak"""
    # Setup
    risk_manager.intraday_dd_hard_stop_pct = 0.10 # 10%
    risk_manager.daily_max_loss_pct = 1.0 # Disable daily stop (100% loss allowed) for this test
    risk_manager._intraday_peak_balance = 1000.0 # Recovered peak
    risk_manager._daily_start_balance = 1000.0 # Must be set to avoid reset in rollover
    risk_manager._daily_date = datetime.now(timezone.utc).date() # Must be today to avoid rollover reset
    
    # Execute - Drawdown 15% from peak (850)
    # Current balance 850
    signal = {"symbol": "BTCUSDT", "risk_pct": 1.0}
    result = risk_manager.validate_trade(signal, account_balance=850.0)
    
    # Verify
    assert result["approved"] is False
    assert "Hard stop intradiário" in result["reason"]
