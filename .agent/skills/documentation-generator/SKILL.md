---
name: documentation-generator
description: Gera documentação técnica seguindo padrões do projeto Vector Protocol. Inclui templates para API, README, e changelog.
---

# Documentation Generator Skill

Este skill auxilia na criação e atualização de documentação técnica para o projeto Vector Protocol.

---

## 🎯 Quando Usar

- Ao criar novos módulos ou endpoints
- Ao modificar comportamento existente
- Para documentar decisões arquiteturais
- Ao preparar releases

---

## 📁 Estrutura de Documentação

```
docs/
├── ARCHITECTURE.md          # Visão geral do sistema
├── API_SPEC.md              # Especificação completa da API
├── RUNBOOK.md               # Guia operacional
├── DEPLOYMENT.md            # Instruções de deploy
├── CHANGELOG.md             # Histórico de mudanças
├── CONTRIBUTING.md          # Guia de contribuição
├── GOVERNANCE.md            # Regras e papéis
└── [feature].md             # Docs específicas de features
```

---

## 📝 Templates por Tipo

### 1. Documentação de Endpoint API

Ao adicionar novo endpoint, atualize `docs/API_SPEC.md`:

```markdown
============================================================
X) Nome da Seção
============================================================

### POST /api/path/endpoint

**Descrição**: Breve descrição do que o endpoint faz.

**Autenticação**: Requerida (API Key) | Não requerida

**Query Parameters**:
| Param | Tipo | Obrigatório | Default | Descrição |
|-------|------|-------------|---------|-----------|
| param1 | string | Sim | - | Descrição do parâmetro |
| param2 | int | Não | 10 | Descrição com default |

**Request Body** (se aplicável):
```json
{
  "field1": "string",
  "field2": 123,
  "nested": {
    "subfield": true
  }
}
```

**Response** (200 OK):

```json
{
  "success": true,
  "data": {
    "id": "abc123",
    "status": "completed"
  }
}
```

**Códigos de Erro**:

| Código | Descrição |
|--------|-----------|
| 400 | Request inválido (parâmetros faltando/inválidos) |
| 401 | Não autorizado |
| 500 | Erro interno |

**Exemplo curl**:

```bash
curl -sS -X POST "http://localhost:8000/api/path/endpoint?param1=value" \
  -H 'Content-Type: application/json' \
  -d '{"field1": "value"}' | jq .
```

```

### 2. README para Novo Módulo

```markdown
# Nome do Módulo

## Visão Geral

Breve descrição do propósito do módulo (1-2 parágrafos).

## Arquitetura

```

[Diagrama ASCII ou referência a imagem]

```

## Instalação/Configuração

### Variáveis de Ambiente

| Variável | Tipo | Default | Descrição |
|----------|------|---------|-----------|
| VAR_NAME | bool | false | O que controla |

### Dependências

- `dependency1`: Para que serve
- `dependency2`: Para que serve

## Uso

### Uso Básico

```python
from modules.my_module import my_function

result = await my_function(param1="value")
```

### Uso Avançado

```python
# Exemplo de uso com todas as opções
result = await my_function(
    param1="value",
    option1=True,
    option2=42
)
```

## API Reference

### `function_name(param1, param2, **kwargs)`

**Parâmetros:**

- `param1` (str): Descrição
- `param2` (int, optional): Descrição. Default: 10

**Retorna:**

- `dict`: Dicionário com campos x, y, z

**Exceções:**

- `ValueError`: Quando param1 é inválido
- `APIError`: Quando a API externa falha

**Exemplo:**

```python
result = function_name("test", param2=20)
# {'status': 'ok', 'data': [...]}
```

## Testes

```bash
PYTHONPATH=backend pytest backend/tests/test_my_module.py -v
```

## Troubleshooting

### Problema: [Descrição]

**Causa**: [Explicação]
**Solução**: [Passos para resolver]

## Changelog

- **v1.0.0** (2026-01-16): Versão inicial

```

### 3. Changelog Entry (Keep a Changelog)

