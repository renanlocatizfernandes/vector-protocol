# Contexto do Projeto para LLMs: Crypto Trading Bot (Atualizado 2025-11-11)

Este documento fornece um resumo técnico denso e prático para LLMs trabalharem com o projeto “Crypto Trading Bot”. Inclui visão de arquitetura, mapeamento de módulos/flags, fluxo operacional, endpoints, padrões de contribuição, lacunas conhecidas e recomendações priorizadas. Alinhado com README.md, docs/API_SPEC.md, docs/ARCHITECTURE.md e docs/DEPLOYMENT.md.

--------------------------------------------------------------------------------

## 1) Objetivo e Escopo

- Bot autônomo para negociação em Binance Futures USD‑M (Testnet por padrão).
- Pipeline completo: scan de mercado → geração de sinais → filtros (correlação/mercado) → gestão de risco → execução de ordens → monitoramento ativo (trailing, partials, emergency).
- Painel web (React/TS) para operação, status e ajustes de runtime.
- Notificações Telegram para eventos principais.

--------------------------------------------------------------------------------

## 2) Arquitetura e Componentes

- Backend (Python/FastAPI, assíncrono):
  - `backend/api/`: app FastAPI, rotas REST e (se exposto) WebSocket.
  - `backend/config/settings.py`: Pydantic Settings (carrega `.env`/`.env.docker`).
  - `backend/modules/`: estratégia/execução/risco/monitor (core do bot).
  - `backend/utils/`: binance client, logger, telegram.
- Infra:
  - PostgreSQL (persistência de trades/posições, etc.).
  - Redis (cache/PubSub; reservado para contadores e métricas simples).
  - Docker Compose (orquestração local).
- Frontend (Vite + React + TS):
  - Páginas: Dashboard, Config Bot, Supervisor.
  - Serviços em `frontend/src/services/api.ts`.

Fluxo principal:
1) Scanner → 2) Signal Generator → 3) Correlation/Market Filter → 4) Risk Manager → 5) Order Executor → 6) Position Monitor.

--------------------------------------------------------------------------------

## 3) Módulos do Backend (mapa rápido e flags relevantes)

- market_scanner.py
  - Obtém universo USDT em TRADING, ordena por quoteVolume, coleta klines 1h/4h.
  - Recomendações: parametrizar via settings (SCANNER_TOP_N, SCANNER_MAX_SYMBOLS, MIN_QUOTE_VOLUME_USDT_24H, SCANNER_CONCURRENCY, TESTNET_WHITELIST), filtrar PERPETUAL.

- signal_generator.py
  - Indicadores: EMA50/200, RSI(14), ATR, regime (slope EMA200 + ATR%), momentum; ajustes derivados (funding/OI/taker).
  - Calcula SL/TP e leverage dinâmica; checa R:R mínimo.
  - Estado atual permissivo (testnet): min_score=0 etc.
  - Recomendações: presets testnet/prod via settings (PROD_MIN_SCORE, PROD_VOLUME_THRESHOLD, PROD_RSI_*, REQUIRE_TREND_CONFIRMATION, MIN_MOMENTUM_THRESHOLD_PCT, RR_MIN_*).

- correlation_filter.py
  - Correlação 14d (1d klines), threshold 0.5, cache 1h.
  - Recomendações: settings (CORR_WINDOW_DAYS, MAX_CORRELATION) + seleção “greedy” max‑diversificada.

- market_filter.py
  - Pump/dump (+/−30% em 2h com volume sustentado), gating por regime BTC, fim de semana mais exigente.
  - Recomendações: parametrizar thresholds (PUMP/DUMP_*), REQUIRED_SCORE_SIDEWAYS, considerar dump explícito.

- risk_manager.py
  - Hoje: 3% por trade e 60% total embutidos; ajusta risco por streak de wins/losses; métricas de portfólio.
  - Gap: desalinhado ao settings (RISK_PER_TRADE=0.02, MAX_PORTFOLIO_RISK=0.15).
  - Recomendações: ler do settings, respeitar MAX_POSITIONS, considerar DAILY_MAX_LOSS_PCT e INTRADAY_DRAWDOWN_HARD_STOP_PCT (Redis).

- order_executor.py
  - Execução robusta: LIMIT com re-quote, maker post‑only (manual/auto por spread), fallback MARKET com avgPrice por fills; pós‑abertura ajusta headroom.
  - Flags: USE_POST_ONLY_ENTRIES, AUTO_POST_ONLY_ENTRIES, AUTO_MAKER_SPREAD_BPS, ORDER_TIMEOUT_SEC, HEADROOM_MIN_PCT, REDUCE_STEP_PCT, TAKE_PROFIT_PARTS, USE_MARK_PRICE_FOR_STOPS.

