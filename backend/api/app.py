# backend/api/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from models.database import engine, Base, SessionLocal
from api.models import trades, trading_rules
from api.routes import positions, config, market, trading, system, rules
from api.routes import database_config

# ML Analytics (optional - graceful degradation if ML not available)
try:
    from api.routes import ml_analytics
    ML_ANALYTICS_AVAILABLE = True
except ImportError:
    ML_ANALYTICS_AVAILABLE = False
    logger.warning("⚠️ ML Analytics not available (dependencies not installed)")

# Advanced Strategies (optional)
try:
    from api.routes import strategies
    STRATEGIES_AVAILABLE = True
except ImportError:
    STRATEGIES_AVAILABLE = False
    logger.warning("⚠️ Advanced Strategies not available (dependencies not installed)")

from api import backtesting, websocket
from modules.config_database import Base as ConfigBase
from utils.logger import setup_logger
from config.settings import get_settings
from sqlalchemy import text
from pathlib import Path
import asyncio
import redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Setup logger
logger = setup_logger("api")

PUBLIC_PATHS = {
    "/",
    "/health",
    "/version",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        settings = get_settings()
        if not getattr(settings, "API_AUTH_ENABLED", False):
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
            return await call_next(request)

        header_name = getattr(settings, "API_KEY_HEADER", "X-API-Key")
        api_key = request.headers.get(header_name)
        if not api_key or api_key != getattr(settings, "API_KEY", ""):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: criar tabelas
    logger.info("Criando tabelas do banco de dados...")
    try:
        Base.metadata.create_all(bind=engine)
        # ✅ Criar tabelas do database de configurações
        ConfigBase.metadata.create_all(bind=engine)
        logger.info("✅ Tabelas criadas com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
    
    # Iniciar sincronização automática de posições (se habilitada)
    try:
        settings = get_settings()
        if getattr(settings, "POSITIONS_AUTO_SYNC_ENABLED", False):
            interval_s = max(60, int(getattr(settings, "POSITIONS_AUTO_SYNC_MINUTES", 10)) * 60)

            async def _auto_sync_loop():
                from api.routes.positions import reconcile_positions
                while True:
                    try:
                        strict_default = bool(getattr(settings, "POSITIONS_AUTO_SYNC_STRICT", False))
                        db = SessionLocal()
                        try:
                            await reconcile_positions(db, strict=strict_default)
                        finally:
                            db.close()
                    except Exception as e:
                        logger.error(f"Auto-sync error: {e}")
                    await asyncio.sleep(interval_s)

            app.state.auto_sync_task = asyncio.create_task(_auto_sync_loop())
            logger.info(f"🟢 Auto-sync de posições iniciado (intervalo={interval_s}s)")
    except Exception as e:
        logger.error(f"Falha ao iniciar auto-sync: {e}")



    # ✅ Inicializar Binance Client Streams (Independente do Bot)
    try:
        from utils.binance_client import binance_client
        # Garantir One-Way Mode
        await binance_client.ensure_position_mode(dual_side=False)
    except Exception as e:
        logger.error(f"Falha ao garantir Position Mode: {e}")

    try:
        from utils.binance_client import binance_client
        # Iniciar Market Stream (WebSocket de Preços)
        await binance_client.start_market_stream()
    except Exception as e:
        logger.error(f"Falha ao iniciar streams da Binance: {e}")

    # Auto-start do bot se habilitado nas settings
    try:
        settings = get_settings()
        if getattr(settings, "AUTOSTART_BOT", False):
            from modules.autonomous_bot import autonomous_bot

            try:
                autonomous_bot.min_score = int(getattr(settings, "BOT_MIN_SCORE", 0))
            except Exception:
                pass
            try:
                si = int(getattr(settings, "BOT_SCAN_INTERVAL_MINUTES", 1))
                autonomous_bot.scan_interval = max(10, si * 60)
            except Exception:
                pass
            try:
                # Forçando max_positions para 15 para depuração
                max_positions = int(getattr(settings, "BOT_MAX_POSITIONS", getattr(settings, "MAX_POSITIONS", 15)))
                autonomous_bot.max_positions = max_positions
                if hasattr(autonomous_bot, "base_max_positions"):
                    autonomous_bot.base_max_positions = max_positions
            except Exception:
                pass

            try:
                await autonomous_bot.start(dry_run=bool(getattr(settings, "BOT_DRY_RUN", False)))
                logger.info("🟢 Autostart BOT: iniciado")
            except Exception as e:
                logger.error(f"Falha ao iniciar BOT no autostart: {e}")
    except Exception as e:
        logger.error(f"Falha ao configurar autostart: {e}")

    # Watchdog do BOT: mantém o bot rodando quando habilitado (supervisor flag + settings)
    try:
        settings = get_settings()
        if getattr(settings, "AUTOSTART_BOT", False):
            supervisor_flag = Path("/logs/supervisor_enabled.flag")

            async def _bot_watchdog_loop():
                last_restart_ts = 0.0
                while True:
                    try:
                        # Supervisor pode desabilitar temporariamente
                        enabled = True
                        try:
                            if supervisor_flag.exists():
                                val = supervisor_flag.read_text(encoding="utf-8").strip()
                                enabled = val != "0"
                        except Exception:
                            enabled = True

                        if enabled:
                            from modules.autonomous_bot import autonomous_bot
                            if not autonomous_bot.running:
                                now = asyncio.get_event_loop().time()
                                # evitar reinícios muito frequentes
                                if now - last_restart_ts > 15.0:
                                    logger.info("🟢 Watchdog: bot não está rodando — iniciando...")
                                    try:
                                        await autonomous_bot.start(dry_run=bool(getattr(settings, "BOT_DRY_RUN", False)))
                                        last_restart_ts = now
                                    except Exception as e:
                                        logger.error(f"Watchdog: falha ao iniciar bot: {e}")
                        # checar a cada 10s
                        await asyncio.sleep(10)
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Watchdog loop erro: {e}")
                        await asyncio.sleep(10)

            app.state.bot_watchdog_task = asyncio.create_task(_bot_watchdog_loop())
            logger.info("🟢 Bot Watchdog iniciado")
    except Exception as e:
        logger.error(f"Falha ao iniciar watchdog do bot: {e}")

    # ✅ Telegram Bot Command Handler (sempre roda, independente do bot de trading)
    try:
        from modules.telegram_bot import telegram_bot
        await telegram_bot.start()
        logger.info("🤖 Telegram Bot Command Handler iniciado!")
    except Exception as e:
        logger.error(f"Falha ao iniciar Telegram Bot: {e}")

    # WebSocket Redis Listener
    try:
        app.state.redis_listener_task = asyncio.create_task(websocket.redis_event_listener())
        logger.info("🟢 WebSocket Redis Event Listener iniciado")
    except Exception as e:
        logger.error(f"Falha ao iniciar Redis listener: {e}")

    yield
    
    # Shutdown
    try:
        task = getattr(app.state, "auto_sync_task", None)
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass
            logger.info("🟡 Auto-sync de posições cancelado")
    except Exception as e:
        logger.error(f"Falha ao desligar auto-sync: {e}")

    try:
        wtask = getattr(app.state, "bot_watchdog_task", None)
        if wtask:
            wtask.cancel()
            try:
                await wtask
            except Exception:
                pass
            logger.info("🟡 Bot Watchdog cancelado")
    except Exception as e:
        logger.error(f"Falha ao desligar watchdog: {e}")

    try:
        task = getattr(app.state, "redis_listener_task", None)
        if task:
            task.cancel()
            try:
                await task
            except Exception:
                pass
            logger.info("🟡 WebSocket Redis Listener cancelado")
    except Exception as e:
        logger.error(f"Falha ao desligar Redis listener: {e}")

    # ✅ Parar Telegram Bot
    try:
        from modules.telegram_bot import telegram_bot
        await telegram_bot.stop()
        logger.info("🤖 Telegram Bot parado")
    except Exception as e:
        logger.error(f"Falha ao parar Telegram Bot: {e}")

    logger.info("🔴 Encerrando aplicação...")


app = FastAPI(
    title="Crypto Trading Bot API",
    description="API para gestão do bot de trading autônomo com backtesting",
    version="1.1.0",  # ← ATUALIZAR versão
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiKeyMiddleware)


# ✅ Rotas existentes
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(config.router, prefix="/api/config", tags=["Config"])
app.include_router(market.router, prefix="/api/market", tags=["Market"])
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])

