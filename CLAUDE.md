# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Antigravity Trading Bot** is an autonomous cryptocurrency trading system for Binance Futures. The system consists of:
- **Backend**: FastAPI-based Python application with async architecture
- **Frontend**: React + TypeScript with Vite and Tailwind CSS (cyberpunk theme)
- **Infrastructure**: PostgreSQL database, Redis cache, WebSocket real-time updates
- **Core Features**: Autonomous trading bot, backtesting, risk management, technical analysis, Telegram notifications

## Architecture

### Core Trading Flow
1. **Market Scanner** (`backend/modules/market_scanner.py`) → Filters USDT-M Futures by volume/trend
2. **Signal Generator** (`backend/modules/signal_generator.py`) → Generates Long/Short signals with confidence scores using multi-timeframe analysis, RSI divergence, ADX, VWAP, MACD, Bollinger Bands
3. **Risk Calculator** (`backend/modules/risk_calculator.py`) → Calculates position sizes based on risk % (default 2%)
4. **Order Executor** (`backend/modules/order_executor.py`) → Executes trades with LIMIT orders (fallback to MARKET), manages stops/TPs
5. **Position Monitor** (`backend/modules/position_monitor.py`) → Tracks open positions, handles liquidation headroom checks
6. **Autonomous Bot** (`backend/modules/autonomous_bot.py`) → Orchestrates the full cycle in a loop

### Key Components
- **Binance Client** (`backend/utils/binance_client.py`): Singleton wrapper around python-binance, handles WebSocket streams (market data + user data), Redis caching for API calls, position mode enforcement (One-Way)
- **Settings** (`backend/config/settings.py`): Pydantic Settings with environment-based configuration (testnet/prod presets)
- **Database Models** (`backend/api/models/`): SQLAlchemy ORM for trades/positions
- **API Routes** (`backend/api/routes/`): FastAPI routers for trading, positions, config, market, system
- **WebSocket** (`backend/api/websocket.py`): Real-time updates via WebSocket + Redis pub/sub

### Trading Strategies
- **Trend Following**: Uses EMA crossovers, ADX strength filter
- **Mean Reversion**: Bollinger Bands, RSI oversold/overbought (30/70)
- **Volume Confirmation**: Minimum 50% above average volume
- **Multi-Timeframe**: Analyzes 1m, 5m, 1h candles for confirmation
- **Risk Management**: Max 15 positions, 2% risk per trade, 15% max portfolio risk, dynamic leverage (3-20x)

### Execution System (Phase 1+)
- **Post-Only (Maker) Mode**: Configurable via `USE_POST_ONLY_ENTRIES` or auto-enabled based on spread (`AUTO_POST_ONLY_ENTRIES` + `AUTO_MAKER_SPREAD_BPS`)
- **Order Timeout**: `ORDER_TIMEOUT_SEC` (default 3s), retries up to 3 times with requotes
- **Fallback to MARKET**: Last attempt uses MARKET order with average fill price calculation (`get_order_avg_price`)
- **Liquidation Headroom**: After opening, checks distance to liquidation; reduces position if below `HEADROOM_MIN_PCT` (35%)
- **Trailing Stop**: Optional (`ENABLE_TRAILING_STOP`), ATR-based callback percentage
- **Take Profit Ladder**: Configurable via `TAKE_PROFIT_PARTS` (e.g., "0.5,0.3,0.2")

## Development Commands

### Backend (Python)
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run API server (development with auto-reload)
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Run tests
PYTHONPATH=backend pytest -q backend/tests

# Run single test
PYTHONPATH=backend pytest backend/tests/test_specific.py::test_function_name -v
```

### Frontend (React + TypeScript)
```bash
cd frontend

# Install dependencies
npm ci

# Development server (with Vite proxy to API)
npm run dev
# Access at http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests (Vitest)
npm test
```

### Docker (Full Stack)
```bash
# Start all services (DB, Redis, API, Frontend)
docker compose up -d --build

# View API logs
docker logs -f trading-bot-api

# Stop all services
docker compose down

# Full reset (remove volumes)
docker compose down -v
docker compose build --no-cache
docker compose up -d

# Health check
curl -sS http://localhost:8000/health | jq .
```

### Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Required variables:
# - BINANCE_API_KEY, BINANCE_API_SECRET
# - BINANCE_TESTNET=true (for testing)
# - DATABASE_URL, REDIS_HOST, REDIS_PORT
# - TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional)
# - API_PORT_HOST=8000 (Docker host port)
```

## Critical Constraints & Gotchas

### Performance & Rate Limits
- **Binance API**: Respect 1200 weight/min limit. Use Redis caching when enabled
- **Analysis Loop**: Must complete in <5 seconds per symbol
- **Database**: Currently synchronous SQLAlchemy (async recommended for scale)

### Position Mode
- **One-Way Mode**: System enforces `dual_side=False` on startup via `binance_client.ensure_position_mode()`
- Never mix One-Way and Hedge mode positions

### Order Execution
- Always check symbol filters: `minQty`, `stepSize`, `minNotional` before placing orders
- Round quantities correctly using `step_size` precision
- Handle Binance error codes properly (e.g., -2019 insufficient margin, -1111 precision errors)

### Settings System
- **Environment-based**: Settings automatically detect testnet vs prod via `BINANCE_TESTNET`
- **Prod Presets**: Even in testnet, signal generator uses prod-quality thresholds (min_score=70, volume_threshold=50%)
- **Runtime Flags**: Execution config (`/api/trading/execution/config`) is in-memory, doesn't persist across restarts unless mapped to `.env`

