---
status: filled
generated: 2026-01-12
---

# Project Overview

The Antigravity Trading Bot is an autonomous crypto futures trading platform focused on Binance Futures. It provides a FastAPI backend for trading logic, risk controls, and orchestration, plus a React dashboard for operators to monitor, configure, and intervene. Primary users are traders and ops engineers who need controlled automation, visibility, and guardrails, including testnet validation and manual override paths for safety.

## Quick Facts

- Root path: `C:\Projetos\Vector Protocol`
- Primary languages detected:
- .js (8051 files)
- .map (2558 files)
- .ts (1470 files)
- .json (601 files)
- .md (475 files)

## Entry Points
- [`frontend\src\main.tsx`](frontend\src\main.tsx)

## Key Exports
**Classes:**
- [`TelegramNotifier`](backend\utils\telegram_notifier.py#L10)
- [`RedisClient`](backend\utils\redis_client.py#L7)
- [`JSONFormatter`](backend\utils\logger.py#L13)
- [`RedisLogHandler`](backend\utils\logger.py#L28)
- [`DataValidationError`](backend\utils\binance_client.py#L20)
- [`DataValidator`](backend\utils\binance_client.py#L28)
- [`BinanceClientManager`](backend\utils\binance_client.py#L290)
- [`TestDataValidator`](backend\tests\test_validations.py#L18)
- [`TestSupervisor`](backend\tests\test_validations.py#L219)
- [`TestSystemStateError`](backend\tests\test_validations.py#L348)
- [`TestDataValidationError`](backend\tests\test_validations.py#L369)
- [`TestIntegration`](backend\tests\test_validations.py#L393)
- [`CmdResult`](backend\scripts\supervisor.py#L84)
- [`StressTestExecutor`](backend\scripts\stress_test_execution.py#L27)
- [`TelegramBot`](backend\modules\telegram_bot.py#L10)
- [`SystemStateError`](backend\modules\supervisor.py#L14)
- [`Supervisor`](backend\modules\supervisor.py#L22)
- [`SignalGenerator`](backend\modules\signal_generator.py#L30)
- [`RulesEngine`](backend\modules\rules_engine.py#L19)
- [`RiskManager`](backend\modules\risk_manager.py#L21)
- [`RiskCalculator`](backend\modules\risk_calculator.py#L18)
- [`ProfitOptimizer`](backend\modules\profit_optimizer.py#L27)
- [`PositionMonitor`](backend\modules\position_monitor.py#L31)
- [`OrderExecutor`](backend\modules\order_executor.py#L59)
- [`MetricsDashboard`](backend\modules\metrics_dashboard.py#L24)
- [`MetricsCollector`](backend\modules\metrics_collector.py#L13)
- [`MarketScanner`](backend\modules\market_scanner.py#L22)
- [`MarketMonitor`](backend\modules\market_monitor.py#L14)
- [`MarketIntelligence`](backend\modules\market_intelligence.py#L29)
- [`MarketFilter`](backend\modules\market_filter.py#L19)
- [`HistoryAnalyzer`](backend\modules\history_analyzer.py#L17)
- [`ErrorAggregator`](backend\modules\error_aggregator.py#L18)
- [`DailyReport`](backend\modules\daily_report.py#L12)
- [`CorrelationFilter`](backend\modules\correlation_filter.py#L17)
- [`ConfigManager`](backend\modules\config_manager.py#L14)
- [`Configuration`](backend\modules\config_database.py#L12)
- [`ConfigurationHistory`](backend\modules\config_database.py#L42)
- [`Backtester`](backend\modules\backtester.py#L16)
- [`AutonomousBot`](backend\modules\autonomous_bot.py#L41)
- [`Settings`](backend\config\settings.py#L5)
- [`ConnectionManager`](backend\api\websocket.py#L13)
- [`BacktestRequest`](backend\api\backtesting.py#L15)
- [`BacktestResponse`](backend\api\backtesting.py#L24)
- [`ApiKeyMiddleware`](backend\api\app.py#L34)
- [`TradingLoop`](backend\modules\bot\trading_loop.py#L28)
- [`BotStrategies`](backend\modules\bot\strategies.py#L11)
- [`PositionManager`](backend\modules\bot\position_manager.py#L10)
- [`BotLoops`](backend\modules\bot\loops.py#L10)
- [`BotConfig`](backend\modules\bot\bot_config.py#L3)
- [`BotActions`](backend\modules\bot\actions.py#L12)
- [`ExecuteTradeRequest`](backend\api\routes\trading.py#L78)
- [`ManualTradeRequest`](backend\api\routes\trading.py#L1689)
- [`TradingRuleCreate`](backend\api\routes\rules.py#L23)
- [`TradingRuleUpdate`](backend\api\routes\rules.py#L47)
- [`TradingRuleResponse`](backend\api\routes\rules.py#L57)
- [`RuleTypeSchema`](backend\api\routes\rules.py#L74)
- [`ConfigValue`](backend\api\routes\database_config.py#L28)
- [`ConfigUpdateResponse`](backend\api\routes\database_config.py#L35)
- [`BatchUpdateResponse`](backend\api\routes\database_config.py#L44)
- [`ConfigUpdate`](backend\api\routes\config.py#L11)
- [`TradingRule`](backend\api\models\trading_rules.py#L22)
- [`Trade`](backend\api\models\trades.py#L21)

**Interfaces:**
- [`HistoryAnalysis`](frontend\src\services\api.ts#L531)
- [`SniperTrade`](frontend\src\services\api.ts#L553)
- [`SniperStats`](frontend\src\services\api.ts#L568)
- [`CumulativePnlPoint`](frontend\src\services\api.ts#L585)
- [`CumulativePnlResponse`](frontend\src\services\api.ts#L594)
- [`ErrorLog`](frontend\src\services\api.ts#L604)
- [`ErrorsResponse`](frontend\src\services\api.ts#L612)
- [`ErrorRateResponse`](frontend\src\services\api.ts#L627)
- [`ErrorSummary`](frontend\src\services\api.ts#L640)
- [`LatencyStats`](frontend\src\services\api.ts#L652)
- [`SyncStatus`](frontend\src\services\api.ts#L670)
- [`MarketConditions`](frontend\src\services\api.ts#L693)
- [`InputProps`](frontend\src\components\ui\input.tsx#L4)
- [`ButtonProps`](frontend\src\components\ui\button.tsx#L26)
- [`BadgeProps`](frontend\src\components\ui\badge.tsx#L19)

## File Structure & Code Organization
- `ACOMPANHAMENTO_README.md/` - Operational monitoring cheat sheet; update when runbook commands or thresholds change.
- `backend/` - FastAPI API, trading engine modules, DB models, scripts; edit when changing backend behavior.
- `CLAUDE.md/` - Claude-specific contributor instructions; update when agent guidance changes.
- `docker-compose.yml/` - Local/container orchestration for API, frontend, DB, Redis; edit for service topology/ports/env.
- `docs/` - Human-facing documentation and governance; update when processes or behavior change.
- `frontend/` - React/Vite dashboard; edit when UI or API usage changes.
- `IMPROVEMENTS_IMPLEMENTED.md/` - Record of improvements already shipped; update when completing initiatives.
- `kubernetes/` - Kubernetes manifests for cluster deployment; edit for infra changes.
- `logs/` - Runtime log output; usually read-only for debugging.
- `monitor_continuous.py/` - Monitoring script for continuous checks; edit when monitoring logic changes.
- `MONITOR_LOG.txt/` - Output log from the monitor; avoid manual edits.
- `MONITORING_SETUP.md/` - Setup instructions for monitoring tooling; update when the monitor setup changes.
- `open_bananausdt.py/` - One-off manual trade helper script; edit for manual execution flows.
- `open_position.py/` - Manual single-position execution script; edit for manual trade flow updates.
- `open_three_positions.py/` - Manual multi-position execution script; edit for manual trade flow updates.
- `open_two_positions_safe.py/` - Safer multi-position execution script; edit for manual trade flow updates.
- `otrading/` - Strategy notes, token lists, and research artifacts; update when research changes.
- `photo_2024-08-17_13-10-41.jpg/` - Static asset used for documentation or reference.
- `PRODUCTION_DEPLOYMENT_PLAN.md/` - Production deployment plan; update ahead of releases.
- `PRODUCTION_FULL_ROLLOUT.md/` - Full rollout checklist and phases; update when rollout strategy changes.
- `project-knowledge.md/` - Shared AI context and project knowledge; update when key facts change.
- `pytest.ini/` - Pytest configuration; edit when test discovery or markers change.
- `quantbrasil_ativos.html/` - Static data export/reference; update when source data changes.
- `README.md/` - Primary project overview; update when positioning or setup changes.
- `smart_monitor.sh/` - Shell monitor script; edit when monitoring automation changes.
- `specs/` - Feature and system specifications; add specs before implementation.
- `TESTNET_READY.md/` - Testnet readiness checklist; update after validation cycles.
- `TESTNET_SUMMARY.txt/` - Testnet run summary output; update after testnet runs.
- `tests/` - Python tests for system validation and regression; update alongside backend changes.
- `VALIDATION_REPORT_2026-01-06.md/` - Validation report snapshot; update when new validation is performed.

## Technology Stack Summary

Backend runs on Python (FastAPI + Uvicorn) with SQLAlchemy and PostgreSQL, using Redis for caching and messaging. Frontend is React + TypeScript on Vite with Tailwind CSS, Radix UI, Zustand, Axios, and Recharts. Docker Compose orchestrates local and production-like environments, with testnet workflows validated via the runbooks and test suites.

## Core Framework Stack

Backend: FastAPI with Pydantic settings, SQLAlchemy models, and modules that split scanning, signals, execution, risk, and monitoring. Data: PostgreSQL for persistence, Redis for fast state and events. Frontend: React + React Router with a service layer (`frontend/src/services`) that wraps API calls.

## UI & Interaction Libraries

UI uses Tailwind CSS for styling, Radix UI for accessible primitives, Lucide icons, and Recharts for charts. Components are mostly in `frontend/src/components` and `frontend/src/components/ui`. Keep accessible labels and consistent Tailwind patterns when editing.

## Development Tools Overview

Primary tools: Docker Compose for stack orchestration, Uvicorn for backend dev server, npm/Vite for frontend. Useful scripts live in `backend/scripts`, plus monitoring helpers like `monitor_continuous.py` and `smart_monitor.sh`. Operational flow is captured in `docs/RUNBOOK.md` and `ACOMPANHAMENTO_README.md`. See [Tooling & Productivity Guide](./tooling.md) for details.

## Getting Started Checklist

1. Install dependencies with `npm install`.
2. Explore the CLI by running `npm run dev`.
3. Review [Development Workflow](./development-workflow.md) for day-to-day tasks.

## Next Steps

Align upcoming work with `specs/` and the docs in `docs/`. Add links to external product specs and stakeholder notes as they become available.
