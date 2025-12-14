# System Specification

> **ID**: SPEC-000
> **Registry**: [SPEC_INDEX.md](SPEC_INDEX.md)


## 1. System Overview
The **Antigravity Crypto Trading Bot** is an automated trading system for Binance Futures. It aims to generate profit by executing algorithmic strategies (Trend Following, Mean Reversion) while strictly managing risk.

## 2. Core Objectives
- **Profitability**: Maximize Sharpe Ratio.
- **Safety**: Prevent catastrophic loss (Liquidation).
- **Autonomy**: Run 24/7 with minimal human intervention.

## 3. High-Level Flows

### 3.1. Market Scanning
- **Input**: All USDT-M Futures symbols.
- **Process**: Filter by Volume > 10M, Trend > Threshold.
- **Output**: Whitelist of tradable symbols.

### 3.2. Signal Generation
- **Input**: Candle data (1m, 5m, 1h).
- **Process**: Apply technical indicators (RSI, MACD, Bollinger).
- **Output**: Long/Short signals with Confidence Score (0-100).

### 3.3. Execution
- **Input**: Signals + Risk Constraints.
- **Process**: Calculate position size based on Risk % (default 2%). Place Orders (Limit/Market).
- **Output**: Open Positions.

## 4. Key Constraints
- **Latency**: Analysis loop < 5 seconds.
- **Rate Limits**: Respect Binance API weight limits (1200/min).
- **Database**: Async IO for all DB operations.
- **Security**: No logging of API Keys.
