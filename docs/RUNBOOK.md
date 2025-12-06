# Runbook

Operational guide for the Crypto Trading Bot.

## Environment Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.10+ (for local backend dev)

### Configuration
1. Copy example env:
   ```bash
   cp .env.example .env
   ```
2. Populate critical variables:
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
   - `DATABASE_URL` (if not using Docker default)

## Starting the System

### Production (Docker)
To start the entire stack (DB, Redis, API, Frontend):
```bash
docker compose up --build -d
```

### Development (Local)
**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Verification

### Health Checks
- **API Health**: `GET http://localhost:8000/health` -> Should return `200 OK`.
- **Frontend**: Access `http://localhost:3000` (Docker) or `http://localhost:5173` (Local).

### Logging
- **Docker Logs**:
  ```bash
  docker compose logs -f api
  docker compose logs -f supervisor
  ```
- **Files**: Check `./logs/` directory for application logs.

## Troubleshooting

### "Database connection failed"
- Ensure Postgres container is healthy: `docker compose ps`
- Check logs: `docker compose logs db`
- Verify `DATABASE_URL` in `.env`.

### "Binance API permissions"
- Ensure API Key has specific futures permissions.
- Check `BINANCE_TESTNET` value. If `true`, ensure you are using Testnet keys.

### "Frontend connection refused"
- Check if backend is running on port 8000.
- Verify `VITE_API_BASE` in frontend config matches backend URL.
