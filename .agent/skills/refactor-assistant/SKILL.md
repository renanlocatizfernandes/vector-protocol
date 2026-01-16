---
name: refactor-assistant
description: Auxilia refatorações mantendo compatibilidade, testes e padrões do projeto Vector Protocol.
---

# Refactor Assistant Skill

Este skill guia refatorações seguras no projeto Vector Protocol, garantindo compatibilidade e qualidade.

---

## 🎯 Quando Usar

- Ao extrair código duplicado
- Ao renomear classes/funções
- Ao reorganizar módulos
- Ao otimizar performance
- Ao atualizar dependências

---

## 🔄 Processo de Refatoração Segura

### Fase 1: Análise de Impacto

Antes de modificar qualquer código:

```
1. IDENTIFICAR todos os usos do código alvo
   - grep_search por nome da função/classe
   - Verificar imports em outros módulos
   - Checar se é exposto via API

2. MAPEAR dependências afetadas
   - Ver arquivo docs/CHANGE-MAP.md
   - Listar módulos que importam o alvo
   - Verificar se é usado em testes

3. VERIFICAR testes existentes
   - Quais testes cobrem o código?
   - Testes passando atualmente?
```

### Exemplo de Análise

```markdown
## Análise de Impacto: Refatorar `calculate_position_size`

### Usos Encontrados:
- `backend/modules/order_executor.py` (linha 145)
- `backend/modules/autonomous_bot.py` (linha 203, 287)
- `backend/api/routes/trading_routes.py` (linha 89)

### Dependências:
- Depende de: `binance_client`, `settings`
- É dependido por: `order_executor`, `autonomous_bot`

### Testes:
- `backend/tests/test_risk_manager_persistence.py` - 2 testes
- `backend/tests/test_validations.py` - 1 teste

### Risco: MÉDIO
- Função central para execução de trades
- Mudança de assinatura afetaria 3 módulos
```

---

### Fase 2: Planejamento

```
1. DEFINIR escopo da mudança
   - O que muda?
   - O que permanece igual?
   - Backward compatibility necessária?

2. CRIAR checklist de mudanças
   - Arquivos a modificar
   - Testes a atualizar
   - Docs a atualizar

3. DEFINIR estratégia de rollback
   - Como reverter se der errado?
```

### Estratégias de Refatoração

#### A) Renomear Função/Classe

```python
# 1. Criar nova função com novo nome
async def new_function_name(params) -> Result:
    """Nova implementação ou delegação."""
    pass

# 2. Deprecar antiga (opcional, para backward compat)
import warnings

async def old_function_name(params) -> Result:
    """Deprecated: Use new_function_name instead."""
    warnings.warn(
        "old_function_name is deprecated, use new_function_name",
        DeprecationWarning,
        stacklevel=2
    )
    return await new_function_name(params)

# 3. Atualizar todos os usos
# 4. Remover função antiga (após período de transição)
```

#### B) Mudar Assinatura de Função

```python
# Antes
async def calculate_size(symbol: str, risk: float) -> float:
    pass

# Depois (mantendo compatibilidade)
async def calculate_size(
    symbol: str, 
    risk: float,
    leverage: int = None,  # Novo parâmetro com default
) -> float:
    # Manter comportamento antigo se leverage=None
    if leverage is None:
        leverage = 10  # default antigo
    pass
```

#### C) Extrair Módulo

```python
# Antes: tudo em risk_calculator.py

# Depois:
# risk_calculator.py (mantém interface pública)
from .risk_calculator_core import calculate_position_size
from .risk_calculator_margin import calculate_margin

__all__ = ['calculate_position_size', 'calculate_margin']

# risk_calculator_core.py (nova implementação)
# risk_calculator_margin.py (lógica extraída)
```

---

### Fase 3: Execução

```
1. FAZER mudanças incrementais
   - Um arquivo por vez quando possível
   - Commits pequenos e frequentes
   - Mensagens descritivas

2. ATUALIZAR testes junto com código
   - Testes devem passar após cada mudança
   - Adicionar testes para nova lógica

3. VERIFICAR a cada passo
   - pytest após cada mudança significativa
   - Type checking se disponível
```

### Padrão de Commits para Refatoração

```bash
# Sequência de commits para refatoração grande:
git commit -m "refactor: extract margin calculation to separate function"
git commit -m "refactor: rename calculate_size to calculate_position_size"
git commit -m "test: update tests for new function signature"
git commit -m "docs: update API documentation for refactored module"
```

---

### Fase 4: Validação

```
1. RODAR suite de testes completa
   PYTHONPATH=backend pytest -q backend/tests
   cd frontend && npm test

2. VERIFICAR build
   docker compose build

3. TESTAR manualmente (se crítico)
   - Start bot em dry_run
   - Executar trade teste
   - Verificar logs

4. VALIDAR documentação
   - Links funcionando
   - Exemplos atualizados
```

---

## 📋 Checklists por Tipo de Refatoração

### Renomear Função

```
[ ] Buscar todos os usos (grep)
[ ] Criar nova função (ou renomear)
[ ] Atualizar todos os imports
[ ] Atualizar todos os usos
[ ] Atualizar testes
[ ] Atualizar documentação
[ ] Rodar testes
```

### Mudar Assinatura

```
[ ] Adicionar novos params com defaults
[ ] Atualizar docstring
[ ] Atualizar type hints
[ ] Atualizar chamadas que usam novos params
[ ] Manter chamadas antigas funcionando
[ ] Atualizar testes
[ ] Rodar testes
```

### Extrair Módulo

```
[ ] Criar novo arquivo
[ ] Mover código
[ ] Ajustar imports internos
[ ] Manter exports públicos no módulo original
[ ] Atualizar __init__.py se necessário
[ ] Atualizar testes
[ ] Rodar testes
```

### Otimizar Performance

```
[ ] Medir performance atual (baseline)
[ ] Implementar otimização
[ ] Verificar que comportamento não mudou (testes)
[ ] Medir nova performance
[ ] Documentar ganho
```

---

## ⚠️ Regras Importantes

1. **NUNCA** refatore e adicione features no mesmo commit
2. **SEMPRE** mantenha testes passando a cada passo
3. **PREFIRA** mudanças incrementais a refatorações big-bang
4. **DOCUMENTE** decisões de design importantes
5. **PRESERVE** backward compatibility quando possível
6. **USE** `docs/CHANGE-MAP.md` para entender impactos

---

## 🛠️ Ferramentas Úteis

### Encontrar Usos

```bash
# Buscar uso de função
grep -r "function_name" backend/ --include="*.py"

# Buscar imports
grep -r "from module import function_name" backend/

# Com ripgrep (mais rápido)
rg "function_name" backend/ -t py
```

### Verificar Imports

```python
# Script para verificar imports circulares
import importlib
import sys

module = importlib.import_module('modules.risk_calculator')
print(f"Module loaded: {module}")
```

### Testar Mudanças Isoladas

```bash
# Testar apenas arquivos modificados
PYTHONPATH=backend pytest backend/tests/test_specific.py -v

# Testar com mais detalhes
PYTHONPATH=backend pytest backend/tests/ -v --tb=long
```
