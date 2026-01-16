---
description: Workflow para corrigir bugs no Vector Protocol
---

# Bug Fix Workflow

Use este workflow ao corrigir bugs.

---

## Passos

### 1. Reproduzir o Bug

Antes de corrigir, confirme que consegue reproduzir:

```bash
# Verificar logs
curl -sS "http://localhost:8000/api/system/logs?component=<module>&tail=100" | jq .

# Ou via Docker
docker logs -f trading-bot-api --tail 100
```

### 2. Criar Branch

```bash
// turbo
git checkout main
git pull origin main
git checkout -b fix/<descrição-do-bug>
```

### 3. Identificar Causa Raiz

Use as skills:

- `project-context` - para entender o módulo
- `trading-module` - se for bug de trading

Ferramentas:

```bash
# Buscar referências
rg "function_name" backend/ -t py

# Ver estrutura do módulo
cat backend/modules/<module>.py | head -100
```

### 4. Escrever Teste de Regressão

**ANTES de corrigir**, escreva um teste que falha:

```python
# backend/tests/test_regression_<bug>.py

def test_bug_scenario():
    """Reproduz o cenário do bug."""
    # Arrange
    # Act
    # Assert - deve falhar antes do fix
```

```bash
// turbo
PYTHONPATH=backend pytest backend/tests/test_regression_<bug>.py -v
```

### 5. Implementar Correção

- Mudanças mínimas necessárias
- Sem refatoração junto com fix
- Adicionar logging se ajudar debug futuro

### 6. Verificar Correção

```bash
// turbo
PYTHONPATH=backend pytest backend/tests/test_regression_<bug>.py -v
```

O teste deve passar agora.

### 7. Rodar Suite Completa

```bash
// turbo
PYTHONPATH=backend pytest -q backend/tests
```

### 8. Atualizar CHANGELOG

```markdown
## [Unreleased]

### Fixed
- Corrigido [descrição do bug] (#issue se houver)
```

### 9. Commit

```bash
git add .
git commit -m "fix(<scope>): <descrição curta do fix>

<descrição mais longa se necessário>

Closes #<issue_number>"
```

### 10. Push e PR

```bash
git push -u origin fix/<descrição-do-bug>
```

---

## Checklist

```
[ ] Bug reproduzido localmente
[ ] Teste de regressão escrito
[ ] Correção implementada
[ ] Teste de regressão passa
[ ] Suite completa passa
[ ] CHANGELOG atualizado
[ ] Commit com formato correto
[ ] PR aberto
```

---

## Para Bugs Críticos (Hotfix)

Se o bug está em produção:

```bash
# Branch de hotfix
git checkout main
git checkout -b hotfix/<descrição>

# Após fix e merge em main, criar tag
git tag -a v1.x.x -m "Hotfix: <descrição>"
git push origin v1.x.x
```
