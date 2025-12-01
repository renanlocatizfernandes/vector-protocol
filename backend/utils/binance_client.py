from binance.client import Client
from binance.exceptions import BinanceAPIException
from config.settings import get_settings
from utils.logger import setup_logger
from typing import Dict, List, Optional
import asyncio
import contextlib
from binance.streams import ThreadedWebsocketManager
import json
import websockets

logger = setup_logger("binance_client")

class BinanceClientManager:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.BINANCE_API_KEY
        self.api_secret = settings.BINANCE_API_SECRET
        self.testnet = settings.BINANCE_TESTNET
        # Estado do User Data Stream
        self._twm: Optional[ThreadedWebsocketManager] = None
        self._listen_key: Optional[str] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._user_stream_running: bool = False
        self._last_user_event_at: Optional[str] = None
        self._ws_task: Optional[asyncio.Task] = None
        # contador simples para logar primeiras mensagens cruas do WS
        self._ws_msg_count: int = 0
        
        # Inicializar cliente
        # Inicializar cliente
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
                logger.info("Cliente Binance inicializado no TESTNET (HTTPS)")
            else:
                self.client = Client(self.api_key, self.api_secret)
                logger.info("Cliente Binance inicializado em PRODUÇÃO")
        except Exception as e:
            logger.error(f"Falha ao inicializar cliente Binance (provavelmente erro de rede ou região): {e}")
            self.client = None

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
        """Retorna saldo da conta de futuros com retries"""
        try:
            account = await self._retry_call(self.client.futures_account)
            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])

            logger.info(f"Saldo Total: {total_balance} USDT")
            logger.info(f"Saldo Disponível: {available_balance} USDT")

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
    
    async def get_symbol_price(self, symbol: str):
        """Retorna preço atual de um símbolo com retries"""
        try:
            ticker = await self._retry_call(self.client.futures_symbol_ticker, symbol=symbol)
            price = float(ticker['price'])
            logger.info(f"Preço de {symbol}: {price}")
            return price
        except BinanceAPIException as e:
            logger.error(f"Erro ao obter preço de {symbol} (após retries): {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao obter preço de {symbol}: {e}")
            return None
    
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
        """Retorna informações de precisão e filtros do símbolo com retries"""
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

    async def get_positions_margin_modes(self) -> List[Dict]:
        """
        Retorna posições vivas com indicação do modo de margem (CROSSED/ISOLATED) por símbolo.
        Usa futures_account (já empregado no projeto) e deduz pelo campo 'isolated' ou 'marginType'.
        """
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

    async def get_taker_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 12) -> Dict:
        """
        Retorna o último buySellRatio (taker long/short volume) no período.
        >1 indica predominância de takers 'long'; <1, takers 'short'.
        """
        # Em TESTNET alguns endpoints de dados agregados não retornam; responder neutro
        if self.testnet:
            return {"symbol": symbol, "period": period, "buySellRatio": 1.0}
        try:
            rows = await self._retry_call(self.client.futures_taker_longshort_ratio, symbol=symbol, period=period, limit=limit, attempts=2, base_sleep=0.5)
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
                logger.warning(f"User WS desconectado: {e} — tentando reconectar em 5s")
                await asyncio.sleep(5)

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

# Instância global
binance_client = BinanceClientManager()