### WebSocket Streams
- **Market Stream**: Provides real-time price updates, started automatically on API startup
- **User Data Stream**: Optional, requires explicit start via `/api/system/userstream/start`
- Both streams handle reconnection with exponential backoff

### Auto-Sync & Watchdog
- **Position Auto-Sync**: Reconciles DB vs Binance positions (controlled by `POSITIONS_AUTO_SYNC_ENABLED`)
- **Bot Watchdog**: Keeps bot running when `AUTOSTART_BOT=true`, checks every 10s

## API Key Endpoints (Common Operations)

```bash
# Check bot status
curl -sS http://localhost:8000/api/trading/bot/status | jq .

# Start bot (dry_run=false for real trading)
curl -sS -X POST "http://localhost:8000/api/trading/bot/start?dry_run=false" | jq .

# Stop bot
curl -sS -X POST "http://localhost:8000/api/trading/bot/stop" | jq .

# Update bot config
curl -sS -X PUT "http://localhost:8000/api/trading/bot/config?scan_interval_minutes=1&min_score=55&max_positions=10" | jq .

# Get execution config
curl -sS http://localhost:8000/api/trading/execution/config | jq .

# Update execution config (enable maker mode + TP ladder)
curl -sS -X PUT "http://localhost:8000/api/trading/execution/config?use_post_only_entries=true&take_profit_parts=0.5,0.3,0.2&headroom_min_pct=35" | jq .

# Execute single trade
curl -sS -X POST "http://localhost:8000/api/trading/execute" \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","risk_profile":"moderate","dry_run":false}' | jq .

# Close position
curl -sS -X POST "http://localhost:8000/api/trading/positions/close?symbol=BTCUSDT" | jq .

# View logs
curl -sS "http://localhost:8000/api/system/logs?component=api&tail=200" | jq -r .

# Test Telegram notification
curl -sS -X POST "http://localhost:8000/api/trading/test/telegram?text=Bot%20operacional" | jq .
```

## Security & Safety Rules

### Prohibited Actions (from .ai/safety-profile.md)
- **NEVER** modify files in: `clients/`, `data/`, `logs/`, `.git/`, `node_modules/`, `__pycache__`, `.venv`
- **NEVER** output contents of `.env` files or API keys (redact as `sk-***`)
- **NEVER** run destructive commands: `rm -rf`, `git clean -fdx`, `docker system prune -a`
- **NEVER** skip git hooks or force push to main/master without explicit user request

### Read-Only Files (Require Explicit Permission)
- `.env` (contains live secrets)
- `backend/config/settings.py` (modify only when adding new config vars)
- `docker-compose.yml` (core orchestration)

### Code Quality Standards (from .ai/agent-guidelines.md)
- **Python**: Async-first, mandatory type hints, docstrings for all public functions
- **Frontend**: Functional React components, Tailwind for styling
- **Commits**: Use Conventional Commits format (e.g., `feat: add scanner filter`, `fix: resolve overflow`)
- **Testing**: Never delete existing tests to make build pass - fix the code instead
- **Documentation**: Always update `docs/` when changing logic

## Testing Strategy

### Backend Tests
- Located in `backend/tests/`
- Run with `PYTHONPATH=backend pytest -q backend/tests`
- Key test files: `test_phase1.py` (validates Phase 1 features)

### Frontend Tests
- Uses Vitest with Testing Library
- Run with `npm test` in `frontend/`
- Configuration in `frontend/vitest.config.ts`

### CI Pipeline
- **GitHub Actions**: `.github/workflows/ci.yml`
- Runs on all pushes and PRs
- Two jobs: Backend (pytest), Frontend (Vitest)
- Uses caching for pip and npm dependencies

## AI-Specific Guidelines

### Before Starting Work
1. Read `.ai/context-map.md` for critical file locations
2. Read `.ai/safety-profile.md` for security boundaries
3. Check existing patterns in codebase before creating new abstractions

### When Making Changes
- **Plan First**: For complex features, create implementation plan before coding
- **Verify Changes**: Propose test or manual verification method
- **Update Docs**: Sync changes to `docs/` (especially API_SPEC.md, RUNBOOK.md)
- **Avoid Over-Engineering**: Don't add features/refactoring beyond what was asked
- Don't add error handling for scenarios that can't happen
- Three similar lines > premature abstraction

### Security Reminders
- No logging of API keys (already enforced in logger setup)
- No committing `.env` files
- Consider API auth (`API_AUTH_ENABLED`, `API_KEY`) for exposed environments
- Use testnet (`BINANCE_TESTNET=true`) by default in development

## Module Dependencies

Key import patterns:
```python
# Logging
from utils.logger import setup_logger
logger = setup_logger("module_name")

# Settings
from config.settings import get_settings
settings = get_settings()

# Binance Client (singleton)
from utils.binance_client import binance_client
price = await binance_client.get_symbol_price("BTCUSDT")

# Database
from models.database import SessionLocal, engine
from api.models.trades import Trade, Position

# Risk Calculation
from modules.risk_calculator import risk_calculator
size = await risk_calculator.calculate_position_size(...)

# Signal Generation
from modules.signal_generator import signal_generator
signals = await signal_generator.generate_signal(scan_results)
```

## Documentation References

For detailed information, consult:
- **API Spec**: `docs/API_SPEC.md` - Complete API endpoint documentation
- **Runbook**: `docs/RUNBOOK.md` - Operational procedures and troubleshooting
- **Deployment**: `docs/DEPLOYMENT.md` - Deployment guide with runtime flags
- **System Spec**: `specs/SYSTEM_SPEC.md` - High-level architecture and objectives
- **Context Map**: `.ai/context-map.md` - File sensitivity and critical paths
- **Agent Guidelines**: `.ai/agent-guidelines.md` - AI contributor rules
