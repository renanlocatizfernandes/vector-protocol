---
name: code-review
description: Revisa código para bugs, segurança, performance e padrões do projeto Vector Protocol. Use antes de fazer merge ou ao revisar PRs.
---

# Code Review Skill

Este skill fornece um checklist estruturado para revisar código no projeto Vector Protocol.

---

## 🎯 Quando Usar

- Antes de fazer commit/push de mudanças significativas
- Ao revisar Pull Requests
- Após implementar uma nova feature
- Quando solicitado a auditar código existente

---

## ✅ Checklist de Review

### 1. 🔒 Segurança

```
[ ] Sem hardcoded secrets (API keys, passwords, tokens)
[ ] Inputs de usuário validados (especialmente em endpoints)
[ ] Sem exposição de dados sensíveis em logs
[ ] Rate limiting considerado para endpoints públicos
[ ] Sem SQL injection (usar SQLAlchemy ORM corretamente)
[ ] Trading: Validar quantidades contra filters da Binance
[ ] Margin/Leverage: Validações antes de ordens
[ ] Secrets redatados em mensagens de erro/log
```

### 2. ⚡ Performance

```
[ ] Sem N+1 queries no banco de dados
[ ] Uso adequado de cache Redis quando disponível
[ ] Funções async quando chamando I/O (API, DB)
[ ] Loop de análise completa em <5 segundos por símbolo
[ ] Sem bloqueio de event loop (uso de asyncio.to_thread se necessário)
[ ] Conexões HTTP reutilizadas (httpx/aiohttp clients)
[ ] Lazy loading para dados grandes
```

### 3. 📐 Qualidade de Código

```
[ ] Type hints em TODOS os parâmetros e retornos
[ ] Docstrings em funções públicas
[ ] Nomenclatura clara e consistente (snake_case Python, camelCase TypeScript)
[ ] Funções com tamanho adequado (<50 linhas ideal)
[ ] Sem código duplicado significativo
[ ] Imports organizados (stdlib, third-party, local)
[ ] Sem código comentado/morto
```

### 4. 🏗️ Arquitetura

```
[ ] Segue padrões existentes no projeto
[ ] Módulos com responsabilidade única
[ ] Dependências injetadas corretamente (Singleton para binance_client)
[ ] Configurações via Pydantic Settings, não hardcoded
[ ] Erros tratados com mensagens claras
[ ] Logs estruturados com nível apropriado
```

### 5. 🧪 Testes

```
[ ] Testes unitários existem para nova lógica
[ ] Happy path coberto
[ ] Edge cases considerados (valores nulos, limites)
[ ] Mocks apropriados para dependências externas
[ ] Testes passando localmente (pytest, npm test)
```

### 6. 📜 Documentação

```
[ ] README atualizado se necessário
[ ] docs/API_SPEC.md atualizado para novos endpoints
[ ] docs/CHANGELOG.md atualizado
[ ] Docstrings em código novo
[ ] Comentários para lógica complexa
```

### 7. 🔄 Trading Específico

```
[ ] Validação de symbol filters (minQty, stepSize, minNotional)
[ ] Arredondamento correto de quantities
[ ] Position mode verificado (One-Way enforced)
[ ] Handling de erros Binance (-2019 margin, -1111 precision)
[ ] Dry-run testado antes de trades reais
[ ] Risk limits respeitados (max positions, portfolio risk)
```

---

## 📊 Formato de Feedback

Organize seu feedback em três categorias:

### 🔴 **CRÍTICO** (Bloqueia Merge)

Problemas que DEVEM ser corrigidos antes de merge:

- Vulnerabilidades de segurança
- Bugs que causam perda financeira
- Breaking changes não documentadas
- Testes falhando

```markdown
🔴 **CRÍTICO**: [Descrição do problema]
📍 Arquivo: `path/to/file.py`, linha X
💡 Sugestão: [Como corrigir]
```

### 🟡 **IMPORTANTE** (Deveria ser Corrigido)

Problemas que idealmente devem ser corrigidos:

- Code smells significativos
- Performance sub-ótima
- Documentação faltando em áreas chave

```markdown
🟡 **IMPORTANTE**: [Descrição do problema]
📍 Arquivo: `path/to/file.py`, linha X
💡 Sugestão: [Como corrigir]
```

### 🟢 **SUGESTÃO** (Nice to Have)

Melhorias opcionais:

- Refatorações menores
- Estilo de código
- Otimizações possíveis

```markdown
🟢 **SUGESTÃO**: [Descrição da melhoria]
📍 Arquivo: `path/to/file.py`, linha X
💡 Sugestão: [Alternativa proposta]
```

---

## 🔍 Exemplo de Review

```markdown
## Code Review: PR #42 - Add new signal filter

### 🔴 CRÍTICO

1. **Hardcoded API endpoint**
   📍 `backend/modules/new_filter.py`, linha 15
   💡 Mover para `settings.py` como variável de ambiente

### 🟡 IMPORTANTE

1. **Falta type hint no retorno**
   📍 `backend/modules/new_filter.py`, linha 28
   💡 Adicionar `-> Optional[Signal]` no retorno

2. **Sem tratamento de erro para API call**
   📍 `backend/modules/new_filter.py`, linhas 45-50
   💡 Adicionar try/except com retry via tenacity

### 🟢 SUGESTÃO

1. **Docstring poderia incluir exemplo**
   📍 `backend/modules/new_filter.py`, linha 28
   💡 Adicionar seção "Example:" na docstring

---

### ✅ Pontos Positivos
- Boa estrutura de código
- Type hints consistentes
- Testes unitários incluídos

### 📊 Resumo
| Categoria | Qtd |
|-----------|-----|
| 🔴 Crítico | 1 |
| 🟡 Importante | 2 |
| 🟢 Sugestão | 1 |

**Decisão**: ⏸️ Aguardar correção dos itens críticos antes de aprovar.
```

---

## 🛠️ Ferramentas Auxiliares

### Verificar Estilo Python

```bash
# Se tiver ruff/flake8 instalado
cd backend
ruff check .
```

### Rodar Testes

```bash
# Backend
PYTHONPATH=backend pytest -q backend/tests

# Frontend
cd frontend && npm test
```

### Verificar Types (se mypy disponível)

```bash
cd backend
mypy --ignore-missing-imports .
```
