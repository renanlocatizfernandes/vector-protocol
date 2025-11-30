import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger("telegram_bot")

class TelegramBot:
    def __init__(self):
        self.settings = get_settings()
        self.token = self.settings.TELEGRAM_BOT_TOKEN
        self.allowed_chat_id = str(self.settings.TELEGRAM_CHAT_ID)
        self.application = None
        self.running = False

    async def start(self):
        """Inicia o bot do Telegram"""
        if not self.settings.TELEGRAM_ENABLED or not self.token:
            logger.warning("Telegram Bot desabilitado ou sem token.")
            return

        try:
            self.application = ApplicationBuilder().token(self.token).build()
            
            # Registrar comandos
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("stop", self._cmd_stop))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("balance", self._cmd_balance))
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            self.application.add_handler(CommandHandler("force_exit", self._cmd_force_exit))

            # Iniciar polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.running = True
            logger.info("🤖 Telegram Bot Command Handler iniciado!")
            
        except Exception as e:
            logger.error(f"Falha ao iniciar Telegram Bot: {e}")

    async def stop(self):
        """Para o bot do Telegram"""
        if self.application and self.running:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            self.running = False
            logger.info("Telegram Bot parado.")

    # ==================================================================
    # HANDLERS
    # ==================================================================

    def _check_auth(self, update: Update) -> bool:
        if str(update.effective_chat.id) != self.allowed_chat_id:
            logger.warning(f"Acesso negado: Chat ID {update.effective_chat.id}")
            return False
        return True

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        from modules.autonomous_bot import autonomous_bot
        if autonomous_bot.running:
            await update.message.reply_text("⚠️ O bot já está rodando!")
        else:
            await update.message.reply_text("🚀 Iniciando o bot...")
            asyncio.create_task(autonomous_bot.start(dry_run=autonomous_bot.dry_run))

    async def _cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        from modules.autonomous_bot import autonomous_bot
        if not autonomous_bot.running:
            await update.message.reply_text("⚠️ O bot já está parado.")
        else:
            await update.message.reply_text("🛑 Parando o bot...")
            autonomous_bot.stop()
            await update.message.reply_text("✅ Bot parado com sucesso.")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        from modules.autonomous_bot import autonomous_bot
        open_positions_count = asyncio.run(autonomous_bot._get_open_positions_count())
        status = "🟢 ONLINE" if autonomous_bot.running else "🔴 OFFLINE"
        mode = "DRY RUN" if autonomous_bot.dry_run else "LIVE"
        
        msg = (
            f"🤖 <b>STATUS DO BOT</b>\n\n"
            f"Estado: {status}\n"
            f"Modo: {mode}\n"
            f"Score Min: {autonomous_bot.bot_config.min_score}\n"
            f"Posições: {open_positions_count}/{autonomous_bot.max_positions}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        # Tentar pegar saldo real via RiskManager ou BinanceClient
        try:
            from utils.binance_client import binance_client
            balance = await binance_client.get_account_balance()
            await update.message.reply_text(f"💰 <b>Saldo Disponível:</b> {balance:.2f} USDT", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao consultar saldo: {e}")

    async def _cmd_force_exit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        if not context.args:
            await update.message.reply_text("⚠️ Uso: /force_exit SYMBOL (ou ALL)")
            return
            
        symbol = context.args[0].upper()
        
        if symbol == "ALL":
            await update.message.reply_text("⚠️ Fechando TODAS as posições... (Implementar lógica)")
            # TODO: Implementar close_all em autonomous_bot
        else:
            # Tentar fechar posição específica
            # Como autonomous_bot não expõe método direto fácil, vamos usar order_executor via signal fake ou método novo
            await update.message.reply_text(f"⚠️ Fechamento forçado de {symbol} ainda não implementado via comando.")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_auth(update): return
        
        help_text = """
🤖 <b>COMANDOS DISPONÍVEIS</b>

/start - Inicia o bot
/stop - Para o bot
/status - Ver status atual
/balance - Ver saldo USDT
/help - Ajuda
"""
        await update.message.reply_text(help_text, parse_mode="HTML")

# Instância global
telegram_bot = TelegramBot()
