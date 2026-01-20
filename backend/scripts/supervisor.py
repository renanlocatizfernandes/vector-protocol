#!/usr/bin/env python3
"""
Supervisor do Crypto Trading Bot

Responsabilidades:
- Garantir e "ativar" a venv backend/.venv (criar se necessário e instalar dependências)
- Orquestrar Docker (compose build/up/restart/down, status, logs)
- Validar saúde da API (GET /health)
- Vigiar logs do container e tentar corrigir problemas comuns automaticamente
- Registrar toda intervenção em supervisor_interventions.log

Uso rápido:
  python3 supervisor.py ensure-venv
  python3 supervisor.py build
  python3 supervisor.py up
  python3 supervisor.py restart
  python3 supervisor.py down
  python3 supervisor.py status
  python3 supervisor.py logs --name trading-bot-api --tail 200
  python3 supervisor.py health
  python3 supervisor.py watch --interval 60

Observações:
- "Ativar venv" no contexto deste supervisor significa garantir sua existência e usar
  seus binários (python/pip) para tarefas necessárias; não é possível alterar a sessão
  interativa do shell chamador via subprocess.
- O supervisor registra todas as intervenções em 'supervisor_interventions.log'.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from urllib import request as urlrequest, error as urlerror

# Constantes de paths
ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
VENV_PIP = VENV_DIR / "bin" / "pip"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
COMPOSE_FILE = ROOT / "docker-compose.yml"

LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
INTERVENTIONS_LOG = LOGS_DIR / "supervisor_interventions.log"
SUPERVISOR_FLAG = LOGS_DIR / "supervisor_enabled.flag"

# Containers
API_CONTAINER = "trading-bot-api"
DB_CONTAINER = "trading-bot-db"
REDIS_CONTAINER = "trading-bot-redis"
API_SERVICE = "api"

# Endpoints base
API_TRADING_BASE = "http://127.0.0.1:8000/api/trading"


def log_intervention(message: str, details: Optional[str] = None) -> None:
    """Registra intervenção com timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {message}"
    if details:
        entry += f"\n{details}"
    entry += "\n" + ("-" * 80) + "\n"
    INTERVENTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(INTERVENTIONS_LOG, "a", encoding="utf-8") as f:
        f.write(entry)
    print(entry, end="")


@dataclass
class CmdResult:
    code: int
    out: str
    err: str


def is_supervisor_enabled() -> bool:
    """Lê flag em logs/supervisor_enabled.flag. Ausente ou != '0' => habilitado."""
    try:
        if SUPERVISOR_FLAG.exists():
            val = SUPERVISOR_FLAG.read_text(encoding="utf-8").strip()
            return val != "0"
        return True
    except Exception:
        return True

def run(cmd: str | List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> CmdResult:
    """Executa comando shell e captura stdout/stderr."""
    if isinstance(cmd, list):
        cmd_list = cmd
        cmd_display = " ".join(shlex.quote(x) for x in cmd_list)
    else:
        cmd_list = cmd
        cmd_display = cmd

    print(f"$ {cmd_display}")
    try:
        cp = subprocess.run(
            cmd_list,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=isinstance(cmd_list, str),
        )
        out = cp.stdout or ""
        err = cp.stderr or ""
        if out:
            print(out, end="" if out.endswith("\n") else "\n")
        if err:
            print(err, file=sys.stderr, end="" if err.endswith("\n") else "\n")
        return CmdResult(cp.returncode, out, err)
    except subprocess.TimeoutExpired as e:
        msg = f"Timeout executando: {cmd_display}"
        log_intervention("Timeout de comando", msg)
        return CmdResult(124, e.stdout or "", e.stderr or "")
    except Exception as e:
        log_intervention("Falha ao executar comando", f"cmd={cmd_display}\nerr={e}")
        return CmdResult(1, "", str(e))


def ensure_venv() -> None:
    """Garante que a venv exista e tenha dependências instaladas."""
    created = False
    if not VENV_DIR.exists():
        log_intervention("Venv não encontrada. Criando...", f"path={VENV_DIR}")
        # Tenta criar com o python atual
        r = run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if r.code != 0:
            raise SystemExit("Falha ao criar venv")
        created = True

    # Instalar/atualizar dependências se requirements existir
    if REQUIREMENTS.exists():
        log_intervention("Instalando/atualizando dependências do backend na venv", f"requirements={REQUIREMENTS}")
        r = run([str(VENV_PIP), "install", "--upgrade", "pip"])
        if r.code != 0:
            raise SystemExit("Falha ao atualizar pip na venv")
        r = run([str(VENV_PIP), "install", "-r", str(REQUIREMENTS)])
        if r.code != 0:
            raise SystemExit("Falha ao instalar requirements")
    else:
        log_intervention("Arquivo requirements.txt não encontrado. Pulando instalação.", f"esperado em {REQUIREMENTS}")

    # Checagem de versões
    r = run([str(VENV_PYTHON), "-V"])
    r2 = run([str(VENV_PIP), "-V"])
    if created:
        log_intervention("Venv criada com sucesso", f"python={r.out.strip()} pip={r2.out.strip()}")


def docker_compose(args: List[str]) -> CmdResult:
    """Wrapper para docker compose -f docker-compose.yml ..."""
    if not COMPOSE_FILE.exists():
        raise SystemExit(f"docker-compose.yml não encontrado em {COMPOSE_FILE}")
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)] + args
    return run(cmd, cwd=ROOT)


