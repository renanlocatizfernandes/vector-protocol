# 🚀 Acompanhamento Contínuo - Instruções Rápidas

## Status Atual ✅
- **Sistema**: Operacional
- **Monitor**: Ativo (rodando em background)
- **Posições Abertas**: 0
- **Total de Trades**: 734
- **Lucro Médio**: ~2-5% por trade

---

## ⚡ Comando Rápido (Use Quando Quiser)

```bash
# Status ULTRA-rápido (2 segundos, 3 queries)
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -c \
  "SELECT 'Abertas: ' || COUNT(*) FROM trades WHERE status='open'; \
   SELECT 'Última: ' || symbol || ' ' || ROUND(pnl_percentage::numeric,1) || '%' FROM trades ORDER BY opened_at DESC LIMIT 1; \
   SELECT 'Total: ' || COUNT(*) FROM trades WHERE status='closed';"
```

**Saída esperada:**
```
 Abertas: 0
 Última: TURBOUSDT LONG 0.0%
 Total: 734
```

---

## 🤖 Monitor Automático (Rodando)

O sistema está acompanhando automaticamente com verificações a cada 2 minutos.

**Se houver mudança** → Você receberá alerta automático
**Se estiver estável** → Mensagem a cada 20 minutos

### Parar o Monitor (se necessário)
```bash
docker exec trading-bot-api pkill -f "smart_monitor"
```

### Reiniciar o Monitor
```bash
docker cp C:/Projetos/Vector\ Protocol/smart_monitor.sh trading-bot-api:/app/
docker exec -d trading-bot-api bash /app/smart_monitor.sh
```

---

## 📊 Três Níveis de Verificação

### **Nível 1: Super Rápido** (Usar para check em 5s)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -t \
  -c "SELECT COUNT(*) FROM trades WHERE status='open';"
```
**Saída**: Um número (0, 1, 2, etc.)

---

### **Nível 2: Resumido** (2-3 segundos)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT status, COUNT(*) FROM trades GROUP BY status;" && \
curl -s http://localhost:8000/api/trading/bot/status | jq '.status' 2>/dev/null
```

**Saída**:
```
 status | count
--------+-------
 closed |   734
---------+-------
"running"
```

---

### **Nível 3: Detalhado** (Se houver alerta)
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT symbol, direction, entry_price, pnl_percentage, \
             take_profit_1, take_profit_2, status, opened_at \
      FROM trades WHERE status='open' OR (status='closed' AND opened_at > now() - interval '1 hour') \
      ORDER BY opened_at DESC LIMIT 10;"
```

---

## 🎯 Quando Intervir

### ❌ **CRÍTICO** - Intervir IMEDIATAMENTE
- [ ] API offline (curl http://localhost:8000 → erro)
- [ ] Banco offline (psql → erro de conexão)
- [ ] Docker containers parados (docker ps → algum container abaixo)
- [ ] Erros repetidos nos logs

### ⚠️ **ATENÇÃO** - Revisar em breve
- [ ] Posição com P&L negativo > -2%
- [ ] Posição aberta > 4 horas
- [ ] Spread > 0.5%

### ✅ **NORMAL** - Deixar rodar
- [ ] Posições abrindo/fechando normalmente
- [ ] P&L positivo em geral
- [ ] Sem posições abertas = aguardando sinal

---

## 📈 Análises Úteis

### Ver Últimos 10 Trades
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT symbol, pnl_percentage, status, opened_at FROM trades \
      ORDER BY opened_at DESC LIMIT 10;"
```

### Lucro Médio das Últimas 24h
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT ROUND(AVG(pnl_percentage)::numeric, 2) as media FROM trades \
      WHERE status='closed' AND opened_at > now() - interval '1 day';"
```

### Estatísticas Gerais
```bash
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT
        COUNT(*) as total,
        ROUND(AVG(pnl_percentage)::numeric, 2) as media,
        MAX(pnl_percentage) as melhor,
        MIN(pnl_percentage) as pior
      FROM trades WHERE status='closed';"
