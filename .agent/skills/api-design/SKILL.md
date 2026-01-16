---
name: api-design
description: Guia para design e implementação de endpoints FastAPI seguindo padrões do Vector Protocol.
---

# API Design Skill

Skill para design e implementação de endpoints FastAPI no Vector Protocol.

---

## 🎯 Quando Usar

- Ao criar novos endpoints
- Ao modificar endpoints existentes
- Para validar contratos de API
- Ao documentar APIs

---

## 🏗️ Estrutura de API

```
backend/api/
├── app.py              # Aplicação FastAPI principal
├── routes/             # Routers organizados por domínio
│   ├── trading_routes.py    # /api/trading/*
│   ├── market_routes.py     # /api/market/*
│   ├── system_routes.py     # /api/system/*
│   └── config_routes.py     # /api/config/*
├── models/             # Modelos SQLAlchemy
│   ├── database.py
│   └── trades.py
└── websocket.py        # WebSocket handlers
```

---

## 📐 Padrões de Endpoint

### Estrutura de Router

```python
"""
Routes para funcionalidade X.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("routes.feature_name")
settings = get_settings()

router = APIRouter(prefix="/api/feature", tags=["Feature Name"])


# ==================== MODELS ====================

class FeatureRequest(BaseModel):
    """Request model com validação."""
    
    symbol: str = Field(..., description="Símbolo do par", example="BTCUSDT")
    amount: float = Field(..., ge=0, description="Quantidade", example=100.0)
    option: Optional[str] = Field(None, description="Opção opcional")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "amount": 100.0,
                "option": "value"
            }
        }


class FeatureResponse(BaseModel):
    """Response model."""
    
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None


# ==================== ENDPOINTS ====================

@router.get("/items", response_model=List[FeatureResponse])
async def list_items(
    limit: int = Query(10, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Lista items com paginação.
    
    - **limit**: Número máximo de items (1-100)
    - **offset**: Offset para paginação
    """
    logger.info(f"Listing items: limit={limit}, offset={offset}")
    
    try:
        # Implementação
        items = []
        return items
        
    except Exception as e:
        logger.error(f"Error listing items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}")
async def get_item(item_id: str):
    """
    Retorna item específico por ID.
    
    - **item_id**: ID único do item
    """
    logger.info(f"Getting item: {item_id}")
    
    # Implementação
    item = None
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return item


@router.post("/items", response_model=FeatureResponse, status_code=201)
async def create_item(request: FeatureRequest):
    """
    Cria novo item.
    
    Body:
    - **symbol**: Símbolo obrigatório
    - **amount**: Quantidade (>= 0)
    - **option**: Opção opcional
    """
    logger.info(f"Creating item: {request.symbol}")
    
    try:
        # Validação adicional
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        # Implementação
        result = {"id": "new_id", "symbol": request.symbol}
        
        return FeatureResponse(
            success=True,
            data=result,
            message="Item created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    amount: Optional[float] = Query(None, ge=0),
    option: Optional[str] = Query(None),
):
    """
    Atualiza item existente via query params.
    
    - **item_id**: ID do item
    - **amount**: Nova quantidade (opcional)
    - **option**: Nova opção (opcional)
    """
    logger.info(f"Updating item {item_id}")
    
    # Implementação
    updates = {}
    if amount is not None:
        updates["amount"] = amount
    if option is not None:
        updates["option"] = option
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    return {"success": True, "updated": updates}


@router.delete("/items/{item_id}")
async def delete_item(item_id: str):
    """
    Remove item por ID.
    
    - **item_id**: ID do item a remover
    """
    logger.info(f"Deleting item: {item_id}")
    
    # Implementação
    return {"success": True, "deleted": item_id}
```

### Registrar Router no App

```python
# backend/api/app.py
from fastapi import FastAPI
from api.routes import feature_routes

app = FastAPI(
    title="Vector Protocol API",
    description="Autonomous Crypto Trading Bot API",
    version="1.0.0",
)

# Registrar routers
app.include_router(feature_routes.router)
```

---

## 🔒 Autenticação (Opcional)

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

from config.settings import get_settings

settings = get_settings()

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verifica API key se autenticação habilitada."""
    if not settings.API_AUTH_ENABLED:
        return True
    
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return True


# Uso no endpoint
@router.get("/secure-endpoint")
async def secure_endpoint(authenticated: bool = Security(verify_api_key)):
    """Endpoint protegido por API key."""
    return {"status": "authenticated"}
```

---

## 📝 Validação com Pydantic

### Request Models

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime


class TradeRequest(BaseModel):
    """Request para executar trade."""
    
    symbol: str = Field(
        ...,  # Required
        min_length=3,
        max_length=20,
        pattern=r"^[A-Z]+USDT$",
        description="Símbolo do par (ex: BTCUSDT)",
    )
    
    direction: Literal["LONG", "SHORT"] = Field(
        ...,
        description="Direção do trade",
    )
    
    risk_pct: float = Field(
        default=0.02,
        ge=0.001,
        le=0.10,
        description="Risco por trade (1-10%)",
    )
    
    dry_run: bool = Field(
        default=True,
        description="Se True, não executa ordem real",
    )
    
    @validator("symbol")
    def validate_symbol(cls, v):
        """Validação customizada de símbolo."""
        if not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        return v.upper()


class TradeResponse(BaseModel):
    """Response de trade executado."""
    
    success: bool
    trade_id: Optional[str] = None
    symbol: str
    direction: str
    entry_price: Optional[float] = None
    quantity: Optional[float] = None
    error: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Response Patterns

```python
# Sucesso
return {
    "success": True,
    "data": {...},
    "message": "Operation completed"
}

# Erro controlado (400)
raise HTTPException(
    status_code=400,
    detail="Invalid symbol format"
)

# Não encontrado (404)
raise HTTPException(
    status_code=404,
    detail=f"Position for {symbol} not found"
)

# Conflito (409)
raise HTTPException(
    status_code=409,
    detail="Position already exists"
)

# Erro interno (500)
raise HTTPException(
    status_code=500,
    detail="Internal server error"
)
```

---

## 🔌 WebSocket

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio


class ConnectionManager:
    """Gerencia conexões WebSocket."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para atualizações em tempo real."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Aguarda mensagem do cliente
            data = await websocket.receive_text()
            
            # Processa comando
            command = json.loads(data)
            
            if command.get("type") == "subscribe":
                # Handle subscription
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## ✅ Checklist de Novo Endpoint

```
[ ] Endpoint segue padrão REST (GET, POST, PUT, DELETE)
[ ] Request model com validação Pydantic
[ ] Response model definido
[ ] Docstring com descrição clara
[ ] Logging adequado (info, warning, error)
[ ] Tratamento de erros com códigos HTTP corretos
[ ] Documentação em docs/API_SPEC.md atualizada
[ ] Teste unitário criado
[ ] Exemplo de curl funcional
```

---

## 📚 Referências

- `docs/API_SPEC.md` - Especificação completa
- `backend/api/routes/trading_routes.py` - Exemplo de router complexo
- [FastAPI Docs](https://fastapi.tiangolo.com/)
