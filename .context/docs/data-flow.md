---
status: filled
generated: 2026-01-12
---

# Data Flow & Integrations

Explain how data enters, moves through, and exits the system, including interactions with external services.

## Module Dependencies
- **frontend\src\services\websocket.ts/** -> `frontend\src\services\api.ts`
- **frontend\src\hooks\useBotStatus.ts/** -> `frontend\src\services\api.ts`
- **frontend\src\main.tsx/** -> `frontend\src\App.tsx`, `frontend\src\index.css`
- **frontend\src\App.tsx/** -> `frontend\src\components\Layout.tsx`, `frontend\src\pages\ConfigBot.tsx`, `frontend\src\pages\Dashboard.tsx`, `frontend\src\pages\Logs.tsx`, `frontend\src\pages\Markets.tsx`, `frontend\src\pages\Metrics.tsx`, `frontend\src\pages\Positions.tsx`, `frontend\src\pages\Supervisor.tsx`
- **frontend\src\App.test.tsx/** -> `frontend\src\App.tsx`
- **frontend\src\pages\Supervisor.tsx/** -> `frontend\src\components\DockerStatus.tsx`, `frontend\src\services\api.ts`
- **frontend\src\pages\Positions.tsx/** -> `frontend\src\components\PositionsTable.tsx`
- **frontend\src\pages\Metrics.tsx/** -> `frontend\src\components\ui\badge.tsx`, `frontend\src\components\ui\button.tsx`, `frontend\src\components\ui\card.tsx`, `frontend\src\components\ui\table.tsx`, `frontend\src\services\api.ts`
- **frontend\src\pages\Markets.tsx/** -> `frontend\src\components\ui\badge.tsx`, `frontend\src\components\ui\button.tsx`, `frontend\src\components\ui\card.tsx`, `frontend\src\components\ui\input.tsx`, `frontend\src\components\ui\table.tsx`, `frontend\src\services\api.ts`
- **frontend\src\pages\Logs.tsx/** -> `frontend\src\components\LogsViewer.tsx`
- **frontend\src\pages\Dashboard.tsx/** -> `frontend\src\components\BotStatus.tsx`, `frontend\src\components\HealthDashboard.tsx`, `frontend\src\components\ManualTrade.tsx`, `frontend\src\components\PerformanceChart.tsx`, `frontend\src\components\PositionsTable.tsx`, `frontend\src\components\RealizedPnlChart.tsx`, `frontend\src\components\SniperOperations.tsx`
- **frontend\src\pages\ConfigBot.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\SniperOperations.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\RealizedPnlChart.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\PositionsTable.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\PerformanceChart.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\ManualTrade.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\LogsViewer.tsx/** -> `frontend\src\services\api.ts`, `frontend\src\services\websocket.ts`
- **frontend\src\components\HealthDashboard.tsx/** -> `frontend\src\components\ErrorsPanel.tsx`, `frontend\src\components\LatencyPanel.tsx`, `frontend\src\components\MarketConditionsPanel.tsx`, `frontend\src\components\SyncStatusPanel.tsx`
- **frontend\src\components\DockerStatus.tsx/** -> `frontend\src\services\api.ts`
- **frontend\src\components\BotStatus.tsx/** -> `frontend\src\services\api.ts`

## Service Layer
- *No service classes detected.*

## High-level Flow

Market data flows from Binance into scanner modules, which filter symbols and feed the signal generator. Signals pass through rules and risk checks before orders are executed. Executions update positions and trade history in PostgreSQL, while Redis and log streams provide near-real-time status for the frontend. The dashboard reads API endpoints for health, metrics, and configuration and can trigger manual actions.

## Internal Movement

Trading logic runs inside `backend/modules`, which coordinate API calls, risk evaluation, and persistence through `backend/api` and `backend/models`. The frontend (`frontend/src`) reads and writes via REST endpoints in `backend/api/routes` and consumes optional WebSocket events for live logs. Monitoring scripts (`monitor_continuous.py`, `smart_monitor.sh`) read logs and DB state, surfacing changes into `logs/` and operational runbooks.

## External Integrations

- Binance Futures API: provides market data and trading endpoints; authenticated with API key/secret; requests are rate-limited and must back off on 429s.
- Telegram Bot API: delivers notifications to operators; authenticated with bot token; failures should degrade to logs.
- PostgreSQL: authoritative storage for trades and configuration; guarded by SQLAlchemy models.
- Redis: cache and pub/sub for status and metrics; used to keep UI responsive.

## Observability & Failure Modes

Observability is centered on API logs in `logs/`, dashboard metrics endpoints, and monitoring scripts that check status. Failures in exchange calls should pause execution and surface alerts; DB outages block persistence and should trigger safe shutdown. Redis outages should degrade gracefully by falling back to DB reads where possible.
