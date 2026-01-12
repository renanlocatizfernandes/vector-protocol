import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from config.settings import get_settings
from utils.redis_client import redis_client
from utils.logger import setup_logger

logger = setup_logger("telegram_bot")


class TelegramBot:
    def __init__(self):
        self.settings = get_settings()
        self.token = self.settings.TELEGRAM_BOT_TOKEN
        self.allowed_chat_id = str(self.settings.TELEGRAM_CHAT_ID)
        self.application = None
        self.running = False
        self._starting = False
        self._positions_cache = None
        self._last_positions_update = 0
        self._lock_key = "telegram_bot_lock"
        self._lock_acquired = False
        self._lock_task = None

    async def start(self):
        """Inicia o bot do Telegram."""
        if self.running or self._starting:
            logger.info("Telegram Bot ja iniciado (ignorar start duplicado).")
            return
        if not self.settings.TELEGRAM_ENABLED or not self.token:
            logger.warning("Telegram Bot desabilitado ou sem token.")
            return

        self._starting = True
        self._lock_acquired = False
        try:
            if redis_client and redis_client.client:
                if not redis_client.client.set(self._lock_key, "1", nx=True, ex=120):
                    logger.warning("Telegram Bot lock ativo; abortando start.")
                    return
                self._lock_acquired = True
        except Exception as e:
            logger.warning(f"Falha ao obter lock do Telegram: {e}")

        try:
            self.application = ApplicationBuilder().token(self.token).build()

            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("stop", self._cmd_stop))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("balance", self._cmd_balance))
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            self.application.add_handler(CommandHandler("force_exit", self._cmd_force_exit))
            self.application.add_handler(CommandHandler("positions", self._cmd_positions))
            self.application.add_handler(CommandHandler("trades", self._cmd_trades))
            self.application.add_handler(MessageHandler(filters.Regex(r"^/pnl"), self._cmd_pnl))
            self.application.add_handler(CommandHandler("config", self._cmd_config))
            self.application.add_handler(CommandHandler("market", self._cmd_market))
            self.application.add_handler(CommandHandler("risk", self._cmd_risk))
            self.application.add_handler(CommandHandler("logs", self._cmd_logs))
            self.application.add_handler(CommandHandler("testnet", self._cmd_testnet))
            self.application.add_handler(CommandHandler("dry_run", self._cmd_dry_run))

            await self.application.initialize()
            await self.application.start()
            if self.application.updater:
                await self.application.updater.start_polling()

            self.running = True
            if self._lock_acquired and self._lock_task is None:
                self._lock_task = asyncio.create_task(self._refresh_lock())
            logger.info("Telegram Bot Command Handler iniciado.")
        except Exception as e:
            logger.error(f"Falha ao iniciar Telegram Bot: {e}")
        finally:
            self._starting = False

    async def stop(self):
        """Para o bot do Telegram."""
        if self.application and self.running:
            if self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.running = False
        self._starting = False
        if self._lock_task is not None:
            self._lock_task.cancel()
            self._lock_task = None
        if self._lock_acquired:
            try:
                if redis_client and redis_client.client:
                    redis_client.client.delete(self._lock_key)
            except Exception:
                pass
        self._lock_acquired = False
        logger.info("Telegram Bot parado.")

    async def _refresh_lock(self):
        while self._lock_acquired:
            try:
                if redis_client and redis_client.client:
                    redis_client.client.set(self._lock_key, "1", xx=True, ex=120)
            except Exception:
                pass
            await asyncio.sleep(60)

    def _check_auth(self, update: Update) -> bool:
        if str(update.effective_chat.id) != self.allowed_chat_id:
            logger.warning(f"Acesso negado: Chat ID {update.effective_chat.id}")
            return False
        return True

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        from modules.autonomous_bot import autonomous_bot

        if autonomous_bot.running:
            await update.message.reply_text("O bot ja esta rodando.")
        else:
            await update.message.reply_text("Iniciando o bot...")
            asyncio.create_task(autonomous_bot.start(dry_run=autonomous_bot.dry_run))

    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        from modules.autonomous_bot import autonomous_bot

        if not autonomous_bot.running:
            await update.message.reply_text("O bot ja esta parado.")
        else:
            await update.message.reply_text("Parando o bot...")
            autonomous_bot.stop()
            await update.message.reply_text("Bot parado com sucesso.")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        from modules.autonomous_bot import autonomous_bot

        try:
            open_positions_count = await autonomous_bot._get_open_positions_count()
        except Exception as e:
            logger.error(f"Erro ao obter count de posicoes: {e}")
            open_positions_count = 0

        status = "ONLINE" if autonomous_bot.running else "OFFLINE"
        mode = "DRY RUN" if autonomous_bot.dry_run else "LIVE"

        try:
            min_score = getattr(autonomous_bot.bot_config, "min_score", 0)
        except Exception:
            min_score = 0

        try:
            max_positions = getattr(autonomous_bot, "max_positions", 4)
        except Exception:
            max_positions = 4

        msg = (
            "<b>STATUS DO BOT</b>\n\n"
            f"Estado: {status}\n"
            f"Modo: {mode}\n"
            f"Score Min: {min_score}\n"
            f"Posicoes: {open_positions_count}/{max_positions}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        try:
            from utils.binance_client import binance_client

            balance_data = await binance_client.get_account_balance()

            if balance_data and isinstance(balance_data, dict):
                available_balance = balance_data.get("available_balance", 0)
                total_balance = balance_data.get("total_balance", 0)

                msg = (
                    f"<b>Saldo Disponivel:</b> {available_balance:.2f} USDT\n"
                    f"<b>Saldo Total:</b> {total_balance:.2f} USDT"
                )
                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.message.reply_text("Erro ao consultar saldo: dados invalidos")
        except Exception as e:
            await update.message.reply_text(f"Erro ao consultar saldo: {e}")

    async def _cmd_force_exit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("Uso: /force_exit SYMBOL (ou ALL)")
            return

        symbol = context.args[0].upper()

        if symbol == "ALL":
            await update.message.reply_text("Fechando TODAS as posicoes... (nao implementado)")
        else:
            await update.message.reply_text(
                f"Fechamento forcado de {symbol} nao implementado via comando."
            )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update):
            return

        help_text = """
<b>COMANDOS DISPONIVEIS</b>

<b>Controle:</b>
/start - Inicia o bot
/stop - Para o bot
/status - Ver status atual
/dry_run - Toggle modo DRY RUN
/testnet - Toggle modo TESTNET

<b>Financeiro:</b>
/balance - Ver saldo USDT
/pnl - Ver P&L total
/positions - Ver posicoes abertas
/trades - Ver trades recentes

<b>Informacoes:</b>
/config - Ver configuracoes
/market - Ver condicoes de mercado
/risk - Ver metricas de risco
/logs - Ver logs recentes

<b>Operacoes:</b>
/force_exit SYMBOL - Fechar posicao
/force_exit ALL - Fechar todas

<b>Ajuda:</b>
/help - Mostra esta mensagem
"""
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista posicoes abertas."""
        if not self._check_auth(update):
            return

        try:
            from utils.binance_client import binance_client

            balance_data = await binance_client.get_account_balance()

            if balance_data and isinstance(balance_data, dict):
                positions = balance_data.get("positions", [])
                filtered = []
                seen = set()
                for pos in positions:
                    try:
                        amount = float(pos.get("positionAmt", 0) or 0)
                    except Exception:
                        amount = 0.0
                    try:
                        entry_price = float(pos.get("entryPrice", 0) or 0)
                    except Exception:
                        entry_price = 0.0
                    if abs(amount) <= 0:
                        continue
                    if entry_price <= 0:
                        continue
                    key = (
                        str(pos.get("symbol", "")),
                        str(pos.get("positionSide", "")),
                        f"{amount:.8f}",
                        f"{entry_price:.8f}",
                        str(pos.get("leverage", "")),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    filtered.append(pos)
                positions = filtered

                if not positions:
                    await update.message.reply_text(
                        "<b>Nenhuma posicao aberta</b>", parse_mode="HTML"
                    )
                    return

                msg = "<b>POSICOES ABERTAS</b>\n\n"

                for pos in positions[:10]:
                    symbol = pos.get("symbol", "N/A")
                    amount = float(pos.get("positionAmt", 0))
                    entry_price = float(pos.get("entryPrice", 0))
                    unrealized_pnl = float(pos.get("unRealizedProfit", 0))
                    leverage = int(pos.get("leverage", 0))

                    direction = "LONG" if amount > 0 else "SHORT"
                    pnl_tag = "OK" if unrealized_pnl >= 0 else "ERR"

                    msg += (
                        f"{direction} <b>{symbol}</b> ({leverage}x)\n"
                        f"Qtd: {abs(amount):.4f}\n"
                        f"Entry: {entry_price:.6f}\n"
                        f"{pnl_tag} P&L: {unrealized_pnl:+.2f} USDT\n\n"
                    )

                if len(positions) > 10:
                    msg += f"...e mais {len(positions) - 10} posicoes\n"

                await update.message.reply_text(msg, parse_mode="HTML")
            else:
                await update.message.reply_text("Erro ao buscar posicoes")
        except Exception as e:
            await update.message.reply_text(f"Erro ao buscar posicoes: {e}")

    async def _cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista trades recentes."""
        if not self._check_auth(update):
            return

        try:
            from api.models.trades import Trade
            from models.database import SessionLocal

            db = SessionLocal()
            try:
                trades = db.query(Trade).order_by(Trade.opened_at.desc()).limit(10).all()

                if not trades:
                    await update.message.reply_text(
                        "<b>Nenhum trade registrado</b>", parse_mode="HTML"
                    )
                    return

                msg = "<b>ULTIMOS TRADES</b>\n\n"

                for trade in trades:
                    pnl_value = float(trade.pnl or 0)
                    emoji = "OK" if pnl_value >= 0 else "ERR"
                    direction = "LONG" if trade.direction == "LONG" else "SHORT"
                    pnl_pct = (
                        (pnl_value / (trade.entry_price * trade.quantity)) * 100
                        if trade.entry_price and trade.quantity
                        else 0
                    )
                    reason = getattr(trade, "reason", None) or "N/A"

                    msg += (
                        f"{emoji} <b>{trade.symbol}</b> {direction}\n"
                        f"P&L: {pnl_value:+.2f} USDT ({pnl_pct:+.2f}%)\n"
                        f"Motivo: {reason}\n\n"
                    )

                await update.message.reply_text(msg, parse_mode="HTML")
            finally:
                db.close()
        except Exception as e:
            await update.message.reply_text(f"Erro ao buscar trades: {e}")

    async def _cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra P&L total."""
        if not self._check_auth(update):
            return

        try:
            from api.models.trades import Trade
            from models.database import SessionLocal
            from utils.binance_client import binance_client
            from datetime import datetime, timedelta, timezone

            days = 30
            label = "30d"
            arg = None
            if context.args:
                arg = str(context.args[0]).lower()
            else:
                raw = getattr(update.message, "text", "") or ""
                cmd = raw.split()[0] if raw else ""
                cmd = cmd.split("@")[0]
                if cmd.startswith("/pnl") and len(cmd) > 4:
                    tail = cmd[4:]
                    if tail.startswith("_"):
                        tail = tail[1:]
                    if tail:
                        arg = tail.lower()

            if arg:
                if arg in ("today", "hoje", "1", "1d"):
                    days = 1
                    label = "hoje"
                elif arg in ("7", "7d"):
                    days = 7
                    label = "7d"
                elif arg in ("30", "30d"):
                    days = 30
                    label = "30d"
                elif arg == "all":
                    days = 30
                    label = "30d (limite)"
                elif arg.startswith("since="):
                    try:
                        date_str = arg.split("=", 1)[1]
                        since = datetime.strptime(date_str, "%Y-%m-%d").date()
                        today = datetime.now(timezone.utc).date()
                        days = max(1, (today - since).days + 1)
                        label = f"since {date_str}"
                    except Exception:
                        pass
                else:
                    try:
                        days = int(arg)
                        label = f"{days}d"
                    except Exception:
                        pass

            days = max(1, min(int(days), 30))
            today = datetime.now(timezone.utc).date()
            start_date = today - timedelta(days=days - 1)
            start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)

            realized = 0.0
            fees = 0.0
            funding = 0.0
            try:
                income_history = await asyncio.to_thread(
                    binance_client.client.futures_income_history,
                    startTime=int(start_dt.timestamp() * 1000),
                    limit=1000,
                )
            except Exception:
                income_history = []

            for item in income_history or []:
                income_type = item.get("incomeType")
                try:
                    amount = float(item.get("income", 0) or 0)
                except Exception:
                    amount = 0.0
                if income_type == "REALIZED_PNL":
                    realized += amount
                elif income_type == "COMMISSION":
                    fees += amount
                elif income_type == "FUNDING_FEE":
                    funding += amount

            realized_net = realized + fees + funding

            balance_data = await binance_client.get_account_balance()
            unrealized_pnl = 0.0
            if balance_data and isinstance(balance_data, dict):
                positions = balance_data.get("positions", [])
                for p in positions:
                    try:
                        amt = float(p.get("positionAmt", 0) or 0)
                    except Exception:
                        amt = 0.0
                    if abs(amt) <= 0:
                        continue
                    try:
                        unrealized_pnl += float(p.get("unRealizedProfit", 0) or 0)
                    except Exception:
                        pass

            total_pnl = realized_net + unrealized_pnl

            db = SessionLocal()
            try:
                closed_trades = db.query(Trade).filter(Trade.status == "closed").all()
                filtered = []
                for t in closed_trades:
                    dt = t.closed_at or t.exit_time or t.opened_at
                    if not dt:
                        continue
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= start_dt:
                        filtered.append(t)
                win_rate = (
                    len([t for t in filtered if (t.pnl or 0) > 0]) / len(filtered) * 100
                    if filtered
                    else 0
                )
                trades_count = len(filtered)
            finally:
                db.close()

            emoji = "OK" if total_pnl >= 0 else "ERR"
            msg = (
                f"<b>RESUMO DE P&L</b> ({label})\n\n"
                f"Realizado (Binance): {realized_net:+.2f} USDT\n"
                f"Fees/Funding: {fees + funding:+.2f} USDT\n"
                f"Nao Realizado: {unrealized_pnl:+.2f} USDT\n"
                f"{emoji} TOTAL: {total_pnl:+.2f} USDT\n\n"
                f"Win Rate (DB): {win_rate:.1f}%\n"
                f"Trades (DB): {trades_count}"
            )
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Erro ao calcular P&L: {e}")

    async def _cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra configuracoes atuais."""
        if not self._check_auth(update):
            return

        try:
            from modules.autonomous_bot import autonomous_bot
            from config.settings import get_settings

            settings = get_settings()

            msg = "<b>CONFIGURACOES ATUAIS</b>\n\n"
            msg += "<b>Bot:</b>\n"
            msg += f"Estado: {'Rodando' if autonomous_bot.running else 'Parado'}\n"
            msg += f"Modo: {'DRY RUN' if autonomous_bot.dry_run else 'LIVE'}\n"

            try:
                max_pos = getattr(autonomous_bot, "max_positions", 4)
                msg += f"Max Posicoes: {max_pos}\n"
            except Exception:
                msg += "Max Posicoes: 4\n"

            msg += "\n<b>Binance:</b>\n"
            testnet = getattr(settings, "BINANCE_TESTNET", False)
            msg += f"Modo: {'TESTNET' if testnet else 'MAINNET'}\n"

            msg += "\n<b>Risco:</b>\n"
            try:
                max_risk = getattr(settings, "MAX_POSITION_RISK_PCT", 2.0)
                msg += f"Max Risco por Trade: {max_risk}%\n"
            except Exception:
                msg += "Max Risco por Trade: 2%\n"

            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Erro ao buscar configuracoes: {e}")

    async def _cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra condicoes de mercado."""
        if not self._check_auth(update):
            return

        try:
            from utils.binance_client import binance_client

            btc_price = await binance_client.get_symbol_price("BTCUSDT")

            msg = "<b>CONDICOES DE MERCADO</b>\n\n"
            msg += f"<b>BTCUSDT:</b> ${btc_price:,.2f}\n\n"
            msg += "<b>Indices:</b>\n"
            msg += "Use /api para detalhes completos\n"

            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Erro ao buscar condicoes de mercado: {e}")

    async def _cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra metricas de risco."""
        if not self._check_auth(update):
            return

        try:
            from api.models.trades import Trade
            from models.database import SessionLocal

            db = SessionLocal()
            try:
                trades = db.query(Trade).filter(Trade.pnl.isnot(None)).all()

                if not trades:
                    await update.message.reply_text(
                        "<b>Sem dados de risco disponiveis</b>", parse_mode="HTML"
                    )
                    return

                profits = [t.pnl for t in trades if t.pnl > 0]
                losses = [t.pnl for t in trades if t.pnl < 0]

                avg_profit = sum(profits) / len(profits) if profits else 0
                avg_loss = sum(losses) / len(losses) if losses else 0

                profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
                max_drawdown = min(t.pnl for t in trades) if trades else 0

                msg = "<b>METRICAS DE RISCO</b>\n\n"
                msg += f"<b>Profit Factor:</b> {profit_factor:.2f}\n"
                msg += f"<b>Avg Profit:</b> {avg_profit:+.2f} USDT\n"
                msg += f"<b>Avg Loss:</b> {avg_loss:+.2f} USDT\n"
                msg += f"<b>Max Drawdown:</b> {max_drawdown:+.2f} USDT\n"
                msg += f"<b>Total Trades:</b> {len(trades)}"

                await update.message.reply_text(msg, parse_mode="HTML")
            finally:
                db.close()
        except Exception as e:
            await update.message.reply_text(f"Erro ao calcular metricas de risco: {e}")

    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra logs recentes."""
        if not self._check_auth(update):
            return

        try:
            import os

            log_file = "logs/trading.log"

            if not os.path.exists(log_file):
                await update.message.reply_text(
                    "<b>Arquivo de log nao encontrado</b>", parse_mode="HTML"
                )
                return

            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_logs = lines[-20:] if len(lines) > 20 else lines

            if not recent_logs:
                await update.message.reply_text("<b>Sem logs recentes</b>", parse_mode="HTML")
                return

            msg = "<b>LOGS RECENTES</b>\n\n"
            msg += "<pre>"
            msg += "".join(recent_logs[-10:])
            msg += "</pre>"

            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Erro ao ler logs: {e}")

    async def _cmd_testnet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle modo TESTNET."""
        if not self._check_auth(update):
            return

        try:
            from config.settings import get_settings

            settings = get_settings()

            current = getattr(settings, "BINANCE_TESTNET", False)
            new_status = not current

            await update.message.reply_text(
                "<b>MODO TESTNET</b>\n\n"
                f"Atual: {'TESTNET' if current else 'MAINNET'}\n"
                "Para alterar, edite o arquivo .env:\n"
                f"BINANCE_TESTNET={str(new_status).lower()}\n\n"
                "Reinicie o bot apos alterar.",
                parse_mode="HTML",
            )
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")

    async def _cmd_dry_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle modo DRY RUN."""
        if not self._check_auth(update):
            return

        try:
            from modules.autonomous_bot import autonomous_bot

            current = autonomous_bot.dry_run
            new_status = not current

            await update.message.reply_text(
                "<b>MODO DRY RUN</b>\n\n"
                f"Atual: {'DRY RUN' if current else 'LIVE'}\n"
                "Para alterar, edite o arquivo .env:\n"
                f"BOT_DRY_RUN={str(new_status).lower()}\n\n"
                "Reinicie o bot apos alterar.",
                parse_mode="HTML",
            )
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")


telegram_bot = TelegramBot()
