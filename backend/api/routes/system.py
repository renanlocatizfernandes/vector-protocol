from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import subprocess
import os
import glob
import asyncio
import redis
import json
from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings

router = APIRouter()
logger = setup_logger("system_routes")

LOGS_DIR = Path("/logs")  # Em Docker, mapeado para ./logs na raiz do projeto
DEFAULT_TAIL = 300

# Supervisor integration
SUPERVISOR_FLAG = LOGS_DIR / "supervisor_enabled.flag"
INTERVENTIONS_LOG = LOGS_DIR / "supervisor_interventions.log"


def _latest_log_file(prefix: str) -> Optional[Path]:
    """
    Retorna o arquivo de log mais provÃ¡vel pelo prefixo do logger.
    Tenta o arquivo do dia (ex: api_YYYYMMDD.log), senÃ£o pega o mais recente por glob.
    """
    today = datetime.now().strftime("%Y%m%d")
    candidate = LOGS_DIR / f"{prefix}_{today}.log"
    if candidate.exists():
        return candidate

    matches = sorted(glob.glob(str(LOGS_DIR / f"{prefix}_*.log")))
    if matches:
        return Path(matches[-1])
    return None


def _tail_lines(path: Path, n: int) -> List[str]:
    """
    Tail simples por linhas. Para arquivos grandes isso Ã© O(N),
    mas para logs tÃ­picos do serviÃ§o Ã© suficiente.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return lines[-n:] if n > 0 else lines
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler log: {e}")


@router.get("/logs", summary="Tail de logs do serviÃ§o")
async def get_logs(component: str = Query(default="api", description="Prefixo do logger (ex: api, trading_routes, market_routes)"),
                   tail: int = Query(default=DEFAULT_TAIL, ge=1, le=5000)):
    """
    Retorna as Ãºltimas N linhas do arquivo de log com o prefixo informado.
    Em Docker, os logs ficam em /logs e sÃ£o montados para ./logs no host.
    """
    if not LOGS_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Pasta de logs nÃ£o encontrada: {LOGS_DIR}")

    log_file = _latest_log_file(component)
    if not log_file or not log_file.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo de log nÃ£o encontrado para '{component}'")

    lines = _tail_lines(log_file, tail)
    return {
        "component": component,
        "file": str(log_file),
        "count": len(lines),
        "lines": [ln.rstrip("\n") for ln in lines]
    }


@router.get("/compose", summary="Status do Docker Compose (melhor esforco)")
async def compose_status():
    """
    Retorna o resultado de `docker ps` formatado (se disponivel).
    Em containers sem acesso ao Docker (sem /var/run/docker.sock), retorna 501.
    """
    if not Path("/var/run/docker.sock").exists():
        raise HTTPException(status_code=501, detail="Docker socket nao disponivel no container")

    # Verifica se 'docker' esta disponivel no PATH
    docker_bin = None
    for candidate in ("docker", "/usr/bin/docker", "/usr/local/bin/docker"):
        if os.path.exists(candidate):
            docker_bin = candidate
            break

    if docker_bin is None:
        raise HTTPException(status_code=501, detail="Docker nao disponivel no ambiente da API")

    try:
        # Usa --format para JSON-like por linha; parse simples por tabs se simplificar
        cmd = [docker_bin, "ps", "--format", "{{.Names}}|||{{.Status}}|||{{.Ports}}"]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if cp.returncode != 0:
            raise HTTPException(status_code=500, detail=cp.stderr.strip() or "Falha ao executar docker ps")

        lines = [ln for ln in (cp.stdout or "").splitlines() if ln.strip()]
        items = []
        for ln in lines:
            parts = ln.split("|||")
            if len(parts) >= 3:
                items.append({"name": parts[0], "status": parts[1], "ports": parts[2]})
            else:
                items.append({"raw": ln})

        return {"ok": True, "items": items, "count": len(items)}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout ao executar docker ps")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supervisor/status", summary="Status do Supervisor (flag + Ãºltimas intervenÃ§Ãµes)")
async def supervisor_status(tail: int = Query(default=50, ge=1, le=2000)):
    enabled = True
    try:
        if SUPERVISOR_FLAG.exists():
            val = SUPERVISOR_FLAG.read_text(encoding="utf-8").strip()
            enabled = val != "0"
    except Exception:
        enabled = True

    lines = []
    last_action_at = None
    try:
        if INTERVENTIONS_LOG.exists():
            lines = _tail_lines(INTERVENTIONS_LOG, tail)
            last_action_at = datetime.fromtimestamp(INTERVENTIONS_LOG.stat().st_mtime).isoformat()
    except Exception:
        pass

    return {
        "enabled": enabled,
        "interventions_tail": [ln.rstrip("\n") for ln in lines],
        "last_intervention_at": last_action_at,
        "flag_path": str(SUPERVISOR_FLAG),
        "log_path": str(INTERVENTIONS_LOG)
    }


@router.get("/supervisor/health", summary="RelatÃ³rio de saÃºde do Supervisor")
async def supervisor_health():
    """Retorna status detalhado do Supervisor (heartbeats, recursos, restarts)"""
    from modules.supervisor import supervisor
    return supervisor.get_status()


@router.post("/supervisor/enable", summary="Habilita o Supervisor (flag=1)")
async def supervisor_enable():
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        SUPERVISOR_FLAG.write_text("1", encoding="utf-8")
        return {"ok": True, "enabled": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supervisor/disable", summary="Desabilita o Supervisor (flag=0)")
async def supervisor_disable():
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        SUPERVISOR_FLAG.write_text("0", encoding="utf-8")
        return {"ok": True, "enabled": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/supervisor/toggle", summary="Alterna Supervisor (0/1)")
async def supervisor_toggle():
    try:
        current = "1"
        if SUPERVISOR_FLAG.exists():
            val = SUPERVISOR_FLAG.read_text(encoding="utf-8").strip()
            current = val
        new_val = "0" if current != "0" else "1"
        SUPERVISOR_FLAG.write_text(new_val, encoding="utf-8")
        return {"ok": True, "enabled": new_val != "0"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== USER DATA STREAM (Futures) ==========
@router.get("/userstream/status", summary="Status do Binance User Data Stream")
async def userstream_status():
    try:
        status = await binance_client.get_user_stream_status()
        return {"ok": True, **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/userstream/start", summary="Inicia User Data Stream (listenKey + WS)")
async def userstream_start():
    """
    Dispara o start em background para evitar bloquear o request.
    Retorna imediatamente com o status atual/previsto.
    """
    try:
        # Se jÃ¡ estiver rodando, apenas reporta
        current = await binance_client.get_user_stream_status()
        if bool(current.get("running")):
            return {"ok": True, **current}

        # Iniciar de forma sÃ­ncrona (rÃ¡pida) e retornar status atualizado
        status = await binance_client.start_user_stream()
        return {"ok": True, **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/userstream/stop", summary="Para User Data Stream")
async def userstream_stop():
    try:
        status = await binance_client.stop_user_stream()
        return {"ok": True, **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# HEALTH MONITORING - Phase 4
# ========================================

@router.get("/errors/recent", summary="Get recent errors from error aggregator")
async def get_recent_errors(
    limit: int = Query(50, ge=1, le=500, description="Maximum errors to return"),
    component: Optional[str] = Query(None, description="Filter by component"),
    level: Optional[str] = Query(None, description="Filter by log level (ERROR, CRITICAL)")
):
    """
    Returns recent errors tracked by error aggregator.

    Errors are stored in Redis sorted set for fast retrieval.
    """
    from modules.error_aggregator import error_aggregator

    try:
        errors = await error_aggregator.get_recent_errors(
            limit=limit,
            component=component,
            level=level
        )
        return {
            "errors": errors,
            "count": len(errors),
            "limit": limit,
            "filters": {"component": component, "level": level}
        }
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors/rate", summary="Get error rate statistics")
async def get_error_rate(
    component: Optional[str] = Query(None, description="Filter by component"),
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze")
):
    """
    Returns error rate statistics per hour.

    Useful for identifying error spikes and trends.
    """
    from modules.error_aggregator import error_aggregator

    try:
        rate_data = await error_aggregator.get_error_rate(
            component=component,
            hours=hours
        )
        return rate_data
    except Exception as e:
        logger.error(f"Error getting error rate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors/summary", summary="Get error summary statistics")
async def get_error_summary():
    """
    Returns error summary grouped by component and level.
    """
    from modules.error_aggregator import error_aggregator

    try:
        summary = await error_aggregator.get_error_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latency", summary="Get bot cycle latency statistics")
async def get_latency_stats():
    """
    Returns latency statistics from last bot cycle.

    Includes:
    - scan: Market scanning time
    - signal: Signal generation time
    - execution: Order execution time
    - total: Total cycle time
    """
    try:
        settings = get_settings()
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )

        # Get last cycle latency
        last_cycle_json = redis_client.get("latency:last_cycle")
        if last_cycle_json:
            last_cycle = json.loads(last_cycle_json)
        else:
            last_cycle = {}

        # Determine SLA status (warning if total > 5 seconds)
        total_latency = last_cycle.get('total', 0)
        sla_status = "ok" if total_latency < 5.0 else "warning" if total_latency < 10.0 else "critical"

        return {
            "last_cycle": last_cycle,
            "sla_status": sla_status,
            "sla_threshold": 5.0,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting latency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/conditions", summary="Get market conditions monitoring")
async def get_market_conditions():
    """
    Returns current market conditions including:
    - High funding rate symbols
    - Trending symbols (strong price movement)
    - Market volatility index (0-100)
    """
    from modules.market_monitor import market_monitor

    try:
        conditions = await market_monitor.get_market_conditions()
        return conditions
    except Exception as e:
        logger.error(f"Error getting market conditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", summary="Get metrics dashboard")
async def get_metrics_dashboard():
    """
    Returns comprehensive metrics dashboard with real-time statistics.

    Includes:
    - Execution stats (orders, latency, success rate)
    - Signal stats (received, processed, rejection rate)
    - Trade stats (win rate, PnL)
    - Resource usage (CPU, memory, uptime)
    - Connection status (Binance API, Redis)
    """
    from modules.metrics_dashboard import metrics_dashboard

    try:
        dashboard = metrics_dashboard.get_full_dashboard()
        return dashboard
    except Exception as e:
        logger.error(f"Error getting metrics dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/latency", summary="Get latency statistics")
async def get_latency_dashboard():
    """
    Returns detailed latency statistics.
    """
    from modules.metrics_dashboard import metrics_dashboard

    try:
        stats = metrics_dashboard.get_latency_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting latency stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/trades", summary="Get trade statistics")
async def get_trade_dashboard():
    """
    Returns detailed trade statistics.
    """
    from modules.metrics_dashboard import metrics_dashboard

    try:
        stats = metrics_dashboard.get_trade_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting trade stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/resources", summary="Get resource usage statistics")
async def get_resource_dashboard():
    """
    Returns detailed resource usage statistics.
    """
    from modules.metrics_dashboard import metrics_dashboard

    try:
        stats = metrics_dashboard.get_resource_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting resource stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
