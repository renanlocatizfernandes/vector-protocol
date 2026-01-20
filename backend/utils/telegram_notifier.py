import asyncio
import httpx
from datetime import datetime  # ← ADICIONAR
from typing import Optional, Dict, List
from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger("telegram_notifier")

class TelegramNotifier:
    def __init__(self):
        settings = get_settings()
        self.enabled = settings.TELEGRAM_ENABLED
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        
        if self.enabled and self.bot_token and self.chat_id:
            logger.info(f"Telegram Notifier inicializado (Chat ID: {self.chat_id})")
        else:
            self.enabled = False
            logger.warning("Telegram Notifier desabilitado (credenciais não configuradas)")
        # Cliente HTTP assíncrono
        try:
            self._client: Optional[httpx.AsyncClient] = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        except Exception:
            self._client = None
    
    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Envia mensagem formatada (assíncrono, com retries e backoff simples)"""
        if not self.enabled:
            return
        if not self._client:
            logger.warning("Telegram client não inicializado; mensagem não enviada")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }

        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                resp = await self._client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.debug("Mensagem enviada com sucesso")
                    return
                # Tratar rate limit (429) e erros 5xx com backoff
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait_s = min(5 * attempt, 10)
                    logger.warning(f"Telegram HTTP {resp.status_code}; retry em {wait_s}s")
                    await asyncio.sleep(wait_s)
                    continue
                # Outros erros: logar e sair
                text = (await resp.aread()).decode("utf-8", errors="ignore")
                logger.error(f"Erro ao enviar mensagem: {resp.status_code} - {text}")
                return
            except Exception as e:
                last_exc = e
                wait_s = min(5 * attempt, 10)
                logger.warning(f"Falha Telegram (tentativa {attempt}/3): {e} — retry em {wait_s}s")
                await asyncio.sleep(wait_s)

        if last_exc:
            logger.error(f"Erro ao enviar mensagem (excedeu retries): {last_exc}")
    
    async def send_alert(self, message: str):
        """Atalho semântico para alertas"""
        await self.send_message(message, parse_mode="HTML")

    # ==================================================================
    # MÉTODOS PADRONIZADOS DE NOTIFICAÇÃO
    # ==================================================================

    async def notify_startup(self, version: str = "v4.0", mode: str = "LIVE"):
        """Notifica inicialização do bot"""
        message = f"""
🚀 <b>BOT INICIADO</b>

🤖 <b>Versão:</b> {version}
🌍 <b>Modo:</b> {mode}
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

✅ Sistema online e monitorando o mercado.
"""
        await self.send_message(message)

    async def notify_shutdown(self, reason: str = "Manual"):
        """Notifica desligamento do bot"""
        message = f"""
🛑 <b>BOT PARADO</b>

📌 <b>Motivo:</b> {reason}
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

⚠️ O monitoramento foi interrompido.
"""
        await self.send_message(message)

    async def notify_error(self, context: str, error: str):
        """Notifica erro crítico"""
        message = f"""
❌ <b>ERRO CRÍTICO</b>

📂 <b>Contexto:</b> {context}
⚠️ <b>Erro:</b> {error}
⏰ <b>Hora:</b> {datetime.now().strftime('%H:%M:%S')}

🛠️ Verifique os logs imediatamente.
"""
        await self.send_message(message)

    async def notify_info(self, title: str, message: str):
        """Notifica informação genérica"""
        msg = f"""
