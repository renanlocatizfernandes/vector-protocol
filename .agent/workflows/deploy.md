---
description: Workflow para deploy do Vector Protocol
---

# Deploy Workflow

Use este workflow para deploy em ambiente de produção.

---

## Pré-requisitos

- [ ] Todos os testes passando
- [ ] CHANGELOG atualizado
- [ ] Versão definida
- [ ] Variáveis de ambiente configuradas

---

## Deploy via Docker Compose (Recomendado)

### 1. Preparar Ambiente

```bash
# Verificar .env está configurado
cat .env.example

# Copiar e editar se necessário
cp .env.example .env
# Editar: BINANCE_API_KEY, BINANCE_API_SECRET, etc
```

### 2. Build e Start

```bash
# Build completo
docker compose build --no-cache

# Start em background
docker compose up -d
```

### 3. Verificar Saúde

```bash
// turbo
curl -sS http://localhost:8000/health | jq .
```

Deve retornar:

```json
{
  "status": "healthy",
  "checks": {
    "db": "ok",
    "redis": "ok", 
    "binance": "ok"
  }
}
```

### 4. Verificar Logs

```bash
# API logs
docker logs -f trading-bot-api --tail 50

# Todos os serviços
docker compose logs -f
```

### 5. Testar Frontend

Acessar: <http://localhost:3000>

---

## Rollback

Se algo der errado:

```bash
# Parar serviços
docker compose down

# Reverter para versão anterior (se houver tag)
git checkout v<versão-anterior>

# Rebuild e restart
docker compose up -d --build
```

---

## Atualização de Versão

### 1. Tagear Release

```bash
# Atualizar CHANGELOG com versão
# docs/CHANGELOG.md: Mudar [Unreleased] para [X.Y.Z] - YYYY-MM-DD

git add docs/CHANGELOG.md
git commit -m "chore: prepare release vX.Y.Z"

# Criar tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

### 2. Deploy da Nova Versão

```bash
docker compose down
git pull origin main
docker compose up -d --build
```

---

## Monitoramento Pós-Deploy

```bash
# Status do bot
curl -sS "http://localhost:8000/api/trading/bot/status" | jq .

# Posições abertas
curl -sS "http://localhost:8000/api/trading/positions" | jq .

# Logs recentes
curl -sS "http://localhost:8000/api/system/logs?component=api&tail=50" | jq -r .
```

---

## Variáveis de Ambiente Críticas

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `BINANCE_TESTNET` | Usar testnet | `false` para prod |
| `BINANCE_API_KEY` | API key Binance | `xxx` |
| `BINANCE_API_SECRET` | API secret | `xxx` |
| `DATABASE_URL` | URL PostgreSQL | `postgresql://...` |
| `REDIS_HOST` | Host Redis | `redis` |
| `TELEGRAM_ENABLED` | Notificações | `true` |
| `AUTOSTART_BOT` | Auto-iniciar bot | `false` (recomendado) |

---

## Checklist de Deploy

```
[ ] Testes passando (CI verde)
[ ] CHANGELOG atualizado
[ ] .env configurado corretamente
[ ] BINANCE_TESTNET=false para produção
[ ] Build sem erros
[ ] Health check OK
[ ] Frontend acessível
[ ] Logs sem erros críticos
[ ] Tag de versão criada
```