# ✅ NOVA: Rota de backtesting
app.include_router(backtesting.router, prefix="/api/backtest", tags=["Backtesting"])
# ✅ System: logs e status docker
app.include_router(system.router, prefix="/api/system", tags=["System"])
# ✅ Rules: Trading rules management (Phase 3)
app.include_router(rules.router, tags=["Rules"])

# ✅ NOVA: Database de Configurações
app.include_router(database_config.router, prefix="/api/database-config", tags=["Database Config"])

# 🧠 ML Analytics (Adaptive Intelligence Engine)
if ML_ANALYTICS_AVAILABLE:
    app.include_router(ml_analytics.router)
    logger.info("🧠 ML Analytics endpoints registered")

# 🎯 Advanced Trading Strategies
if STRATEGIES_AVAILABLE:
    app.include_router(strategies.router)
    logger.info("🎯 Advanced Trading Strategies endpoints registered")


@app.get("/", tags=["Health"])
async def root():
    """Endpoint raiz - Status da API"""
    return {
        "status": "online",
        "message": "Crypto Trading Bot API v1.1.0",
        "features": [
            "Trading Autônomo",
            "Backtesting",
            "Gestão de Risco",
            "Análise Técnica",
            "Notificações Telegram",
            "Real-Time WebSockets"
        ],
        "docs": "/docs"
    }


