"""
SQLAlchemy models for Adaptive Intelligence Engine
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, JSON, Text, UniqueConstraint
)
from sqlalchemy.sql import func
from api.models.database import Base


class MLTradeFeature(Base):
    """
    Stores features and outcomes for ML training
    """
    __tablename__ = "ml_trade_features"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String(50), ForeignKey("trades.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)

    # Volatility Features
    atr_1m = Column(Float)
    atr_5m = Column(Float)
    atr_1h = Column(Float)
    bb_width_1m = Column(Float)
    bb_width_5m = Column(Float)

    # Trend Features
    adx_1m = Column(Float)
    adx_5m = Column(Float)
    adx_1h = Column(Float)
    ema_slope_fast = Column(Float)
    ema_slope_slow = Column(Float)

    # Momentum Features
    rsi_1m = Column(Float)
    rsi_5m = Column(Float)
    rsi_1h = Column(Float)
    macd_histogram = Column(Float)
    macd_signal_cross = Column(Boolean)
    rsi_divergence_bull = Column(Boolean)
    rsi_divergence_bear = Column(Boolean)

    # Volume Features
    volume_ratio = Column(Float)
    volume_trend = Column(Float)
    vwap_distance = Column(Float)
    vwap_slope = Column(Float)

    # Market Regime Features
    btc_correlation_15m = Column(Float)
    market_hour = Column(Integer)
    day_of_week = Column(Integer)
    us_market_session = Column(Boolean)
    asian_session = Column(Boolean)

    # Spread & Execution
    spread_bps = Column(Float)

    # Market Regime Classification
    market_regime = Column(Integer, index=True)

    # Trade Outcome
    outcome = Column(String(10), index=True)  # 'WIN' or 'LOSS'
    pnl_pct = Column(Float)
    pnl_absolute = Column(Float)
    duration_minutes = Column(Integer)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())


class RegimeConfig(Base):
    """
    Stores optimized configurations for each market regime
    """
    __tablename__ = "regime_configs"

    id = Column(Integer, primary_key=True, index=True)
    regime_id = Column(Integer, unique=True, nullable=False)
    regime_name = Column(String(50), nullable=False)

    # Optimized Parameters
    min_score = Column(Integer, default=70)
    max_positions = Column(Integer, default=15)
    risk_per_trade_pct = Column(Float, default=2.0)
    rsi_oversold = Column(Integer, default=30)
    rsi_overbought = Column(Integer, default=70)
    adx_min = Column(Integer, default=25)
    volume_threshold_pct = Column(Float, default=50.0)
    stop_loss_atr_mult = Column(Float, default=2.0)
    take_profit_ratio = Column(Float, default=2.0)

    # Performance Metrics
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    avg_pnl_pct = Column(Float)
    profit_factor = Column(Float)
    max_drawdown_pct = Column(Float)

    # Metadata
    trained_at = Column(DateTime, server_default=func.now())
    n_samples = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class FilterRule(Base):
    """
    Stores discovered loss patterns as filter rules
    """
    __tablename__ = "filter_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100))
    rule_json = Column(JSON, nullable=False)

    # Rule Metrics
    confidence = Column(Float, nullable=False, index=True)
    support = Column(Float, nullable=False)
    lift = Column(Float, nullable=False)

    # Effectiveness Tracking
    is_active = Column(Boolean, default=True, index=True)
    trades_prevented = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    last_triggered_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('rule_json', name='unique_rule'),
    )


class MLModelMetadata(Base):
    """
    Tracks ML model versions and performance
    """
    __tablename__ = "ml_model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50), nullable=False, index=True)
    model_type = Column(String(50), nullable=False)
    version = Column(String(20), nullable=False)

    # Model Path
    model_path = Column(String(255))

    # Performance Metrics
    auc_score = Column(Float)
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)

    # Training Info
    n_samples_train = Column(Integer)
    n_samples_test = Column(Integer)
    features_used = Column(JSON)
    hyperparameters = Column(JSON)

    # Metadata
    trained_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=False, index=True)

    __table_args__ = (
        UniqueConstraint('model_name', 'version', name='unique_model_version'),
    )


class MLPerformanceLog(Base):
    """
    Tracks daily performance of the ML system
    """
    __tablename__ = "ml_performance_log"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)

    # Detected Regime
    regime_detected = Column(Integer)
    regime_name = Column(String(50))

    # Trading Metrics
    total_trades = Column(Integer, default=0)
    ml_approved_trades = Column(Integer, default=0)
    ml_rejected_trades = Column(Integer, default=0)

    # Performance
    win_rate = Column(Float)
    avg_pnl_pct = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown_pct = Column(Float)

    # ML Effectiveness
    ml_score_avg = Column(Float)
    traditional_score_avg = Column(Float)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())


class IndicatorWeightsHistory(Base):
    """
    Tracks evolution of indicator weights over time
    """
    __tablename__ = "indicator_weights_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    regime_id = Column(Integer, index=True)

    # Indicator Weights (normalized to sum = 1.0)
    weights_json = Column(JSON, nullable=False)

    # Performance with these weights
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)

    # Metadata
    n_trades_evaluated = Column(Integer, default=0)
