-- ============================================================
-- Migration: Adaptive Intelligence Engine Tables
-- Description: Adds tables for ML features, regime configs, and filter rules
-- Date: 2026-01-17
-- ============================================================

-- Table: ml_trade_features
-- Stores features and outcomes for ML training
CREATE TABLE IF NOT EXISTS ml_trade_features (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,

    -- Volatility Features
    atr_1m FLOAT,
    atr_5m FLOAT,
    atr_1h FLOAT,
    bb_width_1m FLOAT,
    bb_width_5m FLOAT,

    -- Trend Features
    adx_1m FLOAT,
    adx_5m FLOAT,
    adx_1h FLOAT,
    ema_slope_fast FLOAT,
    ema_slope_slow FLOAT,

    -- Momentum Features
    rsi_1m FLOAT,
    rsi_5m FLOAT,
    rsi_1h FLOAT,
    macd_histogram FLOAT,
    macd_signal_cross BOOLEAN,
    rsi_divergence_bull BOOLEAN,
    rsi_divergence_bear BOOLEAN,

    -- Volume Features
    volume_ratio FLOAT,
    volume_trend FLOAT,
    vwap_distance FLOAT,
    vwap_slope FLOAT,

    -- Market Regime Features
    btc_correlation_15m FLOAT,
    market_hour INT,
    day_of_week INT,
    us_market_session BOOLEAN,
    asian_session BOOLEAN,

    -- Spread & Execution
    spread_bps FLOAT,

    -- Market Regime Classification
    market_regime INT,

    -- Trade Outcome
    outcome VARCHAR(10), -- 'WIN' or 'LOSS'
    pnl_pct FLOAT,
    pnl_absolute FLOAT,
    duration_minutes INT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key (optional, may not exist in all setups)
    CONSTRAINT fk_trade
        FOREIGN KEY(trade_id)
        REFERENCES trades(id)
        ON DELETE SET NULL
);

-- Indexes for ml_trade_features
CREATE INDEX IF NOT EXISTS idx_ml_features_symbol ON ml_trade_features(symbol);
CREATE INDEX IF NOT EXISTS idx_ml_features_timestamp ON ml_trade_features(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ml_features_regime ON ml_trade_features(market_regime);
CREATE INDEX IF NOT EXISTS idx_ml_features_outcome ON ml_trade_features(outcome);
CREATE INDEX IF NOT EXISTS idx_ml_features_trade_id ON ml_trade_features(trade_id);

-- Table: regime_configs
-- Stores optimized configurations for each market regime
CREATE TABLE IF NOT EXISTS regime_configs (
    id SERIAL PRIMARY KEY,
    regime_id INT NOT NULL UNIQUE,
    regime_name VARCHAR(50) NOT NULL,

    -- Optimized Parameters
    min_score INT DEFAULT 70,
    max_positions INT DEFAULT 15,
    risk_per_trade_pct FLOAT DEFAULT 2.0,
    rsi_oversold INT DEFAULT 30,
    rsi_overbought INT DEFAULT 70,
    adx_min INT DEFAULT 25,
    volume_threshold_pct FLOAT DEFAULT 50.0,
    stop_loss_atr_mult FLOAT DEFAULT 2.0,
    take_profit_ratio FLOAT DEFAULT 2.0,

    -- Performance Metrics
    sharpe_ratio FLOAT,
    win_rate FLOAT,
    avg_pnl_pct FLOAT,
    profit_factor FLOAT,
    max_drawdown_pct FLOAT,

    -- Metadata
    trained_at TIMESTAMP DEFAULT NOW(),
    n_samples INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert default regime configurations
INSERT INTO regime_configs (regime_id, regime_name, min_score, max_positions, risk_per_trade_pct)
VALUES
    (0, 'trending_high_vol', 65, 12, 1.8),
    (1, 'trending_low_vol', 70, 15, 2.0),
    (2, 'ranging_high_vol', 80, 8, 1.2),
    (3, 'ranging_low_vol', 75, 10, 1.5),
    (4, 'explosive', 85, 5, 1.0)
ON CONFLICT (regime_id) DO NOTHING;

-- Table: filter_rules
-- Stores discovered loss patterns as filter rules
CREATE TABLE IF NOT EXISTS filter_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100),
    rule_json JSONB NOT NULL,

    -- Rule Metrics
    confidence FLOAT NOT NULL,
    support FLOAT NOT NULL,
    lift FLOAT NOT NULL,

    -- Effectiveness Tracking
    is_active BOOLEAN DEFAULT TRUE,
    trades_prevented INT DEFAULT 0,
    false_negatives INT DEFAULT 0, -- Good trades that were blocked

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_triggered_at TIMESTAMP,

    -- Add constraint to ensure unique rules
    CONSTRAINT unique_rule UNIQUE (rule_json)
);

