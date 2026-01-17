-- ============================================================
-- Migration: Advanced Trading Strategies Tables
-- Description: Tables for trailing stops, execution strategies tracking
-- Date: 2026-01-17
-- ============================================================

-- Table: strategy_configurations
-- Stores user preferences for execution strategies per symbol or globally
CREATE TABLE IF NOT EXISTS strategy_configurations (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),  -- NULL for global config

    -- Execution mode
    execution_mode VARCHAR(20) DEFAULT 'static',  -- static, sniper, pyramid, dca, hybrid
    margin_mode VARCHAR(20) DEFAULT 'CROSSED',    -- CROSSED, ISOLATED

    -- Trailing stop config
    trailing_stop_mode VARCHAR(20) DEFAULT 'smart',  -- disabled, static, dynamic, profit_based, breakeven, smart
    min_profit_activation_pct FLOAT DEFAULT 1.5,
    base_callback_pct FLOAT DEFAULT 2.0,

    -- Pyramid config
    pyramid_max_entries INT DEFAULT 4,
    pyramid_scale_factor FLOAT DEFAULT 0.5,
    pyramid_min_profit_pct FLOAT DEFAULT 2.0,

    -- DCA config
    dca_max_entries INT DEFAULT 3,
    dca_interval_pct FLOAT DEFAULT 2.0,
    dca_size_multiplier FLOAT DEFAULT 1.5,

    -- Sniper config
    sniper_max_attempts INT DEFAULT 3,
    sniper_timeout_sec INT DEFAULT 30,
    sniper_price_improvement_bps FLOAT DEFAULT 5.0,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraint: one config per symbol
    CONSTRAINT unique_symbol_config UNIQUE (symbol)
);

-- Table: trade_strategy_executions
-- Tracks how each trade was executed with which strategy
CREATE TABLE IF NOT EXISTS trade_strategy_executions (
    id SERIAL PRIMARY KEY,
    trade_id VARCHAR(50),
    symbol VARCHAR(20) NOT NULL,

    -- Strategy used
    execution_mode VARCHAR(20) NOT NULL,
    margin_mode VARCHAR(20),

    -- Entry tracking
    total_entries INT DEFAULT 1,
    entry_prices JSONB,  -- Array of entry prices
    entry_quantities JSONB,  -- Array of quantities per entry
    average_entry_price FLOAT,
    total_quantity FLOAT,

    -- Trailing stop tracking
    trailing_stop_activated BOOLEAN DEFAULT FALSE,
    trailing_stop_mode VARCHAR(20),
    trailing_callback_pct FLOAT,
    trailing_activated_at TIMESTAMP,
    trailing_activation_price FLOAT,

    -- Exit tracking
    exit_price FLOAT,
    exit_reason VARCHAR(50),  -- stop_loss, take_profit, trailing_stop, manual
    realized_pnl FLOAT,
    realized_pnl_pct FLOAT,

    -- Performance
    duration_minutes INT,
    max_profit_pct FLOAT,  -- Maximum profit reached during trade
    max_drawdown_pct FLOAT,  -- Maximum drawdown during trade

    -- Metadata
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,

    CONSTRAINT fk_trade
        FOREIGN KEY(trade_id)
        REFERENCES trades(id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_strategy_exec_symbol ON trade_strategy_executions(symbol);
CREATE INDEX IF NOT EXISTS idx_strategy_exec_mode ON trade_strategy_executions(execution_mode);
CREATE INDEX IF NOT EXISTS idx_strategy_exec_opened ON trade_strategy_executions(opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_exec_trade_id ON trade_strategy_executions(trade_id);

-- Table: trailing_stop_history
-- Detailed log of trailing stop activations and adjustments
CREATE TABLE IF NOT EXISTS trailing_stop_history (
    id SERIAL PRIMARY KEY,
    trade_execution_id INT REFERENCES trade_strategy_executions(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,

    -- Event type
    event_type VARCHAR(30) NOT NULL,  -- activated, adjusted, triggered, cancelled

    -- Stop details
    callback_rate FLOAT,
    activation_price FLOAT,
    stop_price FLOAT,  -- Calculated stop price at this moment
    current_price FLOAT,
    unrealized_pnl_pct FLOAT,

    -- ML/Smart decision factors (if applicable)
    activation_score INT,  -- For smart mode
    factors_json JSONB,  -- Additional decision factors

    -- Metadata
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trail_history_trade ON trailing_stop_history(trade_execution_id);
CREATE INDEX IF NOT EXISTS idx_trail_history_symbol ON trailing_stop_history(symbol);

-- Table: strategy_performance_stats
-- Aggregated performance statistics per strategy mode
CREATE TABLE IF NOT EXISTS strategy_performance_stats (
    id SERIAL PRIMARY KEY,
    execution_mode VARCHAR(20) NOT NULL UNIQUE,

    -- Count metrics
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,

    -- Profit metrics
    total_pnl_pct FLOAT DEFAULT 0.0,
    avg_win_pct FLOAT DEFAULT 0.0,
    avg_loss_pct FLOAT DEFAULT 0.0,
    largest_win_pct FLOAT DEFAULT 0.0,
    largest_loss_pct FLOAT DEFAULT 0.0,

    -- Risk metrics
    win_rate FLOAT DEFAULT 0.0,
    profit_factor FLOAT DEFAULT 0.0,
    sharpe_ratio FLOAT DEFAULT 0.0,
    max_drawdown_pct FLOAT DEFAULT 0.0,

    -- Execution quality
    avg_entries_per_trade FLOAT DEFAULT 1.0,
    avg_duration_minutes FLOAT DEFAULT 0.0,
    trailing_stop_usage_pct FLOAT DEFAULT 0.0,

    -- Metadata
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Insert default stats for each mode
INSERT INTO strategy_performance_stats (execution_mode) VALUES
    ('static'),
    ('sniper'),
    ('pyramid'),
    ('dca'),
    ('hybrid')
ON CONFLICT (execution_mode) DO NOTHING;

-- Table: margin_mode_history
-- Track margin mode changes per symbol
CREATE TABLE IF NOT EXISTS margin_mode_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,

    -- Mode change
    old_mode VARCHAR(20),
    new_mode VARCHAR(20) NOT NULL,
    leverage INT,

    -- Reason
    changed_by VARCHAR(50),  -- 'user', 'system', 'ml'
    reason TEXT,

    -- Metadata
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_margin_history_symbol ON margin_mode_history(symbol);

-- Add comments
COMMENT ON TABLE strategy_configurations IS 'User and symbol-specific strategy configurations';
COMMENT ON TABLE trade_strategy_executions IS 'Detailed execution tracking for each trade with strategy info';
COMMENT ON TABLE trailing_stop_history IS 'Event log for trailing stop lifecycle';
COMMENT ON TABLE strategy_performance_stats IS 'Aggregated performance metrics per execution mode';
COMMENT ON TABLE margin_mode_history IS 'Audit log for margin mode changes';

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_bot_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_bot_user;
