# 📋 Arquivos Prioritários para Evolução do Bot

Este documento lista os principais arquivos do projeto que merecem atenção para evolução, baseado na análise técnica e gaps identificados na documentação.

---

## 🔴 PRIORIDADE ALTA (Gaps Críticos)

### 1. `backend/modules/risk_manager.py`
**Status:** Parcialmente alinhado (já lê settings, mas pode melhorar)
**Gaps Identificados:**
- ✅ Já lê `RISK_PER_TRADE` e `MAX_PORTFOLIO_RISK` do settings
- ⚠️ Pode melhorar tracking de Daily Max Loss e Intraday Hard Stop com Redis
- ⚠️ Métricas de portfólio podem ser mais detalhadas

**Melhorias Sugeridas:**
- Implementar contadores diários em Redis para `DAILY_MAX_LOSS_PCT`
- Melhorar tracking de `INTRADAY_DRAWDOWN_HARD_STOP_PCT`
- Adicionar métricas estruturadas de exposição total/pico
- Logs mais detalhados de bloqueios por headroom/daily cap

**Impacto:** 🔴 CRÍTICO - Controla todo o risco do bot

---

### 2. `backend/modules/market_scanner.py`
**Status:** Parcialmente parametrizado (já usa alguns settings)
**Gaps Identificados:**
- ✅ Já filtra PERPETUAL + TRADING
- ✅ Já usa SCANNER_TOP_N, SCANNER_MAX_SYMBOLS, MIN_QUOTE_VOLUME_USDT_24H
- ⚠️ Pode melhorar concorrência com Semaphore mais robusto
- ⚠️ Cache de resultados pode ser otimizado

**Melhorias Sugeridas:**
- Otimizar `asyncio.Semaphore` para evitar rate limits
- Implementar cache inteligente de klines (evitar requisições repetidas)
- Adicionar métricas de latência e cobertura
- Blacklist de stablecoins irrelevantes

**Impacto:** 🟠 ALTO - Base de todo o pipeline de trading

---

### 3. `backend/modules/signal_generator.py`
**Status:** Presets implementados, mas pode melhorar
**Gaps Identificados:**
- ✅ Já tem presets PROD/TESTNET
- ⚠️ Alguns thresholds ainda podem ser mais parametrizáveis
- ⚠️ R:R mínimo por regime pode ser mais flexível
- ⚠️ Indicadores técnicos podem ser expandidos

**Melhorias Sugeridas:**
- Adicionar mais indicadores técnicos (MACD, Bollinger Bands, etc.)
- Melhorar detecção de regime (trend/range/sideways)
- Tornar R:R mínimo mais dinâmico baseado em volatilidade
- Adicionar confirmação multi-timeframe mais robusta
- Métricas de distribuição de scores e R:R médio

**Impacto:** 🟠 ALTO - Coração da estratégia de trading

---

## 🟡 PRIORIDADE MÉDIA (Melhorias Importantes)

### 4. `backend/modules/correlation_filter.py`
**Status:** Funcional, mas pode evoluir
**Gaps Identificados:**
- ✅ Já parametrizado via settings (CORR_WINDOW_DAYS, MAX_CORRELATION)
- ⚠️ Seleção ainda não é "greedy max-diversificada"
- ⚠️ Cache pode ser otimizado

**Melhorias Sugeridas:**
- Implementar seleção greedy para maximizar diversidade
  - Ordenar sinais por score
  - Aceitar apenas se |corr| ≤ threshold com TODOS os já selecionados
- Otimizar cálculo de correlação (usar matriz de correlação)
- Cache mais inteligente (invalidação baseada em tempo de mercado)

**Impacto:** 🟡 MÉDIO - Melhora diversificação do portfólio

---

### 5. `backend/modules/market_filter.py`
**Status:** Funcional, mas thresholds podem ser mais flexíveis
**Gaps Identificados:**
- ✅ Já parametrizado (PUMP/DUMP_* no settings)
- ⚠️ Dump explícito pode ser mais robusto
- ⚠️ Score mínimo por regime pode ser mais granular

