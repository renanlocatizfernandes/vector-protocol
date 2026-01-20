#!/usr/bin/env python3
"""
Monitoramento Contínuo Inteligente - Acompanha eventos críticos com eficiência de tokens
"""
import subprocess
import time
import json
from datetime import datetime
from collections import deque

# ========================
# CONFIGURAÇÃO
# ========================
CHECK_INTERVAL = 30  # segundos entre checks
HISTORICAL_EVENTS = deque(maxlen=100)  # Últimos 100 eventos
LAST_POSITIONS_COUNT = 0
CONSECUTIVE_ERRORS = 0
MAX_CONSECUTIVE_ERRORS = 3

def get_system_status():
    """Captura status atual do sistema"""
    try:
        # Posições abertas
        result = subprocess.run(
            ['docker', 'exec', 'trading-bot-db', 'psql', '-U', 'trading_bot',
             '-d', 'trading_bot_db', '-c',
             "SELECT COUNT(*) as count FROM trades WHERE status='open';"],
            capture_output=True,
            text=True,
            timeout=10
        )

        open_positions = 0
        for line in result.stdout.split('\n'):
            if line.strip().isdigit():
                open_positions = int(line.strip())
                break

        return {
            'timestamp': datetime.now().isoformat(),
            'open_positions': open_positions,
            'healthy': True
        }
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'open_positions': -1,
            'error': str(e),
            'healthy': False
        }

def get_recent_logs(minutes=5):
    """Extrai apenas logs CRÍTICOS dos últimos N minutos"""
    try:
        result = subprocess.run(
            ['docker', 'logs', '--tail', '200', 'trading-bot-api'],
            capture_output=True,
            text=True,
            timeout=10
        )

        critical_events = []
        for line in result.stdout.split('\n'):
            # Filtrar apenas eventos importantes
            if any(x in line for x in ['✅', '❌', '⚠️', 'ERROR', 'Exception',
                                       'Position', 'Trade', 'Order', 'FAIL']):
                try:
                    data = json.loads(line)
                    msg = data.get('message', '')
                    level = data.get('level', '')

                    event = {
                        'time': data.get('timestamp', ''),
                        'level': level,
                        'message': msg[:100],  # Truncar para economizar tokens
                        'critical': level in ['ERROR', 'CRITICAL'] or '❌' in msg
                    }

                    if event['critical'] or '✅' in msg:
                        critical_events.append(event)
                except:
                    pass

        return critical_events
    except Exception as e:
        return [{'error': str(e)}]

def print_status_report(status, events):
    """Imprime relatório RESUME (sem repetição)"""
    global LAST_POSITIONS_COUNT, CONSECUTIVE_ERRORS

    timestamp = datetime.now().strftime('%H:%M:%S')

    # Mudança no número de posições = importante
    if status['open_positions'] != LAST_POSITIONS_COUNT:
        if status['open_positions'] > LAST_POSITIONS_COUNT:
            print(f"\n✨ [{timestamp}] NOVA POSIÇÃO ABERTA - Total: {status['open_positions']}")
        else:
            print(f"\n✅ [{timestamp}] POSIÇÃO FECHADA - Total: {status['open_positions']}")
        LAST_POSITIONS_COUNT = status['open_positions']

    # Erros críticos
    critical_events = [e for e in events if e.get('critical')]
    if critical_events:
        CONSECUTIVE_ERRORS += 1
        print(f"\n🔴 ALERTA [{timestamp}] - {len(critical_events)} erro(s) detectado(s):")
        for event in critical_events[-3:]:  # Últimos 3 erros
            print(f"   └─ {event.get('message', 'Erro desconhecido')}")
    else:
        CONSECUTIVE_ERRORS = 0

    # Health check
    if not status['healthy']:
        print(f"\n⚠️  [{timestamp}] Problema ao conectar com sistema")

    # Sucesso registrado
    success_events = [e for e in events if '✅' in e.get('message', '')]
    if success_events:
        print(f"\n🟢 [{timestamp}] {len(success_events)} ação(ões) bem-sucedida(s)")

def main():
    """Loop de monitoramento contínuo"""
    print("=" * 70)
    print("🚀 MONITORAMENTO CONTÍNUO INICIADO")
    print(f"   Check a cada {CHECK_INTERVAL} segundos")
    print("   Capturando apenas eventos CRÍTICOS")
    print("=" * 70)

    iteration = 0

    try:
        while True:
            iteration += 1

            # Status do sistema
            status = get_system_status()

            # Logs críticos
            events = get_recent_logs()

            # Mostrar apenas se houver mudanças
            if iteration == 1:  # Sempre mostrar no início
                print(f"\n✅ Sistema iniciado - {status['open_positions']} posição(ões) aberta(s)")
            elif status['open_positions'] != LAST_POSITIONS_COUNT or events:
                print_status_report(status, events)

            # Intervalo entre checks
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n🛑 Monitoramento parado")
        print(f"   Iterações: {iteration}")
        print(f"   Tempo total: {iteration * CHECK_INTERVAL // 60}min")

if __name__ == "__main__":
    main()
