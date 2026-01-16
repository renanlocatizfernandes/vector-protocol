---
description: Regras arquiteturais do Vector Protocol
---

# Architecture Rules

Princípios arquiteturais e padrões do projeto Vector Protocol.

---

## 🏗️ Princípios Core

### 1. Separação de Responsabilidades

```
backend/
├── api/            # HTTP layer (FastAPI routes)
├── modules/        # Business logic (trading)
├── models/         # Data layer (SQLAlchemy)
├── config/         # Configuration (Pydantic)
└── utils/          # Shared utilities
```

**Regras:**

- Routes NÃO devem conter lógica de negócio
- Modules NÃO devem fazer I/O diretamente (usar utils)
- Models são apenas representação de dados

### 2. Async-First

```python
# ✅ Usar async para I/O
async def fetch_price(symbol: str) -> float:
    return await binance_client.get_symbol_price(symbol)

# ✅ Usar asyncio.gather para paralelismo
prices = await asyncio.gather(
    fetch_price("BTCUSDT"),
    fetch_price("ETHUSDT"),
)

# ❌ NUNCA bloquear event loop
import time
time.sleep(1)  # ERRADO

# ✅ Correto
await asyncio.sleep(1)
```

### 3. Configuração via Settings

```python
# ✅ Usar Pydantic Settings
from config.settings import get_settings

settings = get_settings()
max_positions = settings.MAX_POSITIONS

# ❌ NUNCA hardcodar valores de configuração
max_positions = 10  # ERRADO
```

### 4. Singleton Pattern para Clientes

```python
# ✅ Usar singleton para clients compartilhados
from utils.binance_client import binance_client

# O mesmo cliente é usado em todos os módulos
price = await binance_client.get_symbol_price("BTCUSDT")

# ❌ NUNCA criar nova instância
client = BinanceClient()  # ERRADO - desperdiça recursos
```

---

## 📦 Estrutura de Módulos

### Módulo de Trading Padrão

```python
"""
Módulo de [Funcionalidade].

Responsável por [descrição].
"""
from typing import Optional, Dict, List
import asyncio

from utils.logger import setup_logger
from config.settings import get_settings
from utils.binance_client import binance_client

logger = setup_logger("module_name")
settings = get_settings()


class ModuleName:
    """Classe principal do módulo."""
    
    def __init__(self):
        """Inicializa o módulo."""
        self._cache: Dict = {}
    
    async def main_method(
        self,
        param1: str,
        param2: float = 1.0,
    ) -> Optional[Dict]:
        """
        Método principal.
        
        Args:
            param1: Descrição
            param2: Descrição. Default: 1.0
        
        Returns:
            Dict ou None se falhar
        """
        logger.info(f"Processing {param1}")
        
        try:
            result = await self._process(param1, param2)
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    async def _process(self, param1: str, param2: float) -> Dict:
        """Método privado de processamento."""
        # Implementação
        pass


# Singleton global
module_name = ModuleName()
```

---

## 🔄 Fluxo de Dados

### Trading Pipeline

```
1. Market Scanner
   └─→ Lista de símbolos candidatos

2. Signal Generator
   └─→ Sinais com score e direção

3. Risk Calculator
   └─→ Tamanho de posição validado

4. Order Executor
   └─→ Ordem executada na Binance

5. Position Monitor
   └─→ Gerencia SL/TP/TSL
```

### Regras de Comunicação

```
Scanner → Retorna lista de dicts com dados de mercado
Signal  → Retorna dict com signal ou None
Risk    → Retorna dict com sizing ou raises Exception
Executor→ Retorna order result ou raises Exception
Monitor → Atualiza estado assincronamente
```

---

## 🔌 Integrações

### Binance API

```python
# Todas as chamadas via BinanceClient singleton
from utils.binance_client import binance_client

# Preço
price = await binance_client.get_symbol_price(symbol)

# Klines
klines = await binance_client.get_klines(symbol, "1h", 100)

# Ordens
order = await binance_client.create_order(...)

# Account
account = await binance_client.get_account()
```

### Database (SQLAlchemy)

```python
from models.database import SessionLocal
from api.models.trades import Trade, Position

# Usar session context
with SessionLocal() as session:
    position = session.query(Position).filter_by(symbol=symbol).first()
    session.add(new_trade)
    session.commit()
```

### Redis Cache

```python
# Caching via binance_client (automático se CACHE_ENABLED)
# Ou diretamente:
import redis

redis_client = redis.Redis(host=settings.REDIS_HOST)
redis_client.setex("key", ttl_seconds, value)
cached = redis_client.get("key")
```

### Telegram

```python
from modules.telegram_bot import telegram_bot

# Notificações assíncronas (fire-and-forget)
await telegram_bot.notify_trade_opened(trade_data)
await telegram_bot.notify_trade_closed(trade_data)
```

---

## 📐 Padrões de API

### Endpoints REST

| Método | Uso | Exemplo |
|--------|-----|---------|
| GET | Ler recursos | `GET /api/trading/positions` |
| POST | Criar/Executar | `POST /api/trading/execute` |
| PUT | Atualizar | `PUT /api/trading/bot/config` |
| DELETE | Remover | `DELETE /api/trading/positions` |

### Códigos HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 201 | Criado |
| 400 | Request inválido |
| 401 | Não autorizado |
| 404 | Não encontrado |
| 409 | Conflito |
| 500 | Erro interno |

### Response Format

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message",
  "error": null
}
```

---

## ⚠️ Anti-Patterns

### Evitar

```python
# ❌ Lógica de negócio em routes
@router.post("/trade")
async def trade(symbol: str):
    # 50 linhas de lógica aqui... ERRADO

# ❌ Múltiplas responsabilidades
class EverythingClass:
    def scan_market(self): ...
    def generate_signal(self): ...
    def execute_order(self): ...
    def send_notification(self): ...

# ❌ Hardcoded values
max_positions = 10  # Deveria estar em settings

# ❌ Blocking I/O in async
import requests  # Deveria usar httpx/aiohttp
```

### Preferir

```python
# ✅ Routes delegam para modules
@router.post("/trade")
async def trade(request: TradeRequest):
    return await order_executor.execute(request)

# ✅ Classes com responsabilidade única
class MarketScanner:
    """Apenas scanning."""
    
class SignalGenerator:
    """Apenas sinais."""

# ✅ Configuração centralizada
max_positions = settings.MAX_POSITIONS

# ✅ Async I/O
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```
