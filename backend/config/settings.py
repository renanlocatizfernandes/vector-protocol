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
    API_AUTH_ENABLED: bool = False
    API_KEY: str = ""
    API_KEY_HEADER: str = "X-API-Key"
    
    # ============================================
    # BOT SETTINGS - OTIMIZADO PARA RECUPERAÇÃO (CONSERVADOR)
    # ============================================
    MAX_POSITIONS: int = 4  # Limite para 4 posições
    RISK_PER_TRADE: float = 0.014  # 1.4% por trade (reduzido 30% para liberar margem DCA)
    MAX_PORTFOLIO_RISK: float = 0.15  # 15% máximo em risco
    MAX_TOTAL_CAPITAL_USAGE: float = 0.90  # Fraction of total capital available
    DCA_RESERVE_PCT: float = 0.20  # Reservar 20% do capital para DCA
    REVERSAL_EXTRA_SLOTS_PCT: float = 0.5  # 50% de posições extras para reversão (Smart Reversal)
    MAX_MARGIN_USD_PER_POSITION: float = 5.0  # 🎯 Máximo de $5 de margem por posição
    DEFAULT_LEVERAGE: int = 10  # 10x padrão (reduz margem requerida 50%)
    # Risco e spread (afinamento fino)
    SNIPER_RISK_PER_TRADE: float = 0.02  # 2% por sniper
    MAX_SPREAD_PCT_CORE: float = 0.20 # Spread mais apertado
    MAX_SPREAD_PCT_SNIPER: float = 0.40  # 0.4% ideal para sniper

    # Sniper strategy (scalps rápidos) - AGRESSIVO
    SNIPER_EXTRA_SLOTS: int = 5  # 5 slots extras para sniper
    SNIPER_TP_PCT: float = 1.2  # Alvos um pouco maiores
    SNIPER_SL_PCT: float = 0.8  # Stops mais largos para evitar ruído
    SNIPER_DEFAULT_LEVERAGE: int = 5  # 5x para sniper (era 20x)
    SNIPER_LEVERAGE_MIN: int = 3
    SNIPER_LEVERAGE_MAX: int = 15
    SNIPER_SL_MIN_PCT: float = 0.4
    SNIPER_SL_MAX_PCT: float = 1.2
    SNIPER_TP_MIN_PCT: float = 0.8
    SNIPER_TP_MAX_PCT: float = 2.5
    SNIPER_SL_ATR_MULT: float = 1.0
    SNIPER_TP_ATR_MULT: float = 2.0
    SNIPER_MIN_RR: float = 1.5
    SNIPER_IGNORE_WHITELIST: bool = True

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
    USE_ALGO_STOP_ORDERS: bool = True            # Usar Algo Order API para Stop Loss
    ALGO_STOP_FALLBACK_TO_STANDARD: bool = True  # Fallback para endpoint padrao se algo falhar
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
    SCANNER_TOP_N: int = 800                     # Top-N por volume (quoteVolume) para priorização
    SCANNER_MAX_SYMBOLS: int = 80                # Limite de simbolos processados por ciclo (performance)
    SCANNER_STRICT_WHITELIST: bool = False       # Se True, restringe ao whitelist em qualquer ambiente
    SCANNER_TESTNET_STRICT_WHITELIST: bool = False # Se True, restringe ao whitelist no TESTNET
    SCANNER_MIN_VOLUME_24H: float = 20_000_000.0   # Liquidez minima 24h para scanner
    MIN_QUOTE_VOLUME_USDT_24H: float = 500_000.0   # Legacy - fallback
    SCANNER_CONCURRENCY: int = 8                 # Paralelismo sugerido para chamadas de klines/validações
    SYMBOL_WHITELIST: list[str] = [              # Whitelist principal (prod/testnet)
        # ❌ REMOVED: "HYPERUSDT", "TURBOUSDT", "BANANAUSDT" - Massive losses (77% loss rate, -8k USDT)
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "PENDLEUSDT", "TAOUSDT", "SUIUSDT", "FETUSDT", "LINKUSDT",
        # ✅ PROVEN WINNERS (100% win rate):
        "TRXUSDT", "JSTUSDT", "RENDERUSDT", "1000PEPEUSDT", "1000BONKUSDT", "STXUSDT"
    ]
    TESTNET_WHITELIST: list[str] = [             # Whitelist padrão para TESTNET
        "BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT",
        "DOGEUSDT","SOLUSDT","LTCUSDT","DOTUSDT","LINKUSDT","TRXUSDT","BCHUSDT"
    ]

    # ========================================
    # EXECUTION & RISK (v5.0)
    # ========================================
    
    # Smart DCA - Multi-Level (Melhoria #3)
    DCA_ENABLED: bool = True
    MAX_DCA_COUNT: int = 3  # 3 níveis de DCA
    # DCA Multi-Nível: Níveis progressivos de averaging
    DCA_LEVEL_1_THRESHOLD_PCT: float = -3.0  # 1º DCA aos -3%
    DCA_LEVEL_1_SIZE_PCT: float = 0.30  # Adicionar 30% da posição original
    DCA_LEVEL_2_THRESHOLD_PCT: float = -6.0  # 2º DCA aos -6%
    DCA_LEVEL_2_SIZE_PCT: float = 0.40  # Adicionar 40% da posição original
    DCA_LEVEL_3_THRESHOLD_PCT: float = -10.0  # 3º DCA aos -10%
    DCA_LEVEL_3_SIZE_PCT: float = 0.30  # Adicionar 30% da posição original
    # Legacy (manter compatibilidade)
    DCA_THRESHOLD_PCT: float = -3.0  # Fallback para código antigo
    DCA_MULTIPLIER: float = 1.3  # Fallback
    
    # Time-Based Exit (Melhoria #10)
    TIME_EXIT_ENABLED: bool = True
    TIME_EXIT_HOURS: int = 4  # Fechar se aberta > 4h
    TIME_EXIT_MIN_PNL_PCT: float = -0.8  # P&L minimo para exit: -0.8%
    TIME_EXIT_MAX_PNL_PCT: float = -2.0  # P&L maximo para exit: -2.0%
    TIME_EXIT_REQUIRE_TREND_AGAINST: bool = True
    TIME_EXIT_MIN_VOLUME_RATIO: float = 0.8
    TIME_EXIT_MIN_PROFIT_PCT: float = 0.3  # Legacy

    # Take Profit Ladder (Melhoria #4)
    TP_LADDER_ENABLED: bool = True
    TP_LADDER_LEVEL_1_PCT: float = 20.0  # 1º TP aos +20%
    TP_LADDER_LEVEL_1_SIZE: float = 0.30  # Realizar 30% da posição
    TP_LADDER_LEVEL_2_PCT: float = 40.0  # 2º TP aos +40%
    TP_LADDER_LEVEL_2_SIZE: float = 0.30  # Realizar mais 30%
    TP_LADDER_LEVEL_3_PCT: float = 60.0  # 3º TP aos +60%
    TP_LADDER_LEVEL_3_SIZE: float = 0.40  # Realizar 40% restante

    # Breakeven Rápido (Melhoria #6)
    BREAKEVEN_ENABLED: bool = True
    BREAKEVEN_THRESHOLD_PCT: float = 8.0  # Mover SL para breakeven aos +8% (era +15%)

    # Trailing Stop ATR-Based (Melhoria #5)
    TRAILING_STOP_ATR_ENABLED: bool = True
    TRAILING_STOP_ACTIVATION_PCT: float = 15.0  # Ativar trailing aos +15%
    TRAILING_STOP_ATR_MULTIPLIER: float = 2.0  # Callback = 2x ATR(14)
    TRAILING_STOP_MIN_CALLBACK_PCT: float = 0.5  # Mínimo 0.5%
    TRAILING_STOP_MAX_CALLBACK_PCT: float = 3.0  # Máximo 3.0%
    
    # ✅ PASSO 1: PADRONIZAR MIN_SCORE EM TODOS OS MÓDULOS
    # Signal Generator Thresholds (Production-Quality)
    PROD_MIN_SCORE: int = 70  # High Quality (padronizado com BOT_MIN_SCORE)
    TESTNET_MIN_SCORE: int = 65  # Slightly relaxed para testnet
    PROD_VOLUME_THRESHOLD: float = 0.5  # 50% do volume médio de 20 períodos
    PROD_RSI_OVERSOLD: int = 30  # Oversold clássico
    PROD_RSI_OVERBOUGHT: int = 65  # Overbought mais agressivo para SHORTs (antes 70)
    REQUIRE_TREND_CONFIRMATION: bool = True  # Confirmação multi-timeframe (1h + 4h)
    SMART_REVERSAL_ENABLED: bool = True  # Habilita shorts contra tendência em condições extremas
    SMART_REVERSAL_RSI_THRESHOLD: int = 72  # RSI mínimo para Smart Reversal SHORT (mais agressivo)
    MIN_MOMENTUM_THRESHOLD_PCT: float = 0.2  # 0.2% momentum mínimo
    RR_MIN_TREND: float = 1.2  # R:R mínimo para trending market
    RR_MIN_RANGE: float = 1.6  # R:R mínimo para ranging market

    # Correlação
    CORR_WINDOW_DAYS: int = 14
    MAX_CORRELATION: float = 0.85

    # Mercado (pump/dump e requisitos)
    PUMP_THRESHOLD_PCT: float = 40.0
    PUMP_TIMEFRAME_HOURS: int = 2
    PUMP_MIN_SUSTAINED_VOLUME_X: float = 2.0
    DUMP_THRESHOLD_PCT: float = 30.0
    DUMP_TIMEFRAME_HOURS: int = 2
    DUMP_MIN_SUSTAINED_VOLUME_X: float = 2.0
    REQUIRED_SCORE_SIDEWAYS: int = 70  # Alinhado com ML min_score para consistência
    SIDEWAYS_MIN_VOLUME_RATIO: float = 0.3  # Permite trades com 30% do volume médio em sideways

    # ✅ PASSO 2: AJUSTAR HARD STOPS PARA CRYPTO-FRIENDLY
    # Crypto-friendly hard stops (volatilidade nativa do mercado)
    DAILY_MAX_LOSS_PCT: float = 0.08  # 8% máximo de perda/dia (antes 5%)
    INTRADAY_DRAWDOWN_HARD_STOP_PCT: float = 0.30  # 30% drawdown intraday (antes 25%)
    CIRCUIT_BREAKER_DAILY_LOSS_PCT: float = 8.0  # Parar se perder 8% do capital no dia (antes 5%)

    # Circuit Breaker (Melhoria #8/#14)
    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_DAILY_LOSS_PCT: float = 5.0  # Parar se perder 5% do capital no dia
    CIRCUIT_BREAKER_CONSECUTIVE_LOSSES: int = 3  # Parar após 3 stops consecutivos
    CIRCUIT_BREAKER_COOLDOWN_HOURS: int = 2  # Aguardar 2h antes de retomar
    CIRCUIT_BREAKER_RESET_UTC_HOUR: int = 0  # Reset automático às 00:00 UTC

    # Whitelist Dinâmica (Melhoria #7)
    DYNAMIC_WHITELIST_ENABLED: bool = True
    DYNAMIC_WHITELIST_MIN_VOLUME_24H: float = 500_000_000  # $500M volume mínimo
    DYNAMIC_WHITELIST_MIN_LIQUIDITY: float = 1_000_000  # $1M order book 5% depth
    DYNAMIC_WHITELIST_MAX_SPREAD_BPS: float = 10.0  # Max 10 bps spread
    DYNAMIC_WHITELIST_ALLOW_SCORE_100: bool = True  # Permitir top 3 sinais score 100/dia fora whitelist
    DYNAMIC_WHITELIST_MAX_SCORE_100_PER_DAY: int = 3  # Máximo 3 sinais score 100 fora whitelist/dia

    # Anti-Correlação (Melhoria #9)
    ANTI_CORRELATION_ENABLED: bool = True
    ANTI_CORRELATION_MAX_SAME_SECTOR: int = 2  # Máximo 2 posições do mesmo setor
    ANTI_CORRELATION_PRICE_THRESHOLD: float = 0.7  # Correlação de preço > 0.7 = setor correlacionado
    # Categorias de setores
    SECTOR_L1: list[str] = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT"]
    SECTOR_DEFI: list[str] = ["AAVEUSDT", "UNIUSDT", "CRVUSDT", "PENDLEUSDT", "LINKUSDT"]
    SECTOR_MEME: list[str] = ["1000PEPEUSDT", "1000BONKUSDT", "DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"]
    SECTOR_AI: list[str] = ["FETUSDT", "RENDERUSDT", "AGIXUSDT", "TAOUSDT"]

    # Hedge em Downturn (Melhoria #11)
    HEDGE_ENABLED: bool = True
    HEDGE_TRIGGER_NEGATIVE_PCT: float = 60.0  # Hedge quando >60% posições negativas
    HEDGE_SIZE_PCT: float = 30.0  # Hedge = 30% do valor total do portfólio
    HEDGE_SYMBOLS: list[str] = ["BTCUSDT", "ETHUSDT"]  # Símbolos para hedge SHORT
    HEDGE_EXIT_NEGATIVE_PCT: float = 40.0  # Fechar hedge quando <40% posições negativas

    # Stop Loss ATR Dinâmico (Melhoria #12)
    SL_ATR_ENABLED: bool = True
    SL_ATR_MULTIPLIER: float = 2.0  # SL = 2x ATR(14)
    SL_ATR_PERIOD: int = 14  # Período ATR
    SL_ATR_MIN_DISTANCE_PCT: float = 1.0  # Mínimo 1% de distância
    SL_ATR_MAX_DISTANCE_PCT: float = 8.0  # Máximo 8% de distância

    # Margem Híbrida (Melhoria #15)
    HYBRID_MARGIN_ENABLED: bool = True
    HYBRID_MARGIN_CROSS_MIN_SCORE: int = 85  # Usar margem cruzada para score >= 85
    HYBRID_MARGIN_ISOLATED_MAX_SCORE: int = 84  # Usar margem isolada para score <= 84

    # Priorização por Score (Melhoria #8)
    SCORE_PRIORITY_ENABLED: bool = True
    SCORE_PRIORITY_MIN_REPLACEMENT: int = 75  # Score 100 pode substituir posições score < 75
    SCORE_PRIORITY_MAX_LOSS_PCT: float = -2.0  # Somente se P&L < -2%

    # ========================================
    # SIGNAL GENERATOR - Advanced Filters (v5.0)
    # ========================================
    
    # ADX Trend Strength Filter
    ENABLE_ADX_FILTER: bool = False
    ADX_MIN_TREND_STRENGTH: float = 10.0
    
    # Auto-start do Bot - AGRESSIVO
    AUTOSTART_BOT: bool = False
    BOT_DRY_RUN: bool = True
    BOT_MIN_SCORE: int = 70  # Alta qualidade apenas (era 55)
    BOT_MAX_POSITIONS: int = 4  # Até 4 posições
    BOT_SCAN_INTERVAL_MINUTES: int = 1

    # Positions Sync
    POSITIONS_AUTO_SYNC_ENABLED: bool = True
    POSITIONS_AUTO_SYNC_MINUTES: int = 10
    POSITIONS_AUTO_SYNC_STRICT: bool = False

    # Rate Limiting (evitar ban da Binance)
    POSITION_MONITOR_INTERVAL_SEC: int = 15  # Intervalo de monitoramento (era 6s)
    API_MAX_REQUESTS_PER_MINUTE: int = 800  # Limite seguro (Binance permite 1200)
    PRICE_CACHE_TTL_SEC: int = 5  # Cache de preços (era 2s)

    # Virtual Balance (opera "como se fosse" uma banca fixa)
    VIRTUAL_BALANCE_ENABLED: bool = False
    VIRTUAL_BALANCE_USDT: float = 100.0
    
    # Cache Settings (Redis)
    CACHE_ENABLED: bool = True  # Habilitar cache para reduzir chamadas à API
    CACHE_ACCOUNT_TTL: int = 10  # Saldo: 10s
    CACHE_POSITIONS_TTL: int = 5  # Posições: 5s
    CACHE_SYMBOL_INFO_TTL: int = 3600  # Info de símbolos: 1h
    CACHE_MARKET_DATA_TTL: int = 2  # Preços: 2s
    CACHE_KLINES_TTL: int = 30  # Klines: 30s
    
    # ✅ PASSO 3: CONNECTION POOLING PARA BINANCE API
    # Configurações de otimização de conexões HTTP
    BINANCE_MAX_CONNECTIONS: int = 100  # Máximo de conexões simultâneas
    BINANCE_MAX_KEEPALIVE: int = 20  # Conexões keep-alive no pool
    BINANCE_CONNECTION_TIMEOUT: int = 10  # Timeout de conexão (segundos)
    BINANCE_READ_TIMEOUT: int = 30  # Timeout de leitura (segundos)
    BINANCE_REQUEST_TIMEOUT: int = 60  # Timeout total da requisição (segundos)
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False

    # PnL Divergence Guard
    PNL_DIVERGENCE_BLOCK_ENABLED: bool = False  # Desabilitado temporariamente - reconciliar DB manualmente
    PNL_DIVERGENCE_THRESHOLD_PCT: float = 50.0  # Aumentado para evitar bloqueios frequentes

    # ========================================
    # PROFIT OPTIMIZATION - Advanced Market Intelligence
    # ========================================

    # Top Trader Sentiment
    ENABLE_TOP_TRADER_FILTER: bool = True
    TOP_TRADER_MIN_BULLISH_RATIO: float = 1.15  # >1.15 = strong bullish
    TOP_TRADER_MAX_BEARISH_RATIO: float = 0.85  # <0.85 = strong bearish
    TOP_TRADER_SCORE_BONUS: int = 15

    # Liquidation Detection
    ENABLE_LIQUIDATION_ZONES: bool = True
    LIQUIDATION_ZONE_LOOKBACK_HOURS: int = 24
    LIQUIDATION_ZONE_PROXIMITY_PCT: float = 2.0  # Within 2% = bonus
    LIQUIDATION_ZONE_SCORE_BONUS: int = 15

    # Funding Rate Intelligence
    FUNDING_HISTORY_PERIODS: int = 24  # Last 24 periods = 7 days
    FUNDING_EXTREME_THRESHOLD: float = 0.001  # 0.1% = extreme
    FUNDING_BLOCK_THRESHOLD: float = 0.0008  # Block if > 0.08%
    FUNDING_EXIT_THRESHOLD: float = 0.0008  # Exit before funding if > 0.08%
    FUNDING_EXIT_MIN_PROFIT: float = 0.5  # Min profit % to exit for funding

    # OI-Price Correlation
    ENABLE_OI_CORRELATION: bool = True
    OI_CORRELATION_MIN_CHANGE: float = 3.0  # Min 3% OI change
    OI_STRONG_SIGNAL_BONUS: int = 10

    # Order Book Depth
    ENABLE_ORDER_BOOK_FILTER: bool = True
    MIN_LIQUIDITY_DEPTH_USDT: float = 100000.0  # $100k within 5%
    ORDER_BOOK_DEPTH_LEVELS: int = 100
    ORDER_BOOK_BLOCK_INVALID: bool = True
    ORDER_BOOK_BLOCK_LOW_LIQUIDITY: bool = True

    # Mark-Last Deviation
    MARK_LAST_WARNING_PCT: float = 0.5
    MARK_LAST_CRITICAL_PCT: float = 1.0

    # ========================================
    # PROFIT OPTIMIZATION - Fee & Breakeven Tracking
    # ========================================

    # Fee-Aware Trading
    TRACK_FEES_PER_TRADE: bool = True
    ESTIMATE_TAKER_FEE: float = 0.0005  # 0.05% Binance taker default
    ESTIMATE_MAKER_FEE: float = 0.0002  # 0.02% Binance maker default
    USE_REAL_FEES_FROM_API: bool = True  # Fetch real fees from Binance API (every 5 min)

    # Breakeven Stop
    ENABLE_BREAKEVEN_STOP: bool = True
    BREAKEVEN_ACTIVATION_PCT: float = 2.0  # Activate at +2% profit

    # Dynamic Take Profit
    ENABLE_DYNAMIC_TP: bool = True
    TP_MOMENTUM_RSI_THRESHOLD: float = 65.0  # RSI > 65 for extension
    TP_MOMENTUM_VOLUME_THRESHOLD: float = 1.5  # Volume > 1.5x avg
    TP_FIBONACCI_EXTENSIONS: list[float] = [1.618, 2.618, 4.236]

    # Funding-Aware Exits
    ENABLE_FUNDING_EXITS: bool = True
    FUNDING_EXIT_TIME_WINDOW_MIN: int = 30  # Exit 30min before

    # ========================================
    # PROFIT OPTIMIZATION - Feature Flags
    # ========================================

    ENABLE_MARKET_INTELLIGENCE: bool = True  # Master switch for all MI features
    ENABLE_PROFIT_OPTIMIZER: bool = True      # Master switch for profit optimization

    # ========================================
    # TRADING RULES - Phase 3
    # ========================================

    ENABLE_DB_RULES: bool = False  # Use database-based trading rules (whitelist, sniper, risk)

    class Config:
        # ✅ CORRIGIR: Detectar automaticamente o ambiente
        # Tenta achar .env no root do repo
        try:
            _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            _env_path = os.path.join(_root, ".env")
        except:
            _env_path = ".env"
        
        env_file = ".env.docker" if os.path.exists("/.dockerenv") else _env_path
        case_sensitive = True
        extra = "ignore"  # Ignorar variáveis extras

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Função para limpar cache (útil para testes)
def reload_settings():
    get_settings.cache_clear()
    return get_settings()
