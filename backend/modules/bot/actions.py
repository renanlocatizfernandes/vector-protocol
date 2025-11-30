from utils.logger import setup_logger
from modules.market_scanner import market_scanner
from modules.signal_generator import signal_generator
from modules.market_filter import market_filter
from modules.correlation_filter import correlation_filter
from modules.order_executor import order_executor
from utils.telegram_notifier import telegram_notifier
import asyncio

logger = setup_logger("bot_actions")

class BotActions:
    def __init__(self, bot):
        self.bot = bot

    async def add_strategic_positions(self, count: int) -> dict:
        """
        Abre novas posições utilizando todo o pipeline estratégico atual.
        """
        try:
            target = max(1, int(count))
        except Exception:
            target = 1

        account_balance = await self.bot.position_manager.get_account_balance()
        open_positions_exch = await self.bot.position_manager.get_open_positions_from_binance()
        open_positions_count = len(open_positions_exch)
        
        available_slots = min(
            target,
            max(0, self.bot.bot_config.max_positions - open_positions_count),
        )
        if available_slots <= 0:
            msg = "Sem slots disponíveis para novas posições"
            logger.warning(f"❌ {msg}")
            return {"success": False, "message": msg, "opened": 0, "attempted": 0, "available_slots": 0}

        market_sentiment = await market_filter.check_market_sentiment()
        scan_results = await market_scanner.scan_market()
        if not scan_results:
            return {"success": False, "message": "Nenhum símbolo retornado pelo scanner", "opened": 0}

        signals = await signal_generator.generate_signal(scan_results)
        if not signals:
            return {"success": False, "message": "Nenhum sinal gerado", "opened": 0}

        approved_signals = [s for s in signals if await market_filter.should_trade_symbol(s, market_sentiment)]
        if not approved_signals:
            return {"success": False, "message": "Todos os sinais bloqueados pelo market filter", "opened": 0}

        filtered_signals = await correlation_filter.filter_correlated_signals(approved_signals, open_positions=open_positions_exch)
        if not filtered_signals:
            return {"success": False, "message": "Todos os sinais filtrados por correlação", "opened": 0}

        final_signals = filtered_signals[:available_slots]
        results = []
        opened = 0

        logger.info(f"📤 Abertura estratégica: alvo={target} | slots={available_slots} | sinais={len(final_signals)}")

        for sig in final_signals:
            try:
                exec_res = await order_executor.execute_signal(
                    signal=sig,
                    account_balance=account_balance,
                    open_positions=open_positions_count + opened,
                    dry_run=self.bot.dry_run
                )
                if exec_res.get("success"):
                    opened += 1
                results.append({"signal": sig, "execution": exec_res, "success": exec_res.get("success")})
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erro ao executar {sig.get('symbol')}: {e}")
                results.append({"signal": sig, "execution": {"success": False, "reason": str(e)}, "success": False})

        try:
            await telegram_notifier.send_message(f"🚀 Abertura estratégica concluída\nAlvo: {target} | Executadas: {opened}")
        except Exception:
            pass

        return {"success": True, "opened": opened, "results": results}
