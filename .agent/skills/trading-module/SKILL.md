---
name: trading-module
description: Guia para desenvolvimento e modificação de módulos de trading (signal generator, executor, risk manager). Use ao trabalhar com lógica de trading.
---

# Trading Module Skill

Skill especializado para desenvolvimento de módulos de trading no Vector Protocol.

---

## 🎯 Quando Usar

- Ao modificar lógica de sinais
- Ao trabalhar com order executor
- Ao ajustar risk management
- Ao otimizar estratégias de trading

---

## 🏗️ Arquitetura de Trading

```
                    ┌─────────────────┐
                    │  Autonomous Bot │
                    │  (Orquestrador) │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │Market Scanner│ │Position      │ │Telegram Bot  │
    │              │ │Monitor       │ │(Notificações)│
    └──────┬───────┘ └──────┬───────┘ └──────────────┘
           │                │
           ▼                │
    ┌──────────────┐        │
    │Signal        │        │
    │Generator     │        │
    └──────┬───────┘        │
           │                │
           ▼                │
    ┌──────────────┐        │
    │Risk Calculator│       │
    └──────┬───────┘        │
           │                │
           ▼                ▼
    ┌────────────────────────────┐
    │      Order Executor        │
    │  (Execução de Ordens)      │
    └────────────────────────────┘
               │
               ▼
    ┌────────────────┐
    │ Binance Client │
    │  (API/WebSocket)│
    └────────────────┘
```

---

## 📦 Módulos Principais

### 1. Market Scanner (`market_scanner.py`)

**Propósito**: Filtra universo de símbolos para análise.

```python
# Entrada
scan_config = {
    "top_n": 800,           # Top por volume
    "max_symbols": 80,      # Limite por ciclo
    "min_volume_24h": 20_000_000,  # Volume mínimo
}

# Saída
scan_results = [
    {
        "symbol": "BTCUSDT",
        "price": 50000.0,
        "volume_24h": 15_000_000_000,
        "change_24h": 2.5,
        "trend": "bullish",
    },
    # ...
]
```

**Settings Relacionados**:

- `SCANNER_TOP_N`, `SCANNER_MAX_SYMBOLS`
- `SCANNER_MIN_VOLUME_24H`
- `SYMBOL_WHITELIST`, `TESTNET_WHITELIST`

### 2. Signal Generator (`signal_generator.py`)

**Propósito**: Gera sinais de trading com score de confiança.

```python
# Indicadores Usados
indicators = {
    "RSI": "Oversold/Overbought (30/70)",
    "EMA": "Crossover (9/21)",
    "MACD": "Momentum",
    "ADX": "Trend strength",
    "Bollinger": "Mean reversion",
    "VWAP": "Volume weighted price",
}

# Saída
signal = {
    "symbol": "BTCUSDT",
    "direction": "LONG",  # ou "SHORT"
    "score": 85,          # 0-100
    "entry_price": 50000.0,
    "stop_loss": 49000.0,
    "take_profit": 52000.0,
    "rr_ratio": 2.0,
    "regime": "trending",  # ou "ranging"
}
```

**Settings Relacionados**:

- `PROD_MIN_SCORE`, `TESTNET_MIN_SCORE`
- `PROD_VOLUME_THRESHOLD`
- `PROD_RSI_OVERSOLD`, `PROD_RSI_OVERBOUGHT`
- `RR_MIN_TREND`, `RR_MIN_RANGE`

### 3. Risk Calculator (`risk_calculator.py`)

**Propósito**: Calcula posição sizing e valida risco.

```python
# Entrada
risk_params = {
    "balance": 1000.0,
    "risk_per_trade": 0.02,  # 2%
    "entry_price": 50000.0,
    "stop_loss": 49000.0,
    "leverage": 10,
}

# Saída
position_calc = {
    "quantity": 0.01,
    "notional": 500.0,
    "margin_required": 50.0,
    "risk_amount": 20.0,  # 2% of 1000
    "leverage": 10,
}
```

**Settings Relacionados**:

- `RISK_PER_TRADE`, `MAX_PORTFOLIO_RISK`
- `MAX_POSITIONS`, `DEFAULT_LEVERAGE`
- `MAX_MARGIN_USD_PER_POSITION`

### 4. Order Executor (`order_executor.py`)

**Propósito**: Executa ordens na Binance com retry e fallback.

```python
# Fluxo de Execução
execution_flow = """
1. LIMIT order com buffer (3 retries)
   - Post-Only (GTX) se configurado
   - Timeout: ORDER_TIMEOUT_SEC
   
2. Fallback para MARKET na última tentativa

3. Verificar headroom até liquidação
   - Se < HEADROOM_MIN_PCT, reduzir posição

4. Colocar SL/TP
   - Trailing Stop se habilitado
   - TP Ladder se configurado
"""

# Tipos de Ordem
order_types = {
    "LIMIT": "Ordem limite padrão",
    "MARKET": "Ordem a mercado (fallback)",
    "STOP_MARKET": "Stop Loss",
    "TAKE_PROFIT_MARKET": "Take Profit",
    "TRAILING_STOP_MARKET": "Trailing Stop",
}
```

**Settings Relacionados**:

- `ORDER_TIMEOUT_SEC`, `USE_POST_ONLY_ENTRIES`
- `TAKE_PROFIT_PARTS`, `ENABLE_TRAILING_STOP`
- `HEADROOM_MIN_PCT`, `REDUCE_STEP_PCT`

### 5. Position Monitor (`position_monitor.py`)

**Propósito**: Monitora posições abertas e gerencia exits.