def compose_build() -> None:
    log_intervention("Executando docker compose build")
    r = docker_compose(["build"])
    if r.code != 0:
        raise SystemExit("Falha no docker compose build")


def compose_up_detached() -> None:
    log_intervention("Executando docker compose up -d")
    r = docker_compose(["up", "-d"])
    if r.code != 0:
        raise SystemExit("Falha no docker compose up -d")


def compose_restart(service: Optional[str] = None) -> None:
    if service:
        log_intervention(f"Executando docker compose restart {service}")
        r = docker_compose(["restart", service])
    else:
        log_intervention("Executando docker compose restart (todos serviços)")
        r = docker_compose(["restart"])
    if r.code != 0:
        raise SystemExit("Falha no docker compose restart")


def compose_down() -> None:
    log_intervention("Executando docker compose down")
    r = docker_compose(["down"])
    if r.code != 0:
        raise SystemExit("Falha no docker compose down")


def docker_ps() -> None:
    run(["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"])


def docker_logs(name: str, tail: int = 200) -> str:
    r = run(["docker", "logs", "--tail", str(tail), name])
    return r.out


def api_health(timeout_s: int = 5) -> Tuple[int, str]:
    """Consulta GET /health na API local via host."""
    url = "http://127.0.0.1:8000/health"
    r = run(f'curl -sS --max-time {timeout_s} -o /tmp/sup_resp.json -w "%{{http_code}}" "{url}" && echo && cat /tmp/sup_resp.json')
    # O out contem "HTTP_CODE\n{json...}" por causa do echo && cat
    # Vamos separar o primeiro número de 3 dígitos que aparece
    m = re.search(r"\b(\d{3})\b", r.out.splitlines()[0] if r.out else "")
    code = int(m.group(1)) if m else 0
    body = "\n".join(r.out.splitlines()[1:]) if r.out else ""
    return code, body


def http_request(method: str, url: str, data: Optional[Dict] = None, timeout: int = 8) -> Tuple[int, Optional[Dict], str]:
    """HTTP helper usando urllib (sem dependências extras). Retorna (status, json|None, raw_text)."""
    try:
        req = urlrequest.Request(url)
        req.method = method.upper()
        if data is not None:
            payload = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        else:
            payload = None
        with urlrequest.urlopen(req, data=payload, timeout=timeout) as resp:
            status = resp.status
            body_bytes = resp.read()
            body_text = body_bytes.decode("utf-8") if body_bytes else ""
            try:
                body_json = json.loads(body_text) if body_text else None
            except json.JSONDecodeError:
                body_json = None
            return status, body_json, body_text
    except urlerror.HTTPError as e:
        text = e.read().decode("utf-8") if e.fp else ""
        return e.code, None, text
    except Exception as e:
        return 0, None, str(e)


def bot_start(dry_run: bool = True) -> bool:
    """Inicia o bot autônomo via API."""
    url = f"{API_TRADING_BASE}/bot/start?dry_run={'true' if dry_run else 'false'}"
    code, body, raw = http_request("POST", url)
    ok = 200 <= code < 300 and (body or {}).get("status") == "running"
    log_intervention("Comando bot.start", f"http_code={code}\nbody={body or raw}\ndry_run={dry_run}")
    return ok


