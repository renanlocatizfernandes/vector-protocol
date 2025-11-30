# Changelog

Todas as mudanças relevantes deste projeto serão registradas aqui. Este arquivo resume o histórico (com base no README.md e no contexto condensado) e servirá de trilha de auditoria para todas as ações futuras.

Formato recomendado:
- Data no padrão YYYY-MM-DD
- Seções: Adicionado, Alterado, Corrigido, Removido, Infra/DevOps, Validação/Observações
- Referências a arquivos, endpoints e decisões de arquitetura quando aplicável

--------------------------------------------------------------------------------

## [Unreleased] - 2025-10-26
Estado: Em andamento

Objetivos solicitados pelo usuário:
- Criar e manter este CHANGELOG com tudo que for feito a partir de agora, referenciando histórico e README.md quando necessário.
- Validação minuciosa do backend: diagnosticar por que o bot parece não estar funcionando; testar tudo; adicionar fallback e retry onde necessário.
- Utilizar o supervisor.py para ajudar nas validações.
- Permitir ativar/desativar o Supervisor via frontend.
- Validar e tornar o frontend mais dinâmico com atualizações mais eficazes.
- Após correções, reiniciar tudo garantindo ausência de cache e build finalizado; enviar mensagem de “bot operacional” no Telegram; iniciar e monitorar o bot. Repetir até pleno funcionamento.

Plano de execução (alto nível):
- Backend:
  - Auditar endpoints: /health, /version, /api/trading/bot/status|start|stop, /api/trading/stats/daily, /api/config (GET/PUT), /api/positions/…, /api/system/logs, /api/system/compose.
  - Testes de integração locais (uvicorn) e via docker-compose; revisar logs em ./logs.
  - Reforçar robustez: timeouts, retries com backoff exponencial, circuit breaker simples, validações de credenciais (Binance/Telegram), tratamento de falhas de DB e rede.
  - Melhorar health-check (incluindo dependências externas) e padronizar logger estruturado.
  - Expor endpoints do Supervisor: status/start/stop/toggle.
- Frontend:
  - Controles de Supervisor (ligar/desligar, status).
  - Melhorar dinâmica: polling com backoff, estados de carregamento granulares, toasts de erro, cancelamento de requests.
  - Opcional (posterior): WebSocket para eventos/logs.
- Ops:
  - Limpar caches e rebuild (frontend e backend).
  - Mensagem Telegram “bot operacional” após sucesso do health-check ampliado.
  - Start do bot e monitoramento contínuo (logs/health/stats).

--------------------------------------------------------------------------------

## 2025-11-11

### Adicionado
- Documentação expandida e análise técnica detalhada do bot:
  - README.md (Atualizado 2025-11-11) com diagnóstico por módulo, recomendações e links de referência.
  - docs/ARCHITECTURE.md (Atualizado) incluindo fluxos completos, análise por módulo, gaps e recomendações.
  - docs/API_SPEC.md (Atualizado) incluindo a seção “2b) Configuração Global” com `GET /api/config/`.
  - docs/DEPLOYMENT.md (Atualizado) alinhado às rotas e flags atuais, incluindo exemplos de validação e operação.
  - docs/FRONTEND_PLAN.md (Atualizado) com objetivos, páginas, serviços, polling/erros e roadmap.
- Recomendações documentadas (ainda não implementadas em código):
  - Parametrizar MarketScanner via settings: `SCANNER_TOP_N`, `SCANNER_MAX_SYMBOLS`, `MIN_QUOTE_VOLUME_USDT_24H`, `SCANNER_CONCURRENCY`, `TESTNET_WHITELIST`, filtro `PERPETUAL` + `TRADING`.
  - Presets PROD/TESTNET para SignalGenerator (min_score, volume_threshold, RSI, confirmação multi-TF, momentum, RR mínimos).
  - Expor thresholds do CorrelationFilter/MarketFilter em settings e adicionar seleção max-diversificada (greedy).
  - Alinhar RiskManager a `RISK_PER_TRADE` e `MAX_PORTFOLIO_RISK` do settings; avaliar Daily Max Loss/Intraday Hard Stop.
  - Trailing adaptativo por ATR e métricas/KPIs de pipeline (observabilidade).

