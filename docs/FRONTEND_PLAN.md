# Plano de Trabalho do Frontend (Painel do Crypto Trading Bot) — Atualizado 2025-11-11

Este documento descreve o plano de trabalho, arquitetura e decisões do frontend do painel web, considerando a operação COM e SEM o Supervisor (`supervisor.py`). Está alinhado ao README.md, API_SPEC.md e ARCHITECTURE.md atualizados.

## Objetivos

- Visualizar operação do bot (status, saúde da API, estatísticas, posições).
- Alterar parâmetros em tempo de execução (intervalo de varredura, min_score, max_positions).
- Visualizar resultados (P&L diário, trades/posições).
- Exibir subset de configurações globais de runtime (somente leitura) via `/api/config/`.
- Ajustar toggles de execução avançada via `/api/trading/execution/config`.
- Integrar de forma segura com a API existente.
- Considerar o Supervisor ativo ou inativo sem acoplamento rígido.

## Stack Técnica

- Vite + React + TypeScript
- React Router
- Axios (serviços HTTP)
- Zustand (opcional para estado global)
- Recharts (opcional para gráficos — ainda não utilizado no MVP)
- CSS simples (global.css)

Variáveis de ambiente:
- `VITE_API_BASE` (opcional). Em dev, o proxy do Vite para `http://localhost:8000` já está configurado (vite.config.ts).

## Estrutura e Páginas

- Dashboard
  - Saúde da API: `/health` e `/version`
  - Status/config do bot: `/api/trading/bot/status`
  - Ações: Start/Stop (`/api/trading/bot/start|stop`)
  - Ajuste rápido de config: `PUT /api/trading/bot/config` (scan_interval_minutes, min_score, max_positions)
  - Estatísticas do dia: `/api/trading/stats/daily`
  - Posições/trades abertos (resumo): endpoints de posições (ver API_SPEC)
  - Subset de configurações globais (somente leitura): `GET /api/config/`

- Config Bot
  - Exibe config global (pydantic-settings) via `/api/config/` (somente leitura)
  - Ajusta parâmetros de runtime do bot (mesmos do Dashboard, com formulário dedicado)
  - Toggles de execução avançada (execução/risco) via `GET|PUT /api/trading/execution/config`
  - Teste de Telegram: `/api/trading/test/telegram`

- Supervisor
  - Guia operacional do `supervisor.py` (comandos e cenários)
  - Exibe estado atual do Supervisor e controles (quando expostos):
    - `GET /api/system/supervisor/status`
    - `POST /api/system/supervisor/{enable|disable|toggle}`

Futuras (opcional/etapas seguintes):
- Mercado (sinais): `/api/market/signals`, `analyze`, `price`
- Backtesting: `/api/backtest/*`
- Trades detalhados: rotas de posições (`open`, `closed`), e ações de fechamento manual
- WebSocket (se `backend/api/websocket.py` exposto)

## Arquitetura de Serviços (API)

Arquivo: `frontend/src/services/api.ts`

- `http` (axios) com `baseURL` lendo `VITE_API_BASE` (ou proxy do Vite)
- Funções principais:
  - `getHealth()`, `getVersion()`
  - `getConfig()` (somente leitura de `/api/config/`)
  - `getExecutionConfig()`, `updateExecutionConfig(params)` (toggles runtime)
  - `getBotStatus()`, `startBot(dry_run)`, `stopBot()`, `updateBotConfig(params)`
  - `getDailyStats()`
  - `getPositionsDashboard()` (quando existir endpoint consolidado)
  - `testTelegram(text)`
  - Supervisor (se exposto): `getSupervisorStatus()`, `supervisorEnable()`, `supervisorDisable()`, `supervisorToggle()`
  - (Futuros) `getSignals()`, `backtestQuick()`, `backtestRun()`

Contrato e endpoints devem seguir `docs/API_SPEC.md`.

## Com e Sem Supervisor

- Supervisor DESLIGADO (controle manual pela UI)
  - Utilize o painel para iniciar/parar o bot, ajustar parâmetros e acompanhar resultados.
  - A API continua sendo a fonte de verdade e a UI faz polling leve (10–15s) para status essenciais.
  - Recomendado em desenvolvimento e testes exploratórios.