def bot_stop() -> bool:
    """Para o bot autônomo via API."""
    url = f"{API_TRADING_BASE}/bot/stop"
    code, body, raw = http_request("POST", url)
    ok = 200 <= code < 300 and (body or {}).get("status") == "stopped"
    log_intervention("Comando bot.stop", f"http_code={code}\nbody={body or raw}")
    return ok


def bot_status() -> Dict:
    """Obtém status do bot autônomo via API."""
    url = f"{API_TRADING_BASE}/bot/status"
    code, body, raw = http_request("GET", url)
    log_intervention("Consulta bot.status", f"http_code={code}\nbody={body or raw}")
    return body or {}


def get_daily_trades_count() -> Optional[int]:
    """Retorna trades_count do endpoint de estatísticas diárias."""
    url = f"{API_TRADING_BASE}/stats/daily"
    code, body, raw = http_request("GET", url)
    if 200 <= code < 300 and isinstance(body, dict):
        try:
            return int(body.get("trades_count", 0))
        except Exception:
            return 0
    return None


def get_open_positions_count() -> Optional[int]:
    """Retorna quantidade de posições abertas."""
    url = f"{API_TRADING_BASE}/positions"
    code, body, raw = http_request("GET", url)
    if 200 <= code < 300 and isinstance(body, dict):
        try:
            return int(body.get("count", 0))
        except Exception:
            return 0
    return None


Issue = Tuple[str, str]  # (issue_code, details)


def parse_issues_from_logs(text: str) -> List[Issue]:
    """Analisa logs e retorna lista de issues detectadas."""
    issues: List[Issue] = []

    # Autenticação no Postgres
    if "password authentication failed for user" in text:
        issues.append(("DB_AUTH", "Falha de autenticação no Postgres"))

    # Porta em uso
    if "address already in use" in text:
        issues.append(("PORT_IN_USE", "Porta já está em uso"))

    # ModuleNotFoundError
    if "ModuleNotFoundError" in text:
        issues.append(("MISSING_MODULE", "Pacote ausente detectado"))

    # Erros de conexão externas ocasionais (não-fatais)
    if "RemoteDisconnected(" in text or "Connection aborted" in text:
        issues.append(("NETWORK_GLITCH", "Falha transitória de rede/serviço"))

    # Símbolo inválido na Binance (normalmente não fatal)
    if "APIError(code=-1121): Invalid symbol" in text:
        issues.append(("BINANCE_SYMBOL", "Símbolo inválido na exchange"))

    return issues


def try_auto_fix(issues: List[Issue]) -> bool:
    """Tenta corrigir problemas conhecidos. Retorna True se alguma ação foi tomada."""
    took_action = False

    for code, details in issues:
        if code == "DB_AUTH":
            # Em Docker, este erro normalmente ocorre apenas se subir localmente fora do compose,
            # ou se variáveis do .env.docker estiverem incorretas.
            msg = "Detectado DB_AUTH. Verificar .env.docker e reiniciar API."
            log_intervention("AUTO-FIX DB_AUTH", msg)
            # Estratégia: reiniciar somente a API (db está healthy)
            compose_restart(API_SERVICE)
            took_action = True

        elif code == "PORT_IN_USE":
            msg = "Detectado PORT_IN_USE. Reiniciar API para desalocar porta em uso."
            log_intervention("AUTO-FIX PORT_IN_USE", msg)
            compose_restart(API_SERVICE)
            took_action = True

        elif code == "MISSING_MODULE":
            # Reconstruir imagem para garantir deps instaladas
            msg = "Detectado MISSING_MODULE. Rebuild da imagem e restart."
            log_intervention("AUTO-FIX MISSING_MODULE", msg)
            compose_build()
            compose_up_detached()
            took_action = True

        elif code == "NETWORK_GLITCH":
            # Normalmente transitório. Apenas log e segue.
            msg = "Detectado NETWORK_GLITCH. Sinal transitório; monitorar."
            log_intervention("OBS NETWORK_GLITCH", msg)
            # sem ação

        elif code == "BINANCE_SYMBOL":
            # Normalmente não fatal. Apenas registrar.
            msg = "Detectado BINANCE_SYMBOL inválido. Verificar lista/normalização, não-fatal."
            log_intervention("OBS BINANCE_SYMBOL", msg)
            # sem ação

    return took_action


