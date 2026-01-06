from config.settings import get_settings

class BotConfig:
    def __init__(self):
        self.settings = get_settings()
        self.reload_settings()

    def reload_settings(self):
        """
        Recarrega configurações dinamicamente (chamado via API)
        """
        from config.settings import reload_settings
        self.settings = reload_settings()
        
        # Atualizar atributos críticos
        self.min_score = int(getattr(self.settings, "BOT_MIN_SCORE", 70))
        self.scan_interval = int(getattr(self.settings, "BOT_SCAN_INTERVAL_MINUTES", 1)) * 60
        self.max_positions = int(getattr(self.settings, "BOT_MAX_POSITIONS", 10))
        self.pyramiding_enabled = bool(getattr(self.settings, "PYRAMIDING_ENABLED", True))
        symbols = list(getattr(self.settings, "SYMBOL_WHITELIST", []))
        if not symbols:
            symbols = list(getattr(self.settings, "TESTNET_WHITELIST", []))
        self.symbols_to_scan = symbols
        
        # Propagar para módulos
        from modules.market_scanner import market_scanner
        from modules.signal_generator import signal_generator
        market_scanner.reload_settings()
        signal_generator.reload_settings()
