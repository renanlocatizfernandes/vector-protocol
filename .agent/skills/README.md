# Agent Skills - Vector Protocol

Este diretório contém **Agent Skills** personalizadas para o projeto Vector Protocol, otimizadas para uso com Google Antigravity e outros agentes LLM.

---

## 📚 Skills Disponíveis

| Skill | Descrição | Quando Usar |
|-------|-----------|-------------|
| [`project-context`](project-context/SKILL.md) | Contexto completo do projeto | **SEMPRE** no início de tarefas complexas |
| [`code-review`](code-review/SKILL.md) | Checklist de review de código | Antes de merge, ao revisar PRs |
| [`test-generator`](test-generator/SKILL.md) | Geração de testes unitários | Ao criar features, corrigir bugs |
| [`documentation-generator`](documentation-generator/SKILL.md) | Templates de documentação | Ao criar/atualizar docs |
| [`refactor-assistant`](refactor-assistant/SKILL.md) | Guia de refatoração segura | Ao refatorar código |
| [`git-workflow`](git-workflow/SKILL.md) | Padrões Git/Conventional Commits | Ao commitar, criar branches |
| [`trading-module`](trading-module/SKILL.md) | Desenvolvimento de trading | Ao trabalhar com lógica de trading |
| [`api-design`](api-design/SKILL.md) | Design de endpoints FastAPI | Ao criar/modificar APIs |

---

## 🚀 Como Usar

### No Antigravity IDE

As skills são carregadas automaticamente. Ao realizar uma tarefa, o agente identificará a skill relevante e a consultará.

### Manualmente

Referencie a skill pelo nome quando precisar de orientação:

```
Use a skill 'code-review' para revisar o código do PR #42
```

```
Consulte a skill 'project-context' antes de começar
```

---

## 📁 Estrutura de uma Skill

```
skill-name/
├── SKILL.md           # Arquivo principal (obrigatório)
├── scripts/           # Scripts auxiliares (opcional)
├── templates/         # Templates reutilizáveis (opcional)
└── examples/          # Exemplos de uso (opcional)
```

### Formato do SKILL.md

```markdown
---
name: skill-name
description: Breve descrição da skill
---

# Título da Skill

Instruções detalhadas...
```

---

## 🔧 Workflows Relacionados

Os workflows em `.agent/workflows/` usam estas skills:

| Workflow | Skills Usadas |
|----------|---------------|
| `/new-feature` | project-context, git-workflow, test-generator |
| `/bug-fix` | project-context, test-generator |
| `/deploy` | project-context |

---

## 📋 Rules Relacionadas

As rules em `.agent/rules/` complementam as skills:

- `code-style-rules.md` - Padrões de código
- `security-rules.md` - Regras de segurança
- `architecture-rules.md` - Princípios arquiteturais

---

## ➕ Adicionando Novas Skills

1. Crie o diretório: `.agent/skills/nova-skill/`
2. Crie o arquivo: `SKILL.md` com frontmatter YAML
3. Adicione ao README (este arquivo)
4. Teste a skill em um cenário real

### Template Mínimo

```markdown
---
name: nova-skill
description: O que esta skill faz
---

# Nova Skill

## Quando Usar

- Caso 1
- Caso 2

## Instruções

[Instruções detalhadas]

## Exemplos

[Exemplos de uso]
```

---

## 🔗 Recursos Relacionados

- [Antigravity Skills Docs](https://antigravity.google/docs/skills)
- [Agent Skills Standard](https://agentskills.io/home)
- `.ai/` - Contexto adicional para agentes
- `docs/` - Documentação técnica do projeto
