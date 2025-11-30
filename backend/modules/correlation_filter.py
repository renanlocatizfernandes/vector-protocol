"""
Correlation Filter - PROFESSIONAL VERSION v3.0
✅ Janela de correlação reduzida para 14 dias (antes 60)
✅ Threshold 0.5 (antes 0.7) para verdadeira diversificação
✅ Cálculo de correlação mais eficiente
"""
import asyncio
import numpy as np
from typing import Dict, List
from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("correlation_filter")


class CorrelationFilter:
    def __init__(self):
        self.client = binance_client.client
        self.settings = get_settings()
        
        # ✅ Parametrizado via settings (com defaults)
        self.correlation_window = int(getattr(self.settings, "CORR_WINDOW_DAYS", 14))  # dias
        self.max_correlation = float(getattr(self.settings, "MAX_CORRELATION", 0.5))  # fração (0.5 = 50%)
        
        # Cache de correlações
        self.correlation_cache = {}
        self.cache_ttl = 3600  # 1 hora
        
        logger.info("✅ Correlation Filter PROFISSIONAL v3.0 inicializado")
        logger.info(f"📊 Janela: {self.correlation_window} dias")
        logger.info(f"🎯 Max Correlation: {self.max_correlation*100:.0f}%")
    
    async def filter_correlated_signals(
        self,
        signals: List[Dict],
        open_positions: List[Dict] = None,
        max_correlation: float = None
    ) -> List[Dict]:
        """
        Filtra sinais correlacionados
        """
        
        if not signals:
            return []
        
        if max_correlation is None:
            max_correlation = self.max_correlation
        
        # Símbolos das posições abertas
        open_symbols = []
        if open_positions:
            open_symbols = [p['symbol'] for p in open_positions]
        
        filtered_signals = []
        added_symbols = []
        
        for signal in signals:
            symbol = signal['symbol']
            
            # Verificar correlação com posições abertas
            if open_symbols:
                is_correlated = await self._is_correlated_with_positions(
                    symbol,
                    open_symbols,
                    max_correlation
                )
                
                if is_correlated:
                    logger.warning(f"❌ {symbol}: Altamente correlacionado com posições abertas")
                    continue
            
            # Verificar correlação com outros sinais já adicionados
            if added_symbols:
                is_correlated = await self._is_correlated_with_positions(
                    symbol,
                    added_symbols,
                    max_correlation
                )
                
                if is_correlated:
                    logger.warning(f"❌ {symbol}: Altamente correlacionado com outros sinais")
                    continue
            
            # Adicionar à lista
            filtered_signals.append(signal)
            added_symbols.append(symbol)
        
        if len(filtered_signals) < len(signals):
            logger.info(
                f"🔄 Filtro de correlação: {len(signals)} → {len(filtered_signals)} sinais\n"
                f"  Removidos: {len(signals) - len(filtered_signals)}"
            )
        
        return filtered_signals
    
    async def _is_correlated_with_positions(
        self,
        symbol: str,
        position_symbols: List[str],
        threshold: float
    ) -> bool:
        """Verifica se símbolo está correlacionado com posições"""
        
        for pos_symbol in position_symbols:
            correlation = await self._calculate_correlation(symbol, pos_symbol)
            
            if abs(correlation) > threshold:
                logger.debug(
                    f"📊 {symbol} ↔️ {pos_symbol}: "
                    f"Correlação {correlation:.2f} > {threshold:.2f}"
                )
                return True
        
        return False
    
    async def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Calcula correlação entre dois símbolos
        """
        
        if symbol1 == symbol2:
            return 1.0
        
        # Verificar cache
        cache_key = f"{symbol1}_{symbol2}"
        reverse_key = f"{symbol2}_{symbol1}"
        
        if cache_key in self.correlation_cache:
            cached_data = self.correlation_cache[cache_key]
            if cached_data['timestamp'] + self.cache_ttl > asyncio.get_event_loop().time():
                return cached_data['correlation']
        
        if reverse_key in self.correlation_cache:
            cached_data = self.correlation_cache[reverse_key]
            if cached_data['timestamp'] + self.cache_ttl > asyncio.get_event_loop().time():
                return cached_data['correlation']
        
        try:
            # ✅ CORREÇÃO: Usar janela de 14 dias (antes 60)
            klines1 = await binance_client.get_klines(
                symbol=symbol1,
                interval='1d',
                limit=self.correlation_window
            )
            
            klines2 = await binance_client.get_klines(
                symbol=symbol2,
                interval='1d',
                limit=self.correlation_window
            )
            
            if len(klines1) < 10 or len(klines2) < 10:
                return 0.0
            
            # Extrair retornos diários
            closes1 = [float(k[4]) for k in klines1]
            closes2 = [float(k[4]) for k in klines2]
            
            returns1 = [
                (closes1[i] - closes1[i-1]) / closes1[i-1]
                for i in range(1, len(closes1))
            ]
            
            returns2 = [
                (closes2[i] - closes2[i-1]) / closes2[i-1]
                for i in range(1, len(closes2))
            ]
            
            # Calcular correlação
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            # Salvar no cache
            self.correlation_cache[cache_key] = {
                'correlation': correlation,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            return correlation
            
        except Exception as e:
            logger.error(f"Erro ao calcular correlação {symbol1}-{symbol2}: {e}")
            return 0.0

    # ✅ NOVO v5.0: Sector Guard
    # Mapa simplificado de setores (Top 50 coins)
    SECTOR_MAP = {
        # L1 / Smart Contracts
        'BTCUSDT': 'L1', 'ETHUSDT': 'L1', 'BNBUSDT': 'L1', 'ADAUSDT': 'L1', 'SOLUSDT': 'L1',
        'AVAXUSDT': 'L1', 'DOTUSDT': 'L1', 'MATICUSDT': 'L1', 'TRXUSDT': 'L1', 'LTCUSDT': 'L1',
        'ATOMUSDT': 'L1', 'NEARUSDT': 'L1', 'ALGOUSDT': 'L1', 'FTMUSDT': 'L1', 'EGLDUSDT': 'L1',
        
        # DeFi
        'UNIUSDT': 'DEFI', 'AAVEUSDT': 'DEFI', 'MKRUSDT': 'DEFI', 'CRVUSDT': 'DEFI', 
        'SNXUSDT': 'DEFI', 'COMPUSDT': 'DEFI', 'CAKEUSDT': 'DEFI', 'LDOUSDT': 'DEFI',
        
        # Metaverse / Gaming
        'SANDUSDT': 'GAME', 'MANAUSDT': 'GAME', 'AXSUSDT': 'GAME', 'GALAUSDT': 'GAME', 
        'APEUSDT': 'GAME', 'IMXUSDT': 'GAME', 'ENJUSDT': 'GAME',
        
        # Infrastructure / Storage
        'LINKUSDT': 'INFRA', 'FILUSDT': 'INFRA', 'GRTUSDT': 'INFRA', 'ARUSDT': 'INFRA',
        
        # Meme
        'DOGEUSDT': 'MEME', 'SHIBUSDT': 'MEME', 'PEPEUSDT': 'MEME', 'FLOKIUSDT': 'MEME'
    }

    def check_sector_exposure(self, symbol: str, open_positions: List[Dict]) -> bool:
        """
        ✅ NOVO v5.0: Verifica se já temos muitas posições no mesmo setor
        Retorna True se exposição estiver OK, False se exceder limite.
        """
        sector = self.SECTOR_MAP.get(symbol, 'OTHER')
        if sector == 'OTHER':
            return True
            
        max_per_sector = int(getattr(self.settings, "MAX_POSITIONS_PER_SECTOR", 3))
        
        current_sector_count = 0
        for pos in open_positions:
            pos_sym = pos.get('symbol')
            if self.SECTOR_MAP.get(pos_sym) == sector:
                current_sector_count += 1
                
        if current_sector_count >= max_per_sector:
            logger.warning(f"🛡️ Sector Guard: {symbol} rejeitado. Setor {sector} cheio ({current_sector_count}/{max_per_sector})")
            return False
            
        return True


# Instância global
correlation_filter = CorrelationFilter()
