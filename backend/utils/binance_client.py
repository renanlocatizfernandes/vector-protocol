from binance.client import Client
from binance.exceptions import BinanceAPIException
from config.settings import get_settings
from utils.logger import setup_logger
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
import asyncio
import contextlib
from binance.streams import ThreadedWebsocketManager
import json
import websockets
import redis.asyncio as redis
from urllib3.util.retry import Retry
from urllib3 import PoolManager
from datetime import datetime

logger = setup_logger("binance_client")

# ✅ PR1.2: Validação de Consistência de Dados

class DataValidationError(Exception):
    """Exceção para erros de validação de dados"""
    def __init__(self, field: str, reason: str, data: Any = None):
        self.field = field
        self.reason = reason
        self.data = data
        super().__init__(f"Validação falhou em '{field}': {reason}")

class DataValidator:
    """Validador de dados para respostas da API Binance"""
    
    # Campos obrigatórios por endpoint
    REQUIRED_FIELDS = {
        'futures_account': ['totalWalletBalance', 'availableBalance', 'positions'],
        'futures_symbol_ticker': ['symbol', 'price'],
        'futures_exchange_info': ['symbols'],
        'futures_position_information': ['symbol', 'positionAmt', 'entryPrice'],
        'futures_get_order': ['symbol', 'orderId', 'status'],
    }
    
    # Tipos esperados para campos críticos
    FIELD_TYPES = {
        'totalWalletBalance': (int, float, str),
        'availableBalance': (int, float, str),
        'price': (int, float, str),
        'quantity': (int, float, str),
        'positionAmt': (int, float, str),
        'entryPrice': (int, float, str),
        'liquidationPrice': (int, float, str),
        'unRealizedProfit': (int, float, str),
        'avgPrice': (int, float, str),
        'executedQty': (int, float, str),
        'cumQuote': (int, float, str),
    }
    
    # Valores que indicam dados inválidos
    INVALID_VALUES = [None, '', 'NaN', 'Infinity', '-Infinity', 'null', 'undefined']
    
    @staticmethod
    def validate_required_fields(endpoint: str, data: Dict) -> Tuple[bool, List[str]]:
        """
        Valida se campos obrigatórios estão presentes e não vazios
        
        Args:
            endpoint: Nome do método da API
            data: Dados recebidos
            
        Returns:
            (valid, missing_fields)
        """
        if not isinstance(data, dict):
            return False, ['response_is_not_dict']
        
        required = DataValidator.REQUIRED_FIELDS.get(endpoint, [])
        missing = []
        
        for field in required:
            if field not in data:
                missing.append(field)
            elif DataValidator._is_invalid_value(data[field]):
                missing.append(f"{field}_invalid")
        
        if missing:
            logger.warning(f"⚠️ Validação {endpoint}: campos faltando/inválidos: {missing}")
        
        return len(missing) == 0, missing
    
    @staticmethod
    def validate_field_types(data: Dict, fields_to_check: Optional[Set[str]] = None) -> Tuple[bool, List[str]]:
        """
        Valida se campos têm tipos esperados (para conversão segura)
        
        Args:
            data: Dados recebidos
            fields_to_check: Conjunto específico de campos para validar (None = todos)
            
        Returns:
            (valid, invalid_fields)
        """
        if not isinstance(data, dict):
            return False, ['data_is_not_dict']
        
        fields = fields_to_check if fields_to_check is not None else DataValidator.FIELD_TYPES.keys()
        invalid = []
        
        for field in fields:
            if field not in data:
                continue
                
            value = data[field]
            expected_types = DataValidator.FIELD_TYPES.get(field)
            
            if expected_types and not isinstance(value, expected_types):
                # Verificar se pode ser convertido para float
                if not DataValidator._can_convert_to_float(value):
                    invalid.append(f"{field}_type_{type(value).__name__}")
        
        if invalid:
            logger.warning(f"⚠️ Validação de tipos: campos com tipo incorreto: {invalid}")
        
        return len(invalid) == 0, invalid
    
    @staticmethod
    def validate_numeric_range(data: Dict, field: str, min_val: Optional[float] = None, max_val: Optional[float] = None) -> bool:
        """
        Valida se campo numérico está dentro de range esperado
        
        Args:
            data: Dados recebidos
            field: Campo para validar
            min_val: Valor mínimo (None = não validar)
            max_val: Valor máximo (None = não validar)
            
        Returns:
            True se válido
        """
        if field not in data:
            return True  # Não validar se campo não existe
        
        value = DataValidator._safe_float(data[field])
        if value is None:
            return False
        
        if min_val is not None and value < min_val:
            logger.warning(f"⚠️ Valor {field}={value} abaixo do mínimo {min_val}")
            return False
        
        if max_val is not None and value > max_val:
            logger.warning(f"⚠️ Valor {field}={value} acima do máximo {max_val}")
            return False
        
        return True
    
    @staticmethod
    def validate_api_response(endpoint: str, data: Dict) -> Tuple[bool, Optional[DataValidationError]]:
        """
        Validação completa de resposta da API
        
        Args:
            endpoint: Nome do método da API
            data: Dados recebidos
            
        Returns:
            (is_valid, error) - error=None se válido
        """
        # 1. Validar campos obrigatórios
        required_valid, missing = DataValidator.validate_required_fields(endpoint, data)
        if not required_valid:
            return False, DataValidationError(
                f"{endpoint}_required_fields",
                f"Campos obrigatórios faltando: {missing}",
                data
            )
        
        # 2. Validar tipos de campos críticos
        types_valid, invalid_types = DataValidator.validate_field_types(data)
        if not types_valid:
            return False, DataValidationError(
                f"{endpoint}_field_types",
                f"Campos com tipos incorretos: {invalid_types}",
                data
            )
        
        # 3. Validações específicas por endpoint
        if endpoint == 'futures_account':
            # Saldo não pode ser negativo
            if not DataValidator.validate_numeric_range(data, 'totalWalletBalance', min_val=0):
                return False, DataValidationError(
                    'futures_account_negative_balance',
                    'Saldo total negativo',
                    data.get('totalWalletBalance')
                )
        
        elif endpoint == 'futures_symbol_ticker':
            # Preço deve ser positivo
            if not DataValidator.validate_numeric_range(data, 'price', min_val=0):
                return False, DataValidationError(
                    'futures_symbol_ticker_invalid_price',
                    'Preço inválido (não positivo)',
                    data.get('price')
                )
        
        return True, None
    
    @staticmethod
    def compare_cache_vs_api(cache_key: str, cached_value: Any, api_value: Any, tolerance_pct: float = 5.0) -> bool:
        """
        Compara valor em cache vs valor da API para detectar divergências
        
        Args:
            cache_key: Chave do cache
            cached_value: Valor armazenado em cache
            api_value: Valor retornado pela API
            tolerance_pct: Tolerância percentual para comparações numéricas
            
        Returns:
            True se valores são consistentes dentro da tolerância
        """
        # Ambos None ou vazios = consistente
        if not cached_value and not api_value:
            return True
        
        # Um valor, outro None = divergência
        if bool(cached_value) != bool(api_value):
            logger.warning(f"⚠️ Divergência cache/API [{cache_key}]: cache={cached_value}, api={api_value}")
            return False
        
        # Tentar comparação numérica
        try:
            cached_num = float(cached_value)
            api_num = float(api_value)
            
            if cached_num == 0 and api_num == 0:
                return True
            
            # Calcular diferença percentual
            pct_diff = abs(cached_num - api_num) / max(abs(api_num), 0.0001) * 100
            
            if pct_diff > tolerance_pct:
                logger.warning(
                    f"⚠️ Divergência significativa [{cache_key}]: "
                    f"cache={cached_num}, api={api_num}, diff={pct_diff:.2f}%"
                )
                return False
            
            return True
            
        except (ValueError, TypeError):
            # Comparação string
            if cached_value != api_value:
                logger.warning(
                    f"⚠️ Divergência string [{cache_key}]: cache={cached_value}, api={api_value}"
                )
                return False
            
            return True
    
    @staticmethod
    def _is_invalid_value(value: Any) -> bool:
        """Verifica se valor é inválido (null, empty, NaN, etc.)"""
        if value in DataValidator.INVALID_VALUES:
            return True
        
        # Verificar string
        if isinstance(value, str) and not value.strip():
            return True
        
        return False
    
    @staticmethod
    def _can_convert_to_float(value: Any) -> bool:
        """Verifica se valor pode ser convertido para float"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Converte valor para float de forma segura, retorna None se falhar"""
        try:
            result = float(value)
            # Verificar se não é NaN ou Infinity
            if result != result or result == float('inf') or result == float('-inf'):
                return None
            return result
        except (ValueError, TypeError):
            return None

