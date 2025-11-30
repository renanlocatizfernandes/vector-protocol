# API Specification — Crypto Trading Bot (Atualizado 2025-11-11)

Este documento descreve os endpoints expostos pelo backend (FastAPI) após as modernizações P1, P2 e P3, incluindo flags runtime de execução e rotas administrativas.

Base URL (dev)
- API (Uvicorn em Docker): http://localhost:8000
- Frontend (Vite dev): http://localhost:5173 (proxy para /api, /health, /version, /docs → :8000)

Autenticação
- Não há autenticação habilitada por padrão (ambiente local). Em produção, recomenda-se adicionar API key/JWT.

Formato
- JSON UTF-8
- Códigos HTTP padrão:
  - 2xx sucesso
  - 4xx erro do cliente (params inválidos, símbolo inexistente, sem sinal, etc.)
  - 5xx erro do servidor (falhas internas ou dependências)

============================================================
1) Health & Version
============================================================

GET /health
- Retorna estado geral (inclui DB/Redis/Binance e supervisor_enabled quando disponível).
- Exemplo:
  {
    "status": "healthy | degraded | unhealthy",
    "checks": { "db": "ok", "redis": "ok", "binance": "ok", "supervisor_enabled": true }
  }

GET /version
- Opcional (se exposto). Retorna versão do serviço.

============================================================
2) Trading — Execução e Sinais
============================================================

POST /api/trading/execute
- Executa 1 trade a partir de um sinal gerado para um símbolo.
- Body:
  { "symbol": "BTCUSDT", "risk_profile": "moderate", "dry_run": true }
- Resposta: { signal, execution, account_balance }

POST /api/trading/execute-batch?min_score=70&max_trades=3&dry_run=true
- Gera sinais em batch e executa até max_trades aprovados.
- Resposta: { total_signals, executed_count, executed[], remaining_balance }

GET /api/trading/positions
- Posições abertas atuais (best-effort via futures_account).
- Resposta: { count, positions[] }

POST /api/trading/positions/close
- Fecha manualmente uma posição (reduceOnly) e atualiza DB.
- Query: ?symbol=BTCUSDT
- Resposta: { success, close_price, pnl, pnl_percentage }

POST /api/trading/positions/close-all
- Fecha todas as posições abertas que existirem no DB com status 'open'.

POST /api/trading/test/telegram?text=Mensagem+custom
- Enfileira envio de mensagem de teste ao Telegram (não bloqueante).

============================================================
2b) Configuração Global
============================================================

GET /api/config/
- Retorna um subconjunto de configurações globais carregadas via Pydantic Settings.
- Exemplo de resposta:
  {
    "max_positions": 15,
    "risk_per_trade": 0.02,
    "max_portfolio_risk": 0.15,
    "default_leverage": 3,
    "testnet": true
  }
- Observação: endpoint somente leitura. Para ajustes dinâmicos de execução, utilize as rotas de Execução Avançada (seção 4) ou de Bot (seção 3).

============================================================
3) Trading — Bot Supervisor
============================================================

POST /api/trading/bot/start?dry_run=true
- Inicia o bot autônomo.

POST /api/trading/bot/stop
- Para o bot autônomo.

GET /api/trading/bot/status
- Retorna status do bot (running/scanInterval/etc).
- Resposta:
  { "running": true, "dry_run": false, "scan_interval": 60, "min_score": 55, "max_positions": 10 }

PUT /api/trading/bot/config
- Atualiza config do bot (scan_interval_minutes, min_score, max_positions).
- Ex.: /api/trading/bot/config?scan_interval_minutes=1&min_score=55&max_positions=10

============================================================
4) Trading — Execução Avançada (runtime toggles)
============================================================

GET /api/trading/execution/config
- Retorna flags de execução avançada (efeito em memória).
- Campos:
  - ENABLE_TRAILING_STOP (bool)
  - TSL_CALLBACK_PCT_MIN (float)
  - TSL_CALLBACK_PCT_MAX (float)
  - TSL_ATR_LOOKBACK_INTERVAL (str)
  - ENABLE_BRACKET_BATCH (bool)
  - USE_MARK_PRICE_FOR_STOPS (bool)
  - DEFAULT_MARGIN_CROSSED (bool)
  - AUTO_ISOLATE_MIN_LEVERAGE (int)
  - ALLOW_MARGIN_MODE_OVERRIDE (bool)
  - ORDER_TIMEOUT_SEC (int)
  - USE_POST_ONLY_ENTRIES (bool)
  - TAKE_PROFIT_PARTS (str, ex: "0.5,0.3,0.2")
  - AUTO_POST_ONLY_ENTRIES (bool)
  - AUTO_MAKER_SPREAD_BPS (float)
  - HEADROOM_MIN_PCT (float)
  - REDUCE_STEP_PCT (float)

PUT /api/trading/execution/config
- Atualiza qualquer subconjunto dos campos acima, efeito imediato.
- Exemplo:
  /api/trading/execution/config?order_timeout_sec=3&use_post_only_entries=true&take_profit_parts=0.5,0.3,0.2&auto_post_only_entries=true&auto_maker_spread_bps=3.0&headroom_min_pct=35&reduce_step_pct=10

