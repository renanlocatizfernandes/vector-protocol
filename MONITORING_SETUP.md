# 📊 Sistema de Acompanhamento Inteligente - Vector Protocol

**Status**: ✅ ATIVO E OPERACIONAL
**Data**: 2026-01-06 21:32
**Posições Abertas**: 0
**Total de Trades**: 734 (todos fechados)

---

## 🎯 Objetivo

Acompanhar o sistema **sem gastar tokens desnecessariamente**, focando apenas em **mudanças significativas** e alertas críticos.

---

## ⚙️ Configuração

### Monitor Inteligente (Rodando em Background)
```bash
docker exec -d trading-bot-api bash /app/smart_monitor.sh
```

**Características:**
- ✅ Verifica a cada **2 minutos**
- ✅ Alerta APENAS quando posições abrem/fecham
- ✅ Resume a cada 20 minutos de inatividade
- ✅ Consumo mínimo de tokens
- ✅ Rodando continuamente

---

## 📈 Métricas Monitoradas

### 1. **Posições Abertas** (Crítico)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT COUNT(*) FROM trades WHERE status='open';"
```
**Frequência**: A cada 2 minutos (automático)
**Alerta**: Quando count muda

### 2. **Últimas Transações** (Informativo)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT symbol, direction, pnl_percentage, status FROM trades ORDER BY opened_at DESC LIMIT 5;"
```
**Quando verificar**: Se houver mudança no count

### 3. **Taxa de Lucro** (Análise)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT AVG(pnl_percentage) as avg_pnl, COUNT(*) FROM trades WHERE status='closed';"
```
**Quando verificar**: A cada sessão de testes

### 4. **Saúde da API** (Health Check)
```bash
curl -s http://localhost:8000/api/trading/bot/status | jq '.status'
```
**Frequência**: Sob demanda
**Esperado**: "running" ou "healthy"

---

## 📋 Eventos a Monitorar

### ✅ **Eventos Positivos** (Esperados)
- Posição aberta com sucesso
- Ordem fechada com lucro
- Take Profit ativado
- Breakeven Stop ativado

### ⚠️ **Eventos de Atenção** (Raros)
- Erro ao abrir posição
- Breakeven stop não ativado
- Spread alto (>0.3%)

### 🔴 **Eventos Críticos** (Ação Imediata)
- API offline
- Erro ao conectar Binance
- Capital insuficiente
- Liquidação iminente

---

## 🔄 Protocolo de Acompanhamento

### **Semanal** (Eficiente)
1. Verificar último log crítico
2. Comparar com baseline anterior
3. Analisar tendências

**Comando:**
```bash
docker logs --tail 100 trading-bot-api | grep -E "✅|❌|ERROR" | tail -20
```

### **Quando Alerta Aparecer**
1. Monitor automático notifica
2. Verificar contexto imediato
3. Intervir se necessário
4. Registrar mudanças

**Status Rápido:**
```bash
# Tudo em um comando
echo "=== STATUS ===" && \
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT COUNT(*) as open_trades FROM trades WHERE status='open'; \
      SELECT AVG(pnl_percentage) as avg_pnl FROM trades WHERE status='closed' AND opened_at > now() - interval '1 hour';" && \
curl -s http://localhost:8000/api/trading/bot/status | jq '.status' && \
echo "=== FIM ==="
```

---

## 💾 Estado Persistente

**Arquivo de Estado:**
```
/tmp/vector_state.txt  - Último count de posições
```

Este arquivo é atualizado automaticamente pelo monitor.

---

## 🎛️ Controles

### Iniciar Monitor
```bash
docker exec -d trading-bot-api bash /app/smart_monitor.sh
```

### Parar Monitor (se necessário)
```bash
docker exec trading-bot-api pkill -f "smart_monitor"
```

### Ver Logs do Monitor
```bash
docker logs trading-bot-api | grep "MONITOR\|POSIÇÃO\|alerta"
```

### Reset de Estado
```bash
rm /tmp/vector_state.txt
```

---

## 📊 Dashboard Rápido (Copy-Paste)

Para uma visão geral em segundos:

```bash
#!/bin/bash
echo "📊 DASHBOARD - $(date '+%H:%M:%S')"
echo "========================================="
echo ""
echo "Posições abertas:"
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT COUNT(*) FROM trades WHERE status='open';" | grep -oE '[0-9]+'

echo ""
echo "Últimos 3 trades:"
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT symbol, pnl_percentage, status FROM trades ORDER BY opened_at DESC LIMIT 3;" | tail -3

echo ""
echo "Lucro médio (última hora):"
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT ROUND(AVG(pnl_percentage)::numeric, 2) FROM trades WHERE status='closed' AND opened_at > now() - interval '1 hour';" | grep -oE '[0-9\.\-]+'

echo ""
echo "API Status:"
curl -s -m 2 http://localhost:8000/api/trading/bot/status | python3 -c "import sys,json; print('✅' if json.load(sys.stdin).get('status') else '❌')" 2>/dev/null || echo "❌"
```

---

## 🎯 Cenários de Resposta

### **Cenário 1: Alerta de Nova Posição**
```
Input: Monitor detecta mudança 0 → 1
Ação:
1. Verificar symbol e direção
2. Confirmar TPs configurados
3. Notar entrada no log
```

### **Cenário 2: Posição Fechada**
```
Input: Monitor detecta mudança 1 → 0
Ação:
1. Verificar PnL (lucro/prejuízo)
2. Confirmar se foi por TP, SL ou timeout
3. Registrar para análise
```

### **Cenário 3: Nenhuma Mudança**
```
Input: Monitor - "✅ [20min] Sistema estável - 0 posições"
Ação:
1. Bot aguardando novo sinal
2. Sem ação necessária
3. Continuar acompanhando
```

---

## 📈 Análise de Desempenho

### Weekly Report
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db << 'SQL'
SELECT
    COUNT(*) as total_trades,
    ROUND(AVG(pnl_percentage)::numeric, 2) as avg_pnl,
    MAX(pnl_percentage) as best_trade,
    MIN(pnl_percentage) as worst_trade,
    SUM(CASE WHEN pnl_percentage > 0 THEN 1 ELSE 0 END) as winners
FROM trades
WHERE status='closed'
  AND opened_at > now() - interval '7 days';
SQL
```

---

## ✅ Checklist de Status

- [ ] Monitor rodando (`docker ps | grep trading`)
- [ ] API respondendo (`curl http://localhost:8000/api/trading/bot/status`)
- [ ] Banco de dados conectado (`docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -c "SELECT 1"`)
- [ ] Sem erros críticos (`docker logs trading-bot-api | grep ERROR | wc -l`)
- [ ] Posições sendo executadas (verif últimas 24h)

---

## 🚀 Próximos Passos

1. ✅ Monitor inteligente rodando
2. ⏳ Aguardar primeira mudança de posição
3. 📊 Analisar execução automática
4. 🎯 Ajustar parâmetros se necessário

---

**Última atualização**: 2026-01-06 21:32:56
**Sistema**: ✅ Operacional
**Acompanhamento**: ✅ Ativo