### Alterado
- Consolidação das referências entre README.md, API_SPEC.md, ARCHITECTURE.md, DEPLOYMENT.md e FRONTEND_PLAN.md para coerência e navegação.
- API_SPEC.md passou a listar `GET /api/config/` (somente leitura de subset de settings).

### Corrigido
- Documentação corrigida para refletir nomes e rotas atuais, reduzindo ambiguidades (ex.: método correto para teste de Telegram via `POST`).

### Validação/Observações
- Mudanças desta data foram exclusivamente de documentação; nenhum ajuste de código operacional foi realizado neste commit.
- Próximos passos: implementar as recomendações priorizadas (RiskManager alinhado ao settings, parametrização do Scanner, presets de SignalGenerator, thresholds em settings para filtros).

--------------------------------------------------------------------------------

## 2025-11-10

### Adicionado
- PositionMonitor v3.0 integrado ao runtime:
  - Trailing stop ativado a +3% com distância de 50% do pico.
  - Take Profit parcial dinâmico (30–70%) baseado em volatilidade (ATR simplificada).
  - Kill switch automático em 15% de drawdown sobre saldo inicial.
  - Circuit breaker global após 3 perdas consecutivas (pausa 1h) e blacklist por símbolo (2h).
  - Auto-sync de “posições fantasma” detectadas na Binance que não existem no DB.
- Integrações Telegram conectadas aos eventos reais do monitor:
  - `notify_take_profit_hit`, `notify_breakeven_activated`,
    `notify_trailing_stop_activated`, `notify_trailing_stop_executed`,
    `notify_emergency_stop`, `notify_stop_loss_hit`, `notify_trade_closed`.
  - Novo helper `send_alert`.
- Documentação:
  - `docs/DEPLOYMENT.md` criado (runbook, flags, endpoints, operação).
  - `docs/ARCHITECTURE.md` atualizado com P1/P2/P3, flags em runtime e fluxo do monitor.

### Alterado
- `TelegramNotifier.notify_trade_closed` agora aceita `close_price` ou `exit_price` (fallback robusto).
- Mensagens de parcial passaram a disparar Telegram (TP Parcial + breakeven).

### Corrigido
- Fechamento com arredondamento por `step_size` (evita -1111).
- Conexão de notificações a eventos do monitor (Emergency Stop, Max Loss, Trailing).
- Logs do monitor ajustados para evitar spam.

### Validação/Observações
- Frontend dev ativo em http://localhost:5173 (proxy funcionando para API).
- `/health` via 5173 e 8000: `healthy`; checks `{db, redis, binance}=ok`, `supervisor_enabled=true`.
- Bot status: `running=true`, `dry_run=false`.

## 2025-10-26

### Adicionado
- Backend:
  - Rotas do sistema para observabilidade:
    - GET `/api/system/logs?component=<prefix>&tail=<n>`: obtém tail de logs em `./logs`.
    - GET `/api/system/compose`: tenta obter status do Docker (retorna mensagem clara quando docker.sock não está disponível no ambiente da API).
  - Integração dessas rotas no app FastAPI (inclusão do `system.router` em `/api/system`).

