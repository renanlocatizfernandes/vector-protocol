# Database de Configurações

Sistema de gerenciamento de configurações centralizado via PostgreSQL com histórico de mudanças e rollback granular.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Características](#características)
- [Arquitetura](#arquitetura)
- [Migração](#migração)
- [API Endpoints](#api-endpoints)
- [Uso](#uso)
- [Rollback](#rollback)
- [Exemplos](#exemplos)

---

## Visão Geral

O sistema de Database de Configurações permite gerenciar todas as configurações do bot via PostgreSQL, mantendo histórico completo de todas as mudanças e permitindo rollback instantâneo.

**Categorias de Configurações:**
- `bot` - Configurações principais do bot (min_score, scan_interval, etc)
- `sniper` - Configurações do modo sniper (tp_pct, sl_pct, extra_slots, etc)
- `risk` - Gestão de risco (max_positions, risk_per_trade, leverage, etc)
- `scanner` - Scanner de mercado (max_symbols, whitelist, etc)
- `general` - Configurações gerais (telegram, virtual_balance, etc)

---

## Características

✅ **Zero Downtime** - Migração sem parar o bot  
✅ **Histórico Completo** - Todas as mudanças são registradas  
✅ **Rollback Granular** - Reverta configurações específicas ou todas  
✅ **Fallback para .env** - ConfigManager sempre tenta database primeiro, depois .env  
✅ **Cache Automático** - Configurações frequentes ficam em cache  
✅ **Recarregamento Automático** - Bot recarrega após mudanças  
✅ **Batch Updates** - Atualize múltiplas configs de uma vez  
✅ **Validação** - Tipos de dados são validados automaticamente

---

## Arquitetura

### Tabelas do PostgreSQL

```sql
-- Tabela principal de configurações
CREATE TABLE configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de histórico
CREATE TABLE config_history (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by VARCHAR(100),
    reason TEXT,
    changed_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (config_key) REFERENCES configurations(key)
);
```

### ConfigManager

```python
from modules.config_manager import ConfigManager
from config.settings import get_settings
from models.database import SessionLocal

db = SessionLocal()
config_manager = ConfigManager(
    db_session=db,
    env_settings=get_settings()
)
```

---

## Migração

### Primeira Migração

O script de migração importa todas as configurações do .env para o PostgreSQL **sem parar o bot**.

```bash
# No host
docker exec trading-bot-api sh -c "cd /app && python scripts/migrate_to_database_config.py --auto-confirm"

# Ou interativo (para confirmar manualmente)
docker exec trading-bot-api sh -c "cd /app && python scripts/migrate_to_database_config.py"
```

### O que o script faz?

1. ✅ Verifica se PostgreSQL está acessível
2. ✅ Cria tabelas se não existirem
3. ✅ Importa todas as configurações do .env
4. ✅ Registra histórico inicial das configurações
5. ✅ Atualiza cache do ConfigManager
6. ✅ **Bot continua rodando sem parar (zero downtime)**

---

## API Endpoints

Base URL: `http://localhost:8001/api/database-config`

### Health Check

Verifica se o sistema de configurações está funcionando.

```bash
GET /api/database-config/health
```

**Resposta:**
```json
{
  "status": "healthy",
  "database_accessible": true,
  "database_config_count": 31,
  "test_config_value": 70,
  "env_fallback_working": true,
  "cache_enabled": true,
  "timestamp": "2026-01-11T21:26:34.419547"
}
```

### Listar Todas as Configurações

```bash
GET /api/database-config/
```

**Resposta:**
```json
{
  "configs": [
    {
      "key": "BOT_MIN_SCORE",
      "value": 70,
      "value_type": "int",
      "category": "bot",
      "description": "Score mínimo para abrir posição",
      "version": 1,
      "updated_at": "2026-01-11T21:21:15.674026"
    },
    ...
  ],
  "count": 31,
  "timestamp": "2026-01-11T21:21:15.674026"
}
```

### Listar Categorias

```bash
GET /api/database-config/categories
```

**Resposta:**
```json
{
  "categories": ["bot", "general", "risk", "scanner", "sniper"],
  "count": 5
}
```

### Listar por Categoria

```bash
GET /api/database-config/category/{category}

# Exemplo
GET /api/database-config/category/sniper
```

**Resposta:**
```json
{
  "category": "sniper",
  "configs": [
    {
      "key": "SNIPER_TP_PCT",
      "value": 1.2,
      "category": "sniper"
    },
    ...
  ],
  "count": 5
}
```

### Buscar Configuração Específica

```bash
GET /api/database-config/{key}

# Exemplo
GET /api/database-config/BOT_MIN_SCORE
```

**Resposta:**
```json
{
  "key": "BOT_MIN_SCORE",
  "value": 70
}
```

### Atualizar Configuração

```bash
PUT /api/database-config/{key}

# Body
{
  "key": "BOT_MIN_SCORE",
  "value": 80,
  "reason": "Aumentando score para reduzir trades"
}
```

**Resposta:**
```json
{
  "success": true,
  "key": "BOT_MIN_SCORE",
  "old_value": 70,
  "new_value": 80,
  "message": "Configuration 'BOT_MIN_SCORE' updated successfully"
}
```

### Batch Update

Atualize múltiplas configurações em uma única operação.

```bash
POST /api/database-config/batch-update

# Body
[
  {
    "key": "BOT_MIN_SCORE",
    "value": 80,
    "reason": "Teste"
  },
  {
    "key": "MAX_POSITIONS",
    "value": 6,
    "reason": "Aumentando capacidade"
  }
]
```

**Resposta:**
```json
{
  "results": [
    {
      "key": "BOT_MIN_SCORE",
      "success": true,
      "old_value": 70,
      "new_value": 80
    },
    {
      "key": "MAX_POSITIONS",
      "success": true,
      "old_value": 4,
      "new_value": 6
    }
  ],
  "total": 2,
  "success_count": 2
}
```

### Histórico de Configuração

```bash
GET /api/database-config/history/{key}?limit=50

# Exemplo
GET /api/database-config/history/BOT_MIN_SCORE
```

**Resposta:**
```json
{
  "key": "BOT_MIN_SCORE",
  "history": [
    {
      "id": 1,
      "old_value": null,
      "new_value": "70",
      "changed_at": "2026-01-11T21:21:15.674026",
      "changed_by": "migration",
      "reason": "Migração inicial de .env para DB"
    },
    {
      "id": 2,
      "old_value": "70",
      "new_value": "80",
      "changed_at": "2026-01-11T22:30:45.123456",
      "changed_by": "api",
      "reason": "Ajuste de parâmetro"
    }
  ],
  "count": 2
}
```

### Reset para Valor Padrão

```bash
POST /api/database-config/reset/{key}

# Exemplo
POST /api/database-config/reset/BOT_MIN_SCORE
```

**Resposta:**
```json
{
  "success": true,
  "key": "BOT_MIN_SCORE",
  "message": "Configuration 'BOT_MIN_SCORE' reset to default value",
  "timestamp": "2026-01-11T22:35:12.345678"
}
```

### Reload from .env (Rollback Total)

Recarrega todas as configurações do .env, sobrescrevendo o database.

```bash
POST /api/database-config/reload-from-env
```

**Resposta:**
```json
{
  "success": true,
  "message": "Reloaded 31 configurations from .env",
  "count": 31,
  "timestamp": "2026-01-11T21:29:14.101352"
}
```

### Invalidar Cache

```bash
POST /api/database-config/invalidate-cache
POST /api/database-config/invalidate-cache?key=BOT_MIN_SCORE
```

**Resposta:**
```json
{
  "success": true,
  "message": "Todo o cache de configurações invalidado",
  "timestamp": "2026-01-11T22:40:00.000000"
}
```

---

## Uso

### Como usar no código

```python
from modules.config_manager import ConfigManager
from config.settings import get_settings
from models.database import SessionLocal

db = SessionLocal()
config_manager = ConfigManager(
    db_session=db,
    env_settings=get_settings()
)

# Ler configuração
min_score = await config_manager.get('BOT_MIN_SCORE')
print(f"Bot Min Score: {min_score}")  # 70

# Atualizar configuração
await config_manager.set(
    'BOT_MIN_SCORE', 
    80,
    changed_by='script',
    reason='Aumentando threshold'
)

# Obter todas as configurações
all_configs = await config_manager.get_all()

# Obter histórico
history = await config_manager.get_history('BOT_MIN_SCORE', limit=10)

# Invalidar cache
config_manager.invalidate_cache('BOT_MIN_SCORE')
```

---

## Rollback

### Rollback de Configuração Específica

Use o histórico para ver valores anteriores:

```bash
# Ver histórico
GET /api/database-config/history/BOT_MIN_SCORE

# Voltar para valor específico manualmente
PUT /api/database-config/BOT_MIN_SCORE
{
  "key": "BOT_MIN_SCORE",
  "value": 70,
  "reason": "Rollback para valor anterior"
}
```

### Rollback Total para .env

Se precisar restaurar tudo para os valores do .env:

```bash
POST /api/database-config/reload-from-env
```

Isso é útil quando:
- Experimentou mudanças e não funcionaram
- Precisa voltar rapidamente para uma configuração estável
- Migração foi feita e quer restaurar o original

### Reset para Valor Padrão

Para resetar uma configuração para o valor definido no .env:

```bash
POST /api/database-config/reset/BOT_MIN_SCORE
```

---

## Exemplos

### Exemplo 1: Ajuste de Risco During Trading

```bash
# Reduzir risco durante alta volatilidade
curl -X PUT http://localhost:8001/api/database-config/RISK_PER_TRADE \
  -H "Content-Type: application/json" \
  -d '{
    "key": "RISK_PER_TRADE",
    "value": 0.05,
    "reason": "Reduzindo risco durante alta volatilidade"
  }'

# Aumentar positions para compensar
curl -X PUT http://localhost:8001/api/database-config/BOT_MAX_POSITIONS \
  -H "Content-Type: application/json" \
  -d '{
    "key": "BOT_MAX_POSITIONS",
    "value": 8,
    "reason": "Compensando menor risco com mais posições"
  }'
```

### Exemplo 2: Teste de Sniper Parameters

```bash
# Ajustar sniper de forma conservadora
curl -X PUT http://localhost:8001/api/database-config/SNIPER_SL_PCT \
  -H "Content-Type: application/json" \
  -d '{
    "key": "SNIPER_SL_PCT",
    "value": 0.5,
    "reason": "Stop loss mais apertado para reduzir perdas"
  }'

curl -X PUT http://localhost:8001/api/database-config/SNIPER_TP_PCT \
  -H "Content-Type: application/json" \
  -d '{
    "key": "SNIPER_TP_PCT",
    "value": 1.5,
    "reason": "Take profit maior para melhor RR"
  }'

# Se não funcionar, rollback rápido
curl -X POST http://localhost:8001/api/database-config/reload-from-env
```

### Exemplo 3: Mudança em Massa via Batch Update

```bash
curl -X POST http://localhost:8001/api/database-config/batch-update \
  -H "Content-Type: application/json" \
  -d '[
    {
      "key": "BOT_MIN_SCORE",
      "value": 75,
      "reason": "Otimização de parâmetros"
    },
    {
      "key": "MAX_POSITIONS",
      "value": 6,
      "reason": "Aumentando capacidade"
    },
    {
      "key": "RISK_PER_TRADE",
      "value": 0.08,
      "reason": "Ajuste de risco"
    }
  ]'
```

---

## Notas Importantes

⚠️ **Fallback**: O ConfigManager sempre verifica:
1. Database (configurações atualizadas)
2. .env (valores padrão)
3. Defaults hardcoded (última linha de defesa)

⚠️ **Cache**: Configurações são cacheadas automaticamente. Se você alterar diretamente no database, invalide o cache.

⚠️ **Tipos**: Valores são validados por tipo:
- `int` - Números inteiros
- `float` - Números decimais
- `bool` - true/false
- `str` - Strings
- `list` - Arrays JSON

⚠️ **Bot Reload**: Após qualquer atualização via API, o bot recarrega automaticamente as configurações.

---

## Troubleshooting

### Configuração não é aplicada

```bash
# 1. Verificar se valor foi salvo
GET /api/database-config/{key}

# 2. Invalidar cache
POST /api/database-config/invalidate-cache

# 3. Verificar logs
docker logs trading-bot-api | grep "config_manager"
```

### Rollback não funciona

```bash
# Verificar se .env está correto
docker exec trading-bot-api sh -c "cat .env | grep BOT_MIN_SCORE"

# Forçar reload
POST /api/database-config/reload-from-env

# Verificar se bot recarregou
docker logs trading-bot-api | grep "Bot recarregado"
```

### Erro de Validação

```python
# Erro: "validation failed"
# Solução: Verificar tipo de dado correto
# int: 70 (não "70")
# float: 0.1 (não "0.1")
# bool: true/false (não "true"/"false")
# list: ["BTCUSDT", "ETHUSDT"] (não string)
```

---

## Documentação da API

Documentação completa disponível em:
`http://localhost:8001/docs#/Database%20Config`
