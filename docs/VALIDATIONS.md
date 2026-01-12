# Documentação de Validações do Sistema de Trading

> **PR1**: Baseline de Validação e Logs

## Overview
Este documento descreve todas as validações implementadas no sistema de trading, incluindo thresholds, parâmetros configuráveis e ações tomadas quando uma validação falha.

## Índice
1. [Validações de Latência](#validações-de-latência)
2. [Validações de Risco](#validações-de-risco)
3. [Validações de Execução](#validações-de-execução)
4. [Validações de Mercado](#validações-de-mercado)
5. [Validações de Dados](#validações-de-dados)

---

## Validações de Latência

### 1.1 Validação de Latência de Scan

**Componente**: `trading_loop.py`

**Threshold**:
```python
MAX_SCAN_TIME_SEC = 30  # segundos
```

**Descrição**: Valida o tempo máximo para escanear o mercado e obter candidatos para trades.

**Ação em Falha**:
- Log WARNING estruturado com tempo excedido
- Continua o ciclo normalmente (warning apenas)

**Dados Logados**:
```json
{
  "timestamp": "ISO-8601",
  "level": "WARNING",
  "component": "trading_loop",
  "cycle_id": "UUID",
  "event": "latency_validation_failed",
  "data": {
    "stage": "scan",
    "actual_time_sec": 35.123,
    "max_time_sec": 30,
    "exceeded_by_sec": 5.123
  }
}
```

---

### 1.2 Validação de Latência de Geração de Sinal

**Componente**: `trading_loop.py`

**Threshold**:
```python
MAX_SIGNAL_TIME_SEC = 30  # segundos
```

**Descrição**: Valida o tempo máximo para gerar sinais de trading baseados em indicadores técnicos.

**Ação em Falha**:
- Log WARNING estruturado
- Continua o ciclo normalmente

**Dados Logados**:
```json
{
  "timestamp": "ISO-8601",
  "level": "WARNING",
  "component": "trading_loop",
  "cycle_id": "UUID",
  "event": "latency_validation_failed",
  "data": {
    "stage": "signal_generation",
    "actual_time_sec": 32.456,
    "max_time_sec": 30,
    "exceeded_by_sec": 2.456,
    "symbols_scanned": 50
  }
}
```

---

### 1.3 Validação de Latência de Filtros

**Componente**: `trading_loop.py`

**Threshold**:
```python
MAX_FILTER_TIME_SEC = 15  # segundos
```

**Descrição**: Valida o tempo máximo para aplicar filtros de mercado e correlação.

**Ação em Falha**:
- Log WARNING estruturado
- Continua o ciclo normalmente

**Dados Logados**:
```json
{
  "timestamp": "ISO-8601",
  "level": "WARNING",
  "component": "trading_loop",
  "cycle_id": "UUID",
  "event": "latency_validation_failed",
  "data": {
    "stage": "market_filter" | "correlation_filter",
    "actual_time_sec": 18.234,
    "max_time_sec": 15,
    "exceeded_by_sec": 3.234,
    "signals_filtered": 25
  }
}
```

---

### 1.4 Validação de Latência de Execução

**Componente**: `trading_loop.py`

**Threshold**:
```python
MAX_EXECUTION_TIME_SEC = 60  # segundos
```

**Descrição**: Valida o tempo máximo para executar todas as ordens de um ciclo.

**Ação em Falha**:
- Log WARNING estruturado
- Continua o ciclo normalmente

**Dados Logados**:
```json
{
  "timestamp": "ISO-8601",
  "level": "WARNING",
  "component": "trading_loop",
  "cycle_id": "UUID",
  "event": "latency_validation_failed",
  "data": {
    "stage": "execution",
    "actual_time_sec": 72.345,
    "max_time_sec": 60,
    "exceeded_by_sec": 12.345,
    "signals_to_execute": 3
  }
}
```

---

### 1.5 Validação de Timeout do Ciclo

**Componente**: `trading_loop.py`

**Threshold**:
```python
TOTAL_CYCLE_TIMEOUT_SEC = 180  # segundos (3 minutos)
```

**Descrição**: Valida o tempo total de um ciclo completo de trading.

**Ação em Falha**:
- Log ERROR estruturado
- Continua para o próximo ciclo

**Dados Logados**:
```json
{
  "timestamp": "ISO-8601",
  "level": "ERROR",
  "component": "trading_loop",
  "cycle_id": "UUID",
  "event": "cycle_timeout",
  "data": {
    "actual_time_sec": 195.678,
    "max_time_sec": 180,
    "exceeded_by_sec": 15.678,
    "latencies_breakdown": {
      "scan_time_sec": 12.5,
      "signal_generation_time_sec": 8.3,
      "filter_time_sec": 4.2,
      "execution_time_sec": 45.6,
      "total_cycle_time_sec": 195.678
    }
  }
}
```

---

## Validações de Risco

### 2.1 Validação de Risco por Trade

**Componente**: `risk_manager.py`

**Threshold**:
```python
RISK_PER_TRADE = 0.02  # 2% do capital
SNIPER_RISK_PER_TRADE = 0.01  # 1% para trades sniper
```

**Ajuste Dinâmico**:
- Aumenta +30% após 5+ wins consecutivos
- Aumenta +20% após 3+ wins consecutivos
- Reduz -40% após 3+ losses consecutivos
- Reduz -20% após 2+ losses consecutivos

**Descrição**: Valida que o risco por trade não excede o percentual configurado.

**Ação em Falha**:
- Rejeita o trade
- Log WARNING com motivo da rejeição
- Registra métrica de rejeição

---

### 2.2 Validação de Risco Total de Portfólio

**Componente**: `risk_manager.py`

**Threshold**:
```python
MAX_PORTFOLIO_RISK = 0.15  # 15% do capital
```

**Descrição**: Valida que o risco total de todas as posições não excede o limite.

**Ação em Falha**:
- Rejeita o trade
- Log WARNING com risco atual
- Registra métrica de rejeição

---

### 2.3 Validação de Máximo de Posições

**Componente**: `risk_manager.py`

**Threshold**:
```python
MAX_POSITIONS = 5  # posições simultâneas
SNIPER_EXTRA_SLOTS = 2  # slots extras para trades sniper
```

**Descrição**: Limita o número máximo de posições abertas simultaneamente.

**Ação em Falha**:
- Rejeita o trade
- Log WARNING com contagem atual
- Registra métrica de rejeição

---

### 2.4 Hard Stop Diário

**Componente**: `risk_manager.py`

**Threshold**:
```python
DAILY_MAX_LOSS_PCT = 0.0  # configurável (ex: 0.05 = 5%)
```

**Descrição**: Para todos os trades se a perda diária exceder o limite.

**Ação em Falha**:
- Rejeita todos os novos trades
- Log ERROR
- Notifica via Telegram

**Persistência**: Redis (48h TTL)

---

### 2.5 Hard Stop Intradiário (Drawdown)

**Componente**: `risk_manager.py`

**Threshold**:
```python
INTRADAY_DRAWDOWN_HARD_STOP_PCT = 0.0  # configurável
```

**Descrição**: Para todos os trades se o drawdown do pico intradiário exceder o limite.

**Ação em Falha**:
- Rejeita todos os novos trades
- Log ERROR
- Notifica via Telegram

**Persistência**: Redis (48h TTL)

---

## Validações de Execução

### 3.1 Validação de Spread Bid/Ask

**Componente**: `order_executor.py`

**Threshold**:
```python
max_spread_pct = 0.3  # 0.3%
```

**Descrição**: Valida que o spread entre bid e ask não excede o limite.

**Ação em Falha**:
- Rejeita o trade
- Log WARNING com spread atual

---

### 3.2 Validação de Profundidade do Order Book

**Componente**: `order_executor.py`

**Threshold**:
```python
MIN_LIQUIDITY_DEPTH_USDT = 100000.0  # $100k
```

**Descrição**: Valida a liquidez disponível no order book dentro de 5% do preço.

**Ação em Falha**:
- Log WARNING (não bloqueia trade)
- Avisa sobre risco de slippage

---

### 3.3 Validação de maxQty

**Componente**: `order_executor.py`

**Descrição**: Valida que a quantidade calculada não excede maxQty do símbolo.

**Ação em Falha**:
- Ajusta quantidade para 95% do máximo
- Continua com trade

---

### 3.4 Validação de Notional Mínimo

**Componente**: `order_executor.py`

**Descrição**: Valida que o valor notional da posição não está abaixo do mínimo exigido pela Binance.

**Ação em Falha**:
- Rejeita o trade
- Log WARNING

---

## Validações de Mercado

### 4.1 Validação de Sentimento de Mercado

**Componente**: `market_filter.py`

**Descrição**: Valida condições de mercado (tendência BTC, volume, volatilidade).

**Ação em Falha**:
- Rejeita sinais do símbolo
- Registra métrica de rejeição

---

### 4.2 Validação de Correlação

**Componente**: `correlation_filter.py`

**Threshold**:
```python
MAX_CORRELATION = 0.8  # 80%
CORR_WINDOW_DAYS = 30
```

**Descrição**: Evita abrir posições em símbolos altamente correlacionados com posições existentes.

**Ação em Falha**:
- Rejeita sinais correlacionados
- Seleciona símbolo mais diversificado

---

## Validações de Dados

### 5.1 Validação de Campos Obrigatórios

**Componente**: `binance_client.py`

**Descrição**: Valida presença de campos obrigatórios em respostas da API.

**Campos Validados**:
- Preço (> 0)
- Quantidade (> 0)
- Timestamp válido

**Ação em Falha**:
- Log ERROR
- Retorna None ou valor default

---

### 5.2 Validação de Consistência Cache vs API

**Componente**: `binance_client.py`

**Descrição**: Compara dados em cache com API para detectar divergências.

**Ação em Falha**:
- Invalida cache
- Log WARNING
- Rebusca dados da API

---

## Métricas de Validação

Todas as validações geram métricas:

```python
{
  "total_trades_validated": 1234,
  "total_trades_approved": 987,
  "total_trades_rejected": 247,
  "rejection_reasons": {
    "risk_manager": 123,
    "market_filter": 87,
    "correlation_filter": 25,
    "execution_failed": 12
  },
  "approval_rate": 79.9  # %
}
```

---

## Configuração

Todos os thresholds são configuráveis via `config/settings.py` ou `.env`:

```bash
# Latência
MAX_SCAN_TIME_SEC=30
MAX_SIGNAL_TIME_SEC=30
MAX_FILTER_TIME_SEC=15
MAX_EXECUTION_TIME_SEC=60
TOTAL_CYCLE_TIMEOUT_SEC=180

# Risco
RISK_PER_TRADE=0.02
SNIPER_RISK_PER_TRADE=0.01
MAX_PORTFOLIO_RISK=0.15
MAX_POSITIONS=5
SNIPER_EXTRA_SLOTS=2
DAILY_MAX_LOSS_PCT=0.05
INTRADAY_DRAWDOWN_HARD_STOP_PCT=0.03

# Execução
MAX_SPREAD_PCT=0.3
MIN_LIQUIDITY_DEPTH_USDT=100000.0
MAX_CORRELATION=0.8
CORR_WINDOW_DAYS=30
```

---

## Ações Futuras

- [ ] Validação de anomalias em slippage
- [ ] Validação de anomalias em latência de API
- [ ] Detecção de padrões de erro repetitivos
- [ ] Validação de recursos do sistema (memória, CPU)
