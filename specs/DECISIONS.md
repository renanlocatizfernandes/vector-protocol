# Decision Log

Este arquivo registra decisões técnicas importantes tomadas durante o desenvolvimento.

---

## Como Usar

Ao tomar uma decisão significativa (arquitetura, biblioteca, trade-off), registre aqui:

```markdown
## [ID] Título da Decisão

**Data**: YYYY-MM-DD
**Status**: `PROPOSED` | `ACCEPTED` | `DEPRECATED` | `SUPERSEDED`
**Contexto**: Por que essa decisão foi necessária?
**Decisão**: O que foi decidido?
**Consequências**: Quais os impactos positivos e negativos?
**Alternativas Consideradas**: O que mais foi avaliado?
```

---

## Decisões

### DEC-001 Adoção de Spec-Driven Development (SDD)

**Data**: 2026-01-20
**Status**: `ACCEPTED`
**Contexto**: Necessidade de ter um processo estruturado para implementar features e bugfixes, evitando retrabalho e garantindo qualidade.
**Decisão**: Adotar workflow SDD obrigatório com fases: Requirements → Design → Tasks → Implementation → Verify.
**Consequências**:
- (+) Maior clareza antes de implementar
- (+) Decisões documentadas
- (+) Facilita code review
- (-) Overhead inicial para features pequenas
**Alternativas Consideradas**:
- Desenvolvimento ad-hoc (rejeitado: falta de rastreabilidade)
- TDD puro (complementar, não substitui planejamento)

---

### DEC-002 Cache Redis para API Binance

**Data**: 2026-01-20
**Status**: `ACCEPTED`
**Contexto**: IP sendo banido pela Binance por excesso de requisições.
**Decisão**: Adicionar cache Redis com TTL variável por tipo de dado (preços: 5-10s, sentimento: 60s, histórico: 120s).
**Consequências**:
- (+) Redução de 80%+ nas chamadas à API
- (+) Elimina bans de IP
- (-) Dados ligeiramente defasados (aceitável para trading)
**Alternativas Consideradas**:
- Rate limiting simples (insuficiente)
- Reduzir frequência de scan (prejudica oportunidades)

---

### DEC-003 Não Fechar Posições Negativas Automaticamente

**Data**: 2026-01-20
**Status**: `ACCEPTED`
**Contexto**: Usuário prefere manter controle manual sobre fechamento de posições em prejuízo.
**Decisão**: Claude NÃO deve fechar posições negativas a menos que o usuário peça EXPLICITAMENTE.
**Consequências**:
- (+) Usuário mantém controle total sobre gestão de risco
- (+) Evita fechamento prematuro antes de recuperação
- (-) Requer monitoramento manual em casos extremos
**Regra**: Aguardar reversão do mercado ou ordem explícita do usuário.

---

<!-- Adicione novas decisões abaixo -->
