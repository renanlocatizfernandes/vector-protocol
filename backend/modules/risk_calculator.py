"""
Risk Calculator - PROFESSIONAL VERSION v4.0
🎯 OTIMIZADO PARA CONTAS PEQUENAS (70 USDT+)
✅ Margem máxima por posição: 30% (para 2-3 posições maiores)
✅ Stop loss DINÂMICO baseado em ATR + Performance + Volatilidade
✅ Ajuste inteligente: tighter stops em winning streaks, wider em losses
✅ Validação de correlação no cálculo de margem
"""
import asyncio
from typing import Dict, List
from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger("risk_calculator")


class RiskCalculator:
    def __init__(self):
        self.client = binance_client.client
        
        # 🎯 OTIMIZADO PARA CONTAS PEQUENAS (70 USDT)
        # Com poucas posições, cada uma pode ser maior
        self.max_margin_per_position = 0.30  # 30% max = ~21 USDT com 70 USDT
        self.min_margin_per_position = 0.15  # 15% min = ~10.5 USDT com 70 USDT
        self.pyramiding_reserve = 0.10  # 10% reserva = ~7 USDT
        
        # Limite global de capital
        self.max_total_capital_usage = 0.90
        try:
            self.max_total_capital_usage = float(
                getattr(get_settings(), "MAX_TOTAL_CAPITAL_USAGE", self.max_total_capital_usage)
            )
        except Exception:
            pass
        self.max_total_capital_usage = max(0.0, min(1.0, self.max_total_capital_usage))
        
        # 🎯 STOP LOSS DINÂMICO
        # Base 10% com ajustes:
        # - Winning streak: reduce para 6-8% (proteger lucros)
        # - Losing streak: aumenta para 12-15% (dar espaço para recuperar)
        # - Alta volatilidade: aumenta baseado em ATR
        self.base_stop_loss_pct = 10.0  # 10% base (usuário escolheu)
        self.max_stop_loss_pct = 15.0   # 15% máximo absoluto
        self.min_stop_loss_pct = 5.0    # 5% mínimo (sempre ter proteção)
        
        # Performance tracking para stop dinâmico
        self.recent_win_rate = 0.0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        
        logger.info("✅ Risk Calculator v4.0 - AGRESSIVO (70 USDT)")
        logger.info(f"📊 Margem máxima por posição: {self.max_margin_per_position*100:.0f}%")
        logger.info(f"💰 Reserva para pyramiding: {self.pyramiding_reserve*100:.0f}%")
        logger.info(f"🔴 Limite TOTAL de capital: {self.max_total_capital_usage*100:.0f}%")
        logger.info(f"🛑 Stop loss DINÂMICO: {self.min_stop_loss_pct}% - {self.max_stop_loss_pct}% (base {self.base_stop_loss_pct}%)")
    
    def calculate_dynamic_stop_loss(self, atr_pct: float = 0.0) -> float:
        """
        🎯 NOVO v4.0: Calcula stop loss dinâmico baseado em:
        - Performance recente (wins/losses)
        - Volatilidade (ATR)
        - Win rate geral
        
        Returns: stop loss % (ex: 8.5 para 8.5%)
        """
        
        # Começar com base de 10%
        dynamic_sl = self.base_stop_loss_pct
        
        # === AJUSTE POR PERFORMANCE (STREAK) ===
        
        # Winning streak: apertar stop (proteger lucros)
        if self.consecutive_wins >= 5:
            dynamic_sl *= 0.6  # -40% → ~6%
            logger.debug(f"🔥 5+ wins seguidos: Stop apertado para {dynamic_sl:.1f}%")
        elif self.consecutive_wins >= 3:
            dynamic_sl *= 0.75  # -25% → ~7.5%
            logger.debug(f"✅ 3+ wins seguidos: Stop apertado para {dynamic_sl:.1f}%")
        
        # Losing streak: dar mais espaço (evitar whipsaw)
        elif self.consecutive_losses >= 3:
            dynamic_sl *= 1.4  # +40% → ~14%
            logger.debug(f"⚠️ 3+ losses seguidos: Stop ampliado para {dynamic_sl:.1f}%")
        elif self.consecutive_losses >= 2:
            dynamic_sl *= 1.2  # +20% → ~12%
            logger.debug(f"⚠️ 2+ losses seguidos: Stop ampliado para {dynamic_sl:.1f}%")
        
        # === AJUSTE POR WIN RATE ===
        
        if self.recent_win_rate > 0.70:  # > 70% win rate
            dynamic_sl *= 0.85  # Pode arriscar menos
        elif self.recent_win_rate < 0.40:  # < 40% win rate
            dynamic_sl *= 1.15  # Precisa de mais margem
        
        # === AJUSTE POR VOLATILIDADE (ATR) ===
        
        if atr_pct > 0:
            # Se ATR alto (> 3%), aumentar stop proporcionalmente
            if atr_pct > 3.0:
                volatility_mult = min(1.5, 1 + (atr_pct - 3.0) / 5.0)
                dynamic_sl *= volatility_mult
                logger.debug(f"📊 Alta volatilidade (ATR {atr_pct:.1f}%): Stop ajustado x{volatility_mult:.2f}")
        
        # === LIMITES ABSOLUTOS ===
        
        dynamic_sl = max(self.min_stop_loss_pct, min(self.max_stop_loss_pct, dynamic_sl))
        
        logger.info(
            f"🎯 Stop Loss Dinâmico: {dynamic_sl:.1f}% "
            f"(wins: {self.consecutive_wins}, losses: {self.consecutive_losses}, "
            f"win_rate: {self.recent_win_rate*100:.0f}%)"
        )
        
        return dynamic_sl
    
    def calculate_position_size(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        leverage: int,
        account_balance: float,
        open_positions_margin: float = 0.0,
        score: int = 50  # ✅ NOVO: Score para dynamic sizing
    ) -> Dict:
        """
        Calcula tamanho da posição com validações rigorosas
        """
        
        try:
            if account_balance <= 0:
                return {
                    'approved': False,
                    'reason': 'Saldo indisponível para cálculo de risco'
                }
            if entry_price <= 0:
                return {
                    'approved': False,
                    'reason': 'Preço de entrada inválido'
                }
            # ================================
            # 1. VALIDAR LIMITE GLOBAL DE CAPITAL
            # ================================
            
            # ✅ NOVO: Verificar se já estamos no limite de 60%
            total_margin_used = open_positions_margin
            available_capital = account_balance * self.max_total_capital_usage
            
            if total_margin_used >= available_capital:
                return {
                    'approved': False,
                    'reason': f'Limite global de capital atingido ({self.max_total_capital_usage*100:.0f}%)'
                }
            
            remaining_capital = available_capital - total_margin_used
            
            logger.info(
                f"💰 Capital disponível: {remaining_capital:.2f} USDT "
                f"({(remaining_capital/account_balance)*100:.1f}% do balance)"
            )
            
            # ================================
            # 2. CALCULAR RISCO COM STOP DINÂMICO
            # ================================
            
            risk_distance = abs(entry_price - stop_loss)
            risk_pct = (risk_distance / entry_price) * 100
            
            # 🎯 v4.0: Usar stop loss dinâmico baseado em performance
            dynamic_max_sl = self.calculate_dynamic_stop_loss()
            
            if risk_pct > dynamic_max_sl:
                logger.warning(
                    f"⚠️ {symbol}: Stop loss {risk_pct:.2f}% > {dynamic_max_sl:.1f}% (dinâmico)\n"
                    f"  Ajustando stop loss para {dynamic_max_sl:.1f}%"
                )
                
                # Ajustar stop loss para o máximo dinâmico
                if direction == 'LONG':
                    stop_loss = entry_price * (1 - dynamic_max_sl / 100)
                else:
                    stop_loss = entry_price * (1 + dynamic_max_sl / 100)
                
                risk_distance = abs(entry_price - stop_loss)
                risk_pct = dynamic_max_sl
            
            # ================================
            # 3. CALCULAR MARGEM DISPONÍVEL
            # ================================
            
            # Ajustar margem baseado em performance recente
            adjusted_margin_pct = max(self.min_margin_per_position, self._adjust_margin_for_performance())
            
            # ✅ NOVO: Dynamic Sizing baseado no Score
            # Score 40-60: Base (10%)
            # Score 60-80: High Conviction (15%)
            # Score 80+: Sniper/Ultra (20%)
            if score >= 80:
                adjusted_margin_pct = max(adjusted_margin_pct, 0.20)
                logger.info(f"🚀 {symbol}: Score {score} (SNIPER) -> Margem boost para 20%")
            elif score >= 60:
                adjusted_margin_pct = max(adjusted_margin_pct, 0.15)
                logger.info(f"✨ {symbol}: Score {score} (HIGH CONVICTION) -> Margem boost para 15%")
            else:
                logger.info(f"🔹 {symbol}: Score {score} (NORMAL) -> Margem base {adjusted_margin_pct*100:.1f}%")
            
            # Margem disponível para esta posição
            max_margin_this_position = min(
                account_balance * adjusted_margin_pct,
                remaining_capital
            )
            
            logger.info(
                f"📊 Margem ajustada: {adjusted_margin_pct*100:.1f}% "
                f"(base: {self.max_margin_per_position*100:.0f}%)"
            )
            
            # ================================
            # 4. CALCULAR QUANTITY
            # ================================
            
            # Margem necessária = (Entry Price × Quantity) / Leverage
            # Quantity = (Margem × Leverage) / Entry Price
            
            quantity = (max_margin_this_position * leverage) / entry_price
            
            # Calcular quanto será usado como margem
            margin_required = (entry_price * quantity) / leverage
            
            # ================================
            # 5. VALIDAÇÕES FINAIS
            # ================================
            
            if quantity <= 0:
                return {
                    'approved': False,
                    'reason': 'Quantidade calculada inválida'
                }
            
            if margin_required > remaining_capital:
                return {
                    'approved': False,
                    'reason': 'Margem requerida excede capital disponível'
                }
            
            # ✅ NOVO: Verificar se margem está dentro do limite por posição
            margin_pct_of_balance = (margin_required / account_balance) * 100
            
            # Tolerância para arredondamento e variações de preço (evita rejeições por poucos bps)
            tolerance_pct = 0.2  # 0.2pp de folga
            if margin_pct_of_balance > (adjusted_margin_pct * 100) + tolerance_pct:
                logger.warning(
                    f"⚠️ {symbol}: Margem {margin_pct_of_balance:.2f}% > {(adjusted_margin_pct*100):.1f}% (+tol {tolerance_pct:.1f}pp)"
                )
                return {
                    'approved': False,
                    'reason': f'Margem excede limite de {(adjusted_margin_pct*100):.1f}% por posição'
                }
            
            # ================================
            # 6. CALCULAR RISCO EM USDT
            # ================================
            
            # Perda potencial se stop loss for atingido
            potential_loss = quantity * risk_distance
            potential_loss_pct = (potential_loss / account_balance) * 100
            
            logger.info(
                f"✅ {symbol} Position Size Calculado:\n"
                f"  Entry: {entry_price:.4f}\n"
                f"  Stop: {stop_loss:.4f} ({risk_pct:.2f}%)\n"
                f"  Quantity: {quantity:.4f}\n"
                f"  Leverage: {leverage}x\n"
                f"  Margem: {margin_required:.2f} USDT ({margin_pct_of_balance:.2f}%)\n"
                f"  Perda potencial: {potential_loss:.2f} USDT ({potential_loss_pct:.2f}%)"
            )
            
            return {
                'approved': True,
                'quantity': quantity,
                'margin_required': margin_required,
                'stop_loss': stop_loss,  # Ajustado se necessário
                'potential_loss': potential_loss,
                'potential_loss_pct': potential_loss_pct,
                'risk_pct': risk_pct
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular position size: {e}")
            return {
                'approved': False,
                'reason': str(e)
            }
    
    def _adjust_margin_for_performance(self) -> float:
        """
        ✅ NOVO: Ajusta margem baseado em performance recente
        """
        
        base_margin = self.max_margin_per_position
        
        # Não penalizar quando não há histórico (evita cair para 7.5% por default)
        if self.consecutive_wins == 0 and self.consecutive_losses == 0 and self.recent_win_rate == 0.0:
            return base_margin
        
        # Aumentar margem após winning streak
        if self.consecutive_wins >= 5:
            return base_margin * 1.2  # +20%
        elif self.consecutive_wins >= 3:
            return base_margin * 1.1  # +10%
        
        # Reduzir margem após losing streak
        elif self.consecutive_losses >= 3:
            return base_margin * 0.7  # -30%
        elif self.consecutive_losses >= 2:
            return base_margin * 0.85  # -15%
        
        # Win rate geral
        elif self.recent_win_rate > 0.65:  # > 65%
            return base_margin * 1.15  # +15%
        elif self.recent_win_rate < 0.50:  # < 50%
            return base_margin * 0.75  # -25%
        
        return base_margin
    
    def update_performance(self, win: bool):
        """
        ✅ NOVO: Atualiza tracking de performance
        """
        
        if win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            logger.info(f"✅ Win registrado. Streak: {self.consecutive_wins}")
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            logger.warning(f"❌ Loss registrado. Streak: {self.consecutive_losses}")
    
    def update_win_rate(self, win_rate: float):
        """
        ✅ NOVO: Atualiza win rate recente
        """
        
        self.recent_win_rate = win_rate
        logger.info(f"📊 Win rate atualizado: {win_rate*100:.1f}%")
    
    def calculate_atr(self, klines: List) -> float:
        """Calcula Average True Range (ATR)"""
        
        if len(klines) < 2:
            return 0
        
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        
        true_ranges = []
        
        for i in range(1, len(klines)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)
        
        if not true_ranges:
            return 0
        
        # ATR = média dos últimos 14 períodos
        atr = sum(true_ranges[-14:]) / min(len(true_ranges), 14)
        
        return atr
    
    def calculate_volume_ratio(self, klines: List) -> float:
        """
        ✅ CORREÇÃO: Calcula ratio de volume corretamente
        """
        
        if len(klines) < 20:
            return 0
        
        volumes = [float(k[5]) for k in klines]
        
        current_volume = volumes[-1]
        avg_volume_20 = sum(volumes[-20:]) / 20
        
        if avg_volume_20 == 0:
            return 0
        
        volume_ratio = current_volume / avg_volume_20
        
        return volume_ratio

    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """
        ✅ NOVO: Calcula RSI simples para validação de DCA
        """
        if len(closes) < period + 1:
            return 50.0
            
        import numpy as np
        
        deltas = np.diff(closes)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down
        rsi = np.zeros_like(closes)
        rsi[:period] = 100. - 100./(1. + rs)

        for i in range(period, len(closes)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up*(period-1) + upval)/period
            down = (down*(period-1) + downval)/period
            rs = up/down
            rsi[i] = 100. - 100./(1. + rs)
            
        return rsi[-1]
    
    def validate_correlation_impact(
        self,
        existing_positions: List[str],
        new_symbol: str,
        correlation_threshold: float = 0.5
    ) -> Dict:
        """
        ✅ NOVO: Valida impacto de correlação no risco total
        Se nova posição é altamente correlacionada com existentes,
        reduz margem disponível
        """
        
        if not existing_positions:
            return {
                'approved': True,
                'margin_multiplier': 1.0
            }
        
        # Aqui você implementaria cálculo de correlação real
        # Por ora, um placeholder simplificado
        
        # Se tiver > 3 posições correlacionadas, reduzir margem
        correlated_count = 0
        
        for pos_symbol in existing_positions:
            # Exemplo: BTC correlacionado com outras crypto majors
            if 'BTC' in new_symbol and 'BTC' in pos_symbol:
                correlated_count += 1
            elif 'ETH' in new_symbol and 'ETH' in pos_symbol:
                correlated_count += 1
        
        if correlated_count >= 3:
            return {
                'approved': True,
                'margin_multiplier': 0.7,  # Reduzir margem em 30%
                'reason': f'{correlated_count} posições correlacionadas detectadas'
            }
        elif correlated_count >= 2:
            return {
                'approved': True,
                'margin_multiplier': 0.85,  # Reduzir margem em 15%
                'reason': f'{correlated_count} posições correlacionadas detectadas'
            }
        
        return {
            'approved': True,
            'margin_multiplier': 1.0
        }
    
    async def get_symbol_info(self, symbol: str) -> Dict:
        """Obtém informações do símbolo"""
        
        try:
            exchange_info = self.client.futures_exchange_info()
            
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    # Extrair informações relevantes
                    filters = {f['filterType']: f for f in s['filters']}
                    
                    return {
                        'symbol': symbol,
                        'status': s['status'],
                        'tick_size': float(filters['PRICE_FILTER']['tickSize']),
                        'step_size': float(filters['LOT_SIZE']['stepSize']),
                        'min_qty': float(filters['LOT_SIZE']['minQty']),
                        'max_qty': float(filters['LOT_SIZE']['maxQty']),
                        'min_notional': float(filters.get('MIN_NOTIONAL', {}).get('notional', 0))
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter info do símbolo: {e}")
            return None


# Instância global
risk_calculator = RiskCalculator()
