# Crypto Trading Bot (Atualizado 2025-11-11)

Um bot de negociação de criptomoedas autônomo e personalizável, projetado para automatizar estratégias e otimizar retornos no mercado de criptoativos (Binance Futures USD‑M | Testnet por padrão).

Este README foi revisado com uma análise técnica detalhada do projeto e alinhado com os arquivos em `docs/`. Itens de “Recomendações” descrevem melhorias propostas de configuração e arquitetura ainda não implementadas no código.

## Sumário

- Visão geral e destaques
- Estado atual vs. recomendações
- Arquitetura e componentes
- Endpoints principais (resumo)
- Configurações (Settings)
- Instalação e execução
- Operação rápida (exemplos)
- Observabilidade e Supervisor
- Segurança
- Roadmap (próximas etapas)
- Documentação relacionada

## Destaques recentes (P1, P2 e P3)

- P1 Execução
  - LIMIT com buffer e re‑quote inteligente (até 3 tentativas).
  - Maker post‑only (GTX) opcional e automático por spread:
    - USE_POST_ONLY_ENTRIES (força maker) e/ou AUTO_POST_ONLY_ENTRIES + AUTO_MAKER_SPREAD_BPS (decide maker/taker em runtime).
  - Timeout configurável para LIMIT antes de fallback MARKET (ORDER_TIMEOUT_SEC).
  - Fallback MARKET com preço médio correto (consulta fills e calcula avgPrice real).

- P1 Risco
  - Headroom até liquidação: após abrir posição, checa liquidationPrice (futures_position_information) e, se < HEADROOM_MIN_PCT, reduz posição em etapas (REDUCE_STEP_PCT) via reduceOnly até atingir o headroom mínimo (best‑effort).

- P2 Custos
  - Utilitário para consultar taxas maker/taker por símbolo (futures_commission_rate) — base para decisões futuras de execução custo‑ótima.

- P3 Estratégia
  - Sinal com “regime” simples (trend/range) influenciando R:R mínimo aceito (1.0 vs 1.5) e score bônus.
  - Leverage dinâmica (3x–20x) baseada em volume, RSI e R:R (refinada pela política de execução/riscos).

- Notificações Telegram
  - Mensagens ricas em HTML (trade aberto/fechado, TPs, SL, emergency stop, ajuste de headroom).
  - Envio assíncrono com retries e backoff.

## Estado atual (diagnóstico) vs. Recomendações

Análise baseada nos módulos e configurações existentes:

- Market Scanner (`backend/modules/market_scanner.py`)
  - Estado: seleciona top 200 por volume, corta para ~60 e faz whitelist em testnet. Não consome `Settings.SCANNER_TOP_N/SCANNER_MAX_SYMBOLS`.
  - Recomendações:
    - Ler `SCANNER_TOP_N`, `SCANNER_MAX_SYMBOLS`, `SCANNER_TESTNET_STRICT_WHITELIST` de `settings`.
    - Filtrar apenas contratos `PERPETUAL` e status `TRADING`.
    - Parâmetro de liquidez mínima por `MIN_QUOTE_VOLUME_USDT_24H` (novo em `settings`).
    - Concorrência limitada (Semaphore) para klines (evita rate limit).

- Signal Generator (`backend/modules/signal_generator.py`)
  - Estado: parâmetros muito permissivos (min_score=0, volume_threshold=0.0, RSI 80/20 para testnet), confirmação de tendência desativada.
  - Recomendações:
    - Preset PROD/TESTNET via `settings` (prod: min_score 70, volume_threshold 0.5, RSI 30/70, confirmação multi‑TF, momentum mínimo; testnet mais permissivo porém não trivial).
    - Tornar R:R mínimo parametrizável (ex.: `RR_MIN_TREND`, `RR_MIN_RANGE` em `settings`).

- Correlation Filter (`backend/modules/correlation_filter.py`)
  - Estado: janela 14d, threshold 0.5, cache 1h.
  - Recomendações:
    - Expor em `settings` (`CORR_WINDOW_DAYS`, `MAX_CORRELATION`) e adotar seleção “greedy” max‑diversificada.

- Market Filter (`backend/modules/market_filter.py`)
  - Estado: pump&dump +30%/2h com volume sustentado, gating por regime BTC e ajuste em fins de semana.
  - Recomendações:
    - Parametrizar thresholds (pump/dump/timeframe/volume) em `settings` e exigir score maior em regime lateral.