**Melhorias Sugeridas:**
- Melhorar detecção de dump (não apenas pump)
- Score mínimo dinâmico por regime (trend/range/sideways)
- Adicionar filtro de volume sustentado mais sofisticado
- Considerar horário de mercado (fins de semana, abertura/fechamento)

**Impacto:** 🟡 MÉDIO - Protege contra condições de mercado adversas

---

### 6. `backend/modules/order_executor.py`
**Status:** Muito robusto, mas pode adicionar métricas
**Gaps Identificados:**
- ✅ Execução já é muito boa (LIMIT com re-quote, fallback MARKET)
- ✅ Headroom management implementado
- ⚠️ Falta métricas estruturadas de execução

**Melhorias Sugeridas:**
- Adicionar métricas detalhadas:
  - Tentativas LIMIT vs MARKET
  - Maker vs Taker ratio
  - Slippage estimado
  - Tempo médio por ordem
- Logs estruturados (JSON) para análise posterior
- Dashboard de métricas de execução

**Impacto:** 🟡 MÉDIO - Melhora observabilidade e otimização

---

### 7. `backend/modules/position_monitor.py`
**Status:** Muito completo, mas pode melhorar TSL
**Gaps Identificados:**
- ✅ Trailing, partials, breakeven, emergency stop implementados
- ⚠️ TSL callback pode ser mais adaptativo por ATR
- ⚠️ Métricas por evento podem ser mais detalhadas

**Melhorias Sugeridas:**
- TSL callback adaptativo por ATR (respeitar TSL_* min/max)
- Métricas por evento:
  - Tempo médio em posição
  - MAE (Maximum Adverse Excursion)
  - MFE (Maximum Favorable Excursion)
- Dashboard de eventos (trailing/partials/ES/SL)

**Impacto:** 🟡 MÉDIO - Otimiza saídas e proteções

---

### 8. `backend/modules/autonomous_bot.py`
**Status:** Funcional, mas falta observabilidade
**Gaps Identificados:**
- ✅ Orquestra ciclo completo
- ⚠️ Falta KPIs por ciclo
- ⚠️ Métricas de latência não são registradas

**Melhorias Sugeridas:**
- Registrar KPIs por ciclo:
  - Sinais gerados vs aceitos vs rejeitados (por filtro)
  - Latências (scanner → sinais → filtros → execução)
  - Taxa de sucesso de execução
- Dashboard de performance do bot
- Alertas quando ciclo demora muito

**Impacto:** 🟡 MÉDIO - Melhora observabilidade e debugging

---

## 🟢 PRIORIDADE BAIXA (Otimizações e Expansões)

### 9. `backend/utils/binance_client.py`
**Status:** Funcional, mas pode melhorar retry
**Gaps Identificados:**
- ✅ Já tem lógica robusta
- ⚠️ Retry pode ser centralizado e mais configurável

**Melhorias Sugeridas:**
- Centralizar `_retry_call` com política configurável:
  - max_attempts, base_delay, multiplicador
  - Jitter para evitar thundering herd
  - Códigos de erro específicos da Binance
- Rate limiting mais inteligente
- Circuit breaker para falhas consecutivas

**Impacto:** 🟢 BAIXO - Melhora resiliência

---

### 10. `backend/config/settings.py`
**Status:** Muito completo, mas pode adicionar novas chaves
**Gaps Identificados:**
- ✅ Já tem maioria das configurações
- ⚠️ Algumas chaves sugeridas ainda não implementadas

**Melhorias Sugeridas:**
- Adicionar chaves para observabilidade:
  - ENABLE_METRICS_EXPORT
  - METRICS_EXPORT_INTERVAL
  - ENABLE_PERFORMANCE_LOGGING
