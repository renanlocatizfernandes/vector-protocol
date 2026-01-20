# Feature: Alerta Telegram de PnL Diário

> **Status**: `APPROVED`
> **Author**: Claude
> **Date**: 2026-01-20
> **Spec ID**: FEAT-001

---

## 1. Resumo

Enviar automaticamente um resumo diário de PnL via Telegram às 23:59 UTC.

## 2. Motivação / Problema

O usuário precisa acompanhar o desempenho diário do bot sem precisar acessar o dashboard manualmente. Um alerta automático no Telegram facilita o monitoramento.

## 3. Requisitos

### 3.1 Funcionais
- [x] RF01: Enviar mensagem Telegram com resumo de PnL às 23:59 UTC
- [x] RF02: Incluir: PnL realizado, PnL não-realizado, número de trades, win rate
- [x] RF03: Permitir habilitar/desabilitar via config

### 3.2 Não-Funcionais
- [x] RNF01: Não falhar silenciosamente (logar erros)
- [x] RNF02: Timeout máximo de 10s para envio

## 4. Design Técnico

### 4.1 Arquitetura
```
[Scheduler] --23:59 UTC--> [DailyReportJob] --> [TelegramNotifier]
                                |
                                v
                          [StatsService] --> DB
```

### 4.2 Arquivos Afetados
| Arquivo | Mudança |
|---------|---------|
| `backend/modules/telegram_bot.py` | Adicionar `send_daily_report()` |
| `backend/modules/scheduler.py` | Adicionar job de 23:59 UTC |
| `backend/config/settings.py` | Adicionar `DAILY_REPORT_ENABLED` |

### 4.3 API Changes
Nenhuma (feature interna).

### 4.4 Database Changes
Nenhuma (usa dados existentes).

## 5. Tasks (Implementação)

- [x] Task 1: Adicionar config `DAILY_REPORT_ENABLED` em settings.py
- [x] Task 2: Criar função `send_daily_report()` em telegram_bot.py
- [x] Task 3: Integrar com scheduler para rodar às 23:59 UTC
- [ ] Task 4: Adicionar teste unitário
- [ ] Task 5: Testar manualmente em staging

## 6. Testes

### 6.1 Testes Unitários
- [ ] `test_telegram.py::test_send_daily_report_format`
- [ ] `test_telegram.py::test_send_daily_report_disabled`

### 6.2 Teste Manual
```bash
# Forçar envio do relatório
curl -X POST "http://localhost:8000/api/trading/test/daily-report"
```

## 7. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Telegram API indisponível | Baixa | Retry com backoff, logar erro |
| Dados de PnL incorretos | Baixa | Usar mesma fonte do dashboard |

## 8. Decisões Tomadas

- Horário 23:59 UTC escolhido para alinhar com fechamento diário da Binance
- Formato de mensagem: texto simples (não markdown) para compatibilidade

## 9. Checklist Final

- [x] Spec aprovada pelo usuário
- [ ] Código implementado
- [ ] Testes passando
- [ ] Documentação atualizada
- [ ] PR criado/merged

---

## Histórico

| Data | Autor | Mudança |
|------|-------|---------|
| 2026-01-20 | Claude | Criação inicial (exemplo) |