- Risk Manager (`backend/modules/risk_manager.py`)
  - Estado: embutidos 3% por trade e 60% total (não alinhado ao `settings` que define 2%/15%).
  - Recomendações:
    - Ler `RISK_PER_TRADE` e `MAX_PORTFOLIO_RISK` de `settings`.
    - Opcional: `DAILY_MAX_LOSS_PCT`, `INTRADAY_DRAWDOWN_HARD_STOP_PCT` (novos em `settings`) e uso de Redis para contadores diários.

Nota: as recomendações acima são propostas de documentação/arquitetura. O código ainda não foi alterado para refletir esses pontos.

## Arquitetura e Componentes

- Backend: Python (FastAPI, SQLAlchemy, httpx, python‑binance)
- Frontend: React, TypeScript, Vite
- Banco de Dados: PostgreSQL
- Outros: Redis, Docker, Docker Compose

Estrutura geral:
```
.
├── backend/
│   ├── api/                  # Endpoints (FastAPI), WebSocket (se exposto), modelos
│   ├── config/               # Pydantic settings (variáveis de ambiente)
│   ├── models/               # Modelos/DB
│   ├── modules/              # Core: sinais, execução, risco, monitor etc.
│   └── utils/                # Binance client, logger, Telegram
├── database/                 # Migrações / seeds
├── docs/                     # Documentação (API, Arquitetura, Deploy, Frontend)
├── frontend/                 # App Web (Vite + React + TS)
├── logs/                     # Logs do sistema
├── docker-compose.yml
└── README.md
```

Detalhes completos em `docs/ARCHITECTURE.md`.

## Endpoints principais (resumo)

- Saúde: `GET /health`
- Versão: `GET /version` (se exposto)
- Config global (somente leitura): `GET /api/config/`
- Trading:
  - Execução: `POST /api/trading/execute`, `POST /api/trading/execute-batch`
  - Posições: `GET /api/trading/positions`, `POST /api/trading/positions/close`, `POST /api/trading/positions/close-all`
  - Bot: `POST /api/trading/bot/start`, `POST /api/trading/bot/stop`, `GET /api/trading/bot/status`, `PUT /api/trading/bot/config`
  - Execução (runtime toggles): `GET|PUT /api/trading/execution/config`, `GET /api/trading/execution/leverage-preview`
  - Forçar entradas (admin): `POST /api/trading/execute/force-many`, `POST /api/trading/execute/force-many/async`
  - Telegram teste: `POST /api/trading/test/telegram?text=...`
- System/Observabilidade:
  - Logs: `GET /api/system/logs?component=<prefix>&tail=<n>`
  - User Stream (quando habilitado): `POST /api/system/userstream/{start|stop}`, `GET /api/system/userstream/status`
  - Supervisor (quando exposto): `GET /api/system/supervisor/status`, `POST /api/system/supervisor/{enable|disable|toggle}`

Especificação detalhada em `docs/API_SPEC.md`.

## Configurações (Settings)

Arquivo: `backend/config/settings.py` (Pydantic Settings). Exemplos relevantes:

- Binance/Testnet:
  - `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `BINANCE_TESTNET`
- Bot e Risco:
  - `MAX_POSITIONS`, `RISK_PER_TRADE`, `MAX_PORTFOLIO_RISK`, `DEFAULT_LEVERAGE`
  - `DEFAULT_MARGIN_CROSSED`, `AUTO_ISOLATE_MIN_LEVERAGE`, `ALLOW_MARGIN_MODE_OVERRIDE`
- Execução/Exits:
  - `ENABLE_TRAILING_STOP`, `TSL_CALLBACK_PCT_MIN/MAX`, `TSL_ATR_LOOKBACK_INTERVAL`
  - `ENABLE_BRACKET_BATCH`, `USE_MARK_PRICE_FOR_STOPS`, `ORDER_TIMEOUT_SEC`
  - `USE_POST_ONLY_ENTRIES`, `TAKE_PROFIT_PARTS`, `AUTO_POST_ONLY_ENTRIES`, `AUTO_MAKER_SPREAD_BPS`
  - `HEADROOM_MIN_PCT`, `REDUCE_STEP_PCT`
- Derivatives-aware:
  - `ENABLE_FUNDING_AWARE`, `FUNDING_ADVERSE_THRESHOLD`, `FUNDING_BLOCK_WINDOW_MINUTES`
  - `OI_CHANGE_PERIOD`, `OI_CHANGE_LOOKBACK`, `OI_CHANGE_MIN_ABS`
  - `TAKER_RATIO_LONG_MIN`, `TAKER_RATIO_SHORT_MAX`
- Scanner:
  - `SCANNER_TOP_N`, `SCANNER_MAX_SYMBOLS`, `SCANNER_TESTNET_STRICT_WHITELIST`
- Auto-start/Bot:
  - `AUTOSTART_BOT`, `BOT_DRY_RUN`, `BOT_MIN_SCORE`, `BOT_MAX_POSITIONS`, `BOT_SCAN_INTERVAL_MINUTES`
- Sync de posições:
  - `POSITIONS_AUTO_SYNC_ENABLED`, `POSITIONS_AUTO_SYNC_MINUTES`, `POSITIONS_AUTO_SYNC_STRICT`
- Virtual balance:
  - `VIRTUAL_BALANCE_ENABLED`, `VIRTUAL_BALANCE_USDT`
- Telegram:
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ENABLED`

