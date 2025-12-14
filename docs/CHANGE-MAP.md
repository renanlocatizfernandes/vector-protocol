# Change Impact Map

This document guides the "Impact Analysis" phase of any change. "If you change X, you must likely change Y".

## 1. Backend

### If you modify a `Model` (Database Table)
**Path**: `backend/models/*.py`
- [ ] **Migrations**: Create a migration in `database/versions/` (using alembic).
- [ ] **Schemas**: Update Pydantic schemas in `backend/api/models/` or `schemas/`.
- [ ] **Factories**: Update test factories.
- [ ] **Types**: Check if Frontend types need updating (manual sync required).

### If you modify a `Route` (API Endpoint)
**Path**: `backend/api/routes/*.py`
- [ ] **Docs**: Update Docstring (Swagger UI depends on it).
- [ ] **Tests**: Update `backend/tests/api/`.
- [ ] **Frontend**: Update the API client wrapper in `frontend/src/api/`.

### If you modify `Execution Engine`
**Path**: `backend/modules/execution_engine.py`
- [ ] **Risk**: **CRITICAL**. Verify `Risk Manager` checks are still called.
- [ ] **Simulation**: Verify if this change impacts Backtesting logic.

## 2. Frontend

### If you add a new `Component`
**Path**: `frontend/src/components/`
- [ ] **Design System**: Use existing Tailwind classes / CSS variables.
- [ ] **Responsiveness**: Check Mobile vs Desktop.

### If you modify `Environment Variables`
**Path**: `.env` / `backend/config/`
- [ ] **Docker**: Check `docker-compose.yml`.
- [ ] **CI**: Update CI secrets (if applicable).
- [ ] **Documentation**: Update `README.md` and `RUNBOOK.md` setup steps.

## 3. General

### If you add a Dependency (`pip` or `npm`)
- [ ] **Lockfiles**: Commit `requirements.lock` or `package-lock.json`.
- [ ] **Docker**: Rebuild container to verify installation.
- [ ] **License**: Check for compliant licenses (MIT, Apache 2.0).
