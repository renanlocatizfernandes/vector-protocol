---
name: project-context
description: Contexto completo do projeto Vector Protocol. Use SEMPRE no início de qualquer tarefa complexa para entender a arquitetura e convenções.
---

# Contexto do Projeto Vector Protocol

## 📋 Resumo Executivo

O **Vector Protocol** (também conhecido como Antigravity Trading Bot) é um sistema autônomo de trading de criptomoedas para Binance Futures. É uma aplicação full-stack composta por:

- **Backend**: Python/FastAPI com arquitetura async
- **Frontend**: React + TypeScript com Vite e Tailwind CSS (tema cyberpunk)
- **Infraestrutura**: PostgreSQL, Redis, Docker Compose, GitHub Actions CI/CD
- **Integrações**: Binance API, Telegram Bot

O projeto é otimizado para colaboração com agentes de IA (Antigravity, Claude, Cursor).

---

## 🛠️ Stack Tecnológica

### Backend (Python 3.11+)
| Categoria | Tecnologias |
|-----------|-------------|
| Framework | FastAPI 0.115.0, Uvicorn 0.32.0 |
| Database | PostgreSQL 15, SQLAlchemy 2.0.36, Alembic 1.14.0 |
| Cache | Redis 5.2.0 |
| APIs | python-binance 1.0.21, httpx 0.27.2, aiohttp 3.11.7 |
| Trading | pandas 2.2.3, numpy 2.1.3, ta 0.11.0 (Technical Analysis) |
| Async | asyncio, websockets 13.1, tenacity 9.0.0 (retries) |
| Config | Pydantic Settings 2.6.1, python-dotenv 1.0.1 |
| Telegram | python-telegram-bot 21.8 |
| Testes | pytest 8.3.3, pytest-asyncio 0.24.0 |

### Frontend (Node.js 20+)
| Categoria | Tecnologias |
|-----------|-------------|
| Framework | React 18.3.1, TypeScript 5.6.2 |
| Build | Vite 5.4.0 |
| Styling | Tailwind CSS 3.4.17 |
| State | Zustand 4.4.1 |
| UI | Radix UI (Dialog, Checkbox, Select), Lucide React |
| Charts | Recharts 2.12.7 |
| HTTP | Axios 1.7.2 |
| Testes | Vitest 4.0.8, Testing Library |

### Infraestrutura
| Componente | Tecnologia |
|------------|------------|
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Database | PostgreSQL 15 |
| Cache/Pub-Sub | Redis 7 |
| Reverse Proxy | Nginx (produção) |

---

## 📁 Estrutura de Diretórios

```
Vector Protocol/
├── .agent/                      # Configurações do Antigravity IDE
│   ├── rules/                   # Regras de contexto (4 arquivos)
│   ├── skills/                  # Skills personalizadas ⬅️ VOCÊ ESTÁ AQUI
│   └── workflows/               # Workflows automatizados
├── .ai/                         # Contexto para agentes de IA
│   ├── agent-guidelines.md      # Regras para agentes
│   ├── context-map.md           # Mapa de arquivos críticos
│   ├── focus-modules.md         # Navegação por domínio
│   ├── safety-profile.md        # Limites de segurança
│   └── tasks-playbook.md        # Procedimentos padrão
├── .github/workflows/           # CI/CD (ci.yml)
├── backend/                     # 🔥 Core do sistema
│   ├── api/                     # FastAPI routes e modelos
│   ├── config/                  # settings.py (Pydantic)
│   ├── modules/                 # 🎯 Lógica de trading (25+ módulos)
│   │   ├── autonomous_bot.py    # Orquestrador do bot
│   │   ├── signal_generator.py  # Geração de sinais
│   │   ├── order_executor.py    # Execução de ordens
│   │   ├── position_monitor.py  # Monitoramento de posições
│   │   ├── risk_manager.py      # Gestão de risco
│   │   ├── market_scanner.py    # Scanner de mercado
│   │   └── ...                  # Outros módulos
│   ├── utils/                   # Utilitários (binance_client, logger)
│   └── tests/                   # Testes pytest
├── frontend/                    # 🎨 React UI
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── pages/               # Páginas da aplicação
│   │   ├── services/            # API clients
│   │   └── hooks/               # Custom hooks
│   └── ...
├── docs/                        # 📚 Documentação (20+ arquivos)
│   ├── ARCHITECTURE.md          # Arquitetura do sistema
│   ├── API_SPEC.md              # Especificação da API
│   ├── RUNBOOK.md               # Guia operacional
│   ├── DEPLOYMENT.md            # Guia de deploy
│   └── ...
├── kubernetes/                  # K8s manifests
├── specs/                       # Especificações de features
└── docker-compose.yml           # Orquestração local
```

