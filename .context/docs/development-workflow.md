---
status: filled
generated: 2026-01-12
---

# Development Workflow

Outline the day-to-day engineering process for this repository.

## Branching & Releases
- Simplified Git Flow: `main` is production-ready; feature branches use prefixes like `feature/`, `fix/`, `docs/`, `refactor/`.
- Releases are tagged using semantic versioning (`vMAJOR.MINOR.PATCH`) when a release is ready.

## Local Development
- Commands to install dependencies: `npm install`
- Run the CLI locally: `npm run dev`
- Build for distribution: `npm run build`

## Code Review Expectations
- Human review is mandatory for logic changes; verify tests and ensure secrets are never introduced.
- Confirm alignment with `specs/` and update docs for behavior changes.
- Reference [AGENTS.md](../../AGENTS.md) for agent collaboration tips.

## Onboarding Tasks

- Read `README.md`, `docs/RUNBOOK.md`, and `docs/GOVERNANCE.md` to understand setup and roles.
- Verify local stack with `docker compose up --build -d` and the `/health` endpoint.
- Review `specs/SYSTEM_SPEC.md` and `docs/API_SPEC.md` for system expectations.