GET /api/trading/execution/leverage-preview?symbol=BTCUSDT&entry_price=65000&quantity=0.02
- Mostra alavancagem máxima permitida pela Binance para um notional aproximado.

============================================================
5) Trading — Abertura em Massa (Admin)
============================================================

POST /api/trading/execute/force-many
- Abre múltiplas posições rapidamente sem depender do gerador.
- Query params:
  - count (int, default 15)
  - symbols (CSV opcional)
  - direction (LONG|SHORT, opcional; alterna se vazio)
  - leverage (int, opcional; se ausente usa alavancagem dinâmica baseada em RSI/volume/R:R)
- Resposta: { attempted, opened, target, live_count, results[] }

POST /api/trading/execute/force-many/async
- Dispara o processo acima em background e retorna imediatamente.

============================================================
6) Trading — Estatísticas e Relatórios
============================================================

GET /api/trading/stats/daily
- Estatísticas do dia (P&L total, best/worst trade, win rate, saldo atual).

POST /api/trading/report/daily
- Envia relatório diário manualmente (Telegram).

============================================================
7) System / Observabilidade / User Stream
============================================================

GET /api/system/logs?component=binance_client&tail=200
- Retorna as últimas N linhas de log dos componentes (api, trading_routes, binance_client, order_executor, etc).

POST /api/system/userstream/start
POST /api/system/userstream/stop
GET  /api/system/userstream/status
- Controle de User Data Stream (USD-M Futures) best-effort.

(Se implementadas) Rotas Supervisor:
- GET  /api/system/supervisor/status
- POST /api/system/supervisor/enable
- POST /api/system/supervisor/disable
- POST /api/system/supervisor/toggle

============================================================
8) Execução — Comportamentos Internos (Resumo)
============================================================

- P1 Execução:
  - LIMIT com buffer e re-quote inteligente (até 3 tentativas); post-only (GTX) quando USE_POST_ONLY_ENTRIES=true ou AUTO_POST_ONLY_ENTRIES=true e spread ≥ AUTO_MAKER_SPREAD_BPS.
  - Timeout configurável (ORDER_TIMEOUT_SEC). Na última tentativa, fallback MARKET com recuperação do preço médio via fills (get_order_avg_price).

- P1 Risco:
  - Após abertura, checa headroom até preço de liquidação (get_position_risk); se < HEADROOM_MIN_PCT, reduz posição em etapas (REDUCE_STEP_PCT) com reduceOnly até atingir o headroom mínimo (best-effort, limitado a 3 iterações).

- P2 Custos:
  - Endpoints de taxas podem ser consultados off-path (get_commission_rate). Em etapas futuras, decisões maker/taker considerarão custo efetivo.

- P3 Estratégia:
  - Signal generator com regime simples (trend/range) influenciando R:R mínimo aceito (1.0 em trend, 1.5 em range) e score.

============================================================
9) Telegram — Notificações
============================================================

- Envio assíncrono com retries/backoff.
- Funções:
  - notify_trade_opened, notify_trade_closed, notify_take_profit_hit, notify_stop_loss_hit, notify_emergency_stop, notify_position_closed.
  - Mensagens ricas (HTML) com emojis e métricas claras.

============================================================
10) Códigos de Erro Comuns
============================================================

- 400: símbolo inválido, sem sinal, qty/filters inválidos (minQty, stepSize, minNotional), request malformado.
- 409: conflito de execução (ex.: posição/ordem em estado que impede mudança de margin/leverage).
- 500: erro interno (DB/Redis/Binance indisponível, exceções não tratadas).
- Mensagens de erro dos endpoints da Binance (ex.: -2019 insuficiência de margem) são traduzidas e logadas.

============================================================
11) Exemplos Rápidos (curl)
============================================================

- Ver config de execução:
  curl -sS "http://localhost:8000/api/trading/execution/config" | jq .

- Ativar maker (post-only) e ladder de TPs:
  curl -sS -X PUT "http://localhost:8000/api/trading/execution/config?use_post_only_entries=true&take_profit_parts=0.5,0.3,0.2" | jq .

- Habilitar decisão automática maker por spread (3 bps) e headroom mínimo 35%:
  curl -sS -X PUT "http://localhost:8000/api/trading/execution/config?auto_post_only_entries=true&auto_maker_spread_bps=3&headroom_min_pct=35&reduce_step_pct=10" | jq .

- Executar 1 trade:
  curl -sS -X POST "http://localhost:8000/api/trading/execute" -H 'Content-Type: application/json' -d '{"symbol":"BTCUSDT","risk_profile":"moderate","dry_run":false}' | jq .

- Abertura em massa (dinâmica):
  curl -sS -X POST "http://localhost:8000/api/trading/execute/force-many?count=10" | jq .

- Bot start e status:
  curl -sS -X POST "http://localhost:8000/api/trading/bot/start?dry_run=false" | jq .
  curl -sS "http://localhost:8000/api/trading/bot/status" | jq .