def ensure_stack_running() -> None:
    """Garante que o stack docker esteja ativo e saudável."""
    compose_up_detached()
    # Pequeno grace period
    time.sleep(2)
    docker_ps()
    # Tenta health
    code, body = api_health(timeout_s=8)
    if code != 200:
        log_intervention("Healthcheck inicial falhou", f"http_code={code}\nbody={body}")
        # Consulta logs da API para diagnosticar
        logs = docker_logs(API_CONTAINER, tail=300)
        issues = parse_issues_from_logs(logs)
        if try_auto_fix(issues):
            # Aguarda e revalida saúde
            time.sleep(2)
            code2, body2 = api_health(timeout_s=8)
            if code2 == 200:
                log_intervention("Healthcheck recuperado após auto-fix", f"http_code={code2}")
            else:
                log_intervention("Persistência de falha pós auto-fix", f"http_code={code2}\nbody={body2}")
        else:
            log_intervention("Sem auto-fix aplicável. Verificar logs manualmente.", logs)
    else:
        log_intervention("Healthcheck OK", f"http_code={code}\nbody={body}")


def watch_loop(interval: int, inactive_mins: int = 120, bot_dry_run: bool = True, start_bot: bool = False, ensure_running: bool = False) -> None:
    """Loop de observabilidade, correção e intervenção por inatividade."""
    log_intervention(
        "Iniciando watch loop do supervisor",
        f"intervalo={interval}s inatividade={inactive_mins}min dry_run={bot_dry_run} start_bot={start_bot} ensure_running={ensure_running}"
    )
    ensure_stack_running()
    if start_bot:
        log_intervention("Auto-start do bot solicitado")
        bot_start(dry_run=bot_dry_run)
    last_action_at: Optional[float] = None
    last_activity_at: float = time.time()
    last_trades_count: Optional[int] = None

    while True:
        if not is_supervisor_enabled():
            log_intervention("Supervisor desativado via flag - encerrando loop")
            break
        # Verificar saúde
        code, _ = api_health(timeout_s=5)
        if code != 200:
            log_intervention("Healthcheck falhou no watch", f"http_code={code}")
            logs = docker_logs(API_CONTAINER, tail=400)
            issues = parse_issues_from_logs(logs)
            if try_auto_fix(issues):
                last_action_at = time.time()
            else:
                log_intervention("Restart preventivo da API (nenhuma causa clara)")
                compose_restart(API_SERVICE)
                last_action_at = time.time()
        else:
            # Consultar status do bot e atividade
            status = bot_status() or {}
            running = bool(status.get("running", False))

            trades_count = get_daily_trades_count()
            positions_count = get_open_positions_count()

            details = f"running={running} trades_count={trades_count} positions_count={positions_count}"
            print(details)

            if ensure_running and not running:
                log_intervention("Bot parado - iniciando (ensure-running ativo)")
                ok = bot_start(dry_run=bot_dry_run)
                if ok:
                    log_intervention("Bot iniciado via ensure-running")

            # Atualizar indicador de atividade quando houver mudanças
            if (trades_count is not None and (last_trades_count is None or trades_count > (last_trades_count or 0))) or (positions_count or 0) > 0:
                last_activity_at = time.time()
                last_trades_count = trades_count if trades_count is not None else last_trades_count

            # Intervenção por inatividade prolongada (apenas se o bot estiver rodando)
            if running and (time.time() - last_activity_at) > (inactive_mins * 60):
                log_intervention(
                    "Inatividade prolongada detectada - intervindo",
                    f"sem operações por > {inactive_mins} min | {details}"
                )
                # Tentar reiniciar o bot via API
                ok_stop = bot_stop()
                time.sleep(1)
                ok_start = bot_start(dry_run=bot_dry_run)
                last_action_at = time.time()
                last_activity_at = time.time()
                log_intervention(
                    "Intervenção aplicada (restart bot)",
                    f"stop_ok={ok_stop} start_ok={ok_start} dry_run={bot_dry_run}"
                )
                # Último recurso: restart do serviço da API
                if not ok_start:
                    compose_restart(API_SERVICE)
                    log_intervention("Reiniciado serviço da API após falha em restart do bot")

            # Escanear logs para problemas fatais mesmo com health OK
            logs = docker_logs(API_CONTAINER, tail=200)
            issues = parse_issues_from_logs(logs)
            if any(c for c, _ in issues if c in {"DB_AUTH", "PORT_IN_USE", "MISSING_MODULE"}):
                if try_auto_fix(issues):
                    last_action_at = time.time()

        # Evitar flapping
        sleep_for = interval
        if last_action_at and (time.time() - last_action_at) < interval:
            sleep_for = max(interval, 15)
        time.sleep(sleep_for)


