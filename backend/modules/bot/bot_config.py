import json
import os
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

        # Preferir valores do banco quando disponiveis.
        try:
            from api.database import SessionLocal
            from modules.config_manager import ConfigManager
            db = SessionLocal()
            try:
                cfg = ConfigManager(db, self.settings)
                db_max_positions = cfg.get_sync("BOT_MAX_POSITIONS", getattr(self.settings, "BOT_MAX_POSITIONS", None))
                db_symbols = cfg.get_sync("SYMBOL_WHITELIST", getattr(self.settings, "SYMBOL_WHITELIST", []))
            finally:
                db.close()
        except Exception:
            db_max_positions = getattr(self.settings, "BOT_MAX_POSITIONS", None)
            db_symbols = getattr(self.settings, "SYMBOL_WHITELIST", [])

        # Normalizar e propagar para o ambiente (usado por outros modulos).
        try:
            if db_max_positions is not None:
                os.environ["BOT_MAX_POSITIONS"] = str(int(db_max_positions))
        except Exception:
            pass
        try:
            symbols = db_symbols
            if isinstance(symbols, str):
                try:
                    symbols = json.loads(symbols)
                except Exception:
                    symbols = [s.strip() for s in symbols.split(",")]
            cleaned = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
            if cleaned:
                os.environ["SYMBOL_WHITELIST"] = json.dumps(cleaned)
        except Exception:
            pass

        # Recarregar settings para refletir overrides vindos do banco.
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