- position_monitor.py
  - Trailing, partials, breakeven, emergency stop, kill switch/circuit breaker, blacklist por símbolo; Telegram.

- autonomous_bot.py
  - Orquestra ciclo periódico; respeita min_score/max_positions/scan_interval.

- utils/binance_client.py
  - Cliente para endpoints USD‑M (exchange_info, tickers, klines, premium index, OI, taker ratios, etc.). Recomenda backoff centralizado.

--------------------------------------------------------------------------------

## 4) Settings (Pydantic) — chaves importantes

Arquivo: `backend/config/settings.py` (somente leitura via `/api/config/` subset)
- Bot/Risco: MAX_POSITIONS, RISK_PER_TRADE, MAX_PORTFOLIO_RISK, DEFAULT_LEVERAGE, DEFAULT_MARGIN_CROSSED, AUTO_ISOLATE_MIN_LEVERAGE.
- Execução/Exits: ENABLE_TRAILING_STOP, TSL_CALLBACK_PCT_MIN/MAX, TSL_ATR_LOOKBACK_INTERVAL, ENABLE_BRACKET_BATCH, USE_MARK_PRICE_FOR_STOPS, ORDER_TIMEOUT_SEC, USE_POST_ONLY_ENTRIES, TAKE_PROFIT_PARTS, AUTO_POST_ONLY_ENTRIES, AUTO_MAKER_SPREAD_BPS, HEADROOM_MIN_PCT, REDUCE_STEP_PCT.
- Derivativos: ENABLE_FUNDING_AWARE, FUNDING_ADVERSE_THRESHOLD, FUNDING_BLOCK_WINDOW_MINUTES, OI_CHANGE_PERIOD/LOOKBACK/MIN_ABS, TAKER_RATIO_LONG_MIN, TAKER_RATIO_SHORT_MAX.
- Scanner: SCANNER_TOP_N, SCANNER_MAX_SYMBOLS, SCANNER_TESTNET_STRICT_WHITELIST.
- Bot: AUTOSTART_BOT, BOT_DRY_RUN, BOT_MIN_SCORE, BOT_MAX_POSITIONS, BOT_SCAN_INTERVAL_MINUTES.
- Sync posições: POSITIONS_AUTO_SYNC_*.
- Virtual balance/Telegram.

Novas chaves sugeridas (documentadas em README/ARCHITECTURE):
- MIN_QUOTE_VOLUME_USDT_24H, SCANNER_CONCURRENCY, TESTNET_WHITELIST.
- PROD_MIN_SCORE, PROD_VOLUME_THRESHOLD, PROD_RSI_OVERSOLD/OVERBOUGHT, REQUIRE_TREND_CONFIRMATION, MIN_MOMENTUM_THRESHOLD_PCT, RR_MIN_TREND/RANGE.
- CORR_WINDOW_DAYS, MAX_CORRELATION.
- PUMP/DUMP_* e REQUIRED_SCORE_SIDEWAYS.
- DAILY_MAX_LOSS_PCT, INTRADAY_DRAWDOWN_HARD_STOP_PCT.

--------------------------------------------------------------------------------

## 5) Endpoints Principais (resumo)

- Saúde/Versão:
  - GET `/health`, GET `/version` (se exposto)
- Config global (somente leitura):
  - GET `/api/config/`
- Trading:
  - POST `/api/trading/execute`
  - POST `/api/trading/execute-batch?min_score=...&max_trades=...&dry_run=...`
  - GET `/api/trading/positions`, POST `/api/trading/positions/close`, POST `/api/trading/positions/close-all`
  - Bot: POST `/api/trading/bot/start?dry_run=...`, POST `/api/trading/bot/stop`, GET `/api/trading/bot/status`, PUT `/api/trading/bot/config?scan_interval_minutes=...&min_score=...&max_positions=...`
- Execução avançada (runtime toggles):
  - GET|PUT `/api/trading/execution/config`, GET `/api/trading/execution/leverage-preview`
- Abertura massiva (admin):
  - POST `/api/trading/execute/force-many`, POST `/api/trading/execute/force-many/async`
- Telegram:
  - POST `/api/trading/test/telegram?text=...`
