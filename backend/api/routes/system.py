from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import subprocess
import os
import glob
import asyncio
from utils.binance_client import binance_client

router = APIRouter()

LOGS_DIR = Path("/logs")  # Em Docker, mapeado para ./logs na raiz do projeto
DEFAULT_TAIL = 300

# Supervisor integration
SUPERVISOR_FLAG = LOGS_DIR / "supervisor_enabled.flag"
INTERVENTIONS_LOG = LOGS_DIR / "supervisor_interventions.log"


def _latest_log_file(prefix: str) -> Optional[Path]:
    """
    Retorna o arquivo de log mais provável pelo prefixo do logger.
    Tenta o arquivo do dia (ex: api_YYYYMMDD.log), senão pega o mais recente por glob.
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
    Tail simples por linhas. Para arquivos grandes isso é O(N),
    mas para logs típicos do serviço é suficiente.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return lines[-n:] if n > 0 else lines
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler log: {e}")


@router.get("/logs", summary="Tail de logs do serviço")
async def get_logs(component: str = Query(default="api", description="Prefixo do logger (ex: api, trading_routes, market_routes)"),
                   tail: int = Query(default=DEFAULT_TAIL, ge=1, le=5000)):
    """
    Retorna as últimas N linhas do arquivo de log com o prefixo informado.
    Em Docker, os logs ficam em /logs e são montados para ./logs no host.
    """
    if not LOGS_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Pasta de logs não encontrada: {LOGS_DIR}")

    log_file = _latest_log_file(component)
    if not log_file or not log_file.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo de log não encontrado para '{component}'")

    lines = _tail_lines(log_file, tail)
    return {
        "component": component,
        "file": str(log_file),
        "count": len(lines),
        "lines": [ln.rstrip("\n") for ln in lines]
    }


@router.get("/compose", summary="Status do Docker Compose (melhor esforço)")
async def compose_status():
    """
    Retorna o resultado de `docker ps` formatado (se disponível).
    Em containers sem acesso ao Docker (sem /var/run/docker.sock), retorna 501.
    """
    # Verifica se 'docker' está disponível no PATH
    docker_bin = None
    for candidate in ("docker", "/usr/bin/docker", "/usr/local/bin/docker"):
        if os.path.exists(candidate):
            docker_bin = candidate
            break

    if docker_bin is None:
        raise HTTPException(status_code=501, detail="Docker não disponível no ambiente da API")

    try:
        # Usa --format para JSON-like por linha; vamos fazer parse simples por tabs se simplificar
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

        return {
            "ok": True,
            "items": items,
            "count": len(items)
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout ao executar docker ps")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supervisor/status", summary="Status do Supervisor (flag + últimas intervenções)")
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


@router.get("/supervisor/health", summary="Relatório de saúde do Supervisor")
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
        # Se já estiver rodando, apenas reporta
        current = await binance_client.get_user_stream_status()
        if bool(current.get("running")):
            return {"ok": True, **current}

        # Iniciar de forma síncrona (rápida) e retornar status atualizado
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