# ==========================================
# ✅ REAL-TIME WEBSOCKETS (Phase 3)
# ==========================================

# ✅ REAL-TIME WEBSOCKETS (Phase 3)
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health():
    """Health check da API com validações de dependências (DB, Redis, Binance, Supervisor)"""
    settings = get_settings()

    # DB check
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")

    # Redis check
    redis_ok = False
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        redis_ok = bool(r.ping())
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Binance check (melhor esforço, não bloqueante)
    binance_ok = False
    try:
        from utils.binance_client import binance_client
        price = await binance_client.get_symbol_price("BTCUSDT")
        binance_ok = price is not None
    except Exception as e:
        logger.error(f"Binance health check failed: {e}")

    # Supervisor flag
    supervisor_flag = Path("/logs/supervisor_enabled.flag")
    supervisor_enabled = True
    try:
        if supervisor_flag.exists():
            val = supervisor_flag.read_text(encoding="utf-8").strip()
            supervisor_enabled = val != "0"
    except Exception:
        supervisor_enabled = True

    overall = "healthy" if (db_ok and redis_ok) else ("degraded" if (db_ok or redis_ok) else "unhealthy")

    return {
        "status": overall,
        "version": "1.1.0",
        "modules": {
            "positions": "✅ active",
            "trading": "✅ active",
            "backtesting": "✅ active",
            "market": "✅ active"
        },
        "checks": {
            "db": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
            "binance": "ok" if binance_ok else "fail",
            "supervisor_enabled": supervisor_enabled
        }
    }


@app.get("/version", tags=["Health"])
async def version():
    """Informações de versão"""
    return {
        "version": "1.1.0",
        "release_date": "2025-10-22",
        "changelog": [
            "✅ Sistema de backtesting completo",
            "✅ Trailing stop automático",
            "✅ Pyramiding dinâmico",
            "✅ Notificações Telegram avançadas",
            "✅ Gestão de risco aprimorada"
        ]
    }


logger.info("🚀 API iniciada com sucesso - v1.1.0")
logger.info("📊 Backtesting module: LOADED")
logger.info("🔗 Documentação disponível em: http://localhost:8000/docs")
