#!/bin/bash
# Monitor inteligente - Acompanha mudanças sem spam

STATE_FILE="/tmp/vector_state.txt"
INITIAL_COUNT=$(docker exec trading-bot-db psql -U trading_bot -d trading_bot_db -c "SELECT COUNT(*) FROM trades WHERE status='open';" 2>/dev/null | grep -oE '[0-9]+' | tail -1)
INITIAL_COUNT=${INITIAL_COUNT:-0}
echo "$INITIAL_COUNT" > $STATE_FILE

echo "🚀 MONITOR INTELIGENTE ATIVADO"
echo "   • Acompanhamento: Contínuo"
echo "   • Alertas: Apenas em mudanças"
echo "   • Check: A cada 2 minutos"
echo ""
echo "Posições iniciais: $INITIAL_COUNT"
echo ""

ITERATION=0
while true; do
    ITERATION=$((ITERATION + 1))

    # Leitura de estado
    CURRENT=$(docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
        -c "SELECT COUNT(*) FROM trades WHERE status='open';" 2>/dev/null | grep -oE '[0-9]+' | tail -1)
    CURRENT=${CURRENT:-0}

    LAST=$(cat $STATE_FILE)

    # Comparação
    if [ "$CURRENT" != "$LAST" ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════"
        if [ $CURRENT -gt $LAST ]; then
            echo "✨ NOVA POSIÇÃO ABERTA - $LAST → $CURRENT"
        else
            echo "✅ POSIÇÃO FECHADA - $LAST → $CURRENT"
        fi
        echo "   Timestamp: $(date '+%H:%M:%S')"

        # Mostrar detalhes da posição mais recente
        docker exec trading-bot-db psql -U trading_bot -d trading_bot_db \
            -c "SELECT symbol, direction, entry_price, pnl_percentage FROM trades ORDER BY opened_at DESC LIMIT 1;" 2>/dev/null | tail -1 | sed 's/^/   /'

        echo "═══════════════════════════════════════════════════════"
        echo $CURRENT > $STATE_FILE
    else
        # Status silencioso a cada 10 iterações (20 min)
        if [ $((ITERATION % 10)) -eq 0 ]; then
            echo "✅ [$((ITERATION*2))min] Sistema estável - $CURRENT posição(ões)"
        fi
    fi

    sleep 120  # 2 minutos entre checks
done
