---
description: Regras de segurança para o Vector Protocol
---

# Security Rules

Regras de segurança rigorosas para o projeto Vector Protocol.

---

## 🚫 NUNCA Fazer

### Secrets e Credenciais

```
❌ NUNCA exibir conteúdo de .env em logs ou outputs
❌ NUNCA commitar API keys ou passwords
❌ NUNCA logar requests/responses com secrets
❌ NUNCA hardcodar credenciais no código
```

Se você encontrar uma secret, REDATAR:

```python
# Correto
logger.info(f"Using API key: {api_key[:4]}***")

# ERRADO
logger.info(f"Using API key: {api_key}")
```

### Arquivos Protegidos

```
❌ NUNCA modificar sem permissão explícita:
   - .env (secrets de produção)
   - docker-compose.yml (orquestração core)
   - backend/config/settings.py (apenas novos campos)
```

### Diretórios Proibidos

```
❌ NUNCA modificar:
   - clients/  (dados de clientes)
   - data/     (dados locais)
   - logs/     (logs de runtime)
   - .git/     (controle de versão)
```

### Comandos Perigosos

```bash
# NUNCA executar:
rm -rf /             # Deleção recursiva
rm -rf .             # Deleção do projeto
git clean -fdx       # Limpar arquivos untracked
docker system prune -a  # Limpar todo Docker
```

---

## ✅ SEMPRE Fazer

### Validação de Input

```python
# Validar inputs de API
from pydantic import BaseModel, Field, validator

class TradeRequest(BaseModel):
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    amount: float = Field(..., ge=0, le=1000000)
    
    @validator("symbol")
    def validate_symbol(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Invalid symbol length")
        return v.upper()
```

### Autenticação de API

```python
# Se API_AUTH_ENABLED=true, verificar API key
if settings.API_AUTH_ENABLED:
    api_key = request.headers.get(settings.API_KEY_HEADER)
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
```

### Rate Limiting

```python
# Respeitar rate limits da Binance
# 1200 weight/min para API
# Usar cache Redis para dados frequentes

from asyncio import sleep

async def with_rate_limit(func, *args):
    try:
        return await func(*args)
    except BinanceAPIException as e:
        if e.code == -1015:  # Rate limit
            await sleep(60)  # Wait before retry
            return await func(*args)
```

### Logging Seguro

```python
# Logger já configurado para não exibir secrets
from utils.logger import setup_logger

logger = setup_logger("module_name")

# Log apenas informações seguras
logger.info(f"Processing symbol: {symbol}")
logger.info(f"Order placed: {order_id}")

# NUNCA logar
# logger.info(f"API Response: {full_response}")  # Pode conter dados sensíveis
```

---

## 🔒 Práticas de Segurança

### Variáveis de Ambiente

```bash
# Usar .env.example como template (sem valores reais)
# .env NUNCA vai para o Git (.gitignore)

# Verificar se .env está no .gitignore
cat .gitignore | grep ".env"
```

### Testnet vs Production

```python
# Verificar ambiente antes de operações críticas
from config.settings import get_settings

settings = get_settings()

if not settings.BINANCE_TESTNET:
    logger.warning("⚠️ RUNNING IN PRODUCTION MODE")
    # Extra validations for production
```

### Tratamento de Erros

```python
try:
    result = await dangerous_operation()
except Exception as e:
    # Log erro sem expor detalhes sensíveis
    logger.error(f"Operation failed: {type(e).__name__}")
    
    # Em produção, não expor stack trace para client
    if settings.BINANCE_TESTNET:
        raise HTTPException(500, detail=str(e))
    else:
        raise HTTPException(500, detail="Internal server error")
```

---

## 🚨 Protocolo de Emergência

Se você suspeitar que:

1. **Quebrou o build**:

   ```bash
   git checkout .  # Reverter mudanças locais
   ```

2. **Deletou dados importantes**:

   ```bash
   git reflog  # Ver histórico de refs
   git checkout HEAD~1 -- path/to/file  # Restaurar arquivo
   ```

3. **Expôs credenciais**:
   - Parar imediatamente
   - Notificar o usuário
   - Rotacionar credenciais expostas
   - Verificar histórico de commits

---

## 📋 Checklist de Segurança

Antes de commit/push:

```
[ ] Sem hardcoded secrets no código
[ ] .env não está sendo commitado
[ ] API keys não aparecem em logs
[ ] Inputs de usuário validados
[ ] Erros não expõem informações sensíveis
[ ] Usando TESTNET para desenvolvimento
```
