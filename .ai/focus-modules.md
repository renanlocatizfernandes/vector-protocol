# Focus Modules

This file guides the Agent on where to focus attention based on the task domain, preventing context overload.

## 1. Backend Core (Python/FastAPI)
**Focus Here For**: API Logic, Database models, Trading Engine, Background Tasks.

- **Primary Directories**:
  - `backend/api/`: REST Endpoints (`routes/`), Schemas (`models/`).
  - `backend/modules/`: Core business logic (Scanner, Signals, Execution).
  - `backend/models/`: Database ORM definitions.
- **Key Files**:
  - `backend/main.py` or `backend/api/app.py`: Entry point.
  - `backend/config/settings.py`: Configuration loading.
- **Ignore**:
  - `frontend/`: UI code.
  - `kubernetes/`, `docker-compose.yml`: Unless changing infra requirements.

## 2. Frontend (React/Vite)
**Focus Here For**: UI/UX, Dashboards, Client-side state.

- **Primary Directories**:
  - `frontend/src/components`: Reusable UI elements.
  - `frontend/src/pages` or `views`: Page-level components.
  - `frontend/src/hooks`: Custom React hooks.
  - `frontend/src/api`: Axios/Fetch wrappers for Backend communication.
- **Key Files**:
  - `frontend/package.json`: Dependencies.
  - `frontend/vite.config.ts`: Build config.
- **Ignore**:
  - `backend/`: Server logic (treat API as a black box contract).

## 3. Infrastructure & DevOps
**Focus Here For**: Deployment, Containers, CI/CD.

- **Primary Directories**:
  - `kubernetes/`: K8s manifests.
  - Root: `docker-compose.yml`, `Dockerfile` (in backend/frontend).
- **Key Files**:
  - `.env.example`: Env var templates.
- **Warning**: Do not modify `Dockerfile` unless explicitly asked.

## 4. Documentation & Governance
**Focus Here For**: Updating guidelines, specs, runbooks.

- **Primary Directories**:
  - `docs/`: All human documentation.
  - `specs/`: Feature specifications.
  - `.ai/`: Agent context.
  - `.agent/`: Antigravity rules.

## Navigation Heuristic
If the task is **"Add a new trading strategy"**:
1. Read `specs/SYSTEM_SPEC.md`.
2. Focus on `backend/modules/strategies/` (if exists) or `backend/modules/signal_generator.py`.
3. Check `backend/models/` for data storage.
4. Ignore `frontend/` initially.
