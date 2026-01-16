---
description: Workflow para criar uma nova feature completa no Vector Protocol
---

# New Feature Workflow

Use este workflow ao implementar uma nova funcionalidade.

---

## Pré-requisitos

- [ ] Leia a skill `project-context` para entender a arquitetura
- [ ] Verifique `docs/CHANGE-MAP.md` para impactos potenciais

---

## Passos

### 1. Criar Branch

```bash
// turbo
git checkout main
git pull origin main
git checkout -b feature/<nome-da-feature>
```

### 2. Planejar (se complexo)

Para features complexas, crie um `implementation_plan.md`:

```markdown
# Feature: [Nome]

## Objetivo
[Descrição clara]

## Mudanças Necessárias
- [ ] Backend: [arquivos]
- [ ] Frontend: [arquivos]
- [ ] Docs: [arquivos]

## Riscos
- [Identificar riscos]
```

### 3. Implementar Backend

1. Modificar/criar módulos em `backend/modules/`
2. Adicionar endpoints em `backend/api/routes/`
3. Atualizar settings em `backend/config/settings.py` se necessário

### 4. Implementar Frontend (se aplicável)

1. Adicionar componentes em `frontend/src/components/`
2. Atualizar pages em `frontend/src/pages/`
3. Adicionar API calls em `frontend/src/services/`

### 5. Escrever Testes

```bash
# Criar testes backend
# backend/tests/test_<feature>.py

// turbo
PYTHONPATH=backend pytest backend/tests/test_<feature>.py -v
```

### 6. Atualizar Documentação

- [ ] `docs/API_SPEC.md` - novos endpoints
- [ ] `docs/CHANGELOG.md` - entry da feature
- [ ] Docstrings no código

### 7. Verificar

```bash
// turbo
PYTHONPATH=backend pytest -q backend/tests
```

```bash
// turbo
cd frontend && npm test
```

### 8. Commit e Push

```bash
git add .
git commit -m "feat(<scope>): <descrição>"
git push -u origin feature/<nome-da-feature>
```

### 9. Abrir PR

- Usar template de PR
- Aguardar review

---

## Checklist Final

```
[ ] Código segue padrões (type hints, docstrings)
[ ] Testes passando
[ ] Documentação atualizada
[ ] CHANGELOG atualizado
[ ] Sem secrets no código
[ ] PR aberto com descrição clara
```