- System/Observabilidade:
  - GET `/api/system/logs?component=<prefix>&tail=<n>`
  - User Stream: `POST /api/system/userstream/{start|stop}`, `GET /api/system/userstream/status`
  - Supervisor (quando exposto): `GET /api/system/supervisor/status`, `POST /api/system/supervisor/{enable|disable|toggle}`

Detalhes completos em `docs/API_SPEC.md`.

--------------------------------------------------------------------------------

## 6) Fluxo de Decisão (resumo operacional)

1) Scanner seleciona símbolos (liquidez/volume); coleta klines 1h/4h.
2) Signal Generator calcula indicadores, momentum/regime, DER-aware; valida R:R; define SL/TP/leverage; produz score.
3) Filtros:
   - Correlação: remove correlacionados acima do threshold.
   - Mercado: bloqueia pump/dump, exige score mais alto em fim de semana/sideways; gating por regime BTC.
4) Risco: avalia risco por trade (pct) e total (portfólio); pode ajustar risco via streak.
5) Execução: decide maker/taker; re-quote LIMIT; fallback MARKET; pós‑abertura checa headroom e reduz se necessário.
6) Monitor: trailing/partials/breakeven, emergency/kill-switch e notificações.

--------------------------------------------------------------------------------

## 7) Observabilidade, Logs e KPIs

- Logs em `./logs/*.log` (ex.: `api_YYYYMMDD.log`).
- KPIs desejáveis (ver README/ARCHITECTURE para sugestões):
  - Scanner: cobertura, latências, rate-limit.
  - Sinais: aprovações por filtro, distribuição de scores, R:R médio aceito.
  - Execução: tentativas LIMIT, maker/taker ratio, slippage estimado, avg tempo por ordem.
  - Monitor: eventos trailing/partials/ES/SL, tempo médio em trade.
  - Risco: exposição total/pico, bloqueios por headroom/daily cap.

--------------------------------------------------------------------------------

## 8) Gaps e Recomendações (prioridades)

1) Alinhar RiskManager ao settings (RISK_PER_TRADE/MAX_PORTFOLIO_RISK) e MAX_POSITIONS.
2) Preset PROD/TESTNET no SignalGenerator (thresholds mais realistas em produção).
3) Parametrizar MarketScanner via settings; filtrar PERPETUAL; semáforo de concorrência; liquidez mínima.
4) Expor thresholds em Market/Correlation Filter via settings; seleção max‑diversificada (greedy).
5) TSL adaptativo por ATR (respect a TSL_* min/max) e RR mínimo por regime configurável.
6) Observabilidade: métricas de pipeline (scanner→sinais→filtros→execução→monitor).

Todas as recomendações estão documentadas e justificadas em README.md e docs/ARCHITECTURE.md.

--------------------------------------------------------------------------------

## 9) Padrões para LLMs (edição e PRs)

- Use paths exatos e mantenha imports relativos já existentes.
- Centralize números “mágicos” em `settings.py` quando fizer sentido.
- Ao editar arquivos:
  - Para mudanças localizadas, prefira replace_in_file com blocos SEARCH/REPLACE mínimos e exatos.
  - Para substituições grandes ou criação de novos arquivos, use write_to_file com conteúdo completo.
- Respeite estilo:
  - Python: PEP8, tipagem, logging claro.
  - TS/React: ESLint/Prettier, componentes funcionais, services finos em `api.ts`.
- Atualize documentação relacionada e CHANGELOG a cada alteração relevante (modelo em CONTRIBUTING.md).
- Testes rápidos:
  - Backend: `cd backend && pytest -q`
  - Frontend: `cd frontend && npm test` (quando existir)
  - Dev local: `uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload`
  - Docker compose: `docker compose up -d --build`

--------------------------------------------------------------------------------

## 10) Segurança e Operação

- `BINANCE_TESTNET=True` por padrão; nunca comitar chaves reais.
- Avaliar autenticação (API key/JWT) para exposição pública.
- Supervisor (`supervisor.py`) recomendado para resiliência; UI não depende dele, apenas reflete o estado.

--------------------------------------------------------------------------------

## 11) Referências

- README.md (principal)
- docs/API_SPEC.md (contratos)
- docs/ARCHITECTURE.md (análise por módulo)
- docs/DEPLOYMENT.md (runbook/flags)
- docs/FRONTEND_PLAN.md (UI/serviços/roadmap)
- CHANGELOG.md (histórico)
- CONTRIBUTING.md (processo de contribuição)
- MCP_RECOMMENDATIONS.md (ferramentas MCP úteis no repo)
