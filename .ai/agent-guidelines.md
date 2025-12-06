# AI Agent Guidelines

Directives for Large Language Models working on this repository.

## Golden Rules

1. **First, Read**: Before generating code, read:
   - `README.md`
   - `.ai/context-map.md`
   - `docs/ARCHITECTURE.md`
   - `docs/GOVERNANCE.md`

2. **Plan First**: Never start coding without a plan. For complex features, create a plan in `implementation_plan.md` or similar.

3. **No Secrets**: You are strictly forbidden from outputting API keys, passwords, or `.env` content. If you see them, redact them (e.g., `sk-***`).

4. **Verify**: Always verify your changes. If you write code, propose a test or a way to manually verify it.

5. **Docs Sync**: If you change code logic, you MUST update the corresponding documentation in `docs/`.

## Coding Style

- **Python**: Async first (FastAPI). Type hints are mandatory. Docstrings for all public functions.
- **Frontend**: Functional React components. Tailwind for styling (if present) or CSS modules.
- **Commits**: Use Conventional Commits (e.g., `feat: add scanner filter`, `fix: resolve overflow`).

## Safety checks

- **Destructive Commands**: Do not use `rm -rf`, `format`, or aggressive bulk deletes without specific user authorization.
- **Files**: Do not modify files outside of the requested scope.
