# Project Knowledge: Vector Protocol (Antigravity Trading Bot)

## 🧠 What is this?
**Vector Protocol** (formerly Antigravity Trading Bot) is a high-performance, autonomous cryptocurrency trading system designed for **Binance Futures**. 
It follows a microservices architecture with a **FastAPI** backend, **React** frontend, and **PostgreSQL/Redis** data layer, fully containerized via Docker.

## 🎯 Goal
To provide a robust, safe, and extensible foundation for algorithmic trading that is **AI-Native**, meaning it is designed to be understood, maintained, and actively developed by both humans and LLM agents in tandem.

## 🗺️ Documentation Map

### 1. Context & Orientation (Start Here)
- **[.ai/context-map.md](.ai/context-map.md)**: Technical map of the codebase, critical paths, and data sensitivity.
- **[.ai/focus-modules.md](.ai/focus-modules.md)**: breakdown of modules (Backend, Frontend, etc.) and what logic belongs where.
- **[.ai/safety-profile.md](.ai/safety-profile.md)**: **CRITICAL**. Read this for prohibited actions and security boundaries.

### 2. Operational Docs
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Deep dive into the system components and data flow.
- **[docs/RUNBOOK.md](docs/RUNBOOK.md)**: How to start, restart, debug, and monitor the system.

### 3. Governance & Contribution
- **[docs/GOVERNANCE.md](docs/GOVERNANCE.md)**: Rules of engagement, roles, and decision making.
- **[docs/AI-CONTRIBUTION.md](docs/AI-CONTRIBUTION.md)**: **REQUIRED** reading for Agents. Usage of tools, limits, and review protocols.
- **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)**: General coding standards (formatting, linting).
- **[docs/CHANGE-MAP.md](docs/CHANGE-MAP.md)**: Dependency graph – "If you change X, check Y".

### 4. Specifications
- **[specs/SYSTEM_SPEC.md](specs/SYSTEM_SPEC.md)**: The core " সংবিধান" (Constitution) of the system's business logic.
- **[specs/SPEC_INDEX.md](specs/SPEC_INDEX.md)**: Registry of all Features (Approved, In-Progress, Deprecated).

### 5. History
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)**: Version history.
- **[docs/VERSIONING.md](docs/VERSIONING.md)**: Branching strategy (Git Flow adaptation).

## 🤖 Agent Instructions
If you are an LLM Agent:
1. **Identify** your mission scope.
2. **Consult** `.ai/focus-modules.md` to identify relevant files.
3. **Check** `.ai/safety-profile.md` to know what NOT to touch.
4. **Plan** your changes.
5. **Execute** referring to `docs/AI-CONTRIBUTION.md` for quality standards.
