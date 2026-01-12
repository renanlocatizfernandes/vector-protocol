---
status: filled
generated: 2026-01-12
---

# Tooling & Productivity Guide

Collect the scripts, automation, and editor settings that keep contributors efficient.

## Required Tooling

- Docker + Docker Compose for full-stack orchestration and service parity.
- Node.js 18+ for frontend dev (`npm install`, `npm run dev`, `npm run build`).
- Python 3.10+ for backend dev (`pip install -r backend/requirements.txt`).
- PostgreSQL and Redis are provided via Docker Compose for local workflows.

## Recommended Automation

- Use `npm run dev` (frontend) and `uvicorn api.app:app --reload` (backend) for fast iteration.
- `docker compose up --build -d` keeps local services in sync with production topology.
- Monitoring helpers: `smart_monitor.sh` and `monitor_continuous.py` for ops status checks.

## IDE / Editor Setup

- Recommended: TypeScript and Python language servers, ESLint/Tailwind CSS tooling, and Docker extensions.
- Keep `.env` files excluded from indexing or shared settings.

## Productivity Tips

- Use `docker compose logs -f api` and `docker compose logs -f supervisor` for live triage.
- Keep `logs/` cleaned to reduce noise; archive before major testnet runs.
- For quick checks, reuse commands in `ACOMPANHAMENTO_README.md`.
