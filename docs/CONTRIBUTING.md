# Contributing Guidelines

Thank you for your interest in the Crypto Trading Bot!

## Getting Started
1. Review `README.md` and `docs/RUNBOOK.md` to set up the environment.
2. Check `docs/GOVERNANCE.md` to understand roles and permissions.

## Development Workflow
1. **Find or Create a Task**: Look for open issues or create a Spec/Task in `task.md` (if using Antigravity).
2. **Create a Branch**: Use `feature/`, `fix/`, or `docs/` prefix.
   - Example: `feature/market-scanner-optimization`
3. **Planning**: Check **[docs/CHANGE-MAP.md](CHANGE-MAP.md)** to understand side effects.
4. **Implement**: Write clean, testable code.
4. **Test**: Run existing tests (`pytest`).
   ```bash
   cd backend && pytest
   ```
5. **Open PR**: Submit against `main`.

## Coding Standards
- **Python**: PEP 8. Use type hints.
- **Databases**: Use SQLAlchemy models.
- **Docs**: Keep markdown updated.

## Using AI Tools
We encourage the use of LLMs (Antigravity, Cursor, Copilot). 
**See [docs/AI-CONTRIBUTION.md](AI-CONTRIBUTION.md) for full policies.**

Basic Rules:
- **Review**: Human must review.
- **Context**: Use `project-knowledge.md`.
- **Safety**: No secrets.
