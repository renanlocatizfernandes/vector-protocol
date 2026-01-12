---
status: filled
generated: 2026-01-12
---

# Devops Specialist Agent Playbook

## Mission
Maintain deployment, Docker/K8s, and monitoring; engage for infra or pipeline changes.

## Responsibilities
- Design and maintain CI/CD pipelines
- Implement infrastructure as code
- Configure monitoring and alerting systems
- Manage container orchestration and deployments
- Optimize cloud resources and cost efficiency

## Best Practices
- Automate everything that can be automated
- Implement infrastructure as code for reproducibility
- Monitor system health proactively
- Design for failure and implement proper fallbacks
- Keep security and compliance in every deployment

## Key Project Resources
- Documentation index: [docs/README.md](../docs/README.md)
- Agent handbook: [agents/README.md](./README.md)
- Agent knowledge base: [AGENTS.md](../../AGENTS.md)
- Contributor guide: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Repository Starting Points
- `backend/` - FastAPI API, trading modules, DB models, scripts; edit for backend logic.
- `docs/` - Canonical documentation and runbooks; update when behavior/process changes.
- `frontend/` - React/Vite dashboard and UI components; edit for UX and API usage.
- `kubernetes/` - Deployment manifests; edit for cluster ops changes.
- `logs/` - Runtime logs for debugging; typically read-only.
- `otrading/` - Research notes and token lists; update for strategy research.
- `specs/` - Feature and system specs; add specs before changes.
- `tests/` - Automated tests and validation suites; update alongside changes.

## Key Files
**Entry Points:**
- [`frontend\src\main.tsx`](frontend\src\main.tsx)

**Pattern Implementations:**
- Service Layer: [`WebSocketService`](frontend\src\services\websocket.ts)
- Observer: [`RedisLogHandler`](backend\utils\logger.py)

## Architecture Context

