from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Binance
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str
    BINANCE_TESTNET: bool = True
    
    # Database
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Bot Settings
    MAX_POSITIONS: int = 15  # ← Padrão
    RISK_PER_TRADE: float = 0.02
    MAX_PORTFOLIO_RISK: float = 0.30
    DEFAULT_LEVERAGE: int = 3
    SCANNER_MAX_SYMBOLS: int = 200 # Aumentado para buscar mais símbolos

    # Risco e spread (afinamento fino)
    SNIPER_RISK_PER_TRADE: float = 0.01       # Risco por trade sniper (fração, ex.: 0.01 = 1%)
    MAX_SPREAD_PCT_CORE: float = 0.30         # Spread máximo (%) para entradas core
    MAX_SPREAD_PCT_SNIPER: float = 0.50       # Spread máximo (%) para sniper (mais permissivo)

    # Sniper strategy (scalps rápidos)
    SNIPER_EXTRA_SLOTS: int = 5              # Slots extras além de MAX_POSITIONS para entradas sniper
    SNIPER_TP_PCT: float = 0.6               # Alvo de lucro em % (ex.: 0.6% por trade)
    SNIPER_SL_PCT: float = 0.3               # Stop em % (ex.: 0.3% de perda máxima por sniper)
    SNIPER_DEFAULT_LEVERAGE: int = 10        # Alavancagem padrão para sniper

    # Margin policy (Cross vs Isolated)
    DEFAULT_MARGIN_CROSSED: bool = True  # True = Cross como padrão
    AUTO_ISOLATE_MIN_LEVERAGE: int = 10  # Isola automaticamente quando leverage >= 10x
    ALLOW_MARGIN_MODE_OVERRIDE: bool = True  # Habilita ajuste de margin mode ao abrir ordem

    # Exits avançados / execução
    ENABLE_TRAILING_STOP: bool = True            # TSL ligado (dinâmico por ATR)
    TSL_CALLBACK_PCT_MIN: float = 0.4            # % mínima do callback (limite Binance: 0.1–5.0)
    TSL_CALLBACK_PCT_MAX: float = 1.2            # % máxima do callback
    TSL_ATR_LOOKBACK_INTERVAL: str = "15m"       # janela para ATR (para calibrar callback)
    ENABLE_BRACKET_BATCH: bool = False           # Tentar enviar SL+TP em batch (fallback para sequencial)
    USE_MARK_PRICE_FOR_STOPS: bool = True        # Usar MARK_PRICE para SL/TP/TSL (mais estável)
    ORDER_TIMEOUT_SEC: int = 3                   # Timeout padrão (s) para LIMIT antes de fallback MARKET
    USE_POST_ONLY_ENTRIES: bool = False          # Entradas LIMIT como maker-only (GTX). Se True, reduz taker fees.
    TAKE_PROFIT_PARTS: str = "0.5,0.3,0.2"       # Frações para TP ladder (ex.: 50%/30%/20%)
    AUTO_POST_ONLY_ENTRIES: bool = False         # Decisão automática maker/taker baseada no spread (se True, ignora USE_POST_ONLY_ENTRIES)
    AUTO_MAKER_SPREAD_BPS: float = 3.0           # Usar maker quando spread >= X bps (baseado em best bid/ask)
    HEADROOM_MIN_PCT: float = 35.0               # Headroom mínimo até o preço de liquidação (%). Se menor, reduzir posição.
    REDUCE_STEP_PCT: float = 10.0                # Percentual por etapa ao reduzir posição para atingir headroom mínimo
    ALLOW_RISK_BYPASS_FOR_FORCE: bool = True     # Permitir bypass do RiskManager quando o sinal vier com force=True

    # Derivatives-aware (funding / OI / taker imbalance)
    ENABLE_FUNDING_AWARE: bool = True            # Considerar funding no score/bloqueios
    FUNDING_ADVERSE_THRESHOLD: float = 0.0003    # 0.03% (valor absoluto) para considerar funding "alto"
    FUNDING_BLOCK_WINDOW_MINUTES: int = 20       # Bloquear entradas a X min do funding quando adverso
    OI_CHANGE_PERIOD: str = "5m"                 # Período para variação de Open Interest
    OI_CHANGE_LOOKBACK: int = 12                 # Quantidade de períodos (ex.: 12*5m ≈ 1h)
    OI_CHANGE_MIN_ABS: float = 0.5               # Mínimo absoluto (%) para considerar sinal de OI
    TAKER_RATIO_LONG_MIN: float = 1.02           # Requisito mínimo para LONG (predomínio de takers long)
    TAKER_RATIO_SHORT_MAX: float = 0.98          # Requisito máximo para SHORT (predomínio de takers short)
    
    # Market Scanner (cobertura de universo)
    SCANNER_TOP_N: int = 600                     # Top-N por volume (quoteVolume) para priorização
    SCANNER_MAX_SYMBOLS: int = 160               # Limite de símbolos processados por ciclo (performance)
    SCANNER_TESTNET_STRICT_WHITELIST: bool = False # Se True, restringe ao whitelist no TESTNET
    MIN_QUOTE_VOLUME_USDT_24H: float = 1_000_000.0   # Liquidez mínima 24h reduzida para 1M (Sniper Mode)
    SCANNER_CONCURRENCY: int = 8                 # Paralelismo sugerido para chamadas de klines/validações
    TESTNET_WHITELIST: list[str] = [             # Whitelist padrão para TESTNET
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "DOGEUSDT","SOLUSDT","LTCUSDT","DOTUSDT","LINKUSDT","TRXUSDT","BCHUSDT"
    ]

    # ========================================
    # EXECUTION & RISK (v5.0)
    # ========================================
    
    # Smart DCA
    DCA_ENABLED: bool = True
    MAX_DCA_COUNT: int = 2
    DCA_THRESHOLD_PCT: float = -2.5  # Trigger DCA at -2.5% PnL
    DCA_MULTIPLIER: float = 1.5  # Buy 1.5x the current size
    
    # Time-Based Exit
    TIME_EXIT_HOURS: int = 6  # Close if held > 6h
    TIME_EXIT_MIN_PROFIT_PCT: float = 0.5  # And profit < 0.5% (stagnant)
    
    # Legacy settings (maintained for compatibility)
    PROD_MIN_SCORE: int = 50  # Reduzido para 50 (Aggressive Mode para gerar mais sinais)
    PROD_VOLUME_THRESHOLD: float = 0.3  # Reduzido para 0.3 (Permitir moedas com menos volume relativo)
    PROD_RSI_OVERSOLD: int = 30
    PROD_RSI_OVERBOUGHT: int = 70
    REQUIRE_TREND_CONFIRMATION: bool = True
    MIN_MOMENTUM_THRESHOLD_PCT: float = 0.3  # Mais exigente no momentum
    RR_MIN_TREND: float = 1.5  # R:R mínimo maior para trend
    RR_MIN_RANGE: float = 2.0  # R:R mínimo maior para range

    # Correlação
    CORR_WINDOW_DAYS: int = 14
    MAX_CORRELATION: float = 0.7 # Aumentado para permitir mais sinais correlacionados

    # Mercado (pump/dump e requisitos)
    PUMP_THRESHOLD_PCT: float = 40.0 # Aumentado para ser menos restritivo
    PUMP_TIMEFRAME_HOURS: int = 2
    PUMP_MIN_SUSTAINED_VOLUME_X: float = 2.0
    DUMP_THRESHOLD_PCT: float = 30.0 # Aumentado para ser menos restritivo
    DUMP_TIMEFRAME_HOURS: int = 2
    DUMP_MIN_SUSTAINED_VOLUME_X: float = 2.0
    REQUIRED_SCORE_SIDEWAYS: int = 80  # Mais exigente em lateralidade

    # Risco adicional
    DAILY_MAX_LOSS_PCT: float = 0.05
    INTRADAY_DRAWDOWN_HARD_STOP_PCT: float = 0.08

    # ========================================
    # SIGNAL GENERATOR - Advanced Filters (v5.0)
    # ========================================
    
    # ADX Trend Strength Filter
    ENABLE_ADX_FILTER: bool = True
    ADX_MIN_TREND_STRENGTH: float = 25.0  # Minimum ADX to consider trend strong enough
    
    # Auto-start do Bot
    AUTOSTART_BOT: bool = True
    BOT_DRY_RUN: bool = False
    BOT_MIN_SCORE: int = 50  # Reduzido para 50 (Aggressive Mode para gerar mais sinais)
    BOT_MAX_POSITIONS: int = 10  # Reduzido para 10 (foco em qualidade)
    BOT_SCAN_INTERVAL_MINUTES: int = 1

    # Positions Sync
    POSITIONS_AUTO_SYNC_ENABLED: bool = True
    POSITIONS_AUTO_SYNC_MINUTES: int = 10
    POSITIONS_AUTO_SYNC_STRICT: bool = False

    # Virtual Balance (opera "como se fosse" uma banca fixa)
    VIRTUAL_BALANCE_ENABLED: bool = False
    VIRTUAL_BALANCE_USDT: float = 300.0
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False
    
    class Config:
        # ✅ CORRIGIR: Detectar automaticamente o ambiente
        env_file = ".env.docker" if os.path.exists("/.dockerenv") else "../.env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variáveis extras

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Função para limpar cache (útil para testes)
def reload_settings():
    get_settings.cache_clear()
    return get_settings()
