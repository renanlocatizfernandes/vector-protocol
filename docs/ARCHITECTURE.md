# System Architecture

## Overview
The Antigravity Crypto Trading Bot is a modular, autonomous system designed to trade cryptocurrency futures. It uses a microservices-like architecture orchestrated via Docker Compose.

## Components

### 1. Backend API (`backend/`)
- **Framework**: FastAPI (Python).
- **Responsibility**: 
  - Exposes REST API for frontend and external control.
  - Runs background tasks (via `modules/`).
  - Manages trading logic (Scanner, Signals, Execution, Risk).
- **Entry Point**: `api/app.py` (served via Uvicorn).

### 2. Frontend (`frontend/`)
- **Framework**: React + Vite + TypeScript.
- **Responsibility**: User Interface for monitoring trades, configuration, and system status.
- **Communication**: Talks to Backend API via HTTP requests.

### 3. Database (`db`)
- **Technology**: PostgreSQL 15.
- **Responsibility**: Persistent storage for:
  - Trade history (`Trade` model).
  - Configuration (`Settings` model).
  - User accounts (if applicable).

### 4. Cache / Message Broker (`redis`)
- **Technology**: Redis 7.
- **Responsibility**: 
  - Fast caching for market data.
  - Potential message broker for async tasks (Celery/background workers).

## Container Structure
(Based on `docker-compose.yml`)

| Service | Internal Port | Host Port | Dependencies |
|---------|---------------|-----------|--------------|
| `api` | 8000 | 8000 | db, redis |
| `frontend`| 80 | 3000 | api |
| `db` | 5432 | 5433 | - |
| `redis` | 6379 | 6380 | - |

## Data Flow
1. **Market Scanner** fetches data from Binance API -> Filters symbols -> Stores candidates.
2. **Signal Generator** analyzes candidates -> Generates Buy/Sell signals.
3. **Execution Engine** validates signals via **Risk Manager** -> Places orders on Binance.
4. **Position Monitor** tracks active trades -> Updates DB -> Checks TSL/TP/SL.
5. **Frontend** polls API for latest status.

## Directory Structure
```
root
├── backend/            # Python logic
├── frontend/           # React UI
├── database/           # DB Migrations
├── docs/               # Documentation
├── .ai/                # AI Context & Tools
└── specs/              # Feature Specifications
```