def main() -> None:
    parser = argparse.ArgumentParser(description="Supervisor do Crypto Trading Bot")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("ensure-venv", help="Garante venv criada e dependências instaladas")
    sub.add_parser("build", help="docker compose build")
    sub.add_parser("up", help="docker compose up -d e healthcheck")
    sub.add_parser("restart", help="docker compose restart (todos serviços)")
    p_restart_one = sub.add_parser("restart-api", help="docker compose restart somente API")
    p_restart_one.add_argument("--service", default="api", help="Nome do serviço (default: api)")

    sub.add_parser("down", help="docker compose down")
    sub.add_parser("status", help="docker ps (resumo)")
    p_logs = sub.add_parser("logs", help="docker logs --tail N SERVICE")
    p_logs.add_argument("--name", default=API_CONTAINER, help="Nome do container")
    p_logs.add_argument("--tail", default=200, type=int, help="Qtd de linhas (tail)")
    sub.add_parser("health", help="Testa GET /health")
    p_watch = sub.add_parser("watch", help="Observa e intervém (health + inatividade)")
    p_watch.add_argument("--interval", type=int, default=60, help="Intervalo de checagem em segundos")
    p_watch.add_argument("--inactive-mins", type=int, default=120, help="Minutos sem operações para intervir (restart bot)")
    p_watch.add_argument("--bot-dry-run", action="store_true", help="Iniciar bot em dry-run durante intervenções")
    p_watch.add_argument("--start-bot", action="store_true", help="Iniciar o bot automaticamente ao iniciar o supervisor")
    p_watch.add_argument("--ensure-running", action="store_true", help="Garantir que o bot permaneça em execução (reinicia se parar)")

    # Comandos de controle do bot
    p_bot_start = sub.add_parser("bot-start", help="Inicia o bot autônomo via API")
    p_bot_start.add_argument("--dry-run", choices=["true", "false"], default="true", help="Iniciar em modo dry-run (default: true)")
    sub.add_parser("bot-stop", help="Para o bot autônomo via API")
    sub.add_parser("bot-status", help="Consulta status do bot autônomo via API")

    args = parser.parse_args()

    # Registro de criação/uso do supervisor
    if not INTERVENTIONS_LOG.exists():
        log_intervention("Inicialização do Supervisor", "Arquivo de intervenções criado.")

    if args.cmd == "ensure-venv":
        ensure_venv()
        log_intervention("Venv verificada com sucesso")

    elif args.cmd == "build":
        compose_build()
        log_intervention("Build concluído")

    elif args.cmd == "up":
        ensure_venv()  # opcional: garantir deps locais também
        ensure_stack_running()

    elif args.cmd == "restart":
        compose_restart()
        log_intervention("Restart concluído (todos serviços)")

    elif args.cmd == "restart-api":
        service = getattr(args, "service", API_CONTAINER)
        compose_restart(service)
        log_intervention("Restart concluído do serviço", f"service={service}")

    elif args.cmd == "bot-start":
        ensure_stack_running()
        dry = getattr(args, "dry_run", "true") == "true"
        ok = bot_start(dry_run=dry)
        log_intervention("bot-start concluído", f"ok={ok} dry_run={dry}")

    elif args.cmd == "bot-stop":
        ok = bot_stop()
        log_intervention("bot-stop concluído", f"ok={ok}")

    elif args.cmd == "bot-status":
        st = bot_status()
        print(st)

    elif args.cmd == "down":
        compose_down()
        log_intervention("Stack parado com sucesso")

    elif args.cmd == "status":
        docker_ps()

    elif args.cmd == "logs":
        name = args.name
        tail = args.tail
        out = docker_logs(name, tail=tail)
        print(out)

    elif args.cmd == "health":
        code, body = api_health(timeout_s=8)
        print(f"http_code={code}\nbody={body}")
        if code == 200:
            log_intervention("Health OK via comando manual", f"http_code={code}")
        else:
            log_intervention("Health falhou via comando manual", f"http_code={code}\n{body}")

    elif args.cmd == "watch":
        ensure_venv()
        watch_loop(
            args.interval,
            args.inactive_mins,
            getattr(args, "bot_dry_run", False),
            getattr(args, "start_bot", False),
            getattr(args, "ensure_running", False),
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