---

## 🏗️ Arquitetura do Sistema

### Fluxo Principal de Trading

```
Market Scanner → Signal Generator → Risk Calculator → Order Executor → Position Monitor
```

1. **Market Scanner** (`market_scanner.py`): Filtra top símbolos por volume/tendência
2. **Signal Generator** (`signal_generator.py`): Gera sinais LONG/SHORT com score de confiança
3. **Risk Calculator** (`risk_calculator.py`): Calcula tamanho de posição baseado em risco %
4. **Order Executor** (`order_executor.py`): Executa trades com LIMIT (fallback MARKET)
5. **Position Monitor** (`position_monitor.py`): Acompanha posições, SL/TP/TSL
6. **Autonomous Bot** (`autonomous_bot.py`): Orquestra todo o ciclo em loop

### Componentes Chave

- **Binance Client** (`utils/binance_client.py`): Singleton para API/WebSocket
- **Settings** (`config/settings.py`): ~380 linhas de configuração (Pydantic)
- **Telegram Bot** (`modules/telegram_bot.py`): Notificações assíncronas

---

## 📝 Convenções de Código

### Python (Backend)
```python
# Imports
from utils.logger import setup_logger
from config.settings import get_settings

# Logger por módulo
logger = setup_logger("module_name")

# Async-first
async def my_function(param: str) -> dict:
    """Docstring obrigatória para funções públicas."""
    settings = get_settings()
    ...

# Type hints são OBRIGATÓRIOS
def calculate_risk(balance: float, risk_pct: float) -> float:
    return balance * risk_pct
```

### TypeScript (Frontend)
```typescript
// Componentes funcionais
const MyComponent: React.FC<Props> = ({ prop1, prop2 }) => {
  const [state, setState] = useState<Type>(initial);
  
  // Tailwind para styling
  return (
    <div className="bg-gray-900 p-4 rounded-lg">
      {/* ... */}
    </div>
  );
};
```

### Commits (Conventional Commits)
```
feat: add scanner filter for high-volume symbols
fix: resolve margin calculation overflow
docs: update API_SPEC with new execution endpoints
refactor: simplify risk calculator logic
test: add unit tests for signal generator
chore: update dependencies to latest versions
```

---

## ⚙️ Comandos Importantes

### Desenvolvimento Local

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm ci
npm run dev  # Acessa em http://localhost:5173

# Testes
PYTHONPATH=backend pytest -q backend/tests  # Backend
npm test                                      # Frontend
```

### Docker

```bash
docker compose up -d --build        # Start all
docker compose logs -f api          # View API logs
docker compose down -v              # Stop + remove volumes

# Health check
curl -sS http://localhost:8000/health | jq .
```

### API Endpoints Comuns

```bash
# Bot control
curl -X POST "http://localhost:8000/api/trading/bot/start?dry_run=false"
curl -X POST "http://localhost:8000/api/trading/bot/stop"
curl -sS "http://localhost:8000/api/trading/bot/status"

# Execute trade
curl -X POST "http://localhost:8000/api/trading/execute" \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","risk_profile":"moderate","dry_run":false}'

# View positions
curl -sS "http://localhost:8000/api/trading/positions"
```

---

## ⚠️ Restrições CRÍTICAS

### Arquivos Read-Only (Nunca modificar sem permissão explícita)
- `.env` - Contém secrets (API keys)
- `backend/config/settings.py` - Apenas se adicionando nova config
- `docker-compose.yml` - Orquestração core

### Diretórios Proibidos
- `clients/`, `data/`, `logs/` - Dados de produção
- `.git/`, `node_modules/`, `__pycache__`, `.venv` - Gerados

### Comandos Proibidos
- `rm -rf` em paths genéricos
- `git clean -fdx`
- `docker system prune -a`

### Segurança
- NUNCA exibir conteúdo de `.env`
- Redatar API keys como `sk-***`
- Usar TESTNET para desenvolvimento (`BINANCE_TESTNET=true`)

---

## 📊 Métricas de Qualidade

| Métrica | Valor Atual |
|---------|-------------|
| Testes Backend | 5 arquivos (pytest) |
| Testes Frontend | Vitest configurado |
| CI/CD | GitHub Actions (2 jobs) |
| Cobertura | A definir |
| Linting | Não configurado explicitamente |

---

## 🔗 Documentos Relacionados

Para informações detalhadas, consulte:
- **Arquitetura**: `docs/ARCHITECTURE.md`
- **API**: `docs/API_SPEC.md`
- **Operações**: `docs/RUNBOOK.md`
- **Deploy**: `docs/DEPLOYMENT.md`
- **Segurança AI**: `.ai/safety-profile.md`
- **Mapa de Contexto**: `.ai/context-map.md`
