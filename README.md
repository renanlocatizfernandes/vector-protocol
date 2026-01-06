# Antigravity Trading Bot

A high-performance, autonomous crypto trading bot with advanced governance and AI support.

## 🚀 Overview
This system automates cryptocurrency trading strategies on Binance Futures. It includes a FastAPI backend, a React frontend, and a complete suite of governance tools for safe iteration.

## 📚 Documentation
- **[Architecture](docs/ARCHITECTURE.md)**: System design and components.
- **[Runbook](docs/RUNBOOK.md)**: How to run, test, and troubleshoot.
- **[Governance](docs/GOVERNANCE.md)**: Roles and workflows for humans and agents.
- **[Contributing](docs/CONTRIBUTING.md)**: Guidelines for code changes.
- **[Versioning](docs/VERSIONING.md)**: Branching and tagging strategy.
- **[Changelog](docs/CHANGELOG.md)**: History of changes.

## 🤖 AI Ready
This repository is optimized for LLM agents.
- **[.ai/context-map.md](.ai/context-map.md)**: Map of critical files and sensitivity.
- **[.ai/agent-guidelines.md](.ai/agent-guidelines.md)**: Rules for AI contributors.
- **[.ai/tasks-playbook.md](.ai/tasks-playbook.md)**: Standard procedures for common tasks.
- **[.agent/rules/](.agent/rules/)**: Specific rules for Antigravity IDE.

## ⚡ Quick Start

### Docker (Recommended)
```bash
cp .env.example .env
# Edit .env with your keys
docker compose up --build -d
```
Access Frontend: http://localhost:3000
API default: http://localhost:8000 (configure `API_PORT_HOST` to change)

### Local Development
See [docs/RUNBOOK.md](docs/RUNBOOK.md) for detailed local setup instructions.

## 🔒 Security
- Never commit `.env` or API keys.
- Check `docs/GOVERNANCE.md` for security protocols.
- Optional API key auth is available via `API_AUTH_ENABLED` and `API_KEY`.
