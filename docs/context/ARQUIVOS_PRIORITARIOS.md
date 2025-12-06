# 📋 Arquivos Prioritários para Evolução do Bot (ATUALIZADO)

Este documento reflete o estado atual do projeto após análise do código v4.0/v5.0 e define os próximos passos reais.

---

## 🟢 ESTADO ATUAL (Implementado)

### ✅ `backend/modules/risk_manager.py` (v4.0)
- **Status:** IMPLEMENTADO
- **Features:** Tracking de performance, auto-ajuste de risco, hard stops diários, métricas detalhadas.
- **Ação:** Manter e monitorar.

### ✅ `backend/modules/market_scanner.py` (v4.0)
- **Status:** IMPLEMENTADO
- **Features:** Cache inteligente, semáforo de concorrência, priorização por volatilidade/movimento.
- **Ação:** Ajustar parâmetros de concorrência se houver rate limit.

### ✅ `backend/modules/signal_generator.py` (v5.0)
- **Status:** IMPLEMENTADO
- **Features:** ADX Filter, VWAP, RSI Divergence, MACD, Bollinger Bands.
- **Ação:** Refinar thresholds em produção.

---

## 🟡 PRIORIDADE MÉDIA (Otimizações Pendentes)

### 1. Observabilidade Centralizada
Apesar de os módulos terem métricas internas (`_metrics`), não há um coletor central robusto exportando para um dashboard unificado.
- **Tarefa:** Integrar `metrics_collector.py` (já existente no esqueleto) com os módulos principais.
- **Objetivo:** Ter um endpoint `/api/metrics` funcional.

### 2. Testes Automatizados
O ambiente possui `pytest`, mas a cobertura dos novos recursos v4/v5 precisa ser verificada.
- **Tarefa:** Criar/Atualizar testes para `SignalGenerator` v5.0 e `RiskManager` v4.0.

### 3. Documentação de API
- **Tarefa:** Atualizar Swagger/OpenAPI docs com os novos endpoints e parâmetros de settings.

---

## 🔴 GAP IDENTIFICADO
Os arquivos de documentação anteriores estavam desatualizados em relação ao código. O código está muito mais avançado.
A prioridade agora deve ser **Estabilidade e Observabilidade** do que já foi construído, em vez de "nova features".

**Recomendação de Próximos Passos:**
1. Garantir que o bot roda estável com `python3 backend/main.py` ou via supervisor.
2. Monitorar logs para validar a lógica v5.0 em ação.
3. Criar dashboard simples (pode ser log-based) para visualizar as métricas do `RiskManager`.