ℹ️ <b>{title.upper()}</b>

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(msg)
    
    async def notify_trade_opened(self, trade_data: Dict):
        """Notifica abertura de trade"""
        symbol = trade_data['symbol']
        direction = trade_data['direction']
        entry_price = trade_data['entry_price']
        quantity = trade_data['quantity']
        leverage = trade_data['leverage']
        stop_loss = trade_data['stop_loss']
        take_profit = trade_data.get('take_profit_1', 0)
        tp_strategy = trade_data.get('tp_strategy', 'STATIC')

        entry_display = f"{entry_price:.6f}" if entry_price > 0 else "Market"
        emoji = "🟢" if direction == "LONG" else "🔴"
        strategy_emoji = "✨" if tp_strategy == "FIBONACCI" else "📊" if tp_strategy == "CONSERVATIVE" else "📍"

        message = f"""
{emoji} <b>TRADE ABERTO</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Direção:</b> {direction}
💰 <b>Entry:</b> {entry_display}
📦 <b>Qtd:</b> {quantity:.4f}
⚡ <b>Lev:</b> {leverage}x

🛑 <b>SL:</b> {stop_loss:.6f}
🎯 <b>TP:</b> {take_profit:.6f}
{strategy_emoji} <b>Strategy:</b> {tp_strategy}
"""
        await self.send_message(message)
    
    async def notify_trade_closed(self, trade_data: Dict):
        """Notifica fechamento de trade"""
        symbol = trade_data['symbol']
        direction = trade_data['direction']
        entry_price = trade_data['entry_price']
        close_price = trade_data.get('close_price') or trade_data.get('exit_price') or 0.0
        pnl = trade_data['pnl']
        pnl_pct = trade_data['pnl_percentage']
        reason = trade_data.get('reason', 'Manual')
        
        emoji = "✅" if pnl > 0 else "❌"
        
        message = f"""
{emoji} <b>TRADE FECHADO</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Direção:</b> {direction}
💵 <b>Entry:</b> {entry_price:.6f}
💵 <b>Exit:</b> {close_price:.6f}

💰 <b>P&L:</b> {pnl:+.2f} USDT ({pnl_pct:+.2f}%)
📌 <b>Motivo:</b> {reason}
"""
        await self.send_message(message)
    
    async def notify_pyramiding_executed(self, symbol: str, pnl_pct: float, quantity: float, price: float):
        """Notifica quando pyramiding é executado"""
        message = f"""
🧱 <b>PYRAMIDING EXECUTADO</b>

📊 <b>Símbolo:</b> {symbol}
💰 <b>Lucro Atual:</b> +{pnl_pct:.2f}%
📦 <b>Adicionado:</b> {quantity:.4f}
💵 <b>Preço:</b> {price:.6f}

✅ Aumentando exposição em trade vencedor!
"""
        await self.send_message(message)
    
    async def notify_breakeven_activated(self, symbol: str, entry_price: float, breakeven_price: float, pnl_pct: float):
        """Notifica quando break-even é ativado"""
        message = f"""
🛡️ <b>BREAKEVEN STOP ATIVADO</b>

📊 <b>Símbolo:</b> {symbol}
💰 <b>Entry:</b> {entry_price:.6f}
🔒 <b>Breakeven:</b> {breakeven_price:.6f}
📈 <b>Lucro Atual:</b> +{pnl_pct:.2f}%

✅ Ganho protegido! Risco zero a partir de agora.
"""
        await self.send_message(message)

    async def notify_breakeven_hit(self, symbol: str, entry_price: float, breakeven_price: float, exit_price: float, pnl_pct: float):
        """Notifica quando breakeven stop é acionado"""
        message = f"""
🛡️ <b>BREAKEVEN STOP EXECUTADO</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Entry:</b> {entry_price:.6f}
🔒 <b>Breakeven:</b> {breakeven_price:.6f}
📉 <b>Exit:</b> {exit_price:.6f}

💰 <b>P&L Final:</b> {pnl_pct:+.2f}%

✅ Posição fechada em breakeven - nenhuma perda!
"""
        await self.send_message(message)

    async def notify_trailing_activated(self, symbol: str, pnl_pct: float):
        """Notifica quando trailing stop é ativado"""
        message = f"""
🏃 <b>TRAILING STOP ATIVADO</b>

📊 <b>Símbolo:</b> {symbol}
💰 <b>Lucro Atual:</b> +{pnl_pct:.2f}%

🔒 Lucro será protegido dinamicamente.
"""
        await self.send_message(message)
    
    async def notify_trailing_executed(self, symbol: str, peak_price: float, close_price: float, pnl: float):
        """Notifica quando trailing stop executa"""
        pnl_emoji = "✅" if pnl > 0 else "❌"
        message = f"""
{pnl_emoji} <b>TRAILING STOP EXECUTADO</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Pico:</b> {peak_price:.6f}
📉 <b>Exit:</b> {close_price:.6f}

💰 <b>Lucro Final:</b> {pnl:+.2f} USDT
"""
        await self.send_message(message)
    
    # Aliases para compatibilidade
    async def notify_trailing_stop_activated(self, symbol: str, profit_pct: float):
        await self.notify_trailing_activated(symbol, profit_pct)
    
    async def notify_trailing_stop_executed(self, symbol: str, peak_price: float, close_price: float, pnl: float):
        await self.notify_trailing_executed(symbol, peak_price, close_price, pnl)
    
    async def notify_take_profit_hit(self, symbol: str, tp_level: str, price: float):
        """Notifica TP atingido"""
        message = f"""
🎯 <b>TAKE PROFIT ATINGIDO</b>

📊 <b>Símbolo:</b> {symbol}
📌 <b>Nível:</b> {tp_level}
💵 <b>Preço:</b> {price:.6f}

✅ Lucro parcial realizado.
"""
        await self.send_message(message)
    
    async def notify_stop_loss_hit(self, symbol: str, entry_price: float, exit_price: float, pnl: float, pnl_pct: float, reason: str = "Stop Loss"):
        """Notifica quando Stop Loss é atingido"""
        message = f"""
🛑 <b>STOP LOSS ATINGIDO</b>

📊 <b>Símbolo:</b> {symbol}
📌 <b>Motivo:</b> {reason}

💵 <b>Entry:</b> {entry_price:.6f}
💵 <b>Exit:</b> {exit_price:.6f}

💸 <b>P&L:</b> {pnl:.2f} USDT ({pnl_pct:+.2f}%)
"""
        await self.send_message(message)
    
    async def notify_emergency_stop(self, symbol: str, pnl_pct: float):
        """Notifica Emergency Stop Loss"""
        message = f"""
🚨 <b>EMERGENCY STOP LOSS</b>

📊 <b>Símbolo:</b> {symbol}
📉 <b>Prejuízo:</b> {pnl_pct:.2f}%

⚠️ Posição fechada forçadamente para limitar danos.
"""
        await self.send_message(message)
    
    async def notify_position_closed(self, symbol: str, side: str, entry_price: float, exit_price: float, pnl: float, pnl_pct: float, reason: str):
        """Notifica fechamento de posição genérico"""
        emoji = "✅" if pnl >= 0 else "❌"
        color = "🟢" if pnl >= 0 else "🔴"
        
        message = f"""
{emoji} <b>POSIÇÃO FECHADA</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Lado:</b> {side}
📌 <b>Motivo:</b> {reason}

💵 <b>Entry:</b> {entry_price:.6f}
💵 <b>Exit:</b> {exit_price:.6f}

{color} <b>P&L:</b> {pnl:.2f} USDT ({pnl_pct:+.2f}%)
"""
        await self.send_message(message)
    
    async def notify_risk_alert(self, symbol: str, current_price: float, stop_price: float, distance_pct: float):
        """Alerta de risco"""
        message = f"""
⚠️ <b>ALERTA DE RISCO</b>

📊 <b>Símbolo:</b> {symbol}
📍 <b>Preço:</b> {current_price:.6f}
🛑 <b>Stop:</b> {stop_price:.6f}

⚠️ <b>Distância:</b> {distance_pct:.2f}%
"""
        await self.send_message(message)
    
    async def send_portfolio_update(self, positions: list, total_pnl: float):
        """Envia atualização do portfólio"""
        if not positions:
            message = "📊 <b>PORTFÓLIO:</b> Nenhuma posição aberta."
        else:
            message = "📊 <b>PORTFÓLIO ATIVO</b>\n\n"
            for pos in positions:
                symbol = pos['symbol']
                direction = pos['direction']
                pnl = pos['pnl']
                pnl_pct = pos['pnl_pct']
                emoji = "🟢" if pnl > 0 else "🔴"
                message += f"{emoji} <b>{symbol}</b> {direction}\n   P&L: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)\n\n"
            
            message += f"💰 <b>P&L Total:</b> {total_pnl:+.2f} USDT"
        
        await self.send_message(message)
    
    async def send_daily_summary(self, stats: dict):
        """Envia resumo diário"""
        total_pnl = stats.get('total_pnl', 0)
        trades_count = stats.get('trades_count', 0)
        closed_count = stats.get('closed_count', 0)
        win_rate = stats.get('win_rate', 0)
        best_trade = stats.get('best_trade', {})
        worst_trade = stats.get('worst_trade', {})
        open_positions = stats.get('open_positions', 0)
        
        emoji = "🟢" if total_pnl > 0 else "🔴"
        
        message = f"""
📅 <b>RESUMO DIÁRIO</b>

{emoji} <b>P&L Total:</b> {total_pnl:+.2f} USDT
📈 <b>Trades:</b> {trades_count} ({closed_count} fechados)
🎯 <b>Win Rate:</b> {win_rate:.1f}%

🏆 <b>Melhor:</b> {best_trade.get('symbol', 'N/A')} ({best_trade.get('pnl', 0):+.2f})
📉 <b>Pior:</b> {worst_trade.get('symbol', 'N/A')} ({worst_trade.get('pnl', 0):+.2f})

💰 <b>Saldo:</b> {stats.get('balance', 0):.2f} USDT
📊 <b>Abertas:</b> {open_positions}
"""
        await self.send_message(message)
    
    async def send_daily_report(self, stats: Dict):
        """Alias para send_daily_summary"""
        await self.send_daily_summary(stats)
    
    async def send_portfolio_report(self, portfolio_data: Dict):
        """Envia relatório de portfólio"""
        open_positions = portfolio_data['open_positions']
        total_pnl = portfolio_data['total_unrealized_pnl']
        account_balance = portfolio_data['account_balance']
        
        emoji = "📈" if total_pnl > 0 else "📉"
        
        positions_text = ""
        for pos in portfolio_data.get('positions_list', []):
            pnl_emoji = "🟢" if pos['pnl'] > 0 else "🔴"
            positions_text += f"{pnl_emoji} {pos['symbol']}: {pos['pnl']:+.2f} USDT ({pos['pnl_pct']:+.2f}%)\n"
        
        if not positions_text:
            positions_text = "Nenhuma posição aberta"
        
        message = f"""
{emoji} <b>RELATÓRIO DE PORTFÓLIO</b>

💰 <b>Saldo:</b> {account_balance:.2f} USDT
📊 <b>Abertas:</b> {open_positions}
💵 <b>P&L Total:</b> {total_pnl:+.2f} USDT

<b>Posições:</b>
{positions_text}
"""
        await self.send_message(message)

    # ==================================================================
    # NOTIFICAÇÕES DAS NOVAS FEATURES (AIE, Market Intelligence, etc.)
    # ==================================================================

    async def notify_market_intelligence(self, symbol: str, data: Dict):
        """Notifica análise de Market Intelligence"""
        sentiment = data.get('sentiment', 'NEUTRAL')
        sentiment_score = data.get('sentiment_score', 0)
        funding_rate = data.get('funding_rate', 0)
        oi_change = data.get('oi_change_pct', 0)
        bias = data.get('bias', 'NEUTRAL')

        emoji = "🟢" if sentiment_score > 0 else "🔴" if sentiment_score < 0 else "⚪"
        bias_emoji = "📈" if bias == "LONG" else "📉" if bias == "SHORT" else "➡️"

        message = f"""
🧠 <b>MARKET INTELLIGENCE</b>

📊 <b>Símbolo:</b> {symbol}
{emoji} <b>Sentiment:</b> {sentiment} ({sentiment_score:+.0f})
{bias_emoji} <b>Bias:</b> {bias}

💰 <b>Funding Rate:</b> {funding_rate:.4f}%
📈 <b>OI Change:</b> {oi_change:+.2f}%
"""
        await self.send_message(message)

    async def notify_orderbook_analysis(self, symbol: str, data: Dict):
        """Notifica análise de Order Book"""
        imbalance = data.get('imbalance_pct', 0)
        dominant_side = data.get('dominant_side', 'NEUTRAL')
        depth_score = data.get('depth_score', 0)
        whale_walls = len(data.get('whale_walls', []))

        side_emoji = "🟢" if dominant_side == "BID" else "🔴" if dominant_side == "ASK" else "⚪"

        message = f"""
📊 <b>ORDERBOOK ANALYSIS</b>

📊 <b>Símbolo:</b> {symbol}
{side_emoji} <b>Dominante:</b> {dominant_side}
📈 <b>Imbalance:</b> {imbalance:+.1f}%
💪 <b>Depth Score:</b> {depth_score}/100
🐋 <b>Whale Walls:</b> {whale_walls}
"""
        await self.send_message(message)

    async def notify_capital_status(self, data: Dict):
        """Notifica status do Capital Management"""
        margin_used = data.get('margin_used_pct', 0)
        zone = data.get('zone', 'UNKNOWN')
        can_open = data.get('can_open_new', False)
        safety_buffer = data.get('safety_buffer_pct', 0)

        zone_emoji = "🟢" if zone == "GREEN_ZONE" else "🟡" if zone == "YELLOW_ZONE" else "🔴"
        open_emoji = "✅" if can_open else "❌"

        message = f"""
💰 <b>CAPITAL STATUS</b>

{zone_emoji} <b>Zona:</b> {zone}
📊 <b>Margem Usada:</b> {margin_used:.1f}%
🛡️ <b>Safety Buffer:</b> {safety_buffer:.1f}%
{open_emoji} <b>Pode Abrir:</b> {'Sim' if can_open else 'Não'}
"""
        await self.send_message(message)

    async def notify_ml_regime_change(self, old_regime: str, new_regime: str, confidence: float):
        """Notifica mudança de regime de mercado detectada pelo ML"""
        message = f"""
🤖 <b>ML REGIME CHANGE</b>

📈 <b>Anterior:</b> {old_regime}
📊 <b>Novo:</b> {new_regime}
🎯 <b>Confiança:</b> {confidence:.1f}%

⚙️ Parâmetros ajustados automaticamente.
"""
        await self.send_message(message)

    async def notify_strategy_execution(self, strategy: str, symbol: str, action: str, details: Dict):
        """Notifica execução de estratégia avançada"""
        emoji = "🎯" if strategy == "SNIPER" else "🧱" if strategy == "PYRAMID" else "📉" if strategy == "DCA" else "🏃"

        message = f"""
{emoji} <b>STRATEGY: {strategy}</b>

📊 <b>Símbolo:</b> {symbol}
🎬 <b>Ação:</b> {action}
💰 <b>Preço:</b> {details.get('price', 0):.6f}
📦 <b>Quantidade:</b> {details.get('quantity', 0):.4f}
"""
        if details.get('reason'):
            message += f"📌 <b>Motivo:</b> {details['reason']}\n"

        await self.send_message(message)

    async def notify_smart_trailing_update(self, symbol: str, mode: str, callback_pct: float, peak_price: float):
        """Notifica atualização do Smart Trailing Stop"""
        message = f"""
🏃 <b>SMART TRAILING UPDATE</b>

📊 <b>Símbolo:</b> {symbol}
⚙️ <b>Modo:</b> {mode}
📈 <b>Peak:</b> {peak_price:.6f}
🔒 <b>Callback:</b> {callback_pct:.2f}%
"""
        await self.send_message(message)

    async def notify_risk_heatmap(self, data: Dict):
        """Notifica heatmap de risco do portfólio"""
        total_risk = data.get('total_risk_pct', 0)
        highest_risk_symbol = data.get('highest_risk_symbol', 'N/A')
        highest_risk_pct = data.get('highest_risk_pct', 0)
        positions_at_risk = data.get('positions_at_risk', 0)

        risk_emoji = "🟢" if total_risk < 30 else "🟡" if total_risk < 60 else "🔴"

        message = f"""
🗺️ <b>RISK HEATMAP</b>

{risk_emoji} <b>Risco Total:</b> {total_risk:.1f}%
⚠️ <b>Maior Risco:</b> {highest_risk_symbol} ({highest_risk_pct:.1f}%)
📊 <b>Posições em Risco:</b> {positions_at_risk}
"""
        await self.send_message(message)

    async def notify_emergency_action(self, action: str, details: Dict):
        """Notifica ação de emergência"""
        message = f"""
🚨 <b>EMERGENCY ACTION</b>

⚡ <b>Ação:</b> {action}
📊 <b>Posições Afetadas:</b> {details.get('positions_affected', 0)}
💰 <b>Volume:</b> {details.get('volume_closed', 0):.2f} USDT
📌 <b>Motivo:</b> {details.get('reason', 'N/A')}

⚠️ Intervenção automática executada!
"""
        await self.send_message(message)

    async def notify_system_health(self, data: Dict):
        """Notifica saúde do sistema"""
        status = data.get('status', 'unknown')
        db_ok = data.get('db', False)
        redis_ok = data.get('redis', False)
        binance_ok = data.get('binance', False)
        bot_running = data.get('bot_running', False)

        status_emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"

        message = f"""
🏥 <b>SYSTEM HEALTH</b>

{status_emoji} <b>Status:</b> {status.upper()}
{'✅' if db_ok else '❌'} Database
{'✅' if redis_ok else '❌'} Redis
{'✅' if binance_ok else '❌'} Binance API
{'🟢' if bot_running else '🔴'} Bot

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(message)

    async def notify_bot_cycle_summary(self, data: Dict):
        """Notifica resumo do ciclo do bot"""
        cycle_num = data.get('cycle', 0)
        signals_found = data.get('signals_found', 0)
        trades_executed = data.get('trades_executed', 0)
        positions_open = data.get('positions_open', 0)
        total_pnl = data.get('total_pnl', 0)
        market_regime = data.get('market_regime', 'UNKNOWN')

        pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"

        message = f"""
🔄 <b>CYCLE #{cycle_num} COMPLETE</b>

🔍 <b>Signals:</b> {signals_found}
📈 <b>Executed:</b> {trades_executed}
📊 <b>Positions:</b> {positions_open}
{pnl_emoji} <b>P&L:</b> {total_pnl:+.2f} USDT
🌍 <b>Regime:</b> {market_regime}
"""
        await self.send_message(message)

# Instância global
telegram_notifier = TelegramNotifier()
