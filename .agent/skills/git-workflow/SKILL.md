---
name: git-workflow
description: Padroniza commits, branches e PRs do projeto Vector Protocol seguindo Conventional Commits.
---

# Git Workflow Skill

Este skill padroniza o fluxo de trabalho Git para o projeto Vector Protocol.

---

## 🎯 Quando Usar

- Ao criar novas branches
- Ao escrever mensagens de commit
- Ao abrir Pull Requests
- Para manter histórico limpo

---

## 🌳 Estratégia de Branches

### Branch Principal

- `main` - Branch de produção, sempre estável

### Branches de Trabalho

```
feature/   → Novas funcionalidades
fix/       → Correções de bugs
hotfix/    → Correções urgentes em produção
refactor/  → Refatorações sem mudança de comportamento
docs/      → Atualizações de documentação
test/      → Adição/modificação de testes
chore/     → Tarefas de manutenção
```

### Nomenclatura

```
<tipo>/<descrição-curta>

Exemplos:
feature/add-trailing-stop
fix/margin-calculation-overflow
hotfix/critical-order-execution
refactor/simplify-risk-calculator
docs/update-api-spec
test/add-signal-generator-tests
chore/update-dependencies
```

### Com Ticket (se aplicável)

```
<tipo>/<ticket>-<descrição>

Exemplos:
feature/VEC-123-add-trailing-stop
fix/VEC-456-margin-overflow
```

---

## 📝 Conventional Commits

### Formato

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types Permitidos

| Type | Descrição | Exemplo |
|------|-----------|---------|
| `feat` | Nova funcionalidade | `feat(executor): add post-only order mode` |
| `fix` | Correção de bug | `fix(scanner): resolve infinite loop on empty response` |
| `docs` | Documentação | `docs: update API_SPEC with new endpoints` |
| `style` | Formatação (sem mudança de código) | `style: fix indentation in risk_calculator` |
| `refactor` | Refatoração sem mudança de comportamento | `refactor: extract margin logic to separate module` |
| `test` | Testes | `test: add unit tests for signal generator` |
| `chore` | Manutenção | `chore: update fastapi to 0.115.0` |
| `perf` | Performance | `perf: optimize klines caching strategy` |
| `ci` | CI/CD | `ci: add branch protection rules` |
| `build` | Build/Deps | `build: update docker base image` |
| `revert` | Reverter commit | `revert: feat(executor): add post-only mode` |

### Scopes Comuns

| Scope | Descrição |
|-------|-----------|
| `executor` | Order executor module |
| `scanner` | Market scanner |
| `signals` | Signal generator |
| `risk` | Risk calculator/manager |
| `bot` | Autonomous bot |
| `api` | API routes |
| `ui` | Frontend components |
| `config` | Settings/Configuration |
| `db` | Database models/migrations |
| `telegram` | Telegram notifications |

### Exemplos Completos

#### Commit Simples

```
feat(signals): add RSI divergence detection
```

#### Commit com Body

```
fix(executor): handle Binance -2019 insufficient margin error

The executor now catches -2019 error code and:
- Reduces position size by 20%
- Retries order execution
- Notifies via Telegram if still fails

Closes #42
```

#### Breaking Change

```
feat(api)!: change position response format

BREAKING CHANGE: The /api/trading/positions endpoint now returns
positions grouped by symbol instead of flat list.

Migration:
- Old: response.positions[]
- New: response.positions[symbol][]
```

---

## 🔀 Pull Request Template

```markdown
## Descrição

Breve descrição do que este PR faz.

## Tipo de Mudança

- [ ] 🆕 Nova feature
- [ ] 🐛 Bug fix
- [ ] 📝 Documentação
- [ ] 🔧 Refatoração
- [ ] ⚡ Performance
- [ ] 🧪 Testes

## Mudanças Específicas

- Change 1
- Change 2

## Screenshots (se UI)

[Adicionar screenshots se aplicável]

## Checklist

- [ ] Código segue os padrões do projeto
- [ ] Testes passando localmente
- [ ] Documentação atualizada
- [ ] CHANGELOG.md atualizado
- [ ] Sem secrets/credentials no código

## Testes

Como testar esta mudança:

1. Step 1
2. Step 2
3. Expected result

## Issues Relacionados

Closes #XX
Refs #YY
```

---

## 📋 Fluxo de Trabalho Padrão

### 1. Criar Branch

```bash
# Atualizar main
git checkout main
git pull origin main

# Criar branch de feature
git checkout -b feature/add-new-signal-filter
```

### 2. Fazer Commits

```bash
# Adicionar mudanças
git add backend/modules/signal_generator.py

# Commit com mensagem convencional
git commit -m "feat(signals): add momentum filter for signal validation"

# Múltiplos commits pequenos são preferidos
git commit -m "test(signals): add tests for momentum filter"
git commit -m "docs: update signal generator documentation"
```

### 3. Push e PR

```bash
# Push branch
git push -u origin feature/add-new-signal-filter

# Abrir PR via GitHub/CLI
```

### 4. Após Aprovação

```bash
# Merge (feito via GitHub geralmente)
# Ou localmente:
git checkout main
git merge feature/add-new-signal-filter
git push origin main

# Limpar branch local
git branch -d feature/add-new-signal-filter
```

---

## 🔧 Comandos Git Úteis

### Verificar Status

```bash
git status                    # Ver arquivos modificados
git diff                      # Ver mudanças não staged
git diff --staged             # Ver mudanças staged
git log --oneline -10         # Últimos 10 commits
```

### Antes de Commit

```bash
# Verificar se testes passam
PYTHONPATH=backend pytest -q backend/tests
cd frontend && npm test
```

### Reverter Mudanças

```bash
git checkout -- file.py       # Descartar mudanças em arquivo
git reset HEAD~1              # Desfazer último commit (manter mudanças)
git reset --hard HEAD~1       # Desfazer último commit (perder mudanças)
```

### Rebase (manter histórico limpo)

```bash
# Atualizar branch com main
git checkout feature/my-feature
git rebase main

# Interactive rebase para squash commits
git rebase -i HEAD~3  # Últimos 3 commits
```

---

## ⚠️ Regras Importantes

1. **NUNCA** force push em `main`
2. **SEMPRE** test antes de commit
3. **PREFIRA** commits pequenos e atômicos
4. **USE** Conventional Commits consistentemente
5. **SQUASH** commits de WIP antes de merge
6. **REVISE** diff antes de commit (`git diff --staged`)

---

## 📚 Recursos

### Commit Template (opcional)

Adicione em `.git/hooks/commit-msg`:

```bash
#!/bin/sh
# Validate Conventional Commits format

commit_regex='^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?(!)?: .{1,72}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "ERROR: Commit message must follow Conventional Commits format"
    echo "Example: feat(scope): add new feature"
    exit 1
fi
```

Tornar executável: `chmod +x .git/hooks/commit-msg`
