# Repository Context Map

This file maps the repository structure, identifying critical modules, entry points, and sensitive areas.

## Directory Structure

| Path | Type | Criticality | Description |
|------|------|-------------|-------------|
| `backend/` | Source | High | Core application logic (FastAPI, Python). |
| `backend/api/` | Source | Medium | API endpoints and routing. |
| `backend/modules/` | Source | High | Trading logic (Scanner, Signals, Execution, Risk). |
| `backend/config/` | Config | High | Environment settings (Pydantic). **Sensitve**. |
| `frontend/` | Source | Medium | React/Vite Frontend. |
| `database/` | Data | High | Database migrations and seeds. |
| `docs/` | Ops | Low | Project documentation. |
| `.ai/` | Meta | Medium | AI tools, prompts, and context. |
| `.ai/focus-modules.md` | Guide | High | Map of domains to files. |
| `.ai/safety-profile.md` | Security | **Critical** | Do's and Don'ts. |
| `specs/` | Meta | High | Feature specifications. |

## Critical Entry Points

- **Backend Start**: `backend/api/app.py` (Main FastAPI entry).
- **Docker Entry**: `docker-compose.yml` (Orchestrates all services).
- **Scanner**: `backend/modules/market_scanner.py`.
- **Signal Gen**: `backend/modules/signal_generator.py`.
- **Executor**: `backend/modules/execution_engine.py`.
- **Risk Manager**: `backend/modules/risk_manager.py`.

## Data Sensitivity

> [!CAUTION]
> **HIGH SENSITIVITY AREAS**
> - `backend/config/settings.py` (Loads env vars).
> - `.env` (API Keys, Secrets). **NEVER READ OR OUTPUT CONTENT**.
> - `logs/` (May contain debug info request/response).

## Generated Folders (Ignore)
- `__pycache__/`
- `node_modules/`
- `.pytest_cache/`
- `dist/`
- `.venv/`
