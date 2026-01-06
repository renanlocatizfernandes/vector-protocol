# Guia de Deploy e Operação (Atualizado 2025-11-11)

Este documento descreve como subir, operar e validar o Crypto Trading Bot em ambiente local (desenvolvimento) e em Docker Compose, além de listar flags de execução e endpoints úteis para operação cotidiana. As instruções estão alinhadas ao README.md, API_SPEC.md e ARCHITECTURE.md atualizados.

## Requisitos

- Docker e Docker Compose (v2+)
- Node.js LTS (para rodar o frontend em dev)
- Python 3.11+ (apenas se rodar o backend fora de contêiner)
- curl e jq (validações rápidas por CLI)

## Variáveis de Ambiente

Use `.env.docker` (Docker) ou `.env` (local) na raiz do repositório. Exemplo mínimo:

- Credenciais Binance (Futuros USD‑M):
  - `BINANCE_API_KEY=...`
  - `BINANCE_API_SECRET=...`
  - `BINANCE_TESTNET=true|false`
- Telegram:
  - `TELEGRAM_ENABLED=true|false`
  - `TELEGRAM_BOT_TOKEN=...`
  - `TELEGRAM_CHAT_ID=...`
- Banco de dados / Redis:
  - `POSTGRES_USER=trading_bot`
  - `POSTGRES_PASSWORD=...`
  - `POSTGRES_DB=trading_bot_db`
  - `DATABASE_URL=postgresql+psycopg2://trading_bot:...@db:5432/trading_bot_db`
  - `REDIS_HOST=redis`
  - `REDIS_PORT=6379`
- `API_PORT_HOST=8000`
- `API_AUTH_ENABLED=false`
- `API_KEY=change_me`
- `API_KEY_HEADER=X-API-Key`

Observação: o arquivo `backend/config/settings.py` já mapeia defaults sensatos e detecta `.env.docker` quando roda em container.

## Flags de Execução e Risco (runtime)

Os campos abaixo podem ser consultados/alterados em runtime via API (memória do processo). Veja `docs/API_SPEC.md` seção “Execução Avançada”.

- Execução/ordens:
  - `ORDER_TIMEOUT_SEC` (int, ex.: 3)
  - `USE_POST_ONLY_ENTRIES` (bool)
  - `AUTO_POST_ONLY_ENTRIES` (bool)
  - `AUTO_MAKER_SPREAD_BPS` (float, ex.: 3.0 bps)
  - `TAKE_PROFIT_PARTS` (str, ex.: "0.5,0.3,0.2")
  - `USE_MARK_PRICE_FOR_STOPS` (bool)
  - `ENABLE_BRACKET_BATCH` (bool)
- Headroom/liquidez:
  - `HEADROOM_MIN_PCT` (float, ex.: 35.0)
  - `REDUCE_STEP_PCT` (float, ex.: 10.0)
- Trailing Stop:
  - `ENABLE_TRAILING_STOP` (bool)
  - `TSL_CALLBACK_PCT_MIN` (float, ex.: 0.4)
  - `TSL_CALLBACK_PCT_MAX` (float, ex.: 1.2)
  - `TSL_ATR_LOOKBACK_INTERVAL` (str, ex.: "15m")
- Derivatives-aware:
  - `ENABLE_FUNDING_AWARE` (bool)
  - `FUNDING_ADVERSE_THRESHOLD` (float, ex.: 0.0003)
  - `FUNDING_BLOCK_WINDOW_MINUTES` (int, ex.: 20)
  - `OI_CHANGE_PERIOD` (str, ex.: "5m")
  - `OI_CHANGE_LOOKBACK` (int, ex.: 12)
  - `OI_CHANGE_MIN_ABS` (float, ex.: 0.5)
  - `TAKER_RATIO_LONG_MIN` (float, ex.: 1.02)
  - `TAKER_RATIO_SHORT_MAX` (float, ex.: 0.98)

Bot (autonomous):
- `BOT_SCAN_INTERVAL_MINUTES` (int, ex.: 1)
- `BOT_MIN_SCORE` (int)
- `BOT_MAX_POSITIONS` (int)
- `BOT_DRY_RUN` (bool)
- `AUTOSTART_BOT` (bool)

Consulta de subset imutável (somente leitura) disponível em `GET /api/config/`:
- `max_positions`, `risk_per_trade`, `max_portfolio_risk`, `default_leverage`, `testnet`.

## Subir com Docker Compose

Na raiz do projeto:

```bash
docker compose up -d --build
```

Serviços:
- API FastAPI: http://localhost:8000 (ou API_PORT_HOST)
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Logs: ./logs

Validação rápida:

```bash
curl -sS http://localhost:8000/health | jq .
curl -sS http://localhost:8000/version | jq .
curl -sS http://localhost:8000/api/config/ | jq .
```

Logs da API (stream):

