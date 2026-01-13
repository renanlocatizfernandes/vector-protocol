"""
Market Scanner - PROFESSIONAL VERSION v4.0
- Usa SCANNER_TOP_N, SCANNER_MAX_SYMBOLS, MIN_QUOTE_VOLUME_USDT_24H, SCANNER_CONCURRENCY
- Filtra apenas contratos PERPETUAL e status TRADING
- Whitelist estrita em TESTNET (Settings.TESTNET_WHITELIST) quando habilitado
- Busca klines 1h/4h com concorrência limitada (Semaphore)
- ✅ Cache inteligente para detectar movimentos mais rápido
- ✅ Priorização de símbolos com alta volatilidade e momentum
- ✅ Detecção de movimentos significativos em tempo real
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings
from modules.rules_engine import rules_engine

logger = setup_logger("market_scanner")


class MarketScanner:
    def __init__(self):
        self.client = binance_client.client
        self.settings = get_settings()
        
        # ✅ NOVO v4.0: Cache inteligente de klines (evita requisições repetidas)
        self._klines_cache: Dict[str, Dict] = {}
        self._cache_ttl = 60  # Cache válido por 60 segundos
        self._price_change_cache: Dict[str, Dict] = {}  # Cache de mudanças de preço
        
        # ✅ NOVO v4.0: Priorização de símbolos com movimento
        self._volatility_scores: Dict[str, float] = {}
        
        logger.info("✅ Market Scanner PROFISSIONAL v4.0 inicializado (com cache e priorização)")

    def reload_settings(self):
        """Recarrega configurações dinamicamente"""
        from config.settings import get_settings
        self.settings = get_settings()
        logger.info("🔄 Market Scanner settings reloaded")

    async def _get_perpetual_usdt_symbols(self) -> List[str]:
        """
        Retorna símbolos USDT que estão em TRADING e são PERPETUAL (USD-M).
        """
        exchange_info = await asyncio.to_thread(self.client.futures_exchange_info)
        symbols = []
        for s in exchange_info.get("symbols", []):
            try:
                if (
                    s.get("symbol", "").endswith("USDT") and
                    s.get("status") == "TRADING" and
                    s.get("contractType") == "PERPETUAL"
                ):
                    symbols.append(s["symbol"])
            except Exception:
                continue
        return symbols

    async def _filter_by_liquidity_and_rank(self, candidates: List[str]) -> List[str]:
        """
        Aplica ranking por quoteVolume e filtros:
        - SCANNER_TOP_N por volume
        - MIN_QUOTE_VOLUME_USDT_24H (limiar de liquidez)
        - TESTNET whitelist (opcional)
        """
        s = self.settings
        tickers = await asyncio.to_thread(self.client.futures_ticker)

        # quoteVolume é acumulado 24h na maioria das respostas de ticker da Binance Futures
        volume_dict = {}
        for t in tickers:
            sym = t.get("symbol")
            if sym in candidates:
                try:
                    volume_dict[sym] = float(t.get("quoteVolume", 0.0) or 0.0)
                except Exception:
                    volume_dict[sym] = 0.0

        # Ordena por volume desc e pega top-N
        top_n = int(getattr(s, "SCANNER_TOP_N", 200))
        ranked = sorted(volume_dict.keys(), key=lambda x: volume_dict[x], reverse=True)[:top_n]

        # Aplica limiar de liquidez mínima (ignorar em TESTNET para ampliar universo)
        min_liq = float(getattr(s, "SCANNER_MIN_VOLUME_24H", getattr(s, "MIN_QUOTE_VOLUME_USDT_24H", 0.0)))
        if not getattr(s, "BINANCE_TESTNET", True):
            if min_liq > 0.0:
                ranked = [sym for sym in ranked if volume_dict.get(sym, 0.0) >= min_liq]

        # Apply DB-based rules (if enabled)
        if getattr(s, "ENABLE_DB_RULES", False):
            try:
                ranked = await rules_engine.apply_whitelist_rules(ranked)
                logger.info(f"Applied DB whitelist rules: {len(ranked)} symbols")
            except Exception as e:
                logger.error(f"Error applying DB rules, falling back to env whitelist: {e}")
                # Fallback to env-based whitelist on error
                pass

        # Fallback: Whitelist global (prod/testnet) from env
        if not getattr(s, "ENABLE_DB_RULES", False):
            wl = [str(x).upper() for x in (getattr(s, "SYMBOL_WHITELIST", []) or []) if str(x).strip()]
            if wl and getattr(s, "SCANNER_STRICT_WHITELIST", False):
                ranked = [x for x in ranked if x in wl] or wl

            # Em testnet com whitelist estrita, reduz ao conjunto especificado
            if getattr(s, "BINANCE_TESTNET", True) and getattr(s, "SCANNER_TESTNET_STRICT_WHITELIST", True):
                wl_testnet = list(getattr(s, "TESTNET_WHITELIST", [])) or [
                    'BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','ADAUSDT',
                    'DOGEUSDT','SOLUSDT','LTCUSDT','DOTUSDT','LINKUSDT','TRXUSDT','BCHUSDT'
                ]
                ranked = [x for x in ranked if x in wl_testnet] or wl_testnet

        return ranked

    async def _apply_dynamic_whitelist(self, symbol: str, score: int = 0) -> bool:
        """
        ✅ MELHORIA #7: Whitelist Dinâmica

        Permite símbolos fora da whitelist se:
        1. Volume 24h > $500M
        2. Liquidez (order book 5%) > $1M
        3. Spread < 10 bps
        4. OU Score = 100 (top 3/dia)

        Returns: True se símbolo aprovado
        """
        s = self.settings

        # Se whitelist dinâmica desabilitada, usar whitelist estática
        if not getattr(s, "DYNAMIC_WHITELIST_ENABLED", False):
            wl = [str(x).upper() for x in (getattr(s, "SYMBOL_WHITELIST", []) or [])]
            return symbol in wl

        # Verificar se já está na whitelist estática (sempre aprovar)
        wl = [str(x).upper() for x in (getattr(s, "SYMBOL_WHITELIST", []) or [])]
        if symbol in wl:
            return True

        # ✅ EXCEÇÃO: Score 100 (permitir top 3/dia)
        if score == 100 and getattr(s, "DYNAMIC_WHITELIST_ALLOW_SCORE_100", True):
            # Verificar limite diário
            if not hasattr(self, '_score_100_count'):
                self._score_100_count = {}
                self._score_100_date = datetime.now().date()

            # Reset contador à meia-noite
            if datetime.now().date() != self._score_100_date:
                self._score_100_count = {}
                self._score_100_date = datetime.now().date()

            max_per_day = int(getattr(s, "DYNAMIC_WHITELIST_MAX_SCORE_100_PER_DAY", 3))
            current_count = len(self._score_100_count)

            if current_count < max_per_day:
                self._score_100_count[symbol] = datetime.now()
                logger.info(f"✨ SCORE 100 EXCEPTION: {symbol} approved ({current_count + 1}/{max_per_day} today)")
                return True
            elif symbol in self._score_100_count:
                # Já foi aprovado hoje
                return True

        try:
            # Critério 1: Volume 24h
            ticker = await asyncio.to_thread(self.client.futures_ticker, symbol=symbol)
            volume_24h = float(ticker.get('quoteVolume', 0))
            min_volume = float(getattr(s, "DYNAMIC_WHITELIST_MIN_VOLUME_24H", 500_000_000))

            if volume_24h < min_volume:
                logger.debug(f"❌ {symbol}: Volume {volume_24h/1e6:.1f}M < {min_volume/1e6:.0f}M required")
                return False

            # Critério 2: Spread
            order_book = await asyncio.to_thread(self.client.futures_order_book, symbol=symbol, limit=5)
            if order_book and order_book.get('bids') and order_book.get('asks'):
                best_bid = float(order_book['bids'][0][0])
                best_ask = float(order_book['asks'][0][0])
                spread_bps = ((best_ask - best_bid) / best_bid) * 10000
                max_spread = float(getattr(s, "DYNAMIC_WHITELIST_MAX_SPREAD_BPS", 10.0))

                if spread_bps > max_spread:
                    logger.debug(f"❌ {symbol}: Spread {spread_bps:.2f} bps > {max_spread} bps")
                    return False

            # Critério 3: Liquidez (order book depth 5%)
            # Simplificado: verificar se há volume suficiente nos primeiros níveis
            total_bid_liquidity = sum([float(b[1]) * float(b[0]) for b in order_book['bids'][:20]])
            min_liquidity = float(getattr(s, "DYNAMIC_WHITELIST_MIN_LIQUIDITY", 1_000_000))

            if total_bid_liquidity < min_liquidity:
                logger.debug(f"❌ {symbol}: Liquidity ${total_bid_liquidity/1e3:.0f}K < ${min_liquidity/1e6:.1f}M")
                return False

            logger.info(
                f"✅ DYNAMIC WHITELIST: {symbol} approved\n"
                f"  Volume: ${volume_24h/1e6:.1f}M, Spread: {spread_bps:.2f} bps, "
                f"Liquidity: ${total_bid_liquidity/1e6:.2f}M"
            )
            return True

        except Exception as e:
            logger.debug(f"Error checking dynamic whitelist for {symbol}: {e}")
            return False

    async def _validate_symbol_price(self, symbol: str, sem: asyncio.Semaphore) -> Optional[str]:
        """
        Valida se o símbolo possui preço (evita símbolos inválidos no TESTNET).
        Usa Semaphore para limitar concorrência.
        """
        async with sem:
            try:
                price_ok = await binance_client.get_symbol_price(symbol)
                if price_ok is not None:
                    return symbol
            except Exception:
                return None
        return None

    async def _fetch_symbol_klines(self, symbol: str, sem: asyncio.Semaphore) -> Optional[Dict]:
        """
        ✅ NOVO v4.0: Busca klines 1h e 4h com cache inteligente e detecção de movimento.
        Prioriza símbolos com alta volatilidade e mudanças significativas de preço.
        """
        async with sem:
            try:
                # ✅ NOVO: Verificar cache primeiro
                cache_key = symbol
                now = datetime.now()
                
                if cache_key in self._klines_cache:
                    cached_data = self._klines_cache[cache_key]
                    cache_time = cached_data.get('timestamp', datetime.min)
                    if (now - cache_time).total_seconds() < self._cache_ttl:
                        # Cache válido, retornar dados em cache
                        return cached_data.get('data')
                
                # Buscar dados novos
                klines_1h = await binance_client.get_klines(
                    symbol=symbol,
                    interval='1h',
                    limit=200
                )
                klines_4h = await binance_client.get_klines(
                    symbol=symbol,
                    interval='4h',
                    limit=200
                )
                
                result = {
                    'symbol': symbol,
                    'klines_1h': klines_1h,
                    'klines_4h': klines_4h
                }
                
                # ✅ NOVO: Calcular volatilidade e mudança de preço para priorização
                if klines_1h and len(klines_1h) >= 2:
                    try:
                        current_price = float(klines_1h[-1][4])  # close
                        prev_price = float(klines_1h[-2][4])  # close anterior
                        price_change_pct = abs((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0
                        
                        # Calcular volatilidade (ATR simplificado)
                        high_low_spread = []
                        for k in klines_1h[-14:]:  # Últimas 14 horas
                            high = float(k[2])
                            low = float(k[3])
                            spread = (high - low) / low * 100 if low > 0 else 0
                            high_low_spread.append(spread)
                        
                        volatility = sum(high_low_spread) / len(high_low_spread) if high_low_spread else 0.0
                        
                        # Score de prioridade (combina mudança de preço e volatilidade)
                        priority_score = (price_change_pct * 0.6) + (volatility * 0.4)
                        self._volatility_scores[symbol] = priority_score
                        
                        # Armazenar mudança de preço no cache
                        self._price_change_cache[symbol] = {
                            'price_change_pct': price_change_pct,
                            'volatility': volatility,
                            'timestamp': now
                        }
                        
                    except Exception as e:
                        logger.debug(f"Erro ao calcular volatilidade para {symbol}: {e}")
                
                # Armazenar no cache
                self._klines_cache[cache_key] = {
                    'data': result,
                    'timestamp': now
                }
                
                return result
                
            except Exception as e:
                logger.debug(f"Erro ao carregar klines de {symbol}: {e}")
                return None

    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Analisa um símbolo isolado (carrega klines 1h/4h).
        Retorna o mesmo formato de item gerado no scan_market.
        """
        try:
            # Valida preço rapidamente (evita chamadas desnecessárias)
            price = await binance_client.get_symbol_price(symbol)
            if price is None:
                return None
        except Exception:
            return None

        # Semáforo único para esta análise
        sem = asyncio.Semaphore(int(getattr(self.settings, "SCANNER_CONCURRENCY", 8)))
        return await self._fetch_symbol_klines(symbol, sem)

    async def scan_market(self) -> List[Dict]:
        """
        Escaneia mercado e retorna símbolos (até SCANNER_MAX_SYMBOLS) com dados de klines.
        """
        try:
            # Universo inicial: USDT, TRADING, PERPETUAL
            candidates = await self._get_perpetual_usdt_symbols()

            # Ranking por volume e filtros de liquidez/whitelist
            ranked = await self._filter_by_liquidity_and_rank(candidates)

            # Validar símbolos (existência de preço) com concorrência limitada
            max_symbols = int(getattr(self.settings, "SCANNER_MAX_SYMBOLS", 60))
            sem_validate = asyncio.Semaphore(int(getattr(self.settings, "SCANNER_CONCURRENCY", 8)))

            validate_tasks = [self._validate_symbol_price(sym, sem_validate) for sym in ranked]
            validated_results = await asyncio.gather(*validate_tasks, return_exceptions=False)
            valid_symbols = [sym for sym in validated_results if sym]

            # ✅ NOVO v4.0: Priorizar símbolos com maior movimento/volatilidade
            # Ordenar por score de volatilidade (se disponível) ou manter ordem original
            if self._volatility_scores:
                valid_symbols = sorted(
                    valid_symbols,
                    key=lambda s: self._volatility_scores.get(s, 0.0),
                    reverse=True
                )
            
            # Limitar quantidade para performance
            valid_symbols = valid_symbols[:max_symbols]

            logger.info(f"📊 Escaneando {len(valid_symbols)} símbolos (priorizados por movimento) ...")

            # Buscar klines com concorrência limitada
            sem_klines = asyncio.Semaphore(int(getattr(self.settings, "SCANNER_CONCURRENCY", 8)))
            tasks = [self._fetch_symbol_klines(sym, sem_klines) for sym in valid_symbols]
            results_all = await asyncio.gather(*tasks, return_exceptions=False)

            results = [r for r in results_all if r]
            
            # ✅ NOVO v4.0: Adicionar informações de movimento aos resultados
            for result in results:
                symbol = result.get('symbol')
                if symbol in self._price_change_cache:
                    price_info = self._price_change_cache[symbol]
                    result['price_change_pct'] = price_info.get('price_change_pct', 0.0)
                    result['volatility'] = price_info.get('volatility', 0.0)
                    result['movement_score'] = self._volatility_scores.get(symbol, 0.0)
            
            logger.info(f"✅ {len(results)} símbolos escaneados com sucesso")
            
            # ✅ NOVO v4.0: Log de símbolos com maior movimento
            if results:
                top_movers = sorted(
                    [r for r in results if r.get('movement_score', 0) > 0],
                    key=lambda x: x.get('movement_score', 0),
                    reverse=True
                )[:5]
                if top_movers:
                    movers_str = ", ".join([f"{r['symbol']} ({r.get('price_change_pct', 0):.2f}%)" for r in top_movers])
                    logger.info(f"📈 Top 5 movimentos: {movers_str}")

            return results

        except Exception as e:
            logger.error(f"Erro ao escanear mercado: {e}")
            return []


    def get_movement_insights(self) -> Dict:
        """
        ✅ NOVO v4.0: Retorna insights sobre movimentos de mercado detectados
        """
        return {
            "cached_symbols": len(self._klines_cache),
            "tracked_symbols": len(self._volatility_scores),
            "top_movers": sorted(
                self._volatility_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    async def get_sniper_candidates(self, limit: int = 20) -> List[str]:
        """
        ✅ NOVO v5.0: Retorna candidatos para estratégia Sniper (Baixo Volume + Alta Volatilidade)
        Foca em moedas com volume entre 1M e 50M (mid/low caps) que estão se movendo.
        """
        try:
            # Obter todos os tickers
            tickers = await asyncio.to_thread(self.client.futures_ticker)
            candidates = []
            
            min_vol = 1_000_000.0  # 1M
            max_vol = 50_000_000.0 # 50M (evitar top coins)
            min_change = 2.0       # Pelo menos 2% de variação 24h
            
            for t in tickers:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                    
                vol = float(t.get("quoteVolume", 0) or 0)
                change = abs(float(t.get("priceChangePercent", 0) or 0))
                
                if min_vol <= vol <= max_vol and change >= min_change:
                    candidates.append({
                        "symbol": sym,
                        "vol": vol,
                        "change": change,
                        "score": change * (10_000_000 / (vol + 1)) # Score: alta variação com menor volume = maior potencial explosivo
                    })
            
            # Ordenar por score (potencial explosivo)
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Retornar apenas símbolos
            result = [c["symbol"] for c in candidates[:limit]]
            logger.info(f"Sniper Candidates ({len(result)}): {result[:5]}...")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar candidatos sniper: {e}")
            return []

    def clear_cache(self):
        """✅ NOVO v4.0: Limpa cache (útil para testes ou reset)"""
        self._klines_cache.clear()
        self._price_change_cache.clear()
        self._volatility_scores.clear()
        logger.info("🗑️ Cache do Market Scanner limpo")


# Instância global
market_scanner = MarketScanner()
