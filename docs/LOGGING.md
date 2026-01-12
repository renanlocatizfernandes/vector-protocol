# Documentação de Logs do Sistema de Trading

> **PR1**: Baseline de Validação e Logs

## Overview
Este documento descreve a estrutura padronizada de logs estruturados, níveis de log, campos padrão e exemplos para cada componente do sistema.

## Índice
1. [Estrutura de Logs Estruturados](#estrutura-de-logs-estruturados)
2. [Níveis de Log](#níveis-de-log)
3. [Context Tracking](#context-tracking)
4. [Logs por Componente](#logs-por-componente)
5. [Análise e Correlação](#análise-e-correlação)

---

## Estrutura de Logs Estruturados

### Formato Padrão (JSON)

Todos os logs estruturados seguem este formato:

```json
{
  "timestamp": "ISO-8601",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "component": "component_name",
  "cycle_id": "UUID",
  "trade_id": "UUID (opcional)",
  "event": "specific_event_name",
  "data": { ...dados específicos do evento... }
}
```

### Campos Padrão

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|--------------|-------------|
| `timestamp` | string (ISO-8601) | ✅ Sim | Timestamp UTC do evento |
| `level` | string | ✅ Sim | Nível de log (INFO, WARNING, ERROR, DEBUG) |
| `component` | string | ✅ Sim | Nome do componente (trading_loop, order_executor, etc.) |
| `cycle_id` | string (UUID) | ✅ Sim | ID único do ciclo de trading |
| `trade_id` | string (UUID) | ❌ Não | ID único do trade (apenas em eventos de trade) |
| `event` | string | ✅ Sim | Nome do evento específico |
| `data` | object | ✅ Sim | Dados específicos do evento |

---

## Níveis de Log

### DEBUG
Informações detalhadas úteis para debugging. Não afeta a produção.

**Quando usar**:
- Detalhes de execução interna
- Estados de variáveis
- Informações de performance granulares

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:00.000Z",
  "level": "DEBUG",
  "component": "order_executor",
  "cycle_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "order_detail",
  "data": {
    "symbol": "BTCUSDT",
    "order_id": 123456789,
    "status": "FILLED",
    "executed_qty": 0.001,
    "avg_price": 50000.5
  }
}
```

### INFO
Informações normais de operação. Fluxo padrão do sistema.

**Quando usar**:
- Início de ciclos
- Execução bem-sucedida
- Estado de componentes
- Métricas de performance

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:00.000Z",
  "level": "INFO",
  "component": "trading_loop",
  "cycle_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "cycle_start",
  "data": {
    "cycle_number": 1234
  }
}
```

### WARNING
Situações anormais que não impedem a operação. Atenção necessária.

**Quando usar**:
- Validações falharam (não críticas)
- Latência acima do threshold
- Rejeições de trades
- Recursos limitados

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:00.000Z",
  "level": "WARNING",
  "component": "trading_loop",
  "cycle_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "latency_validation_failed",
  "data": {
    "stage": "scan",
    "actual_time_sec": 35.123,
    "max_time_sec": 30,
    "exceeded_by_sec": 5.123
  }
}
```

### ERROR
Erros que impedem a operação normal. Investigação necessária.

**Quando usar**:
- Exceções não tratadas
- Falhas críticas de validação
- Timeout de ciclo completo
- Erros de API

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:00.000Z",
  "level": "ERROR",
  "component": "trading_loop",
  "cycle_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "cycle_timeout",
  "data": {
    "actual_time_sec": 195.678,
    "max_time_sec": 180,
    "exceeded_by_sec": 15.678,
    "latencies_breakdown": {
      "scan_time_sec": 12.5,
      "signal_generation_time_sec": 8.3,
      "filter_time_sec": 4.2,
      "execution_time_sec": 45.6
    }
  }
}
```

---

## Context Tracking

### Cycle ID

**Propósito**: Correlacionar todos os eventos de um ciclo de trading.

**Geração**: Gerado no início de cada ciclo no `trading_loop.py`
```python
cycle_id = str(uuid.uuid4())
```

**Ciclo de Vida**:
1. Gerado em `cycle_start`
2. Passado para todos os logs do ciclo
3. Registrado nas métricas do ciclo
4. Expira ao final do ciclo

**Exemplo de Uso**:
```json
// cycle_start
{ "cycle_id": "550e8400-e29b-41d4-a716-446655440000", "event": "cycle_start" }

// scan
{ "cycle_id": "550e8400-e29b-41d4-a716-446655440000", "event": "scan_complete" }

// signal_generation
{ "cycle_id": "550e8400-e29b-41d4-a716-446655440000", "event": "signals_generated" }

// execution
{ "cycle_id": "550e8400-e29b-41d4-a716-446655440000", "event": "trade_execution_start" }

// cycle_complete
{ "cycle_id": "550e8400-e29b-41d4-a716-446655440000", "event": "cycle_complete" }
```

### Trade ID

**Propósito**: Correlacionar eventos específicos de um trade.

**Geração**: Gerado antes de cada execução de trade
```python
trade_id = str(uuid.uuid4())
```

**Exemplo de Uso**:
```json
// trade_execution_start
{ 
  "cycle_id": "550e8400-e29b-41d4-a716-446655440000",
  "trade_id": "660e8400-e29b-41d4-a716-446655440001",
  "event": "trade_execution_start",
  "data": { "symbol": "BTCUSDT" }
}

// order_placed
{ 
  "cycle_id": "550e8400-e29b-41d4-a716-4466554400000",
  "trade_id": "660e8400-e29b-41d4-a716-446655440001",
  "event": "order_placed",
  "data": { "order_id": 123456789 }
}

// trade_execution_success
{ 
  "cycle_id": "550e8400-e29b-41d4-a716-4466554400000",
  "trade_id": "660e8400-e29b-41d4-a716-446655440001",
  "event": "trade_execution_success",
  "data": { "entry_price": 50000.5 }
}
```

---

## Logs por Componente

### Trading Loop

**Eventos Principais**:

| Evento | Nível | Descrição |
|---------|--------|-----------|
| `cycle_start` | INFO | Início de novo ciclo de trading |
| `cycle_complete` | INFO | Ciclo finalizado com sucesso |
| `cycle_error` | ERROR | Erro no ciclo (exceção não tratada) |
| `cycle_timeout` | ERROR | Ciclo excedeu tempo máximo |
| `latency_validation_failed` | WARNING | Validação de latência falhou |
| `trade_execution_start` | INFO | Início da execução de um trade |
| `trade_execution_success` | INFO | Trade executado com sucesso |
| `trade_execution_failed` | WARNING | Trade rejeitado/falhou |
| `trade_execution_error` | ERROR | Erro durante execução de trade |

**Exemplo Completo**:
```json
{
  "timestamp": "2026-01-10T20:00:00.000Z",
  "level": "INFO",
  "component": "trading_loop",
  "cycle_id": "550e8400-e29b-41d4-a716-4466554400000",
  "trade_id": "660e8400-e29b-41d4-a716-4466554400001",
  "event": "trade_execution_success",
  "data": {
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 50000.5,
    "quantity": 0.001
  }
}
```

### Order Executor

**Eventos Principais**:

| Evento | Nível | Descrição |
|---------|--------|-----------|
| `signal_received` | DEBUG | Sinal recebido para execução |
| `validation_passed` | DEBUG | Validação inicial passou |
| `order_placed` | INFO | Ordem enviada para Binance |
| `order_filled` | INFO | Ordem executada completamente |
| `order_partially_filled` | WARNING | Ordem executada parcialmente |
| `order_cancelled` | INFO | Ordem cancelada |
| `slippage_detected` | WARNING | Slippage acima do esperado |
| `execution_error` | ERROR | Erro na execução da ordem |

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:01.000Z",
  "level": "INFO",
  "component": "order_executor",
  "cycle_id": "550e8400-e29b-41d4-a716-4466554400000",
  "trade_id": "660e8400-e29b-41d4-a716-4466554400001",
  "event": "order_filled",
  "data": {
    "symbol": "BTCUSDT",
    "order_id": 123456789,
    "order_type": "LIMIT",
    "side": "BUY",
    "executed_qty": 0.001,
    "avg_price": 50000.5,
    "is_maker": true,
    "slippage_pct": 0.01
  }
}
```

### Risk Manager

**Eventos Principais**:

| Evento | Nível | Descrição |
|---------|--------|-----------|
| `trade_validation_start` | DEBUG | Início da validação de trade |
| `trade_approved` | INFO | Trade aprovado pelo risk manager |
| `trade_rejected` | WARNING | Trade rejeitado pelo risk manager |
| `risk_adjusted` | INFO | Risco ajustado baseado em performance |
| `hard_stop_triggered` | ERROR | Hard stop (diário ou intradiário) ativado |
| `daily_rollover` | INFO | Reset diário de métricas |

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:02.000Z",
  "level": "WARNING",
  "component": "risk_manager",
  "cycle_id": "550e8400-e29b-41d4-a716-4466554400000",
  "event": "trade_rejected",
  "data": {
    "symbol": "BTCUSDT",
    "reason": "Risco total 18% > máximo 15%",
    "current_risk_pct": 0.18,
    "max_risk_pct": 0.15,
    "open_positions": 5
  }
}
```

### Binance Client

**Eventos Principais**:

| Evento | Nível | Descrição |
|---------|--------|-----------|
| `api_call_start` | DEBUG | Início de chamada API |
| `api_call_success` | DEBUG | Chamada API bem-sucedida |
| `api_call_failed` | ERROR | Chamada API falhou |
| `api_retry` | WARNING | Retentativa de chamada API |
| `cache_hit` | DEBUG | Cache Redis usado |
| `cache_miss` | DEBUG | Cache não encontrado |
| `rate_limit_warning` | WARNING | Próximo do rate limit |

**Exemplo**:
```json
{
  "timestamp": "2026-01-10T20:00:03.000Z",
  "level": "DEBUG",
  "component": "binance_client",
  "event": "api_call_success",
  "data": {
    "endpoint": "futures_account",
    "duration_ms": 150,
    "cached": false,
    "response": {
      "totalWalletBalance": 10000.0
    }
  }
}
```

---

## Análise e Correlação

### Buscar Todos os Logs de um Ciclo

```bash
# Usando jq para filtrar por cycle_id
cat logs/trading.log | jq 'select(.cycle_id == "550e8400-e29b-41d4-a716-4466554400000")'
```

### Buscar Todos os Logs de um Trade

```bash
# Usando jq para filtrar por trade_id
cat logs/trading.log | jq 'select(.trade_id == "660e8400-e29b-41d4-a716-4466554400001")'
```

### Buscar Erros de um Ciclo

```bash
# Buscar erros no ciclo
cat logs/trading.log | jq 'select(.cycle_id == "550e8400-e29b-41d4-a716-4466554400000" and .level == "ERROR")'
```

### Calcular Latência Total de um Ciclo

```bash
# Extrair tempo total do ciclo
cat logs/trading.log | \
  jq 'select(.event == "cycle_complete" and .cycle_id == "...") | .data.total_time_sec'
```

### Visualizar Timeline de um Ciclo

```bash
# Gerar timeline ordenada por timestamp
cat logs/trading.log | \
  jq -r 'select(.cycle_id == "...") | "\(.timestamp) [\(.level)] \(.event): \(.data)"' | \
  sort
```

---

## Integração com Ferramentas

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Configuração de Logstash**:
```conf
input {
  file {
    path => "/var/log/trading/trading.log"
    codec => json
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "trading-logs-%{+YYYY.MM.dd}"
  }
}
```

**Kibana Queries**:
- Todos os erros do último ciclo: `level: "ERROR" AND component: "trading_loop"`
- Trades rejeitados hoje: `event: "trade_rejected" AND @timestamp:[now-24h TO now]`
- Latência acima de threshold: `event: "latency_validation_failed"`

### Grafana Loki

**LogQL Queries**:
- Erros do trading_loop: `{component="trading_loop", level="ERROR"}`
- Todos os eventos de um ciclo: `{cycle_id="550e8400-e29b-41d4-a716-4466554400000"}`
- Taxa de rejeição: `event="trade_rejected" | rate(1m)`

---

## Melhores Práticas

### 1. Sempre Usar JSON Estruturado

❌ **Não**:
```python
logger.info(f"Trade executado: {symbol} {direction} @ {price}")
```

✅ **Sim**:
```python
logger.info(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "level": "INFO",
    "component": "order_executor",
    "cycle_id": cycle_id,
    "trade_id": trade_id,
    "event": "trade_execution_success",
    "data": {
        "symbol": symbol,
        "direction": direction,
        "price": price
    }
}))
```

### 2. Incluir Context Tracking

Sempre incluir `cycle_id` em logs de operação e `trade_id` em logs de trade.

### 3. Usar Nível Apropriado

- **DEBUG**: Detalhes técnicos
- **INFO**: Operação normal
- **WARNING**: Anomalias não críticas
- **ERROR**: Falhas que impedem operação

### 4. Dados Relevantes no Campo `data`

Incluir apenas dados relevantes para o evento específico. Evitar duplicação de campos.

### 5. Timestamp UTC

Sempre usar UTC para evitar problemas com fusos horários.

---

## Configuração

### Nível de Log

```bash
# .env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Saída de Log

```bash
# .env
LOG_FORMAT=json  # json ou text
LOG_FILE=logs/trading.log
LOG_ROTATION=true  # rotação automática de arquivos
```

### Estrutura de Arquivos

```
logs/
├── trading.log              # Logs atuais
├── trading-2026-01-09.log  # Logs de ontem
├── trading-2026-01-08.log  # Logs de anteontem
└── errors.log             # Apenas erros (separado)
```

---

## Ações Futuras

- [ ] Implementar logging assíncrono (async logging)
- [ ] Adicionar métricas de volume de logs
- [ ] Implementar compressão de logs antigos
- [ ] Adicionar alertas baseados em padrões de log
- [ ] Integração com sistemas de monitoramento (Prometheus)
