# VECTOR Protocol ⚡

![VECTOR Banner](docs/assets/vector_banner.png)

> **High-Frequency Autonomous Trading Engine**
> *Precision. Direction. Magnitude.*

**VECTOR** (formerly `crypto-trading-bot`) is a sophisticated, self-healing algorithmic trading system designed for the Binance Futures market. It combines real-time market scanning ("Radar"), multi-frame signal processing ("Oracle"), and risk-managed execution to capture volatility with mathematical precision.

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/renanlocatizfernandes/crypto-trading-bot)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![AI Managed](https://img.shields.io/badge/AI-Managed-orange)](docs/GOVERNANCE.md)

## ⚡ Core Capabilities

- **🛡️ Aegis Risk Guard**: Dynamic position sizing and liquidation prevention.
- **📡 Vector Radar**: Scans 100+ pairs for volume/volatility anomalies.
- **🧠 Neural Oracle**: Multi-timeframe trend analysis with RSI/MACD confirmation.
- **🔌 Self-Healing**: Supervisor module auto-restarts frozen processes.

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
Access Command Deck: http://localhost:3000
API default: http://localhost:8000 (configure `API_PORT_HOST` to change)

### Local Development
See [docs/RUNBOOK.md](docs/RUNBOOK.md) for detailed local setup instructions.

## 🔒 Security
- Never commit `.env` or API keys.
- Check `docs/GOVERNANCE.md` for security protocols.
- Optional API key auth is available via `API_AUTH_ENABLED` and `API_KEY`.