### Config
Configuration and constants
- **Directories**: `frontend`, `backend\modules`, `backend\config`, `backend\modules\bot`
- **Symbols**: 5 total
- **Key exports**: [`ConfigManager`](backend\modules\config_manager.py#L14), [`Settings`](backend\config\settings.py#L5), [`get_settings`](backend\config\settings.py#L359), [`reload_settings`](backend\config\settings.py#L363), [`BotConfig`](backend\modules\bot\bot_config.py#L3)

### Services
Business logic and orchestration
- **Directories**: `frontend\src\services`
- **Symbols**: 78 total
- **Key exports**: [`Health`](frontend\src\services\api.ts#L48), [`BotStatus`](frontend\src\services\api.ts#L54), [`DailyStats`](frontend\src\services\api.ts#L64), [`RealizedDailyPoint`](frontend\src\services\api.ts#L98), [`RealizedDailyResponse`](frontend\src\services\api.ts#L106), [`DashboardData`](frontend\src\services\api.ts#L111), [`ConfigResponse`](frontend\src\services\api.ts#L155), [`getHealth`](frontend\src\services\api.ts#L168), [`getVersion`](frontend\src\services\api.ts#L172), [`getBotStatus`](frontend\src\services\api.ts#L178), [`startBot`](frontend\src\services\api.ts#L183), [`stopBot`](frontend\src\services\api.ts#L190), [`updateBotConfig`](frontend\src\services\api.ts#L195), [`getDailyStats`](frontend\src\services\api.ts#L207), [`getRealizedDailyStats`](frontend\src\services\api.ts#L212), [`getPositionsDashboard`](frontend\src\services\api.ts#L218), [`syncPositions`](frontend\src\services\api.ts#L228), [`closePositionExchange`](frontend\src\services\api.ts#L234), [`setPositionStopLoss`](frontend\src\services\api.ts#L239), [`setPositionTakeProfit`](frontend\src\services\api.ts#L244), [`setPositionBreakeven`](frontend\src\services\api.ts#L249), [`setPositionTrailingStop`](frontend\src\services\api.ts#L254), [`cancelOpenOrders`](frontend\src\services\api.ts#L259), [`getConfig`](frontend\src\services\api.ts#L265), [`testTelegram`](frontend\src\services\api.ts#L271), [`getSignals`](frontend\src\services\api.ts#L277), [`backtestQuick`](frontend\src\services\api.ts#L283), [`backtestRun`](frontend\src\services\api.ts#L288), [`getComposeStatus`](frontend\src\services\api.ts#L299), [`getLogs`](frontend\src\services\api.ts#L304), [`SupervisorStatus`](frontend\src\services\api.ts#L310), [`getSupervisorStatus`](frontend\src\services\api.ts#L318), [`supervisorEnable`](frontend\src\services\api.ts#L323), [`supervisorDisable`](frontend\src\services\api.ts#L328), [`supervisorToggle`](frontend\src\services\api.ts#L333), [`SupervisorHealth`](frontend\src\services\api.ts#L338), [`getSupervisorHealth`](frontend\src\services\api.ts#L348), [`BotMetrics`](frontend\src\services\api.ts#L354), [`ExecutionMetrics`](frontend\src\services\api.ts#L397), [`MonitoringMetrics`](frontend\src\services\api.ts#L422), [`RiskMetrics`](frontend\src\services\api.ts#L444), [`getBotMetrics`](frontend\src\services\api.ts#L465), [`getExecutionMetrics`](frontend\src\services\api.ts#L470), [`getMonitoringMetrics`](frontend\src\services\api.ts#L475), [`getRiskMetrics`](frontend\src\services\api.ts#L480), [`PnlBySymbol`](frontend\src\services\api.ts#L485), [`getPnlBySymbol`](frontend\src\services\api.ts#L492), [`MarketTicker`](frontend\src\services\api.ts#L497), [`MarketTickersResponse`](frontend\src\services\api.ts#L504), [`getMarketTickers`](frontend\src\services\api.ts#L509), [`FearGreedPoint`](frontend\src\services\api.ts#L514), [`FearGreedResponse`](frontend\src\services\api.ts#L520), [`getFearGreed`](frontend\src\services\api.ts#L526), [`HistoryAnalysis`](frontend\src\services\api.ts#L531), [`getHistoryAnalysis`](frontend\src\services\api.ts#L547), [`SniperTrade`](frontend\src\services\api.ts#L553), [`SniperStats`](frontend\src\services\api.ts#L568), [`getSniperTrades`](frontend\src\services\api.ts#L575), [`CumulativePnlPoint`](frontend\src\services\api.ts#L585), [`CumulativePnlResponse`](frontend\src\services\api.ts#L594), [`getCumulativePnl`](frontend\src\services\api.ts#L598), [`ErrorLog`](frontend\src\services\api.ts#L604), [`ErrorsResponse`](frontend\src\services\api.ts#L612), [`getRecentErrors`](frontend\src\services\api.ts#L619), [`ErrorRateResponse`](frontend\src\services\api.ts#L627), [`getErrorRate`](frontend\src\services\api.ts#L633), [`ErrorSummary`](frontend\src\services\api.ts#L640), [`getErrorSummary`](frontend\src\services\api.ts#L646), [`LatencyStats`](frontend\src\services\api.ts#L652), [`getLatencyStats`](frontend\src\services\api.ts#L664), [`SyncStatus`](frontend\src\services\api.ts#L670), [`getSyncStatus`](frontend\src\services\api.ts#L687), [`MarketConditions`](frontend\src\services\api.ts#L693), [`getMarketConditions`](frontend\src\services\api.ts#L713), [`toMinutes`](frontend\src\services\api.ts#L719), [`toSeconds`](frontend\src\services\api.ts#L723)

### Utils
Shared utilities and helpers
- **Directories**: `frontend\src\lib`, `backend\utils`
- **Symbols**: 11 total
- **Key exports**: [`cn`](frontend\src\lib\utils.ts#L4), [`TelegramNotifier`](backend\utils\telegram_notifier.py#L10), [`RedisClient`](backend\utils\redis_client.py#L7), [`JSONFormatter`](backend\utils\logger.py#L13), [`RedisLogHandler`](backend\utils\logger.py#L28), [`setup_logger`](backend\utils\logger.py#L78), [`round_step_size`](backend\utils\helpers.py#L3), [`format_quantity`](backend\utils\helpers.py#L13), [`DataValidationError`](backend\utils\binance_client.py#L20), [`DataValidator`](backend\utils\binance_client.py#L28), [`BinanceClientManager`](backend\utils\binance_client.py#L290)

### Components
UI components and views
- **Directories**: `frontend\src\pages`, `frontend\src\components`, `frontend\src\components\ui`
- **Symbols**: 18 total
- **Key exports**: [`InputProps`](frontend\src\components\ui\input.tsx#L4), [`ButtonProps`](frontend\src\components\ui\button.tsx#L26), [`BadgeProps`](frontend\src\components\ui\badge.tsx#L19)

### Repositories
Data access and persistence
- **Directories**: `backend`, `backend\tests`, `backend\scripts`, `backend\modules`
- **Symbols**: 17 total
- **Key exports**: [`migrate`](backend\migrate_database.py#L21), [`mock_redis`](backend\tests\test_risk_manager_persistence.py#L8), [`mock_settings`](backend\tests\test_risk_manager_persistence.py#L14), [`risk_manager`](backend\tests\test_risk_manager_persistence.py#L29), [`test_rollover_daily_initialization`](backend\tests\test_risk_manager_persistence.py#L39), [`test_rollover_daily_recovery`](backend\tests\test_risk_manager_persistence.py#L55), [`test_update_intraday_extrema_persistence`](backend\tests\test_risk_manager_persistence.py#L72), [`test_hard_stop_with_recovered_peak`](backend\tests\test_risk_manager_persistence.py#L94), [`print_separator`](backend\scripts\migrate_to_database_config.py#L37), [`check_prerequisites`](backend\scripts\migrate_to_database_config.py#L42), [`show_current_status`](backend\scripts\migrate_to_database_config.py#L79), [`confirm_migration`](backend\scripts\migrate_to_database_config.py#L112), [`migrate_configurations`](backend\scripts\migrate_to_database_config.py#L144), [`show_post_migration_instructions`](backend\scripts\migrate_to_database_config.py#L208), [`main`](backend\scripts\migrate_to_database_config.py#L240), [`Configuration`](backend\modules\config_database.py#L12), [`ConfigurationHistory`](backend\modules\config_database.py#L42)

### Controllers
Request handling and routing
- **Directories**: `backend\utils`, `backend\tests`, `backend\api`, `backend\api\routes`, `backend\api\models`
- **Symbols**: 140 total
- **Key exports**: [`cmd_status`](backend\utils\telegram_bot_handler.py#L10), [`cmd_portfolio`](backend\utils\telegram_bot_handler.py#L42), [`start_telegram_bot`](backend\utils\telegram_bot_handler.py#L66), [`test_supervisor_status`](backend\tests\test_system_routes.py#L7), [`test_logs_endpoint_handles_missing_component`](backend\tests\test_system_routes.py#L21), [`ConnectionManager`](backend\api\websocket.py#L13), [`websocket_endpoint`](backend\api\websocket.py#L51), [`redis_event_listener`](backend\api\websocket.py#L78), [`BacktestRequest`](backend\api\backtesting.py#L15), [`BacktestResponse`](backend\api\backtesting.py#L24), [`run_backtest`](backend\api\backtesting.py#L32), [`quick_backtest`](backend\api\backtesting.py#L116), [`last_month_backtest`](backend\api\backtesting.py#L161), [`get_backtest_templates`](backend\api\backtesting.py#L199), [`ApiKeyMiddleware`](backend\api\app.py#L34), [`lifespan`](backend\api\app.py#L52), [`root`](backend\api\app.py#L285), [`health`](backend\api\app.py#L311), [`version`](backend\api\app.py#L377), [`ExecuteTradeRequest`](backend\api\routes\trading.py#L78), [`execute_trade`](backend\api\routes\trading.py#L85), [`execute_batch_trades`](backend\api\routes\trading.py#L125), [`get_open_positions`](backend\api\routes\trading.py#L177), [`start_position_monitoring`](backend\api\routes\trading.py#L194), [`stop_position_monitoring`](backend\api\routes\trading.py#L205), [`get_monitoring_status`](backend\api\routes\trading.py#L216), [`start_autonomous_bot`](backend\api\routes\trading.py#L226), [`stop_autonomous_bot`](backend\api\routes\trading.py#L273), [`get_bot_status`](backend\api\routes\trading.py#L299), [`get_bot_metrics`](backend\api\routes\trading.py#L314), [`get_execution_metrics`](backend\api\routes\trading.py#L325), [`get_pnl_by_symbol`](backend\api\routes\trading.py#L336), [`get_monitoring_metrics`](backend\api\routes\trading.py#L370), [`get_history_analysis`](backend\api\routes\trading.py#L380), [`get_risk_metrics`](backend\api\routes\trading.py#L389), [`get_execution_config`](backend\api\routes\trading.py#L403), [`update_execution_config`](backend\api\routes\trading.py#L428), [`leverage_preview`](backend\api\routes\trading.py#L492), [`update_bot_config`](backend\api\routes\trading.py#L512), [`test_telegram`](backend\api\routes\trading.py#L547), [`close_position_manual`](backend\api\routes\trading.py#L559), [`close_all_positions`](backend\api\routes\trading.py#L641), [`get_daily_stats`](backend\api\routes\trading.py#L728), [`get_cumulative_pnl`](backend\api\routes\trading.py#L893), [`close_position_exchange`](backend\api\routes\trading.py#L979), [`set_position_stop_loss`](backend\api\routes\trading.py#L1031), [`set_position_take_profit`](backend\api\routes\trading.py#L1067), [`set_position_breakeven`](backend\api\routes\trading.py#L1103), [`set_position_trailing_stop`](backend\api\routes\trading.py#L1151), [`get_realized_daily`](backend\api\routes\trading.py#L1183), [`send_daily_report_manual`](backend\api\routes\trading.py#L1249), [`force_open_many`](backend\api\routes\trading.py#L1262), [`force_open_many_async`](backend\api\routes\trading.py#L1485), [`positions_add_strategic`](backend\api\routes\trading.py#L1502), [`positions_add_strategic_async`](backend\api\routes\trading.py#L1514), [`execute_sniper`](backend\api\routes\trading.py#L1526), [`ManualTradeRequest`](backend\api\routes\trading.py#L1689), [`execute_manual_trade`](backend\api\routes\trading.py#L1699), [`get_trade_history`](backend\api\routes\trading.py#L1789), [`get_sniper_trades`](backend\api\routes\trading.py#L1818), [`get_logs`](backend\api\routes\system.py#L56), [`compose_status`](backend\api\routes\system.py#L79), [`supervisor_status`](backend\api\routes\system.py#L120), [`supervisor_health`](backend\api\routes\system.py#L148), [`supervisor_enable`](backend\api\routes\system.py#L155), [`supervisor_disable`](backend\api\routes\system.py#L165), [`supervisor_toggle`](backend\api\routes\system.py#L175), [`userstream_status`](backend\api\routes\system.py#L190), [`userstream_start`](backend\api\routes\system.py#L199), [`userstream_stop`](backend\api\routes\system.py#L218), [`get_recent_errors`](backend\api\routes\system.py#L231), [`get_error_rate`](backend\api\routes\system.py#L261), [`get_error_summary`](backend\api\routes\system.py#L284), [`get_latency_stats`](backend\api\routes\system.py#L299), [`get_market_conditions`](backend\api\routes\system.py#L342), [`get_metrics_dashboard`](backend\api\routes\system.py#L360), [`get_latency_dashboard`](backend\api\routes\system.py#L382), [`get_trade_dashboard`](backend\api\routes\system.py#L397), [`get_resource_dashboard`](backend\api\routes\system.py#L412), [`TradingRuleCreate`](backend\api\routes\rules.py#L23), [`TradingRuleUpdate`](backend\api\routes\rules.py#L47), [`TradingRuleResponse`](backend\api\routes\rules.py#L57), [`RuleTypeSchema`](backend\api\routes\rules.py#L74), [`list_rules`](backend\api\routes\rules.py#L87), [`create_rule`](backend\api\routes\rules.py#L121), [`get_rule`](backend\api\routes\rules.py#L174), [`update_rule`](backend\api\routes\rules.py#L195), [`delete_rule`](backend\api\routes\rules.py#L252), [`toggle_rule`](backend\api\routes\rules.py#L287), [`get_rule_type_schemas`](backend\api\routes\rules.py#L322), [`get_positions`](backend\api\routes\positions.py#L14), [`get_trades`](backend\api\routes\positions.py#L20), [`get_open_trades`](backend\api\routes\positions.py#L26), [`get_closed_trades`](backend\api\routes\positions.py#L32), [`get_dashboard`](backend\api\routes\positions.py#L38), [`get_positions_margins`](backend\api\routes\positions.py#L194), [`reconcile_positions`](backend\api\routes\positions.py#L243), [`get_sync_status`](backend\api\routes\positions.py#L343), [`sync_positions`](backend\api\routes\positions.py#L417), [`get_open_orders`](backend\api\routes\positions.py#L449), [`cancel_all_open_orders`](backend\api\routes\positions.py#L478), [`diagnostics_exchange`](backend\api\routes\positions.py#L513), [`get_balance`](backend\api\routes\market.py#L22), [`get_price`](backend\api\routes\market.py#L29), [`scan_market`](backend\api\routes\market.py#L36), [`analyze_symbol`](backend\api\routes\market.py#L48), [`get_signals`](backend\api\routes\market.py#L57), [`generate_signal`](backend\api\routes\market.py#L96), [`get_derivatives`](backend\api\routes\market.py#L118), [`get_top_100`](backend\api\routes\market.py#L140), [`get_tickers`](backend\api\routes\market.py#L147), [`get_fear_greed`](backend\api\routes\market.py#L194), [`get_klines`](backend\api\routes\market.py#L241), [`get_db`](backend\api\routes\database_config.py#L19), [`ConfigValue`](backend\api\routes\database_config.py#L28), [`ConfigUpdateResponse`](backend\api\routes\database_config.py#L35), [`BatchUpdateResponse`](backend\api\routes\database_config.py#L44), [`config_health_check`](backend\api\routes\database_config.py#L52), [`get_all_configs`](backend\api\routes\database_config.py#L92), [`get_config_categories`](backend\api\routes\database_config.py#L120), [`get_configs_by_category`](backend\api\routes\database_config.py#L147), [`get_config`](backend\api\routes\database_config.py#L176), [`update_config`](backend\api\routes\database_config.py#L202), [`reload_from_env`](backend\api\routes\database_config.py#L254), [`reset_config`](backend\api\routes\database_config.py#L287), [`get_config_history`](backend\api\routes\database_config.py#L328), [`batch_update_configs`](backend\api\routes\database_config.py#L356), [`invalidate_cache`](backend\api\routes\database_config.py#L406), [`ConfigUpdate`](backend\api\routes\config.py#L11), [`get_config`](backend\api\routes\config.py#L21), [`update_config`](backend\api\routes\config.py#L35), [`TradingRule`](backend\api\models\trading_rules.py#L22), [`Trade`](backend\api\models\trades.py#L21)

### Generators
Content and object generation
- **Directories**: `backend\modules`
- **Symbols**: 1 total
- **Key exports**: [`SignalGenerator`](backend\modules\signal_generator.py#L30)

### Models
Data structures and domain objects
- **Directories**: `backend\models`
- **Symbols**: 1 total
- **Key exports**: [`get_db`](backend\models\database.py#L12)
## Key Symbols for This Agent
- [`TelegramNotifier`](backend\utils\telegram_notifier.py#L10) (class)
- [`RedisClient`](backend\utils\redis_client.py#L7) (class)
- [`JSONFormatter`](backend\utils\logger.py#L13) (class)
- [`RedisLogHandler`](backend\utils\logger.py#L28) (class)
- [`DataValidationError`](backend\utils\binance_client.py#L20) (class)
- [`HistoryAnalysis`](frontend\src\services\api.ts#L531) (interface)
- [`SniperTrade`](frontend\src\services\api.ts#L553) (interface)
- [`SniperStats`](frontend\src\services\api.ts#L568) (interface)
- [`CumulativePnlPoint`](frontend\src\services\api.ts#L585) (interface)
- [`CumulativePnlResponse`](frontend\src\services\api.ts#L594) (interface)

## Documentation Touchpoints
- [Documentation Index](../docs/README.md)
- [Project Overview](../docs/project-overview.md)
- [Architecture Notes](../docs/architecture.md)
- [Development Workflow](../docs/development-workflow.md)
- [Testing Strategy](../docs/testing-strategy.md)
- [Glossary & Domain Concepts](../docs/glossary.md)
- [Data Flow & Integrations](../docs/data-flow.md)
- [Security & Compliance Notes](../docs/security.md)
- [Tooling & Productivity Guide](../docs/tooling.md)

## Collaboration Checklist

1. Confirm assumptions with issue reporters or maintainers.
2. Review open pull requests affecting this area.
3. Update the relevant doc section listed above.
4. Capture learnings back in [docs/README.md](../docs/README.md).

## Hand-off Notes

Summarize outcomes, remaining risks, and suggested follow-up actions after the agent completes its work.
