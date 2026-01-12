---
status: filled
generated: 2026-01-12
---

# Testing Strategy

Document how quality is maintained across the codebase.

## Test Types
- Unit: Backend uses pytest in `backend/tests` and root `tests/`. Frontend uses Vitest via `frontend/npm run test`.
- Integration: Testnet and persistence checks live in `tests/` and backend test suites; require API keys and DB access.
- End-to-end: No dedicated E2E harness currently; use Docker Compose + manual flows.

## Running Tests
- Frontend: `cd frontend && npm run test` (Vitest); use `npm run test -- --watch` while iterating.
- Backend: `cd backend && pytest` or run targeted tests by file.
- Optional coverage: `cd frontend && npm run test -- --coverage` and `cd backend && pytest --cov` if needed.

## Quality Gates
- No hard coverage threshold documented; ensure critical trading paths are covered.
- Follow Python PEP8 and TypeScript conventions; add or update tests for logic changes.

## Troubleshooting

Testnet suites require valid Binance keys and network access; failures often indicate missing env vars or rate limits. DB-dependent tests may require a running PostgreSQL container from Docker Compose.
