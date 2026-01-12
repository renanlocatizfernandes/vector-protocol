from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import get_settings
from utils.telegram_notifier import telegram_notifier
from modules.autonomous_bot import autonomous_bot
from utils.binance_client import binance_client

settings = get_settings()

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    try:
        status = autonomous_bot.get_status()
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao obter status: {e}")
        return
    
    try:
        running = status.get('running', False)
        scan_interval = status.get('scan_interval_minutes', 0)
        min_score = status.get('min_score', 0)
        max_trades = status.get('max_simultaneous_trades', 0)
        monitor_active = status.get('position_monitor_active', False)
    except Exception:
        running = False
        scan_interval = 0
        min_score = 0
        max_trades = 0
        monitor_active = False
    
    message = f"""
📊 <b>STATUS DO BOT</b>

🤖 <b>Estado:</b> {"🟢 Ativo" if running else "🔴 Parado"}
⏱️ <b>Intervalo:</b> {scan_interval:.0f} min
📈 <b>Score Mínimo:</b> {min_score}
🎯 <b>Max Trades:</b> {max_trades}
👁️ <b>Monitor:</b> {"Ativo" if monitor_active else "Parado"}
"""
    await update.message.reply_text(message, parse_mode='HTML')

async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /portfolio"""
    try:
        # Buscar dados do portfólio
        balance_data = await binance_client.get_account_balance()
        
        if balance_data and isinstance(balance_data, dict):
            available_balance = balance_data.get("available_balance", 0)
            total_balance = balance_data.get("total_balance", 0)
            positions = balance_data.get("positions", [])
            
            message = f"""
💰 <b>PORTFÓLIO</b>

💵 <b>Saldo Disponível:</b> {available_balance:.2f} USDT
💎 <b>Saldo Total:</b> {total_balance:.2f} USDT
📊 <b>Posições Abertas:</b> {len(positions)}
"""
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Erro ao buscar dados do portfólio")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar portfólio: {e}")

def start_telegram_bot():
    """Inicia bot de comandos Telegram"""
    if not settings.TELEGRAM_ENABLED:
        return
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    
    app.run_polling()