- Validação de ranges (ex.: leverage entre 1-20)
- Documentação inline melhorada

**Impacto:** 🟢 BAIXO - Facilita configuração

---

### 11. `backend/api/routes/trading.py`
**Status:** Funcional, mas pode expandir endpoints
**Gaps Identificados:**
- ✅ Endpoints principais implementados
- ⚠️ Pode adicionar endpoints de métricas

**Melhorias Sugeridas:**
- Endpoint `/api/trading/metrics` com KPIs agregados
- Endpoint `/api/trading/performance` com análise de performance
- WebSocket para eventos em tempo real

**Impacto:** 🟢 BAIXO - Melhora integração e observabilidade

---

### 12. `backend/modules/backtester.py`
**Status:** Implementado, mas pode expandir
**Gaps Identificados:**
- ✅ Backtesting básico funciona
- ⚠️ Pode adicionar mais estratégias
- ⚠️ Métricas de backtest podem ser mais detalhadas

**Melhorias Sugeridas:**
- Adicionar mais métricas (Sharpe ratio, Sortino, etc.)
- Suporte a múltiplas estratégias simultâneas
- Walk-forward optimization
- Monte Carlo simulation

**Impacto:** 🟢 BAIXO - Melhora validação de estratégias

---

## 📊 Arquivos de Observabilidade (Novos)

### 13. `backend/modules/metrics_collector.py` (NOVO)
**Sugestão:** Criar módulo dedicado para coletar métricas
**Funcionalidades:**
- Coletar KPIs de todos os módulos
- Exportar para Redis/PostgreSQL
- Dashboard de métricas em tempo real
- Alertas baseados em thresholds

**Impacto:** 🟡 MÉDIO - Melhora significativamente observabilidade

---

### 14. `backend/api/routes/metrics.py` (NOVO)
**Sugestão:** Criar rotas dedicadas para métricas
**Endpoints Sugeridos:**
- `GET /api/metrics/pipeline` - KPIs do pipeline completo
- `GET /api/metrics/execution` - Métricas de execução
- `GET /api/metrics/risk` - Métricas de risco
- `GET /api/metrics/performance` - Performance geral

**Impacto:** 🟡 MÉDIO - Facilita monitoramento

---

## 🎯 Resumo por Prioridade

### 🔴 CRÍTICO (Fazer Primeiro)
1. `risk_manager.py` - Alinhar completamente com settings e adicionar métricas
2. `market_scanner.py` - Otimizar concorrência e cache
3. `signal_generator.py` - Expandir indicadores e melhorar presets

### 🟡 IMPORTANTE (Fazer Depois)
4. `correlation_filter.py` - Seleção greedy max-diversificada
5. `market_filter.py` - Melhorar detecção de dump e scores dinâmicos
6. `order_executor.py` - Adicionar métricas estruturadas
7. `position_monitor.py` - TSL adaptativo e métricas por evento
8. `autonomous_bot.py` - KPIs por ciclo

### 🟢 OPCIONAL (Melhorias Futuras)
9. `binance_client.py` - Retry centralizado
10. `settings.py` - Novas chaves de observabilidade
11. `trading.py` - Endpoints de métricas
12. `backtester.py` - Métricas expandidas

### 📊 NOVOS (Criar)
13. `metrics_collector.py` - Módulo de métricas
14. `metrics.py` (routes) - Endpoints de métricas

---

## 📝 Notas Finais

- **Ordem de Implementação:** Seguir prioridades (🔴 → 🟡 → 🟢)
- **Testes:** Sempre adicionar testes ao evoluir módulos críticos
- **Documentação:** Atualizar README.md e ARCHITECTURE.md após mudanças
- **Métricas:** Focar em observabilidade desde o início
- **Backward Compatibility:** Manter compatibilidade com configurações existentes

---

**Última atualização:** 2025-11-12
**Baseado em:** docs/ARCHITECTURE.md, README.md, LLM_CONTEXT.md

