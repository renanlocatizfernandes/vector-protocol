# Feature: [NOME_DA_FEATURE]

> **Status**: `DRAFT` | `IN_REVIEW` | `APPROVED` | `IN_PROGRESS` | `DONE`
> **Author**: [nome]
> **Date**: YYYY-MM-DD
> **Spec ID**: FEAT-XXX

---

## 1. Resumo

_Uma frase descrevendo o que será implementado._

## 2. Motivação / Problema

_Por que essa feature é necessária? Qual problema resolve?_

## 3. Requisitos

### 3.1 Funcionais
- [ ] RF01: _Descrição do requisito funcional_
- [ ] RF02: _..._

### 3.2 Não-Funcionais
- [ ] RNF01: _Performance, segurança, etc._

## 4. Design Técnico

### 4.1 Arquitetura
_Diagrama ou descrição de como a feature se integra ao sistema._

### 4.2 Arquivos Afetados
| Arquivo | Mudança |
|---------|---------|
| `backend/modules/xxx.py` | Adicionar função Y |
| `frontend/src/pages/xxx.tsx` | Novo componente |

### 4.3 API Changes (se aplicável)
```
POST /api/xxx
Body: { ... }
Response: { ... }
```

### 4.4 Database Changes (se aplicável)
```sql
-- Migration
ALTER TABLE xxx ADD COLUMN yyy;
```

## 5. Tasks (Implementação)

- [ ] Task 1: Criar estrutura base
- [ ] Task 2: Implementar lógica principal
- [ ] Task 3: Adicionar testes
- [ ] Task 4: Atualizar documentação
- [ ] Task 5: Code review

## 6. Testes

### 6.1 Testes Unitários
- [ ] `test_xxx.py::test_funcao_principal`

### 6.2 Testes de Integração
- [ ] Cenário A: _descrição_
- [ ] Cenário B: _descrição_

### 6.3 Teste Manual
```bash
# Passos para testar manualmente
curl -X POST http://localhost:8000/api/xxx
```

## 7. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| _Descrição_ | Alta/Média/Baixa | _Como mitigar_ |

## 8. Decisões Tomadas

_Link para `/specs/DECISIONS.md#FEAT-XXX` se houver decisões importantes._

## 9. Checklist Final

- [ ] Spec aprovada pelo usuário
- [ ] Código implementado
- [ ] Testes passando
- [ ] Documentação atualizada
- [ ] PR criado/merged

---

## Histórico

| Data | Autor | Mudança |
|------|-------|---------|
| YYYY-MM-DD | nome | Criação inicial |
