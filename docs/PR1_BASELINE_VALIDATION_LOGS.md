# PR1: Baseline de Validação e Logs

> **Status**: IN PROGRESS
> **Priority**: HIGH
> **Target**: Estabilizar e observabilizar o sistema de trading

## Objetivo
Implementar melhorias críticas de validação e padronização de logs para garantir robustez e observabilidade do sistema de trading.

## Análise do Estado Atual

### Validações Existentes
✅ **order_executor.py**:
- Validação de spread bid/ask (max 0.3%)
- Validação de order book depth
- Validação de maxQty antes de calcular posição
- Validação de notional mínimo
- Validações de margem (cross/isolated)

✅ **risk_manager.py**:
- Validação de risco por trade
- Validação de risco total de portfólio
- Hard stops diários e intradiários
- Controle de posições máximas

✅ **binance_client.py**:
- Retry com backoff exponencial
- Validação de erros fatais (-1003, -4061)
- Cache Redis para reduzir chamadas

### Logs Existentes
✅ **Logs estruturados (JSON) em v4.0**:
- Métricas de execução (order_executor)
- Logs de validação (risk_manager)
- Métricas de ciclo (trading_loop)

### Gaps Identificados

#### Validações
❌ **Faltando/Incompletos**:
1. Validação de latência máxima por etapa do ciclo
2. Validação de consistência de dados entre API e cache
3. Validação de estado do sistema antes de novos trades
4. Detecção de anomalias em métricas (spikes de latência, slippage anormal)

#### Logs
❌ **Faltando/Incompletos**:
1. Context tracking (cycle_id, trade_id) para correlação de eventos
2. Logs estruturados padronizados em todos os módulos
3. Métricas de latência detalhadas por componente
4. Agregação de erros para análise de padrões

## Plano de Implementação

### Fase 1: Melhorias de Validação

#### 1.1 Validação de Latência por Etapa
**Arquivos**: `backend/modules/bot/trading_loop.py`, `backend/utils/logger.py`

**Implementação**:
```python
# Adicionar validação de latência máxima por etapa
MAX_SCAN_TIME_SEC = 30
MAX_SIGNAL_TIME_SEC = 30
MAX_FILTER_TIME_SEC = 15
MAX_EXECUTION_TIME_SEC = 60
```

#### 1.2 Validação de Consistência de Dados
**Arquivos**: `backend/utils/binance_client.py`

**Implementação**:
- Validar campos obrigatórios em respostas da API
- Detectar valores inconsistentes (preço <= 0, quantidade <= 0)
- Comparar dados de cache com API para divergências

#### 1.3 Validação de Estado do Sistema
**Arquivos**: `backend/modules/supervisor.py`

**Implementação**:
- Verificar health de componentes antes de novos trades
- Validação de circuit breaker
- Validação de recursos (memória, CPU)

### Fase 2: Melhorias de Logs

#### 2.1 Context Tracking
**Arquivos**: `backend/utils/logger.py`, `backend/modules/bot/trading_loop.py`

**Implementação**:
```python
# Adicionar context tracking
- cycle_id: UUID único por ciclo de trading
- trade_id: UUID único por trade
- correlation_id: Para correlação entre eventos
```

#### 2.2 Padronização de Logs Estruturados
**Arquivos**: Todos os módulos

**Formato padrão**:
```json
{
  "timestamp": "ISO-8601",
  "level": "INFO|WARNING|ERROR",
  "component": "trading_loop|order_executor|risk_manager",
  "cycle_id": "UUID",
  "trade_id": "UUID (opcional)",
  "event": "evento_especifico",
  "data": { ...dados específicos... }
}
```

#### 2.3 Métricas de Latência Detalhadas
**Arquivos**: `backend/modules/bot/trading_loop.py`, `backend/modules/metrics_collector.py`

**Implementação**:
- Latência por componente (scanner, signal, filter, executor)
- Latência de API calls
- Latência de operações de banco
- Latência de cache (Redis hits/misses)

#### 2.4 Agregação de Erros
**Arquivos**: `backend/utils/logger.py`, `backend/modules/error_aggregator.py`

**Implementação**:
- Contagem de erros por tipo e componente
- Detecção de padrões de erro
- Alertas para spikes de erros

### Fase 3: Documentação e Testes

#### 3.1 Documentação de Validações
**Arquivo**: `docs/VALIDATIONS.md` (novo)

**Conteúdo**:
- Lista de todas as validações implementadas
- Thresholds e parâmetros configuráveis
- Ações tomadas quando validação falha

#### 3.2 Documentação de Logs
**Arquivo**: `docs/LOGGING.md` (novo)

**Conteúdo**:
- Estrutura de logs estruturados
- Níveis de log e quando usar
- Campos padrão
- Exemplos de logs para cada componente

#### 3.3 Testes de Validação
**Arquivo**: `backend/tests/test_validations.py` (novo)

**Testes**:
- Validação de latência máxima
- Validação de consistência de dados
- Validação de estado do sistema
- Testes de integração

## Checklist de Implementação

### Fase 1: Validações
- [x] 1.1 Implementar validação de latência máxima por etapa
- [ ] 1.2 Implementar validação de consistência de dados
- [ ] 1.3 Implementar validação de estado do sistema
- [ ] 1.4 Adicionar testes para validações

### Fase 2: Logs
- [x] 2.1 Implementar context tracking (cycle_id, trade_id)
- [x] 2.2 Padronizar logs estruturados (JSON)
- [x] 2.3 Implementar métricas de latência detalhadas
- [ ] 2.4 Implementar agregação de erros

### Fase 3: Documentação
- [x] 3.1 Criar docs/VALIDATIONS.md
- [x] 3.2 Criar docs/LOGGING.md
- [ ] 3.3 Criar backend/tests/test_validations.py

## Critérios de Aceite

✅ **Validações**:
- Todas as validações implementadas têm testes
- Latência máxima respeitada em todos os componentes
- Inconsistências de dados detectadas e logadas
- Estado do sistema validado antes de novos trades

✅ **Logs**:
- Todos os logs seguem formato estruturado padronizado
- Context tracking (cycle_id, trade_id) presente em todos os logs relevantes
- Métricas de latência disponíveis para todos os componentes críticos
- Erros agregados e monitorados

✅ **Documentação**:
- VALIDATIONS.md documenta todas as validações
- LOGGING.md documenta estrutura e uso de logs
- Testes cobrem todas as validações

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Adicionar muita latência com validações | Alto | Validar performance em testes de carga |
| Logs excessivos impactando performance | Médio | Configurar nível de log dinâmico |
| Complexidade de context tracking | Médio | Usar contexto do Python (contextvars) |
| Testes de validação frágeis | Baixo | Mock de dependências externas |

## Próximos Passos

Após PR1, o sistema terá:
- Validações robustas em todos os pontos críticos
- Observabilidade completa através de logs estruturados
- Base sólida para melhorias futuras

PR2 pode focar em:
- Otimização de performance
- Melhorias na interface de monitoramento
- Adição de alertas inteligentes
