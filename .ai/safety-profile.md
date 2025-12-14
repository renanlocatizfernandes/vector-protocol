# Safety Profile

This document outlines the **HARD BOUNDARIES** for AI Agents working on this repository. Violation of these rules is a critical failure.

## 🚫 Prohibited Directories
Agents are **forbidden** from modifying files in these directories unless explicitly instructed for a specific migration task:

- `clients/` (Customer Data)
- `data/` (Local database storage, parquet files)
- `logs/` (Runtime logs)
- `.git/` (Version control internals)
- `node_modules/`, `__pycache__`, `.venv` (Generated artifacts)

## 🔒 Critical Files (Read-Only)
You may **READ** these for context, but **NEVER MODIFY** them without specific user confirmation:

- `.env`: Contains live secrets. **NEVER OUTPUT CONTENTS**.
- `backend/config/settings.py`: Core configuration logic (modify only if adding new config vars).
- `docker-compose.yml`: Core orchestration.

## 💣 Dangerous Commands
**NEVER** propose or execute the following:

- `rm -rf` (Recursive delete) on root or generic paths.
- `git clean -fdx` (Wipe untracked files).
- `docker system prune -a` (Wipe all docker cache).
- Sending data to external URLs (except authorized APIs).

## 🛡️ Operational Safety
1. **Secrets**: If you encounter an API Key or Password in code or logs, **REDACT** it in your usage (e.g., `******`). Do not repeat it.
2. **Migrations**: Database schema changes must always include a rollback plan.
3. **Tests**: Do not delete existing tests to make a build pass. Fix the code.

## 🚨 Emergency Protocols
If you suspect you have broken the build or deleted data:
1. Stop execution.
2. Notify the user immediately.
3. Suggest a git revert command (`git checkout .` or `git revert HEAD`).