```bash
docker logs -f trading-bot-api
```

Recriar tudo do zero:

```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Rodando o backend local (sem Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

## Rodando o frontend (dev)

O frontend não está containerizado por padrão no `docker-compose.yml`. Para desenvolvimento:

```bash
cd frontend
npm ci
npm run dev
```

- Acesse: http://localhost:5173
- O Vite proxy encaminha `/api`, `/health`, `/version`, `/docs` para `http://localhost:8000`.

Build de preview:

```bash
npm run build
npm run preview -- --port 5174
# http://localhost:5174
```

## Operação do Bot (principais endpoints)

- Saúde:
  - `GET /health` → status agregado (`healthy | degraded | unhealthy`)
  - `GET /version` (se exposto)

- Config global (somente leitura):
  - `GET /api/config/`

- Execução (toggles):
  - `GET /api/trading/execution/config`
  - `PUT /api/trading/execution/config?order_timeout_sec=3&use_post_only_entries=true&take_profit_parts=0.5,0.3,0.2&auto_post_only_entries=true&auto_maker_spread_bps=3&headroom_min_pct=35&reduce_step_pct=10`

- Controle do bot:
  - `GET /api/trading/bot/status`
  - `POST /api/trading/bot/start?dry_run=false`
  - `POST /api/trading/bot/stop`
  - `PUT /api/trading/bot/config?scan_interval_minutes=1&min_score=55&max_positions=10`

- Execução de trades:
  - `POST /api/trading/execute` (um trade por símbolo)
  - `POST /api/trading/execute-batch?min_score=70&max_trades=3&dry_run=true`
  - `POST /api/trading/positions/close?symbol=BTCUSDT`
  - `POST /api/trading/positions/close-all`

- Admin (abertura massiva):
  - `POST /api/trading/execute/force-many?count=10`
  - `POST /api/trading/execute/force-many/async?count=10`

- Observabilidade e suporte:
  - `GET /api/system/logs?component=<prefix>&tail=200`
  - User Stream: `POST /api/system/userstream/{start|stop}`, `GET /api/system/userstream/status`
  - Supervisor (quando exposto): `GET /api/system/supervisor/status`, `POST /api/system/supervisor/{enable|disable|toggle}`

- Teste do Telegram:
  - `POST /api/trading/test/telegram?text=Bot%20operacional`

## Runbook (passo a passo recomendado)

1) Subir dependências e API:
```bash
docker compose up -d --build
curl -sS http://localhost:8000/health | jq .
```

2) Rodar frontend em dev (se necessário):
```bash
cd frontend && npm ci && npm run dev
# acessar http://localhost:5173
```

3) Validar configuração de execução:
```bash
curl -sS http://localhost:8000/api/trading/execution/config | jq .
```

4) Enviar mensagem de teste no Telegram:
```bash
curl -sS -X POST "http://localhost:8000/api/trading/test/telegram?text=Bot%20operacional" | jq .
```

5) Iniciar o bot:
```bash
curl -sS -X POST "http://localhost:8000/api/trading/bot/start?dry_run=false" | jq .
curl -sS "http://localhost:8000/api/trading/bot/status" | jq .
```

6) Acompanhar logs:
```bash
docker logs -f trading-bot-api
# ou via endpoint:
curl -sS "http://localhost:8000/api/system/logs?component=api&tail=200" | jq -r .
```

7) Ajustes dinâmicos de execução: use `PUT /api/trading/execution/config` conforme necessidade operacional.

## Diagnóstico Rápido

- Frontend 5173 com erro proxy (socket hang up/ECONNRESET): API não está rodando/saudável. Valide `/health` diretamente em :8000.
- Mensagens do Telegram não chegam:
  - Verifique `TELEGRAM_ENABLED=true` e credenciais.
  - Teste com `POST /api/trading/test/telegram`.
- Ordens falhando por quantidade/precisão:
  - O executor/monitor arredonda por `step_size`, mas garanta `min_notional` e filtros do símbolo válidos.
- Entradas MARKET com Entry=0.0000:
  - Corrigido via cálculo de preço médio (`get_order_avg_price`) no fallback; valide nos logs de execução.

## Segurança

- Testnet por padrão (`BINANCE_TESTNET=True`) em desenvolvimento.
- Não comitar chaves reais em repositórios.
- Avaliar autenticação (API key/JWT) em ambientes expostos.
- Usar limites de risco e monitorar drawdowns (kill-switch/circuit breaker, quando habilitados).

## Observações Importantes

- `/api/config/` é somente leitura e expõe subset seguro das configurações carregadas por Pydantic Settings.
- Flags de execução têm efeito imediato em memória do processo (não persistem se o serviço reiniciar, a menos que mapeadas em `.env` e reiniciadas).
- Supervisor externo (`supervisor.py`) pode ser usado para resiliência operacional; endpoints para controle podem estar disponíveis conforme ambiente.