- Supervisor LIGADO (`python3 supervisor.py watch ...`)
  - Mantém a API saudável (auto-fix) e o bot rodando (`--ensure-running`), reiniciando quando inativo por muito tempo.
  - A UI permanece como interface de observação e ajuste fino.
  - Recomendado para sessões longas, ambientes semi-prod e maior resiliência.

Decisão de Design:
- A UI NÃO depende do Supervisor; opera integralmente via API.
- Quando o Supervisor está ativo, a UI apenas reflete o estado e orienta melhores práticas com instruções/avisos.

## Estado, Polling e Erros

- Polling recomendado:
  - `getBotStatus()` e `getDailyStats()` a cada 10s
  - `getHealth()` a cada 15–30s
  - `getExecutionConfig()` e `getConfig()` sob demanda (ou refresh manual)
- Tratamento de erros:
  - Toasts/alerts para falhas de rede/timeout
  - Fallback para proxy do Vite quando `VITE_API_BASE` falhar (já suportado no serviço axios)
  - Mensagens claras ao usuário quando a API estiver indisponível
- Cancelamento/limpeza:
  - Cancelar requests pendentes ao desmontar componentes (AbortController ou axios cancel token)

## UX/Estilo

- `global.css` com tema escuro e componentes básicos (cards, badges, grid).
- Layout: Navbar + Conteúdo + Footer.
- Indicadores claros para estado do bot (rodando/parado), saúde da API (healthy/degraded/unhealthy) e toggles ativos.

## Tarefas Prioritárias (Roadmap)

- MVP Refinado
  - [ ] Dashboard: cards com saúde, status do bot, KPIs diários e subset de config (`/api/config/`)
  - [ ] Config Bot: formulários para `PUT /api/trading/bot/config` e `PUT /api/trading/execution/config`
  - [ ] Supervisor: controles e status quando expostos
  - [ ] Toasts e estados de carregamento consistentes; polling com limpeza adequada
- Próximas Etapas
  - [ ] Página de Sinais (mercado): listar sinais com `min_score` configurável e ação “executar (dry-run)”
  - [ ] Trades/Posições detalhados: tabelas e ações; filtros por status (open/closed)
  - [ ] Backtesting: quick/custom com gráficos (Recharts) quando payload suportar
  - [ ] WebSocket (se backend expuser) para reduzir polling e transmitir logs/eventos
  - [ ] Banner “Supervisor ativo” (heurística ou flag de backend quando disponível)

## Execução Local

- Backend (local orquestrado por Docker):
  - `docker compose up --build`
  - API: http://localhost:8000

- Frontend (dev):
  - `cd frontend`
  - `npm install`
  - `npm run dev`
  - Acesse: http://localhost:5173
  - O Vite proxy encaminha `/api`, `/health`, `/version`, `/docs` para `http://localhost:8000`.
  - Opcional: defina `VITE_API_BASE` em `.env` para apontar p/ outra URL (ex.: deploy remoto).

- Build:
  - `npm run build`
  - `npm run preview` (http://localhost:5174)

## Segurança

- Mantenha `BINANCE_TESTNET=True` em ambiente de testes.
- Valide credenciais e limites de risco antes de iniciar operações reais.
- Avalie CORS e autenticação para ambientes expostos (API key/JWT).

## KPIs e Observabilidade (UI)

- Indicadores desejados no painel:
  - Status do bot (running/dry_run/scan_interval/min_score/max_positions)
  - PnL diário, win rate, melhor/pior trade (via `/api/trading/stats/daily`)
  - Exposição total, positions_count, free_margin% (quando disponível)
  - Alertas de eventos críticos (emergency stop, kill switch, circuit breaker)
- Logs:
  - Viewer de logs por componente via `GET /api/system/logs?component=<prefix>&tail=<n>`
  - Auto-refresh configurável e “seguir fim” (opcional)

## Conclusão

O plano mantém o painel simples, focado em operação e observabilidade com baixos acoplamentos. A evolução mapeada amplia monitoramento e operação (sinais, backtesting, trades detalhados, WebSocket), mantendo a separação de responsabilidades entre UI, API e Supervisor. A exposição de `/api/config/` (somente leitura) e a padronização de toggles via `/api/trading/execution/config` clarificam a fronteira entre configuração persistente e ajustes dinâmicos de execução.