class BinanceClientManager:
    def __init__(self):
        # ✅ PR1.2: Inicializar validador de dados
        self.data_validator = DataValidator()
        
        # Estatísticas de validação
        self.validation_stats = {
            'total_validations': 0,
            'validation_errors': 0,
            'cache_divergences': 0,
            'last_validation_time': None
        }
        settings = get_settings()
        self.settings = settings
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        self.testnet = settings.BINANCE_TESTNET
        
        # Redis Cache Connection
        try:
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True
            )
            self.cache_enabled = getattr(settings, 'CACHE_ENABLED', True)
            logger.info(f"Redis cache inicializado (enabled={self.cache_enabled})")
        except Exception as e:
            logger.warning(f"Redis não disponível, cache desabilitado: {e}")
            self.redis = None
            self.cache_enabled = False
        
        # Estado do User Data Stream
        self._twm: Optional[ThreadedWebsocketManager] = None
        self._listen_key: Optional[str] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._user_stream_running: bool = False
        self._last_user_event_at: Optional[str] = None
        self._ws_task: Optional[asyncio.Task] = None
        # contador simples para logar primeiras mensagens cruas do WS
        self._ws_msg_count: int = 0
        
        # Estado do Market Stream
        self._market_stream_running: bool = False
        self._market_ws_task: Optional[asyncio.Task] = None
        # Position mode cache (False = One-Way, True = Hedge)
        self._dual_side_mode: Optional[bool] = None
        
        # ✅ PASSO 3: CONNECTION POOLING PARA BINANCE API
        # Criar PoolManager otimizado para múltiplas conexões simultâneas
        try:
            self.http_pool = PoolManager(
                num_pools=getattr(settings, "BINANCE_MAX_KEEPALIVE", 20),
                maxsize=getattr(settings, "BINANCE_MAX_CONNECTIONS", 100),
                timeout=getattr(settings, "BINANCE_CONNECTION_TIMEOUT", 10),
                retries=Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[502, 503, 504]
                )
            )
            logger.info(f"✅ HTTP Pool criado: maxsize={self.http_pool.poolmanager.maxsize}")
        except Exception as e:
            logger.warning(f"Pool de conexões não disponível: {e}")
            self.http_pool = None
        
        # Inicializar cliente Binance
        try:
            if self.testnet:
                self.client = Client(
                    self.api_key,
                    self.api_secret,
                    testnet=True
                )
                # URL CORRETA do testnet para futuros (com HTTPS)
                self.client.FUTURES_URL = 'https://testnet.binancefuture.com'
                self.client.FUTURES_STREAM_URL = 'wss://testnet.binancefuture.com'
                
                # ✅ PASSO 3: Injetar pool de conexões no cliente
                if self.http_pool:
                    try:
                        self.client.session.mount('https://', self.http_pool)
                        self.client.session.mount('http://', self.http_pool)
                        logger.info("✅ Connection pool injetado no cliente Binance TESTNET")
                    except Exception as e:
                        logger.warning(f"Pool não injetado: {e}")
                
                logger.info("Cliente Binance inicializado no TESTNET (HTTPS)")
            else:
                self.client = Client(self.api_key, self.api_secret)
                
                # ✅ PASSO 3: Injetar pool de conexões no cliente
                if self.http_pool:
                    try:
                        self.client.session.mount('https://', self.http_pool)
                        self.client.session.mount('http://', self.http_pool)
                        logger.info("✅ Connection pool injetado no cliente Binance PRODUÇÃO")
                    except Exception as e:
                        logger.warning(f"Pool não injetado: {e}")
                
                logger.info("Cliente Binance inicializado em PRODUÇÃO")
        except Exception as e:
            logger.error(f"Falha ao inicializar cliente Binance (provavelmente erro de rede ou região): {e}")
            self.client = None

    async def _cached_call(
        self,
        cache_key: str,
        ttl: int,
        fetch_fn: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Generic caching wrapper for API calls.
        Checks Redis cache first, falls back to API call if miss.
        """
        if not self.cache_enabled or not self.redis:
            return await fetch_fn(*args, **kwargs)
        
        try:
            # Try cache first
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"✅ Cache HIT: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error for {cache_key}: {e}")
        
        # Cache miss - fetch from API
        logger.debug(f"❌ Cache MISS: {cache_key}")
        result = await fetch_fn(*args, **kwargs)
        
        # Store in cache
        if result is not None:
            try:
                await self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, default=str)
                )
                logger.debug(f"💾 Cached: {cache_key} (TTL={ttl}s)")
            except Exception as e:
                logger.warning(f"Cache write error for {cache_key}: {e}")
        
        return result
    
    async def invalidate_cache(self, pattern: str):
        """
        Invalidate cache keys matching pattern.
        Example: invalidate_cache('binance:account:*')
        """
        if not self.cache_enabled or not self.redis:
            return
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"🗑️ Invalidated {len(keys)} cache keys: {pattern}")
        except Exception as e:
            logger.warning(f"Cache invalidation error for {pattern}: {e}")
    
    async def _retry_call(self, fn, *args, attempts: int = 3, base_sleep: float = 1.0, **kwargs):
        """
        Executa chamada do client em thread (não bloqueia o event loop) com retries exponenciais (1s, 2s, 4s).
        Retorna o resultado ou relança a última exceção.
        """
        for attempt in range(attempts):
            try:
                if not self.client:
                    raise BinanceAPIException(None, 0, "Client not initialized (network/region error)")
                # Executar a função síncrona do python-binance em thread para não bloquear o loop
                return await asyncio.to_thread(fn, *args, **kwargs)
            except BinanceAPIException as e:
                # ✅ NOVO: Não tentar novamente se for erro fatal (Ban ou Config)
                if e.code in (-1003, -4061):
                    logger.error(f"❌ Erro FATAL da Binance ({e.code}): {e.message} - Abortando retries.")
                    raise
                
                logger.warning(f"Retry Binance API ({attempt+1}/{attempts}) - {e}")
                if attempt < attempts - 1:
                    await asyncio.sleep(base_sleep * (2 ** attempt))
                else:
                    raise
            except Exception as e:
                logger.warning(f"Retry Binance genérico ({attempt+1}/{attempts}) - {e}")
                if attempt < attempts - 1:
                    await asyncio.sleep(base_sleep * (2 ** attempt))
                else:
                    raise

    async def get_account_balance(self):
        """Retorna saldo da conta de futuros com retries, cache (10s TTL) e validação de dados"""
        cache_key = "binance:account:balance"
        
        async def _fetch():
            try:
                # ✅ PR1.2: Obter valor em cache para comparação de divergência
                cached_value = None
                if self.cache_enabled and self.redis:
                    try:
                        cached_str = await self.redis.get(cache_key)
                        if cached_str:
                            cached_value = json.loads(cached_str)
                    except Exception:
                        pass
                
                account = await self._retry_call(self.client.futures_account)
                
                # ✅ PR1.2: Validar resposta da API
                self.validation_stats['total_validations'] += 1
                self.validation_stats['last_validation_time'] = datetime.utcnow().isoformat()
                
                is_valid, validation_error = self.data_validator.validate_api_response(
                    'futures_account', account
                )
                
                if not is_valid:
                    self.validation_stats['validation_errors'] += 1
                    logger.error(f"❌ Validação falhou em get_account_balance: {validation_error.reason}")
                    # Continuar mesmo com erro (fail-soft)
                
                total_balance = float(account['totalWalletBalance'])
                available_balance = float(account['availableBalance'])

                # ✅ PR1.2: Comparar cache vs API
                if cached_value and 'total_balance' in cached_value:
                    cache_total = float(cached_value['total_balance'])
                    if not self.data_validator.compare_cache_vs_api(
                        cache_key,
                        cache_total,
                        total_balance,
                        tolerance_pct=5.0
                    ):
                        self.validation_stats['cache_divergences'] += 1
                        # Invalidar cache se divergência significativa
                        await self.invalidate_cache(cache_key)

                logger.debug(f"Saldo Total: {total_balance} USDT")
                logger.debug(f"Saldo Disponivel: {available_balance} USDT")

                return {
                    "total_balance": total_balance,
                    "available_balance": available_balance,
                    "positions": account.get('positions', [])
                }
            except BinanceAPIException as e:
                logger.error(f"Erro ao obter saldo (após retries): {e}")
                return None
            except Exception as e:
                logger.error(f"Erro inesperado ao obter saldo: {e}")
                return None
        
        return await self._cached_call(cache_key, ttl=10, fetch_fn=_fetch)
    
    async def get_symbol_price(self, symbol: str):
        """Retorna preço atual de um símbolo com retries, cache (2s TTL) e validação de dados"""
        cache_key = f"binance:price:{symbol}"
        
        async def _fetch():
            try:
                # ✅ PR1.2: Obter valor em cache para comparação de divergência
                cached_value = None
                if self.cache_enabled and self.redis:
                    try:
                        cached_str = await self.redis.get(cache_key)
                        if cached_str:
                            cached_value = json.loads(cached_str)
                    except Exception:
                        pass
                
                ticker = await self._retry_call(self.client.futures_symbol_ticker, symbol=symbol)
                
                # ✅ PR1.2: Validar resposta da API
                self.validation_stats['total_validations'] += 1
                
                is_valid, validation_error = self.data_validator.validate_api_response(
                    'futures_symbol_ticker', ticker
                )
                
                if not is_valid:
                    self.validation_stats['validation_errors'] += 1
                    logger.warning(f"⚠️ Validação falhou em get_symbol_price({symbol}): {validation_error.reason}")
                
                price = float(ticker['price'])
                
                # ✅ PR1.2: Validar range de preço (não pode ser negativo ou extremamente baixo)
                if not self.data_validator.validate_numeric_range(ticker, 'price', min_val=0.000001):
                    logger.error(f"❌ Preço inválido para {symbol}: {price}")
                    return None
                
                # ✅ PR1.2: Comparar cache vs API
                if cached_value is not None:
                    cached_price = float(cached_value)
                    if not self.data_validator.compare_cache_vs_api(
                        cache_key,
                        cached_price,
                        price,
                        tolerance_pct=2.0  # 2% tolerância para preço
                    ):
                        self.validation_stats['cache_divergences'] += 1
                
                logger.debug(f"Preco de {symbol}: {price}")
                return price
            except BinanceAPIException as e:
                logger.error(f"Erro ao obter preço de {symbol} (após retries): {e}")
                return None
            except Exception as e:
                logger.error(f"Erro inesperado ao obter preço de {symbol}: {e}")
                return None
        
        return await self._cached_call(cache_key, ttl=2, fetch_fn=_fetch)
    
    async def get_top_futures_symbols(self, limit: int = 100):
        """Retorna os top N símbolos de futuros por volume com retries"""
        try:
            tickers = await self._retry_call(self.client.futures_ticker)

            # Filtrar apenas USDT pairs
            usdt_tickers = [t for t in tickers if t.get('symbol', '').endswith('USDT')]

            # Ordenar por volume
            sorted_tickers = sorted(
                usdt_tickers,
                key=lambda x: float(x.get('quoteVolume', 0) or 0),
                reverse=True
            )

            # Retornar top N
            top_symbols = sorted_tickers[:limit]

            logger.info(f"Top {limit} símbolos obtidos")
            return top_symbols
        except BinanceAPIException as e:
            logger.error(f"Erro ao obter top símbolos (após retries): {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao obter top símbolos: {e}")
            return []
    
    async def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100):
        """Retorna dados de candlestick com retries"""
        try:
            klines = await self._retry_call(
                self.client.futures_klines,
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            logger.info(f"Klines de {symbol} obtidos: {len(klines)} candles")
            return klines
        except BinanceAPIException as e:
            logger.error(f"Erro ao obter klines de {symbol} (após retries): {e}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao obter klines de {symbol}: {e}")
            return []
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Retorna informações de precisão e filtros do símbolo com retries e cache (1h TTL)"""
        cache_key = f"binance:symbol_info:{symbol}"
        
        async def _fetch():
            try:
                exchange_info = await self._retry_call(self.client.futures_exchange_info)

                for s in exchange_info.get('symbols', []):
                    if s.get('symbol') == symbol:
                        # Encontrar precisão de quantidade e preço
                        quantity_precision = s.get('quantityPrecision')
                        price_precision = s.get('pricePrecision')

                        # Encontrar filtros LOT_SIZE e PRICE_FILTER
                        lot_size_filter = next((f for f in s.get('filters', []) if f.get('filterType') == 'LOT_SIZE'), {})
                        price_filter = next((f for f in s.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), {})

                        min_qty = float(lot_size_filter.get('minQty', 0) or 0)
                        max_qty = float(lot_size_filter.get('maxQty', 999999) or 999999)
                        step_size = float(lot_size_filter.get('stepSize', 0) or 0)

                        min_price = float(price_filter.get('minPrice', 0) or 0)
                        tick_size = float(price_filter.get('tickSize', 0) or 0)
                        min_notional_filter = next((f for f in s.get('filters', []) if f.get('filterType') == 'MIN_NOTIONAL'), {})
                        min_notional = float(min_notional_filter.get('notional', 0) or 0)

                        logger.info(f"Info de {symbol}: qty_precision={quantity_precision}, step_size={step_size}")

                        return {
                            'symbol': symbol,
                            'quantity_precision': quantity_precision,
                            'price_precision': price_precision,
                            'min_quantity': min_qty,
                            'max_quantity': max_qty,
                            'step_size': step_size,
                            'min_price': min_price,
                            'tick_size': tick_size,
                            'min_notional': min_notional
                        }

                logger.error(f"Símbolo {symbol} não encontrado")
                return None

            except BinanceAPIException as e:
                logger.error(f"Erro ao obter info do símbolo {symbol} (após retries): {e}")
                return None
            except Exception as e:
                logger.error(f"Erro inesperado ao obter info do símbolo {symbol}: {e}")
                return None
        
        return await self._cached_call(cache_key, ttl=3600, fetch_fn=_fetch)

    async def get_positions_margin_modes(self) -> List[Dict]:
        """
        Retorna posições vivas com indicação do modo de margem (CROSSED/ISOLATED) por símbolo.
        Usa futures_account (já empregado no projeto) e deduz pelo campo 'isolated' ou 'marginType'.
        Cache de 5s para reduzir chamadas frequentes.
        """
        cache_key = "binance:positions:margin_modes"
        
        async def _fetch():
            try:
                account = await self._retry_call(self.client.futures_account)
                positions = account.get("positions", []) or []
                items: List[Dict] = []

                for p in positions:
                    sym = p.get("symbol")
                    if not sym:
                        continue

                    # Quantidade líquida (posição viva se != 0)
                    try:
                        amt = float(p.get("positionAmt", 0) or 0)
                    except Exception:
                        amt = 0.0

                    # Deduz modo de margem
                    iso_flag = None
                    if "isolated" in p:
                        try:
                            iso_flag = bool(p.get("isolated"))
                        except Exception:
                            iso_flag = None
                    if iso_flag is None:
                        iso_flag = str(p.get("marginType", "cross")).lower() == "isolated"

                    margin_mode = "ISOLATED" if iso_flag else "CROSSED"

                    # Campos auxiliares úteis para diagnóstico
                    try:
                        lev = float(p.get("leverage", 0) or 0)
                    except Exception:
                        lev = 0.0
                    try:
                        entry_price = float(p.get("entryPrice", 0) or 0)
                    except Exception:
                        entry_price = 0.0
                    try:
                        iso_wallet = float(p.get("isolatedWallet", 0) or 0)
                    except Exception:
                        iso_wallet = 0.0

                    items.append({
                        "symbol": sym,
                        "positionAmt": amt,
                        "isolated": bool(iso_flag),
                        "margin_mode": margin_mode,
                        "leverage": lev,
                        "entryPrice": entry_price,
                        "isolatedWallet": iso_wallet,
                    })

                # Apenas posições vivas (amt != 0)
                live = [x for x in items if abs(float(x.get("positionAmt", 0) or 0)) > 0]
                return live
            except BinanceAPIException as e:
                logger.error(f"Erro ao obter margin modes (após retries): {e}")
                return []
            except Exception as e:
                logger.error(f"Erro inesperado ao obter margin modes: {e}")
                return []
        
        return await self._cached_call(cache_key, ttl=5, fetch_fn=_fetch)

    async def ensure_margin_type(self, symbol: str, isolated: bool) -> bool:
        """
        Garante o modo de margem do símbolo:
        - True  -> ISOLATED
        - False -> CROSSED
        Retorna True se alterado/ok, False se já estava no modo desejado.
        """
        desired = "ISOLATED" if isolated else "CROSSED"
        try:
            # Tenta setar diretamente (idempotente: ignora erros de 'no need to change')
            def _change():
                return self.client.futures_change_margin_type(symbol=symbol, marginType=desired)

            try:
                await self._retry_call(_change)
                return True
            except BinanceAPIException as e:
                msg = str(getattr(e, "message", "")) or str(e)
                code = getattr(e, "code", None)
                # Já está no modo desejado (códigos comuns no Binance)
                if code in (-4046, -4049) or "No need to change" in msg or "no need to change" in msg or "same margin type" in msg:
                    logger.info(f"Margin type já era {desired} para {symbol}")
                    return False
                raise
        except Exception as e:
            logger.warning(f"Não foi possível garantir margin type {desired} para {symbol}: {e}")
            raise

    async def ensure_position_mode(self, dual_side: bool = False) -> bool:
        """
        Garante o 'Position Mode':
        - True  -> Hedge Mode (Dual Side Position)
        - False -> One-Way Mode
        Retorna True se alterado/ok, False se já estava no modo desejado.
        """
        desired = "HEDGE MODE" if dual_side else "ONE-WAY MODE"
        try:
            # Tenta setar diretamente (idempotente: ignora erros de 'no need to change')
            def _change():
                return self.client.futures_change_position_mode(dualSidePosition=dual_side)

            try:
                await self._retry_call(_change)
                logger.info(f"✅ Position Mode alterado para {desired}")
                self._dual_side_mode = dual_side
                return True
            except BinanceAPIException as e:
                msg = str(getattr(e, "message", "")) or str(e)
                code = getattr(e, "code", None)
                # Já está no modo desejado (-4059: No need to change position side)
                if code == -4059 or "No need to change" in msg or "no need to change" in msg:
                    logger.info(f"Position Mode já era {desired}")
                    self._dual_side_mode = dual_side
                    return False
                if code == -4068 or "Position side cannot be changed" in msg:
                    current = await self.get_position_mode(force_refresh=True)
                    current_txt = "HEDGE MODE" if current else "ONE-WAY MODE"
                    logger.warning(f"Position Mode unchanged due to open positions. Current: {current_txt}")
                    return False
                raise
        except Exception as e:
            logger.warning(f"Não foi possível garantir {desired}: {e}")
            raise

    async def get_position_mode(self, force_refresh: bool = False) -> Optional[bool]:
        """
        Retorna o modo atual de posição:
        - True  -> Hedge Mode
        - False -> One-Way Mode
        """
        if self._dual_side_mode is not None and not force_refresh:
            return self._dual_side_mode
        try:
            data = await self._retry_call(self.client.futures_get_position_mode)
            self._dual_side_mode = bool(data.get("dualSidePosition"))
            return self._dual_side_mode
        except Exception as e:
            logger.warning(f"Falha ao obter Position Mode: {e}")
            return self._dual_side_mode

    async def get_position_side(self, direction: str) -> Optional[str]:
        mode = await self.get_position_mode()
        if mode is True:
            return "LONG" if str(direction).upper() == "LONG" else "SHORT"
        return None

    async def get_leverage_brackets(self, symbol: Optional[str] = None):
        """
        Retorna leverage brackets da Binance Futures para um símbolo.
        Estrutura típica:
        [
          {
            "symbol":"BTCUSDT",
            "brackets":[
              {"initialLeverage":125,"notionalCap":50000,"notionalFloor":0,...},
              ...
            ]
          }
        ]
        """
        try:
            if symbol:
                data = await self._retry_call(self.client.futures_leverage_bracket, symbol=symbol)
            else:
                data = await self._retry_call(self.client.futures_leverage_bracket)
            # python-binance pode retornar lista já normalizada
            return data
        except BinanceAPIException as e:
            logger.warning(f"Falha ao obter leverage brackets ({symbol}): {e}")
            return []
        except Exception as e:
            logger.warning(f"Erro inesperado em leverage brackets ({symbol}): {e}")
            return []

    async def get_max_leverage_for_notional(self, symbol: str, notional: float) -> int:
        """
        Dado um notional (valor da posição), retorna a alavancagem máxima permitida
        segundo os leverage brackets do símbolo.
        """
        try:
            data = await self.get_leverage_brackets(symbol)
            # Normalizar para lista de brackets
            brackets_list = []
            if isinstance(data, list):
                # Pode ser list de dicts com 'symbol' e 'brackets'
                for entry in data:
                    if isinstance(entry, dict):
                        if entry.get("symbol") == symbol and isinstance(entry.get("brackets"), list):
                            brackets_list = entry["brackets"]
                            break
                        # Alguns ambientes retornam diretamente a lista de 'brackets'
                        if "initialLeverage" in entry and "notionalCap" in entry:
                            brackets_list = data
                            break

            # Ordenar por notionalFloor crescente
            def _to_float(x): 
                try: 
                    return float(x) 
                except Exception: 
                    return 0.0

            candidates = []
            for b in brackets_list:
                nf = _to_float(b.get("notionalFloor", 0))
                nc = _to_float(b.get("notionalCap", 0))
                lev = int(b.get("initialLeverage", 0) or 0)
                candidates.append((nf, nc, max(1, lev)))

            candidates.sort(key=lambda x: x[0])

            # Encontrar bracket que cobre o notional
            for nf, nc, lev in candidates:
                if notional >= nf and (nc == 0 or notional <= nc):
                    return max(1, lev)

            # Caso não encontre, usar a menor alavancagem encontrada (mais conservadora)
            if candidates:
                return max(1, min(l for _, __, l in candidates))
            return 20  # fallback conservador
        except Exception as e:
            logger.warning(f"Erro ao calcular max leverage para {symbol} notional {notional}: {e}")
            return 20  # fallback conservador

    async def get_premium_index(self, symbol: str) -> Dict:
        """
        Retorna dados de premium/mark price do símbolo, incluindo lastFundingRate e nextFundingTime.
        Usa /fapi/v1/premiumIndex (python-binance: futures_mark_price).
        """
        try:
            data = await self._retry_call(self.client.futures_mark_price, symbol=symbol, attempts=2, base_sleep=0.5)
            # Campos relevantes: markPrice, indexPrice, lastFundingRate, nextFundingTime
            return {
                "symbol": symbol,
                "markPrice": float(data.get("markPrice", 0) or 0),
                "indexPrice": float(data.get("indexPrice", 0) or 0),
                "lastFundingRate": float(data.get("lastFundingRate", 0) or 0),
                "nextFundingTime": int(data.get("nextFundingTime", 0) or 0)
            }
        except Exception as e:
            logger.warning(f"Falha get_premium_index({symbol}): {e}")
            return {"symbol": symbol, "markPrice": 0.0, "indexPrice": 0.0, "lastFundingRate": 0.0, "nextFundingTime": 0}

    async def get_open_interest(self, symbol: str) -> Dict:
        """
        Retorna open interest atual do símbolo (quantidade de contratos abertos).
        """
        try:
            data = await self._retry_call(self.client.futures_open_interest, symbol=symbol, attempts=2, base_sleep=0.5)
            return {
                "symbol": symbol,
                "openInterest": float(data.get("openInterest", 0) or 0),
                "time": int(data.get("time", 0) or 0)
            }
        except Exception as e:
            logger.warning(f"Falha get_open_interest({symbol}): {e}")
            return {"symbol": symbol, "openInterest": 0.0, "time": 0}

    async def get_open_interest_change(self, symbol: str, period: str = "5m", limit: int = 12) -> Dict:
        """
        Retorna variação percentual aproximada do Open Interest ao longo de 'limit' períodos (ex.: 12*5m ~= 1h).
        Usa /futures/data/openInterestHist.
        """
        # Em TESTNET a família /futures/data pode não estar disponível → retornar neutro rapidamente
        if self.testnet:
            return {"symbol": symbol, "period": period, "pct_change": 0.0}
        try:
            hist = await self._retry_call(self.client.futures_open_interest_hist, symbol=symbol, period=period, limit=limit, attempts=2, base_sleep=0.5)
            if not hist or len(hist) < 2:
                return {"symbol": symbol, "period": period, "pct_change": 0.0}
            def _to_float(x):
                try:
                    return float(x)
                except Exception:
                    return 0.0
            first = _to_float(hist[0].get("sumOpenInterest") or hist[0].get("sumOpenInterestValue") or 0)
            last = _to_float(hist[-1].get("sumOpenInterest") or hist[-1].get("sumOpenInterestValue") or 0)
            if first <= 0:
                return {"symbol": symbol, "period": period, "pct_change": 0.0}
            pct = (last - first) / first * 100.0
            return {"symbol": symbol, "period": period, "pct_change": pct}
        except Exception as e:
            logger.warning(f"Falha get_open_interest_change({symbol}): {e}")
            return {"symbol": symbol, "period": period, "pct_change": 0.0}

    # ============================================================
    # Market Intelligence Wrapper Methods
    # ============================================================

    async def futures_order_book(self, symbol: str, limit: int = 500) -> Dict:
        """
        Get futures order book depth.
        Wrapper for python-binance futures_order_book.
        """
        try:
            data = await self._retry_call(
                self.client.futures_order_book,
                symbol=symbol,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data
        except Exception as e:
            logger.warning(f"Falha futures_order_book({symbol}): {e}")
            return {"bids": [], "asks": []}

    async def futures_funding_rate(self, symbol: str, limit: int = 1) -> list:
        """
        Get funding rate history.
        Wrapper for python-binance futures_funding_rate.
        """
        try:
            data = await self._retry_call(
                self.client.futures_funding_rate,
                symbol=symbol,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_funding_rate({symbol}): {e}")
            return []

    async def futures_open_interest(self, symbol: str) -> Dict:
        """
        Get current open interest.
        Wrapper for python-binance futures_open_interest.
        """
        try:
            data = await self._retry_call(
                self.client.futures_open_interest,
                symbol=symbol,
                attempts=2,
                base_sleep=0.5
            )
            return data
        except Exception as e:
            logger.warning(f"Falha futures_open_interest({symbol}): {e}")
            return {"openInterest": "0"}

    async def futures_open_interest_hist(self, symbol: str, period: str = "5m", limit: int = 12) -> list:
        """
        Get open interest history.
        Wrapper for python-binance futures_open_interest_hist.
        """
        if self.testnet:
            return []
        try:
            data = await self._retry_call(
                self.client.futures_open_interest_hist,
                symbol=symbol,
                period=period,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_open_interest_hist({symbol}): {e}")
            return []

    async def futures_mark_price(self, symbol: str) -> Dict:
        """
        Get mark price and funding rate info.
        Wrapper for python-binance futures_mark_price.
        """
        try:
            data = await self._retry_call(
                self.client.futures_mark_price,
                symbol=symbol,
                attempts=2,
                base_sleep=0.5
            )
            return data
        except Exception as e:
            logger.warning(f"Falha futures_mark_price({symbol}): {e}")
            return {"markPrice": "0", "indexPrice": "0", "lastFundingRate": "0"}

    async def futures_account(self) -> Dict:
        """
        Get futures account information.
        Wrapper for python-binance futures_account.
        """
        try:
            data = await self._retry_call(
                self.client.futures_account,
                attempts=2,
                base_sleep=0.5
            )
            return data
        except Exception as e:
            logger.warning(f"Falha futures_account: {e}")
            return {
                "totalWalletBalance": "0",
                "availableBalance": "0",
                "totalUnrealizedProfit": "0",
                "totalMarginBalance": "0",
                "positions": []
            }

    async def futures_account_balance(self) -> list:
        """
        Get futures account balance.
        Wrapper for python-binance futures_account_balance.
        """
        try:
            data = await self._retry_call(
                self.client.futures_account_balance,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_account_balance: {e}")
            return []

    async def futures_position_information(self, symbol: str = None) -> list:
        """
        Get futures position information.
        Wrapper for python-binance futures_position_information.
        """
        try:
            if symbol:
                data = await self._retry_call(
                    self.client.futures_position_information,
                    symbol=symbol,
                    attempts=2,
                    base_sleep=0.5
                )
            else:
                data = await self._retry_call(
                    self.client.futures_position_information,
                    attempts=2,
                    base_sleep=0.5
                )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_position_information: {e}")
            return []

    async def futures_klines(self, symbol: str, interval: str, limit: int = 500) -> list:
        """Get futures klines/candlestick data."""
        try:
            data = await self._retry_call(
                self.client.futures_klines,
                symbol=symbol,
                interval=interval,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_klines({symbol}): {e}")
            return []

    async def futures_symbol_ticker(self, symbol: str = None) -> Dict:
        """Get futures symbol ticker."""
        try:
            if symbol:
                data = await self._retry_call(
                    self.client.futures_symbol_ticker,
                    symbol=symbol,
                    attempts=2,
                    base_sleep=0.5
                )
            else:
                data = await self._retry_call(
                    self.client.futures_symbol_ticker,
                    attempts=2,
                    base_sleep=0.5
                )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_symbol_ticker: {e}")
            return {}

    async def futures_create_order(self, **kwargs) -> Dict:
        """Create futures order."""
        try:
            data = await self._retry_call(
                self.client.futures_create_order,
                attempts=2,
                base_sleep=0.5,
                **kwargs
            )
            return data if data else {}
        except Exception as e:
            logger.error(f"Falha futures_create_order: {e}")
            raise

    async def futures_change_leverage(self, symbol: str, leverage: int) -> Dict:
        """Change futures leverage."""
        try:
            data = await self._retry_call(
                self.client.futures_change_leverage,
                symbol=symbol,
                leverage=leverage,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_change_leverage({symbol}): {e}")
            return {}

    async def futures_get_open_orders(self, symbol: str = None) -> list:
        """Get open futures orders."""
        try:
            if symbol:
                data = await self._retry_call(
                    self.client.futures_get_open_orders,
                    symbol=symbol,
                    attempts=2,
                    base_sleep=0.5
                )
            else:
                data = await self._retry_call(
                    self.client.futures_get_open_orders,
                    attempts=2,
                    base_sleep=0.5
                )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_get_open_orders: {e}")
            return []

    async def futures_cancel_order(self, symbol: str, orderId: int) -> Dict:
        """Cancel futures order."""
        try:
            data = await self._retry_call(
                self.client.futures_cancel_order,
                symbol=symbol,
                orderId=orderId,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_cancel_order({symbol}, {orderId}): {e}")
            return {}

    async def futures_get_order(self, symbol: str, orderId: int) -> Dict:
        """Get futures order details."""
        try:
            data = await self._retry_call(
                self.client.futures_get_order,
                symbol=symbol,
                orderId=orderId,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_get_order({symbol}, {orderId}): {e}")
            return {}

    async def futures_get_all_orders(self, symbol: str = None) -> list:
        """Get all futures orders."""
        try:
            if symbol:
                data = await self._retry_call(
                    self.client.futures_get_all_orders,
                    symbol=symbol,
                    attempts=2,
                    base_sleep=0.5
                )
            else:
                data = await self._retry_call(
                    self.client.futures_get_all_orders,
                    attempts=2,
                    base_sleep=0.5
                )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_get_all_orders: {e}")
            return []

    async def futures_cancel_all_open_orders(self, symbol: str) -> Dict:
        """Cancel all open futures orders for a symbol."""
        try:
            data = await self._retry_call(
                self.client.futures_cancel_all_open_orders,
                symbol=symbol,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_cancel_all_open_orders({symbol}): {e}")
            return {}

    async def futures_global_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 1) -> list:
        """Get global long/short account ratio."""
        if self.testnet:
            return []
        try:
            data = await self._retry_call(
                self.client.futures_global_longshort_ratio,
                symbol=symbol,
                period=period,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_global_long_short_ratio({symbol}): {e}")
            return []

    async def futures_top_long_short_account_ratio(self, symbol: str, period: str = "5m", limit: int = 1) -> list:
        """Get top trader long/short account ratio."""
        if self.testnet:
            return []
        try:
            data = await self._retry_call(
                self.client.futures_top_longshort_account_ratio,
                symbol=symbol,
                period=period,
                limit=limit,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else []
        except Exception as e:
            logger.warning(f"Falha futures_top_long_short_account_ratio({symbol}): {e}")
            return []

    async def futures_exchange_info(self) -> Dict:
        """Get futures exchange info."""
        try:
            data = await self._retry_call(
                self.client.futures_exchange_info,
                attempts=2,
                base_sleep=0.5
            )
            return data if data else {}
        except Exception as e:
            logger.warning(f"Falha futures_exchange_info: {e}")
            return {}

    async def get_taker_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 12) -> Dict:
        """
        Retorna o último buySellRatio (taker long/short volume) no período.
        >1 indica predominância de takers 'long'; <1, takers 'short'.
        """
        # Em TESTNET alguns endpoints de dados agregados não retornam; responder neutro
        if self.testnet:
            return {"symbol": symbol, "period": period, "buySellRatio": 1.0}
        try:
            if hasattr(self.client, "futures_taker_long_short_ratio"):
                rows = await self._retry_call(
                    self.client.futures_taker_long_short_ratio,
                    symbol=symbol,
                    period=period,
                    limit=limit,
                    attempts=2,
                    base_sleep=0.5,
                )
            elif hasattr(self.client, "futures_takerlongshort_ratio"):
                rows = await self._retry_call(
                    self.client.futures_takerlongshort_ratio,
                    symbol=symbol,
                    period=period,
                    limit=limit,
                    attempts=2,
                    base_sleep=0.5,
                )
            elif hasattr(self.client, "_request_futures_data_api"):
                def _fetch():
                    return self.client._request_futures_data_api(
                        "get",
                        "takerlongshortRatio",
                        data={"symbol": symbol, "period": period, "limit": limit},
                    )
                rows = await self._retry_call(_fetch, attempts=2, base_sleep=0.5)
            else:
                raise AttributeError("futures taker ratio method unavailable")
            if not rows:
                return {"symbol": symbol, "period": period, "buySellRatio": 1.0}
            last = rows[-1]
            ratio = 1.0
            try:
                ratio = float(last.get("buySellRatio", 1) or 1)
            except Exception:
                ratio = 1.0
            return {"symbol": symbol, "period": period, "buySellRatio": ratio}
        except Exception as e:
            logger.warning(f"Falha get_taker_long_short_ratio({symbol}): {e}")
            return {"symbol": symbol, "period": period, "buySellRatio": 1.0}

    # ========== USER DATA STREAM (FUTURES) ==========
    def _handle_user_event(self, msg: Dict):
        """
        Callback dos eventos do User Data Stream.
        Apenas registra e atualiza último timestamp; integração mínima para baixo impacto.
        """
        try:
            from datetime import datetime as _dt
            self._last_user_event_at = _dt.utcnow().isoformat()
            event_type = msg.get("e") or msg.get("eventType")
            logger.info(f"📨 USER_STREAM: {event_type} | recv {self._last_user_event_at}")
        except Exception as e:
            logger.warning(f"Falha ao processar evento do user stream: {e}")

    async def _keepalive_loop(self):
        """
        Mantém o listenKey vivo. Binance recomenda renovar a cada 30min (ou antes).
        """
        try:
            while self._user_stream_running and self._listen_key:
                await asyncio.sleep(25 * 60)
                try:
                    await self._retry_call(self.client.futures_stream_keepalive, listenKey=self._listen_key)
                    logger.debug("User stream keepalive enviado.")
                except Exception as e:
                    logger.warning(f"Keepalive listenKey falhou: {e}")
        except asyncio.CancelledError:
            pass

    def _build_user_ws_url(self) -> Optional[str]:
        """Monta URL do WebSocket de User Data (USD-M Futures) para PROD/TESTNET."""
        if not self._listen_key:
            return None
        # Voltar ao endpoint dedicado de listenKey via /ws/{listenKey}
        base = "wss://stream.binancefuture.com/ws" if self.testnet else "wss://fstream.binance.com/ws"
        return f"{base}/{self._listen_key}"

    async def _user_ws_loop(self):
        """
        Loop do WebSocket de User Data dedicado (compatível com uvloop).
        Reconecta com backoff simples em caso de erro.
        """
        while self._user_stream_running and self._listen_key:
            url = self._build_user_ws_url()
            if not url:
                await asyncio.sleep(1)
                continue
            try:
                logger.info(f"Conectando User WS: {url}")
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    max_queue=32,
                    open_timeout=10,
                    close_timeout=5
                ) as ws:
                    logger.info("User WS conectado")
                    async for raw in ws:
                        # Logar algumas mensagens cruas para diagnóstico
                        try:
                            preview = (raw[:200] if isinstance(raw, (bytes, bytearray)) else str(raw)[:300])
                            if getattr(self, "_ws_msg_count", 0) < 5:
                                self._ws_msg_count += 1
                                logger.info(f"User WS raw[{self._ws_msg_count}]: {preview}")
                        except Exception:
                            pass
                        try:
                            data = json.loads(raw)
                        except Exception:
                            data = {}
                        # Suporte a combined stream: {"stream": "...", "data": {...}}
                        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                            evt = data["data"]
                        else:
                            evt = data if isinstance(data, dict) else {}
                        if isinstance(evt, dict):
                            self._handle_user_event(evt)
            except asyncio.CancelledError:
                logger.info("User WS loop cancelado")
                break
            except Exception as e:
                logger.warning(f"User WS disconnected: {e} - reconnecting in 5s")
                await asyncio.sleep(5)

    async def _market_ws_loop(self):
        """
        Loop do WebSocket de Market Data (!miniTicker@arr).
        Atualiza o cache Redis com os preços em tempo real.
        """
        base = "wss://stream.binancefuture.com/ws" if self.testnet else "wss://fstream.binance.com/ws"
        url = f"{base}/!miniTicker@arr"
        
        logger.info(f"Connecting Market WS: {url}")
        
        while self._market_stream_running:
            try:
                if not self.redis:
                    logger.warning("Redis não disponível para Market WS - aguardando...")
                    await asyncio.sleep(10)
                    continue

                async with websockets.connect(url) as ws:
                    logger.info("✅ Market WS conectado (!miniTicker@arr)")
                    
                    async for raw in ws:
                        if not self._market_stream_running: 
                            break
                        
                        try:
                            data = json.loads(raw)
                            # !miniTicker@arr retorna lista de dicts
                            # [{"e":"24hrMiniTicker","E":123456789,"s":"BTCUSDT","c":"50000.00",...}, ...]
                            if isinstance(data, list):
                                pipeline = self.redis.pipeline()
                                count = 0
                                for item in data:
                                    symbol = item.get("s")
                                    price_str = item.get("c") # Close price
                                    if symbol and price_str:
                                        # Manter compatibilidade com cache key do get_symbol_price
                                        # Armazena apenas o float JSON dumpado
                                        pipeline.setex(
                                            f"binance:price:{symbol}",
                                            10, # 10s TTL (stream é rápido, mas margem segura)
                                            price_str # JSON de float é apenas a string do numero
                                        )
                                        count += 1
                                
                                if count > 0:
                                    await pipeline.execute()
                                    
                        except Exception as e:
                            logger.debug(f"Market WS parse error: {e}")
                            
            except Exception as e:
                logger.warning(f"Market WS desconectado: {e} - reconectando em 5s...")
                await asyncio.sleep(5)

    async def start_market_stream(self):
        """Inicia o stream de dados de mercado (preços)."""
        if self._market_stream_running:
            return
            
        self._market_stream_running = True
        logger.info("🚀 Iniciando Market Data Stream...")
        
        if self._market_ws_task is None or self._market_ws_task.done():
            self._market_ws_task = asyncio.create_task(self._market_ws_loop())

    async def stop_market_stream(self):
        """Para o stream de mercado."""
        self._market_stream_running = False
        if self._market_ws_task and not self._market_ws_task.done():
            self._market_ws_task.cancel()
            try:
                await self._market_ws_task
            except Exception:
                pass
        self._market_ws_task = None
        logger.info("🛑 Market Data Stream parado")

    async def start_user_stream(self) -> Dict:
        """
        Inicia o stream de usuário (USD-M Futures). Idempotente.
        """
        if self._user_stream_running:
            return await self.get_user_stream_status()

        # Obter/renovar listenKey
        try:
            self._listen_key = await self._retry_call(self.client.futures_stream_get_listen_key)
        except Exception as e:
            logger.warning(f"Falha ao obter listenKey (seguindo sem keepalive): {e}")
            self._listen_key = None

        # Marcar como running ANTES de iniciar as tasks (evita condição de corrida no loop do WS)
        self._user_stream_running = True

        # Iniciar WS assíncrono dedicado (modo compatível com uvloop)
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._user_ws_loop())
        self._twm = None

        # Keepalive em background (se houver listenKey)
        if self._listen_key and (self._keepalive_task is None or self._keepalive_task.done()):
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        return await self.get_user_stream_status()

    async def stop_user_stream(self) -> Dict:
        """
        Para o user stream e encerra keepalive.
        """
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            with contextlib.suppress(Exception):
                await self._keepalive_task
        self._keepalive_task = None

        if self._listen_key:
            with contextlib.suppress(Exception):
                await self._retry_call(self.client.futures_stream_close, listenKey=self._listen_key)
        self._listen_key = None

        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            with contextlib.suppress(Exception):
                await self._ws_task
        self._ws_task = None

        if self._twm:
            try:
                self._twm.stop()
            except Exception:
                pass
        self._twm = None
        self._user_stream_running = False
        return await self.get_user_stream_status()

    async def get_user_stream_status(self) -> Dict:
        return {
            "running": bool(self._user_stream_running),
            "listen_key": self._listen_key,
            "last_event_at": self._last_user_event_at
        }

    async def get_order_avg_price(self, symbol: str, order_id) -> float:
        """
        Calcula o preço médio executado de uma ordem.
        Estratégia:
        1) Tenta futures_get_order.avgPrice
        2) Se 0/ausente, usa cumQuote / executedQty
        3) Se ainda 0, agrega fills via futures_account_trades(orderId=...)
        Retorna 0.0 se nada disponível.
        """
        try:
            order = await self._retry_call(self.client.futures_get_order, symbol=symbol, orderId=order_id)
            avg = 0.0
            try:
                avg = float(order.get("avgPrice", 0) or 0)
            except Exception:
                avg = 0.0

            if avg <= 0:
                try:
                    ex_qty = float(order.get("executedQty", 0) or 0)
                    cum_quote = float(order.get("cumQuote", 0) or 0)
                    if ex_qty > 0 and cum_quote > 0:
                        avg = cum_quote / ex_qty
                except Exception:
                    pass

            if avg <= 0:
                try:
                    trades = await self._retry_call(self.client.futures_account_trades, symbol=symbol, orderId=order_id)
                except Exception:
                    trades = []
                total_qty = 0.0
                total_cost = 0.0
                for t in trades or []:
                    try:
                        px = float(t.get("price", 0) or 0)
                        qty = float(t.get("qty", 0) or 0)
                        if qty > 0 and px > 0:
                            total_cost += px * qty
                            total_qty += qty
                    except Exception:
                        continue
                if total_qty > 0:
                    avg = total_cost / total_qty

            return float(avg or 0.0)
        except Exception as e:
            logger.warning(f"get_order_avg_price falhou ({symbol} #{order_id}): {e}")
            return 0.0

    async def get_position_risk(self, symbol: str) -> Dict:
        """
        Retorna informações de risco/posição (liquidationPrice, marginRatio, etc.) para o símbolo.
        Usa futures_position_information (USD-M).
        """
        try:
            rows = await self._retry_call(self.client.futures_position_information, symbol=symbol)
            if isinstance(rows, list):
                for r in rows:
                    if str(r.get("symbol", "")).upper() == symbol.upper():
                        def _f(x, d=0.0):
                            try:
                                return float(x)
                            except Exception:
                                return float(d)
                        return {
                            "symbol": symbol.upper(),
                            "entryPrice": _f(r.get("entryPrice", 0)),
                            "positionAmt": _f(r.get("positionAmt", 0)),
                            "leverage": int(_f(r.get("leverage", 0)) or 0),
                            "liquidationPrice": _f(r.get("liquidationPrice", 0)),
                            "marginType": str(r.get("marginType", "") or "").upper(),
                            "unRealizedProfit": _f(r.get("unRealizedProfit", 0)),
                            "isolatedMargin": _f(r.get("isolatedMargin", 0)),
                            "marginRatio": _f(r.get("marginRatio", 0)),  # pode ser 0 em testnet
                        }
            return {}
        except Exception as e:
            logger.warning(f"get_position_risk({symbol}) falhou: {e}")
            return {}

    async def get_commission_rate(self, symbol: str) -> Dict:
        """
        Retorna taxas maker/taker configuradas para o símbolo (quando disponível).
        """
        try:
            data = await self._retry_call(self.client.futures_commission_rate, symbol=symbol)
            def _f(x, d=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(d)
            return {
                "symbol": symbol.upper(),
                "makerCommission": _f(data.get("makerCommission", 0)),
                "takerCommission": _f(data.get("takerCommission", 0)),
                "buyerCommission": _f(data.get("buyerCommission", 0)),
                "sellerCommission": _f(data.get("sellerCommission", 0)),
            }
        except Exception as e:
            logger.warning(f"get_commission_rate({symbol}) falhou: {e}")
            return {}

    async def get_account_trades(self, symbol: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """
        Retorna histórico de trades da conta (com comissões reais).
        Endpoint: GET /fapi/v1/userTrades

        Cache: 5 min por símbolo, evita rate limits

        Returns:
            List of trades: [{ symbol, id, orderId, price, qty, commission, commissionAsset, time, ... }]
        """
        # Build cache key based on parameters
        if symbol:
            cache_key = f"binance:trades:{symbol}"
        else:
            cache_key = "binance:trades:all"

        async def _fetch():
            try:
                params = {"limit": limit}
                if symbol:
                    params["symbol"] = symbol

                trades = await self._retry_call(self.client.futures_account_trades, **params)
                logger.debug(f"Fetched {len(trades)} account trades{f' for {symbol}' if symbol else ''}")
                return trades
            except BinanceAPIException as e:
                logger.error(f"Erro ao obter trades da conta (após retries): {e}")
                return []
            except Exception as e:
                logger.error(f"Erro inesperado ao obter trades: {e}")
                return []

        # Cache for 5 minutes
        return await self._cached_call(cache_key, ttl=300, fetch_fn=_fetch)

    async def get_income_history(
        self,
        symbol: Optional[str] = None,
        income_type: Optional[str] = None,
        limit: int = 1000,
        start_time: Optional[int] = None
    ) -> List[Dict]:
        """
        Retorna histórico de income (fees, funding, realized PnL).
        Endpoint: GET /fapi/v1/income

        Args:
            symbol: Filter by symbol (optional)
            income_type: TRANSFER, FUNDING_FEE, REALIZED_PNL, COMMISSION, etc. (optional)
            limit: Max records to fetch (default 1000)

        Cache: 5 min, evita rate limits

        Returns:
            List of income records: [{ symbol, incomeType, income, asset, time, ... }]
        """
        # Build cache key
        cache_parts = ["binance:income"]
        if symbol:
            cache_parts.append(symbol)
        if income_type:
            cache_parts.append(income_type)
        cache_key = ":".join(cache_parts)

        async def _fetch():
            try:
                params = {"limit": limit}
                if symbol:
                    params["symbol"] = symbol
                if income_type:
                    params["incomeType"] = income_type
                if start_time:
                    params["startTime"] = int(start_time)

                income = await self._retry_call(self.client.futures_income_history, **params)
                logger.debug(
                    f"Fetched {len(income)} income records"
                    f"{f' for {symbol}' if symbol else ''}"
                    f"{f' type={income_type}' if income_type else ''}"
                )
                return income
            except BinanceAPIException as e:
                logger.error(f"Erro ao obter income history (após retries): {e}")
                return []
            except Exception as e:
                logger.error(f"Erro inesperado ao obter income: {e}")
                return []

        # Cache for 5 minutes
        return await self._cached_call(cache_key, ttl=300, fetch_fn=_fetch)

    async def _create_algo_order(self, params: Dict) -> Dict:
        """
        Cria ordem via endpoint de Algo Order (USD-M Futures).
        """
        if not self.client:
            raise BinanceAPIException(None, 0, "Client not initialized (network/region error)")
        if hasattr(self.client, "_request_futures_api"):
            return await self._retry_call(
                self.client._request_futures_api,
                "post",
                "algo/order",
                data=params
            )
        raise AttributeError("Algo order endpoint unavailable")

    async def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        stop_price: float,
        quantity: float,
        position_side: Optional[str] = None,
        working_type: str = "MARK_PRICE"
    ) -> Dict:
        """
        Cria Stop Loss preferencialmente via Algo Order API.
        Retorna {success, order, algo, reason}.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "stopPrice": stop_price,
            "quantity": quantity,
            "workingType": working_type
        }
        if position_side and position_side != "BOTH":
            params["positionSide"] = position_side

        use_algo = bool(getattr(self.settings, "USE_ALGO_STOP_ORDERS", True))
        fallback = bool(getattr(self.settings, "ALGO_STOP_FALLBACK_TO_STANDARD", True))

        if use_algo:
            try:
                order = await self._create_algo_order(params)
                return {"success": True, "order": order, "algo": True}
            except BinanceAPIException as e:
                logger.warning(f"Algo SL failed ({symbol}): {e.message}")
                if not fallback:
                    return {"success": False, "reason": e.message}
            except Exception as e:
                logger.warning(f"Algo SL failed ({symbol}): {e}")
                if not fallback:
                    return {"success": False, "reason": str(e)}

        try:
            order = await self._retry_call(self.client.futures_create_order, **params)
            return {"success": True, "order": order, "algo": False}
        except Exception as e:
            logger.error(f"Stop loss fallback failed ({symbol}): {e}")
            return {"success": False, "reason": str(e)}

    async def get_top_long_short_account_ratio(
        self,
        symbol: str,
        period: str = "5m",
        limit: int = 1
    ) -> List[Dict]:
        try:
            if hasattr(self.client, "futures_top_long_short_account_ratio"):
                return await self._retry_call(
                    self.client.futures_top_long_short_account_ratio,
                    symbol=symbol,
                    period=period,
                    limit=limit,
                    attempts=2,
                    base_sleep=0.5,
                )
            if hasattr(self.client, "_request_futures_data_api"):
                return await self._retry_call(
                    self.client._request_futures_data_api,
                    "get",
                    "topLongShortAccountRatio",
                    data={"symbol": symbol, "period": period, "limit": limit},
                    attempts=2,
                    base_sleep=0.5,
                )
            raise AttributeError("topLongShortAccountRatio unavailable")
        except Exception as e:
            logger.warning(f"get_top_long_short_account_ratio({symbol}) failed: {e}")
            return []

    async def get_top_long_short_position_ratio(
        self,
        symbol: str,
        period: str = "5m",
        limit: int = 1
    ) -> List[Dict]:
        try:
            if hasattr(self.client, "futures_top_long_short_position_ratio"):
                return await self._retry_call(
                    self.client.futures_top_long_short_position_ratio,
                    symbol=symbol,
                    period=period,
                    limit=limit,
                    attempts=2,
                    base_sleep=0.5,
                )
            if hasattr(self.client, "_request_futures_data_api"):
                return await self._retry_call(
                    self.client._request_futures_data_api,
                    "get",
                    "topLongShortPositionRatio",
                    data={"symbol": symbol, "period": period, "limit": limit},
                    attempts=2,
                    base_sleep=0.5,
                )
            raise AttributeError("topLongShortPositionRatio unavailable")
        except Exception as e:
            logger.warning(f"get_top_long_short_position_ratio({symbol}) failed: {e}")
            return []

# Instância global
binance_client = BinanceClientManager()