```

---

## 🔍 Logs (Se Precisar Debug)

### Últimos Erros
```bash
docker logs --tail 50 trading-bot-api | grep -E "ERROR|❌|Exception"
```

### Últimos Eventos Importantes
```bash
docker logs --tail 50 trading-bot-api | grep -E "✅|Trade|Position|Order"
```

### Ver Tudo dos Últimos 5 Minutos
```bash
docker logs --since 5m trading-bot-api
```

---

## 📋 Protocolo Recomendado

### **Todo dia de manhã**
```bash
# Verificação de saúde
docker ps
curl http://localhost:8000/health
docker logs trading-bot-api | grep ERROR | wc -l
```

### **Quando receber alerta do monitor**
```bash
# Verificar o que aconteceu
docker logs --tail 20 trading-bot-api | grep -E "✅|❌"
# Ver detalhes
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT symbol, pnl_percentage, status FROM trades ORDER BY opened_at DESC LIMIT 1;"
```

### **Semanalmente**
```bash
# Resumo de desempenho
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT
        COUNT(*) as trades,
        ROUND(AVG(pnl_percentage)::numeric, 2) as media,
        SUM(CASE WHEN pnl_percentage > 0 THEN 1 ELSE 0 END) as vencedores
      FROM trades WHERE opened_at > now() - interval '7 days';"
```

---

## ⚙️ Se Algo Quebrar

### Containers não respondem
```bash
# Reiniciar tudo
docker-compose down
docker-compose up -d

# Aguardar 30 segundos
sleep 30

# Verificar saúde
docker ps
docker logs trading-bot-api | tail -20
```

### Reset de Monitor
```bash
# Parar monitor atual
docker exec trading-bot-api pkill -f smart_monitor

# Limpar estado
rm -f /tmp/vector_state.txt

# Reiniciar
docker exec -d trading-bot-api bash /app/smart_monitor.sh
```

### Posições presas
```bash
# Ver posições abertas
docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
  -c "SELECT * FROM trades WHERE status='open';"

# Se necessário fechar manualmente (CUIDADO):
# docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
#   -c "UPDATE trades SET status='closed', closed_at=NOW() WHERE status='open';"
```

---

## 🎁 Copy-Paste Rápidos

### Dashboard 1-linha
```bash
echo "Pos:" $(docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -t -c "SELECT COUNT(*) FROM trades WHERE status='open';") "| Média:" $(docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -t -c "SELECT ROUND(AVG(pnl_percentage)::numeric,1) FROM trades WHERE status='closed' AND opened_at > now() - interval '1 day';") "%" "| API:" $(curl -s -m 1 http://localhost:8000/health 2>/dev/null | grep -q "ok" && echo "✅" || echo "❌")
```

### Ver apenas erros (últimos 2h)
```bash
docker logs --since 2h trading-bot-api | grep -E "❌|ERROR|Exception|FAIL"
```

### Monitoramento Live
```bash
watch -n 5 'docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -t -c "SELECT COUNT(*) FROM trades WHERE status='"'"'open'"'"';"'
```

---

## 📞 Resumo

| Ação | Comando |
|------|---------|
| Status super rápido | `docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -t -c "SELECT COUNT(*) FROM trades WHERE status='open';"` |
| Ver último trade | `docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -c "SELECT * FROM trades ORDER BY opened_at DESC LIMIT 1;"` |
| Check API | `curl http://localhost:8000/health` |
| Ver erros | `docker logs trading-bot-api \| grep ERROR` |
| Reiniciar tudo | `docker-compose down && docker-compose up -d` |

---

## ✅ Checklist de Conforto

- [x] Monitor automático rodando
- [x] Banco de dados saudável
- [x] API respondendo
- [x] Últimos trades com lucro
- [x] Sistema pronto para próximo sinal

---

**Criado em**: 2026-01-06 21:33
**Status**: ✅ ACOMPANHAMENTO INTELIGENTE ATIVO
**Frequência de Verificação**: A cada 2 minutos (automático)