-- Index for filter_rules
CREATE INDEX IF NOT EXISTS idx_filter_rules_active ON filter_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_filter_rules_confidence ON filter_rules(confidence DESC);

-- Table: ml_model_metadata
-- Tracks ML model versions and performance
CREATE TABLE IF NOT EXISTS ml_model_metadata (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'xgboost', 'random_forest', 'logistic'
    version VARCHAR(20) NOT NULL,

    -- Model Path
    model_path VARCHAR(255),

    -- Performance Metrics
    auc_score FLOAT,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,

    -- Training Info
    n_samples_train INT,
    n_samples_test INT,
    features_used JSONB,
    hyperparameters JSONB,

    -- Metadata
    trained_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT FALSE,

    CONSTRAINT unique_model_version UNIQUE (model_name, version)
);

-- Index for ml_model_metadata
CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_model_metadata(is_active);
CREATE INDEX IF NOT EXISTS idx_ml_models_name ON ml_model_metadata(model_name);

-- Table: ml_performance_log
-- Tracks daily performance of the ML system
CREATE TABLE IF NOT EXISTS ml_performance_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- Detected Regime
    regime_detected INT,
    regime_name VARCHAR(50),

    -- Trading Metrics
    total_trades INT DEFAULT 0,
    ml_approved_trades INT DEFAULT 0,
    ml_rejected_trades INT DEFAULT 0,

    -- Performance
    win_rate FLOAT,
    avg_pnl_pct FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown_pct FLOAT,

    -- ML Effectiveness
    ml_score_avg FLOAT,
    traditional_score_avg FLOAT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for ml_performance_log
CREATE INDEX IF NOT EXISTS idx_ml_perf_date ON ml_performance_log(date DESC);

-- Table: indicator_weights_history
-- Tracks evolution of indicator weights over time
CREATE TABLE IF NOT EXISTS indicator_weights_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    regime_id INT,

    -- Indicator Weights (normalized to sum = 1.0)
    weights_json JSONB NOT NULL,

    -- Performance with these weights
    sharpe_ratio FLOAT,
    win_rate FLOAT,

    -- Metadata
    n_trades_evaluated INT DEFAULT 0
);

-- Index for indicator_weights_history
CREATE INDEX IF NOT EXISTS idx_weights_timestamp ON indicator_weights_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_weights_regime ON indicator_weights_history(regime_id);

-- Add comments for documentation
COMMENT ON TABLE ml_trade_features IS 'Stores features and outcomes for ML model training';
COMMENT ON TABLE regime_configs IS 'Optimized trading configurations for each market regime';
COMMENT ON TABLE filter_rules IS 'Pattern-based rules to filter out likely losing trades';
COMMENT ON TABLE ml_model_metadata IS 'Tracks ML model versions and performance metrics';
COMMENT ON TABLE ml_performance_log IS 'Daily performance log of the ML system';
COMMENT ON TABLE indicator_weights_history IS 'Historical evolution of indicator importance weights';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_bot_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_bot_user;