```python
# Funcionalidades
features = {
    "DCA": "Dollar Cost Averaging em níveis",
    "Breakeven": "Move SL para entrada após lucro X%",
    "Trailing Stop": "TSL baseado em ATR",
    "Time Exit": "Fecha após tempo máximo",
    "TP Ladder": "Realização parcial em níveis",
}
```

**Settings Relacionados**:

- `DCA_ENABLED`, `DCA_LEVEL_*`
- `BREAKEVEN_ENABLED`, `BREAKEVEN_THRESHOLD_PCT`
- `TRAILING_STOP_ATR_ENABLED`
- `TIME_EXIT_ENABLED`, `TIME_EXIT_HOURS`

---

## 💡 Padrões de Desenvolvimento

### Estrutura de Módulo

```python
"""
Docstring do módulo descrevendo propósito.
"""
from typing import Optional, Dict, List
import asyncio

from utils.logger import setup_logger
from config.settings import get_settings
from utils.binance_client import binance_client

logger = setup_logger("module_name")
settings = get_settings()


class ModuleName:
    """Docstring da classe."""
    
    def __init__(self):
        """Inicialização."""
        self._cache = {}
    
    async def main_function(
        self,
        symbol: str,
        param: float,
    ) -> Optional[Dict]:
        """
        Docstring com Args, Returns, Raises.
        """
        logger.info(f"Processing {symbol}")
        
        try:
            # Lógica principal
            result = await self._helper_function(symbol)
            return result
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None
    
    async def _helper_function(self, symbol: str) -> Dict:
        """Funções privadas com underscore."""
        pass


# Singleton pattern usado em todos os módulos
module_name = ModuleName()
```

### Chamadas à Binance API

```python
# Sempre usar binance_client singleton
from utils.binance_client import binance_client

# Preço atual
price = await binance_client.get_symbol_price(symbol)

# Klines (candles)
klines = await binance_client.get_klines(
    symbol=symbol,
    interval="1h",
    limit=100,
)

# Account info (cacheado)
account = await binance_client.get_account()
balance = account["totalMarginBalance"]

# Posições
positions = await binance_client.get_positions()
```

### Tratamento de Erros Binance

```python
from binance.exceptions import BinanceAPIException

try:
    order = await binance_client.create_order(...)
    
except BinanceAPIException as e:
    # Códigos comuns:
    # -2019: Margem insuficiente
    # -1111: Precisão inválida
    # -4061: Posição já fechada
    # -2015: API key inválida
    
    if e.code == -2019:
        logger.warning(f"Insufficient margin for {symbol}")
        # Tentar reduzir size
    elif e.code == -1111:
        logger.error(f"Precision error: {e.message}")
        # Ajustar quantity
    else:
        logger.error(f"Binance error {e.code}: {e.message}")
        raise
```

### Validação de Filters

```python
async def validate_order(symbol: str, quantity: float) -> float:
    """Valida e ajusta quantity contra filters da Binance."""
    
    info = await binance_client.get_symbol_info(symbol)
    
    # Extrair filters
    lot_size = next(
        f for f in info["filters"] 
        if f["filterType"] == "LOT_SIZE"
    )
    min_notional = next(
        f for f in info["filters"] 
        if f["filterType"] == "MIN_NOTIONAL"
    )
    
    min_qty = float(lot_size["minQty"])
    step_size = float(lot_size["stepSize"])
    min_notional_value = float(min_notional["minNotional"])
    
    # Validar minQty
    if quantity < min_qty:
        raise ValueError(f"Quantity {quantity} < minQty {min_qty}")
    
    # Arredondar para stepSize
    precision = len(str(step_size).split('.')[-1].rstrip('0'))
    quantity = round(quantity - (quantity % step_size), precision)
    
    # Validar minNotional
    price = await binance_client.get_symbol_price(symbol)
    notional = quantity * price
    if notional < min_notional_value:
        raise ValueError(f"Notional {notional} < minNotional {min_notional_value}")
    
    return quantity
```

---

## ⚠️ Regras Críticas

### NUNCA

```
❌ Executar ordens sem validar filters
❌ Ignorar rate limits da Binance (1200 weight/min)
❌ Usar MARKET orders como padrão
❌ Abrir posições sem SL definido
❌ Modificar margem/leverage sem verificar posição existente
❌ Logar API keys ou secrets
```

### SEMPRE

```
✅ Usar testnet para desenvolvimento (BINANCE_TESTNET=true)
✅ Validar quantity contra minQty/stepSize
✅ Validar notional contra minNotional
✅ Verificar position mode (One-Way enforced)
✅ Tratar erros Binance com códigos específicos
✅ Usar cache Redis para dados frequentes
✅ Testar com dry_run=true primeiro
```

---

## 🧪 Testando Módulos de Trading

```bash
# Testes unitários
PYTHONPATH=backend pytest backend/tests/test_validations.py -v

# Teste manual com dry_run
curl -X POST "http://localhost:8000/api/trading/execute" \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","risk_profile":"moderate","dry_run":true}'

# Verificar bot status
curl -sS "http://localhost:8000/api/trading/bot/status" | jq .

# Ver logs de execução
curl -sS "http://localhost:8000/api/system/logs?component=order_executor&tail=50"
```

---

## 📚 Documentação Relacionada

- `docs/API_SPEC.md` - Endpoints de trading
- `docs/EXECUTION_ENGINE_OPTIMIZATION.md` - Detalhes de execução
- `CLAUDE.md` - Contexto completo do sistema
- `backend/config/settings.py` - Todas as configurações
