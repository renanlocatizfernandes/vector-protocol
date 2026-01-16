---
description: Rules de estilo de código para o Vector Protocol
---

# Code Style Rules

Regras de estilo de código para o projeto Vector Protocol.

---

## Python (Backend)

### Formatação Geral

- **Indentação**: 4 espaços
- **Linha máxima**: 100 caracteres
- **Encoding**: UTF-8
- **Imports**: Agrupados (stdlib, third-party, local)

### Type Hints (OBRIGATÓRIOS)

```python
# ✅ Correto
async def calculate_risk(
    balance: float,
    risk_pct: float,
    symbol: str,
) -> Optional[Dict[str, float]]:
    pass

# ❌ Incorreto
async def calculate_risk(balance, risk_pct, symbol):
    pass
```

### Docstrings (Google Style)

```python
async def function_name(param1: str, param2: int = 10) -> dict:
    """Breve descrição da função.
    
    Descrição mais longa se necessário.
    
    Args:
        param1: Descrição do parâmetro 1
        param2: Descrição do parâmetro 2. Default: 10
    
    Returns:
        dict: Descrição do retorno
    
    Raises:
        ValueError: Quando param1 é inválido
    """
```

### Nomenclatura

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Variáveis | snake_case | `user_balance` |
| Funções | snake_case | `calculate_position_size` |
| Classes | PascalCase | `SignalGenerator` |
| Constantes | UPPER_SNAKE | `MAX_POSITIONS` |
| Módulos | snake_case | `signal_generator.py` |

### Async/Await

```python
# ✅ Prefer async for I/O operations
async def fetch_data():
    result = await client.get_data()
    return result

# ✅ Use asyncio.gather for parallel operations
results = await asyncio.gather(
    fetch_price(symbol1),
    fetch_price(symbol2),
)

# ❌ Don't block event loop
import time
time.sleep(1)  # WRONG

# ✅ Use asyncio
await asyncio.sleep(1)
```

---

## TypeScript (Frontend)

### Formatação

- **Indentação**: 2 espaços
- **Semicolons**: Não (Vite default)
- **Quotes**: Single quotes para strings
- **Trailing commas**: ES5

### Nomenclatura

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Variables | camelCase | `userData` |
| Functions | camelCase | `fetchPositions` |
| Components | PascalCase | `TradingDashboard` |
| Interfaces | PascalCase | `PositionData` |
| Types | PascalCase | `TradeDirection` |
| Constants | UPPER_SNAKE | `API_BASE_URL` |

### Componentes React

```typescript
// ✅ Functional components
interface Props {
  title: string
  onClose: () => void
}

const MyComponent: React.FC<Props> = ({ title, onClose }) => {
  const [state, setState] = useState<string>('')
  
  return (
    <div className="p-4">
      <h1>{title}</h1>
    </div>
  )
}

export default MyComponent
```

### Tailwind Classes

- Ordem: layout → sizing → spacing → colors → effects
- Usar `clsx` ou `tailwind-merge` para condicionais

```typescript
import { clsx } from 'clsx'

<button 
  className={clsx(
    'flex items-center justify-center',
    'px-4 py-2',
    'bg-purple-600 text-white',
    'hover:bg-purple-700',
    isDisabled && 'opacity-50 cursor-not-allowed'
  )}
>
```

---

## Commits

### Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Tipos

- `feat`: Nova feature
- `fix`: Bug fix
- `docs`: Documentação
- `style`: Formatação
- `refactor`: Refatoração
- `test`: Testes
- `chore`: Manutenção

### Exemplos

```bash
# Bom
git commit -m "feat(scanner): add momentum filter"
git commit -m "fix(executor): handle insufficient margin error"
git commit -m "docs: update API specification"

# Ruim
git commit -m "update code"
git commit -m "fix bug"
git commit -m "WIP"
```

---

## Arquivos

### Estrutura de Arquivo Python

```python
"""
Module docstring explaining purpose.
"""
# Standard library imports
import asyncio
from typing import Optional, Dict

# Third-party imports
from fastapi import HTTPException

# Local imports
from utils.logger import setup_logger
from config.settings import get_settings

# Module-level setup
logger = setup_logger("module_name")
settings = get_settings()

# Constants
MAX_RETRIES = 3

# Classes and functions
class MyClass:
    """Class docstring."""
    pass


async def my_function() -> None:
    """Function docstring."""
    pass


# Singleton (if applicable)
my_instance = MyClass()
```

### Estrutura de Arquivo TypeScript

```typescript
// Imports
import { useState, useEffect } from 'react'
import { clsx } from 'clsx'

// Types
interface Props {
  // ...
}

type State = 'loading' | 'success' | 'error'

// Constants
const API_ENDPOINT = '/api/data'

// Helper functions
function formatData(data: unknown): string {
  // ...
}

// Component
const Component: React.FC<Props> = () => {
  // ...
}

// Export
export default Component
```