```markdown
## [1.2.0] - 2026-01-16

### Added
- Novo endpoint `/api/trading/feature` para [descrição]
- Suporte a múltiplos timeframes no signal generator
- Skill `test-generator` para geração automática de testes

### Changed
- Aumentado timeout de conexão de 10s para 30s
- Refatorado `risk_calculator` para suportar DCA multi-nível
- Atualizado dependências: fastapi 0.115.0, pydantic 2.10.2

### Fixed
- Corrigido cálculo de margem em posições com leverage alto
- Resolvido race condition no position monitor
- Tratamento de erro para símbolos delisted

### Deprecated
- Parâmetro `old_param` será removido na v2.0

### Removed
- Removido suporte a Python 3.9

### Security
- Atualizado httpx para 0.27.2 (CVE-XXXX-YYYY)
```

### 4. Docstrings Python (Google Style)

```python
async def calculate_position_size(
    symbol: str,
    entry_price: float,
    direction: str,
    risk_pct: float = 0.02,
) -> dict:
    """Calcula o tamanho da posição baseado em parâmetros de risco.
    
    Este método considera o balanço disponível, risco percentual por trade,
    e filters da Binance (minQty, stepSize) para determinar a quantidade
    ótima a ser operada.
    
    Args:
        symbol: Símbolo do par (ex: "BTCUSDT")
        entry_price: Preço de entrada planejado
        direction: "LONG" ou "SHORT"
        risk_pct: Percentual do capital a arriscar (default: 2%)
    
    Returns:
        dict: Dicionário com campos:
            - quantity (float): Quantidade calculada
            - notional (float): Valor em USDT
            - leverage (int): Alavancagem sugerida
            - margin_required (float): Margem necessária
    
    Raises:
        ValueError: Se symbol for inválido ou direction não for LONG/SHORT
        InsufficientMarginError: Se não houver margem suficiente
    
    Example:
        >>> result = await calculate_position_size("BTCUSDT", 50000, "LONG")
        >>> print(result)
        {'quantity': 0.01, 'notional': 500, 'leverage': 10, 'margin_required': 50}
    
    Note:
        Em modo testnet, os limites de margem são simulados e podem
        diferir do ambiente de produção.
    """
    # Implementação...
```

### 5. TypeScript/JSDoc

```typescript
/**
 * Componente de dashboard de trading.
 * 
 * Exibe posições abertas, status do bot, e métricas de performance.
 * 
 * @component
 * @example
 * ```tsx
 * <TradingDashboard 
 *   refreshInterval={5000}
 *   onError={(err) => console.error(err)}
 * />
 * ```
 */
interface TradingDashboardProps {
  /** Intervalo de refresh em ms (default: 10000) */
  refreshInterval?: number;
  /** Callback para erros de API */
  onError?: (error: Error) => void;
}

/**
 * Busca posições abertas do backend.
 * 
 * @param options - Opções de filtro
 * @param options.symbol - Filtrar por símbolo específico
 * @param options.side - Filtrar por lado (LONG/SHORT)
 * @returns Promise com array de posições
 * @throws {ApiError} Quando a API retorna erro
 * 
 * @example
 * ```ts
 * const positions = await getPositions({ side: 'LONG' });
 * console.log(`${positions.length} posições long`);
 * ```
 */
export async function getPositions(options?: {
  symbol?: string;
  side?: 'LONG' | 'SHORT';
}): Promise<Position[]> {
  // ...
}
```

---

## 🔄 Fluxo de Atualização

### Ao Modificar Código

1. **Identifique docs afetados**:
   - Novo endpoint? → `API_SPEC.md`
   - Mudou comportamento? → `README.md`, `RUNBOOK.md`
   - Nova config? → `DEPLOYMENT.md`, `settings.py` docstring

2. **Atualize docstrings** no código fonte

3. **Adicione entry no CHANGELOG**

4. **Commit junto com código**:

   ```
   feat: add position ladder feature
   
   - New endpoint /api/trading/positions/ladder
   - Updated API_SPEC.md with endpoint documentation
   - Added CHANGELOG entry
   ```

---

## ✅ Checklist de Documentação

```markdown
[ ] Docstrings em todas funções públicas
[ ] API_SPEC.md atualizado para novos endpoints
[ ] README atualizado se mudou setup/usage
[ ] CHANGELOG.md tem entry para a mudança
[ ] Exemplos de código funcionam
[ ] Links internos validados
[ ] Sem typos óbvios
```

---

## 📚 Referências

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