- Frontend (React + Vite + TypeScript):
  - Serviço API robusto (`frontend/src/services/api.ts`) com:
    - baseURL dinâmica: usa `VITE_API_BASE` se válido, senão fallback via proxy do Vite (same-origin).
    - Interceptor de retry: em erro de rede/timeout quando usando `VITE_API_BASE`, refaz a mesma chamada via same-origin uma vez.
    - Timeout padrão reduzido (10s).
    - Ajuste do endpoint `getConfig` para `/api/config/` (trailing slash).
  - Componentes:
    - `DockerStatus.tsx`: exibe status do “compose” (quando disponível).
    - `LogsViewer.tsx`: leitura de logs com auto-refresh, presets de componentes, “seguir fim”.
  - Hook:
    - `useBotStatus.ts`: polling de status do bot.
  - UI/Infra:
    - Navbar com indicador global “Bot: Rodando/Parado”.
    - Página “Supervisor” com Cards de DockerStatus e LogsViewer.
  - Proxy Vite (`frontend/vite.config.ts`) mapeando `/api`, `/health`, `/version`, `/docs` → API (http://localhost:8000 por padrão).

### Alterado
- Ajustes no serviço Axios para ser resiliente a configurações incorretas de `VITE_API_BASE`.
- Padronização de rota `/api/config/` com barra final para compatibilidade.

### Corrigido
- Timeouts no frontend quando `VITE_API_BASE` estava incorreto:
  - Agora há fallback automático para o proxy do Vite em caso de “Network Error/timeout”.
- Tratamento claro para “Compose Status” indisponível (ambiente sem docker.sock).

### Validação/Observações
- Logs acessíveis via `/api/system/logs` (montagem do volume `./logs`).
- Em alguns cenários, o Vite mostrou `http proxy error` (ECONNRESET/socket hang up), sugerindo backend ausente/instável:
  - Fallback no frontend foi implementado, porém a disponibilidade do backend ainda precisa ser garantida.
- Próximos passos incluem subir o backend localmente, testar endpoints individualmente e reforçar resiliência.

--------------------------------------------------------------------------------

## Histórico anterior (resumo)
- Estrutura do backend em FastAPI com módulos: `autonomous_bot.py`, `order_executor.py`, `signal_generator.py`, `position_monitor.py`, `risk_manager.py`, `market_scanner.py`, `backtester.py`.
- Supervisor (`supervisor.py`) que cuida de:
  - Ambiente (venv), comandos docker-compose (up/build/restart/down), health probing e watchdog.
  - Intervenções quando bot está parado ou inativo por muito tempo conforme logs.
- Frontend MVP com páginas: Dashboard, Config Bot, Supervisor; serviços, estilos globais, roteamento, e plano documentado em `docs/FRONTEND_PLAN.md`.

--------------------------------------------------------------------------------

## Notas de Operação
- Quando o backend estiver containerizado sem acesso ao `docker.sock`, `/api/system/compose` retornará indisponível por design; use `supervisor.py` externamente para controlar Docker.
- Logs ficam em `./logs/*.log` (ex.: `api_YYYYMMDD.log`).
- Vite dev server: http://localhost:5173 (proxy → http://localhost:8000).

--------------------------------------------------------------------------------

## Matriz de Validação (alvo)
- Disponibilidade:
  - GET `/health` (ampliado para checar dependências externas).
  - GET `/version`
- Bot Trading:
  - GET `/api/trading/bot/status`
  - POST `/api/trading/bot/start`
  - POST `/api/trading/bot/stop`
  - GET `/api/trading/stats/daily`
- Configuração:
  - GET `/api/config/`
  - PUT `/api/config/` (atualização parcial/total, validação de schema)
  - POST `/api/config/test-telegram` (se existir; enviar mensagem teste)
- Observabilidade:
  - GET `/api/system/logs`
  - GET `/api/system/compose`
- Posicionamento/Mercado/Backtest (se aplicável):
  - Rotas em `/api/positions`, `/api/market`, `/api/backtesting`

--------------------------------------------------------------------------------

## Decisões de Arquitetura recentes
- Frontend resiliente a `VITE_API_BASE` mal configurado (fallback + retry).
- Mensagens claras na UI quando docker compose status não está acessível via API container.

--------------------------------------------------------------------------------

## Próximas Ações (resumidas)
- Backend: executar localmente, diagnosticar indisponibilidade (ECONNRESET), reforçar retries/timeouts/backoff, melhorar health-check e logs estruturados.
- Supervisor: expor endpoints no backend para status/start/stop/toggle e integrar no frontend.
- Frontend: adicionar controles do Supervisor; melhorar polling/estados/toasts; avaliar WebSocket para logs/eventos.
- Ops: rebuild sem cache, enviar “bot operacional” no Telegram, iniciar e monitorar o bot; repetir até estabilidade.

--------------------------------------------------------------------------------

## 2025-10-26 (Atualizações - tarde)

### Adicionado
- Backend:
  - Endpoints de controle do Supervisor:  
    - GET `/api/system/supervisor/status`  
    - POST `/api/system/supervisor/enable`  
    - POST `/api/system/supervisor/disable`  
    - POST `/api/system/supervisor/toggle`  
    Baseados em flag `logs/supervisor_enabled.flag` e leitura do log `logs/supervisor_interventions.log`.
  - Resiliência no cliente Binance (`backend/utils/binance_client.py`):  
    `_retry_call` com backoff exponencial aplicado a `futures_account`, `futures_symbol_ticker`, `futures_ticker`, `futures_klines`, `futures_exchange_info`.
  - Health-check fortalecido em `/health` (DB, Redis, Binance [best-effort], Supervisor enabled).

- Supervisor (`supervisor.py`):
  - Novo diretório de logs consolidado: `logs/`.
  - Flag de ativação `logs/supervisor_enabled.flag` e leitura no loop (`is_supervisor_enabled()`), encerrando o watch quando desativado.
  - `supervisor_interventions.log` movido para `logs/`.

- Frontend:
  - Serviços do Supervisor em `frontend/src/services/api.ts`: `getSupervisorStatus`, `supervisorEnable`, `supervisorDisable`, `supervisorToggle`.
  - Página `Supervisor.tsx`:  
    - Controles de ativar/desativar/alternar Supervisor, exibição de status e últimas intervenções.  
    - Polling reduzido para 5s (mais dinâmica).  

### Alterado
- `backend/api/app.py`:
  - `/health` agora retorna `status` agregado: `healthy | degraded | unhealthy` conforme DB/Redis.
  - Inclusão de `checks.{db, redis, binance, supervisor_enabled}`.

- `supervisor.py`:
  - Escrita/uso de `LOGS_DIR` e `SUPERVISOR_FLAG`.  
  - Watch loop respeita a flag e registra intervenções.

- `frontend/src/pages/Supervisor.tsx`:
  - Correção de erro de build (duplicação de `}, []);` na segunda `useEffect`).  
  - Inclusão de handlers e badges de status do Supervisor.

### Corrigido
- Endpoint de teste do Telegram: `POST /api/trading/test/telegram?text=...` (aceita `text` opcional).  
  CLI anterior usando `GET -G` retornava 405; ajustado para `POST`.

### Validação/Observações
- Rebuild sem cache e subida via docker-compose: OK.  
- `/health` → `healthy`; `checks.db=ok`, `checks.redis=ok`, `checks.binance=ok`, `checks.supervisor_enabled=true`.  
- Vite proxy: `/health` e `/api/trading/bot/status` via `:5173` respondendo OK.  
- Envio de mensagem no Telegram “Bot operacional: API healthy; bot RUNNING”: OK (POST).  
- Start do bot com `dry_run=false` → `running=true` confirmado; logs de `autonomous_bot` disponíveis.  

### Próximas ações operacionais
- Manter `supervisor.py watch` em execução com `--ensure-running` para mitigar quedas e inatividade.  
- Monitorar logs de `autonomous_bot`, `trading_routes` e estatísticas diárias.  
- Iterar em melhorias de UX (toasts, backoff adaptativo no frontend e, opcionalmente, WebSocket para logs/eventos).
