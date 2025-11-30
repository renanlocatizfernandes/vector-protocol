from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import get_settings
from utils.telegram_notifier import telegram_notifier
from modules.autonomous_bot import autonomous_bot

settings = get_settings()

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    status = autonomous_bot.get_status()
    
    message = f"""
📊 <b>STATUS DO BOT</b>

🤖 <b>Estado:</b> {"🟢 Ativo" if status['running'] else "🔴 Parado"}
⏱️ <b>Intervalo:</b> {status['scan_interval_minutes']:.0f} min
📈 <b>Score Mínimo:</b> {status['min_score']}
🎯 <b>Max Trades:</b> {status['max_simultaneous_trades']}
👁️ <b>Monitor:</b> {"Ativo" if status['position_monitor_active'] else "Parado"}
"""
    await update.message.reply_text(message, parse_mode='HTML')

async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /portfolio"""
    # Buscar dados do portfólio
    # Enviar via telegram_notifier.send_portfolio_report()
    await update.message.reply_text("📊 Buscando dados do portfólio...")

def start_telegram_bot():
    """Inicia bot de comandos Telegram"""
    if not settings.TELEGRAM_ENABLED:
        return
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    
    app.run_polling()
