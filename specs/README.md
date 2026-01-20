# Specs - Spec-Driven Development

## Fluxo em 10 Linhas

1. **Toda mudança significativa** precisa de uma spec aprovada antes de codar
2. **Feature nova?** Copie `_TEMPLATE_FEATURE.md` → `FEAT-XXX-nome.md`
3. **Bugfix?** Copie `_TEMPLATE_BUGFIX.md` → `BUG-XXX-nome.md`
4. **Preencha** as seções de Requirements e Design
5. **Aguarde aprovação** do usuário/reviewer
6. **Implemente** seguindo as tasks definidas na spec
7. **Rode testes**: `pytest` (backend) + `npm test` (frontend)
8. **Atualize** o status da spec para `DONE`
9. **Decisões importantes?** Registre em `DECISIONS.md`
10. **Commit** com referência à spec: `feat(FEAT-001): implementa X`

## Estrutura

```
/specs/
├── README.md                    # Este arquivo
├── DECISIONS.md                 # Log de decisões técnicas
├── _TEMPLATE_FEATURE.md         # Template para features
├── _TEMPLATE_BUGFIX.md          # Template para bugfixes
├── FEAT-001-nome-feature.md     # Specs de features
├── BUG-001-nome-bug.md          # Specs de bugfixes
└── SYSTEM_SPEC.md               # Spec geral do sistema
```

## Comandos Rápidos

```bash
# Validar antes de finalizar
PYTHONPATH=backend pytest -q backend/tests   # Backend
cd frontend && npm test                       # Frontend
cd frontend && npm run build                  # TypeCheck
```