Observação: recomenda-se centralizar thresholds do Scanner, Filtros e Sinais em `settings` (ver seção “Recomendações”).

## Instalação e Execução

### 1) Variáveis de Ambiente

Copie `.env.example` para `.env` (ou use `.env.docker` em Docker):

```bash
cp .env.example .env
```

Campos principais:
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `BINANCE_TESTNET=true`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ENABLED`
- `DATABASE_URL` / Postgres e Redis (conforme docker-compose)

### 2) Docker Compose (recomendado para backend)

```bash
docker compose up --build -d
```

- API: http://localhost:8000
- Logs: ./logs

Reiniciar API:
```bash
docker compose restart api
```

### 3) Frontend (dev)

```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173 (proxy → :8000 para /api, /health, /version, /docs)
- Opcional: `VITE_API_BASE` em `frontend/.env` para apontar para outra URL de API.

### 4) Desenvolvimento Local (sem Docker)

Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Operação rápida (exemplos)

- Ativar maker (post‑only) e TP ladder:
```bash
curl -sS -X PUT "http://localhost:8000/api/trading/execution/config?use_post_only_entries=true&take_profit_parts=0.5,0.3,0.2" | jq .
```

- Auto maker por spread e headroom mínimo:
```bash
curl -sS -X PUT "http://localhost:8000/api/trading/execution/config?auto_post_only_entries=true&auto_maker_spread_bps=3&headroom_min_pct=35&reduce_step_pct=10" | jq .
```

- Executar um trade (real, testnet):
```bash
curl -sS -X POST "http://localhost:8000/api/trading/execute" \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","risk_profile":"moderate","dry_run":false}' | jq .
```

- Forçar muitas entradas (dinâmico por padrão):
```bash
curl -sS -X POST "http://localhost:8000/api/trading/execute/force-many?count=10" | jq .
```

- Teste do Telegram:
```bash
curl -sS -X POST "http://localhost:8000/api/trading/test/telegram?text=Bot%20operacional" | jq .
```

## Observabilidade e Supervisor

- Health: `GET /health` e `GET /version` (quando exposto).
- Logs: `GET /api/system/logs?component=<prefix>&tail=<n>`.
- Supervisor (quando exposto): `GET /api/system/supervisor/status`, `POST /api/system/supervisor/{enable|disable|toggle}`.
- Painel Web inclui páginas: Dashboard, Config Bot, Supervisor. Ver `docs/FRONTEND_PLAN.md`.

## Segurança

- Nunca comite chaves reais.
- Use `BINANCE_TESTNET=True` em testes.
- Ative limites de risco e monitore drawdowns.
- Avalie autenticação (API key/JWT) para ambientes expostos.

## Roadmap (próximas etapas – documentação/arquitetura)

- Parametrizar Scanner, Filtros e Sinais via `settings` (top‑N, liquidez, confirmação TF, momentum, thresholds de correlação/pump/dump).
- Alinhar `RiskManager` aos `settings` (2%/15% padrão) e avaliar Daily Max Loss/Intraday Hard Stop.
- Concorrência segura no Scanner (Semáforo) e seleção diversificada no Filtro de Correlação.
- Trailing adaptativo por ATR e score mínimo por regime em `MarketFilter`.

## Documentação relacionada

- Especificação de API: `docs/API_SPEC.md`
- Arquitetura: `docs/ARCHITECTURE.md`
- Guia de Deploy e Operação: `docs/DEPLOYMENT.md`
- Plano do Frontend: `docs/FRONTEND_PLAN.md`
- Changelog: `CHANGELOG.md`
- Guia de Contribuição: `CONTRIBUTING.md`
- Contexto do Projeto para LLMs: `LLM_CONTEXT.md`
- Recomendações MCP: `MCP_RECOMMENDATIONS.md`
