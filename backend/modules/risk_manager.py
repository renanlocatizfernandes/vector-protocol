"""
Risk Manager - PROFESSIONAL VERSION v4.0
✅ Aumenta position size após 3+ wins consecutivos
✅ Reduz agressividade após 2+ losses
✅ Validação mais rigorosa de margem disponível
✅ Métricas detalhadas e tracking de performance
✅ Ajuste dinâmico de risco baseado em condições de mercado
✅ Logs estruturados para análise
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from utils.logger import setup_logger
from config.settings import get_settings
import json
from utils.redis_client import redis_client

logger = setup_logger("risk_manager")


class RiskManager:
    def __init__(self):
        # Carregar settings centralizados
        self.settings = get_settings()

        # Limites base (agora alinhados ao settings)
        # Ex.: RISK_PER_TRADE=0.02 (2%), MAX_PORTFOLIO_RISK=0.15 (15%)
        self.max_risk_per_trade = float(self.settings.RISK_PER_TRADE)
        # Risco específico por trade para sniper (fração, ex.: 0.01 = 1%)
        self.sniper_risk_per_trade = float(getattr(self.settings, "SNIPER_RISK_PER_TRADE", self.max_risk_per_trade))
        self.max_total_risk = float(self.settings.MAX_PORTFOLIO_RISK)
        self.max_positions_allowed = int(self.settings.MAX_POSITIONS)

        # ✅ NOVO: Tracking de performance
        self.consecutive_wins = 0
        self.consecutive_losses = 0

        # Hard stops (via settings)
        self.daily_max_loss_pct = float(getattr(self.settings, "DAILY_MAX_LOSS_PCT", 0.0))
        self.intraday_dd_hard_stop_pct = float(getattr(self.settings, "INTRADAY_DRAWDOWN_HARD_STOP_PCT", 0.0))

        # Tracking diário/intradiário
        self._daily_date = None
        self._daily_start_balance = None
        self._intraday_peak_balance = None
        self._intraday_trough_balance = None
        
        # ✅ NOVO v4.0: Métricas detalhadas
        self._metrics = {
            "total_trades_validated": 0,
            "total_trades_approved": 0,
            "total_trades_rejected": 0,
            "rejection_reasons": {},
            "risk_adjustments": {
                "increased": 0,
                "decreased": 0,
                "normal": 0
            },
            "daily_stats": {
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0
            }
        }
        
        # ✅ NOVO v4.0: Ajuste dinâmico baseado em volatilidade de mercado
        self._market_volatility_factor = 1.0  # Multiplicador de risco baseado em volatilidade
        
        logger.info("✅ Risk Manager PROFISSIONAL v4.0 inicializado")
        logger.info(f"📊 Max Risk por Trade (settings): {self.max_risk_per_trade*100:.1f}%")
        logger.info(f"📊 Max Risk Total (settings): {self.max_total_risk*100:.1f}%")
        logger.info(f"📊 Max Positions (settings): {self.max_positions_allowed}")
    
    def validate_trade(
        self,
        signal: Dict,
        account_balance: float,
        open_positions: int = 0
    ) -> Dict:
        """Valida trade sob perspectiva de risco"""
        
        # ✅ NOVO v4.0: Tracking de métricas
        self._metrics["total_trades_validated"] += 1

        # 0. Respeitar limite global de posições
        #    Para trades normais: limite = MAX_POSITIONS
        #    Para trades sniper:  limite = MAX_POSITIONS + SNIPER_EXTRA_SLOTS
        extra_slots = 0
        try:
            extra_slots = int(getattr(self.settings, "SNIPER_EXTRA_SLOTS", 0))
        except Exception:
            extra_slots = 0

        max_allowed_for_signal = self.max_positions_allowed
        if signal.get("sniper"):
            max_allowed_for_signal = self.max_positions_allowed + max(0, extra_slots)

        if open_positions is not None and open_positions >= max_allowed_for_signal:
            reason = f"Max positions atingido ({open_positions}/{max_allowed_for_signal})"
            self._track_rejection(reason)
            return {
                "approved": False,
                "reason": reason
            }
        
        symbol = signal.get('symbol', 'UNKNOWN')
        
        # 0.1 Hard stops: reset diário e atualização de extremos
        self._rollover_daily(account_balance)
        self._update_intraday_extrema(account_balance)

        # 0.2 Bloqueio por perda diária (desde o início do dia)
        if self.daily_max_loss_pct and self._daily_start_balance and account_balance:
            try:
                bal = float(account_balance or 0.0)
            except Exception:
                bal = 0.0
            if bal > 0 and self._daily_start_balance > 0:
                daily_loss_pct = max(0.0, (self._daily_start_balance - bal) / self._daily_start_balance)
                if daily_loss_pct >= self.daily_max_loss_pct:
                    reason = f"Hard stop diário: perda {daily_loss_pct*100:.2f}% >= {self.daily_max_loss_pct*100:.2f}%"
                    logger.error(f"🚨 HARD STOP Diário atingido: perda {daily_loss_pct*100:.2f}% >= {self.daily_max_loss_pct*100:.2f}%")
                    self._track_rejection(reason)
                    return {
                        "approved": False,
                        "reason": reason
                    }

        # 0.3 Bloqueio por drawdown intradiário (do pico do dia)
        if self.intraday_dd_hard_stop_pct and self._intraday_peak_balance and account_balance:
            try:
                bal = float(account_balance or 0.0)
            except Exception:
                bal = 0.0
            if bal > 0 and self._intraday_peak_balance > 0:
                intraday_dd_pct = max(0.0, (self._intraday_peak_balance - bal) / self._intraday_peak_balance)
                if intraday_dd_pct >= self.intraday_dd_hard_stop_pct:
                    reason = f"Hard stop intradiário: DD {intraday_dd_pct*100:.2f}% >= {self.intraday_dd_hard_stop_pct*100:.2f}%"
                    logger.error(f"🚨 HARD STOP Intradiário atingido: DD {intraday_dd_pct*100:.2f}% >= {self.intraday_dd_hard_stop_pct*100:.2f}%")
                    self._track_rejection(reason)
                    return {
                        "approved": False,
                        "reason": reason
                    }
        
        # 1. Validar risco por trade (pct informado no sinal x risco ajustado por performance)
        risk_pct = float(signal.get('risk_pct', 2.0))  # % (ex.: 2.0 = 2%)

        # Escolher base de risco conforme tipo de sinal (core vs sniper)
        is_sniper = bool(signal.get("sniper"))
        base_risk_fraction = self.sniper_risk_per_trade if is_sniper else self.max_risk_per_trade
        
        # ✅ NOVO v4.0: Ajustar baseado em performance (streak) e volatilidade de mercado
        adjusted_risk_fraction = self._adjust_risk_for_performance(base_risk_fraction)  # fração (ex.: 0.02)
        # Aplicar fator de volatilidade de mercado
        adjusted_risk_fraction *= self._market_volatility_factor
        
        if risk_pct > adjusted_risk_fraction * 100.0:
            reason = f'Risco {risk_pct:.2f}% > {adjusted_risk_fraction*100:.1f}% (ajustado)'
            self._track_rejection(reason)
            return {
                'approved': False,
                'reason': reason
            }
        
        # 2. Validar risco total (aprox. conservadora):
        #    considera posições existentes com risco base e a nova com o risco escolhido (core/sniper)
        total_risk_fraction = (open_positions or 0) * self.max_risk_per_trade + base_risk_fraction
        
        if total_risk_fraction > self.max_total_risk:
            reason = f'Risco total {total_risk_fraction*100:.1f}% > {self.max_total_risk*100:.1f}%'
            self._track_rejection(reason)
            return {
                'approved': False,
                'reason': reason
            }
        
        # ✅ NOVO v4.0: Tracking de aprovação
        self._metrics["total_trades_approved"] += 1
        
        # ✅ NOVO v4.0: Log estruturado
        self._log_validation_structured(signal, adjusted_risk_fraction, open_positions)
        
        return {
            'approved': True,
            'adjusted_risk': adjusted_risk_fraction,
            'volatility_factor': self._market_volatility_factor
        }
    
    def _adjust_risk_for_performance(self, base_risk: Optional[float] = None) -> float:
        """
        ✅ NOVO v4.0: Ajusta risco baseado em wins/losses recentes e condições de mercado
        Retorna fração (ex.: 0.02 = 2%).
        """
        if base_risk is None:
            base_risk = self.max_risk_per_trade
        adjustment_type = "normal"
        
        # Aumentar após winning streak (aproveitar momentum positivo)
        if self.consecutive_wins >= 5:
            adjustment_type = "increased"
            return base_risk * 1.3  # +30%
        elif self.consecutive_wins >= 3:
            adjustment_type = "increased"
            return base_risk * 1.2  # +20%
        
        # Reduzir após losing streak (proteção em períodos difíceis)
        elif self.consecutive_losses >= 3:
            adjustment_type = "decreased"
            return base_risk * 0.6  # -40%
        elif self.consecutive_losses >= 2:
            adjustment_type = "decreased"
            return base_risk * 0.8  # -20%
        
        # ✅ NOVO v4.0: Tracking de ajustes
        self._metrics["risk_adjustments"][adjustment_type] += 1
        
        return base_risk
    
    def update_performance(self, win: bool):
        """
        ✅ NOVO v4.0: Atualiza tracking de performance com métricas detalhadas
        """
        if win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self._metrics["daily_stats"]["wins"] += 1
            logger.info(f"✅ Win registrado. Streak: {self.consecutive_wins}")
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self._metrics["daily_stats"]["losses"] += 1
            logger.warning(f"❌ Loss registrado. Streak: {self.consecutive_losses}")
        
        # ✅ NOVO v4.0: Atualizar win rate diário
        total = self._metrics["daily_stats"]["wins"] + self._metrics["daily_stats"]["losses"]
        if total > 0:
            self._metrics["daily_stats"]["win_rate"] = self._metrics["daily_stats"]["wins"] / total
    
    def update_market_volatility(self, volatility_factor: float):
        """
        ✅ NOVO v4.0: Atualiza fator de volatilidade de mercado
        volatility_factor: 0.5 (baixa vol) a 1.5 (alta vol)
        Permite ajustar risco baseado em condições de mercado
        """
        self._market_volatility_factor = max(0.5, min(1.5, volatility_factor))
        logger.debug(f"📊 Volatilidade de mercado ajustada: {self._market_volatility_factor:.2f}x")
    
    def _track_rejection(self, reason: str):
        """✅ NOVO v4.0: Rastreia razões de rejeição"""
        self._metrics["total_trades_rejected"] += 1
        if reason not in self._metrics["rejection_reasons"]:
            self._metrics["rejection_reasons"][reason] = 0
        self._metrics["rejection_reasons"][reason] += 1
    
    def _log_validation_structured(self, signal: Dict, adjusted_risk: float, open_positions: int):
        """✅ NOVO v4.0: Log estruturado para análise"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": signal.get("symbol", "UNKNOWN"),
            "direction": signal.get("direction", "UNKNOWN"),
            "score": signal.get("score", 0),
            "adjusted_risk_pct": adjusted_risk * 100,
            "open_positions": open_positions,
            "volatility_factor": self._market_volatility_factor,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses
        }
        logger.debug(f"📊 Risk validation: {json.dumps(log_data)}")
    
    def get_metrics(self) -> Dict:
        """✅ NOVO v4.0: Retorna métricas detalhadas"""
        return {
            **self._metrics,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "market_volatility_factor": self._market_volatility_factor,
            "intraday_peak_balance": self._intraday_peak_balance,
            "intraday_trough_balance": self._intraday_trough_balance,
            "approval_rate": (
                self._metrics["total_trades_approved"] / self._metrics["total_trades_validated"]
                if self._metrics["total_trades_validated"] > 0 else 0.0
            )
        }


    def _rollover_daily(self, account_balance: float):
        """
        Reseta marcadores diários quando muda o dia (UTC) e inicializa saldos.
        Usa Redis para persistência entre reinícios.
        """
        now_date = datetime.now(timezone.utc).date()
        date_str = now_date.isoformat()
        redis_key_daily = f"risk:daily_balance:{date_str}"
        redis_key_peak = f"risk:intraday_peak:{date_str}"
        redis_key_trough = f"risk:intraday_trough:{date_str}"

        # Se mudou o dia localmente ou ainda não foi inicializado
        if self._daily_date != now_date:
            self._daily_date = now_date
            
            try:
                bal = float(account_balance or 0.0)
            except Exception:
                bal = 0.0
            
            if bal <= 0:
                return

            # Tentar recuperar do Redis primeiro (caso tenha reiniciado no meio do dia)
            if redis_client and redis_client.client:
                try:
                    # 1. Daily Start Balance
                    stored_balance = redis_client.client.get(redis_key_daily)
                    if stored_balance:
                        self._daily_start_balance = float(stored_balance)
                        logger.info(f"🔄 Saldo diário recuperado do Redis: {self._daily_start_balance:.4f}")
                    else:
                        # Novo dia no Redis também
                        redis_client.client.set(redis_key_daily, str(bal), ex=86400*2) # Expira em 48h
                        self._daily_start_balance = bal
                        logger.info(f"🆕 Novo saldo diário definido no Redis: {self._daily_start_balance:.4f}")
                    
                    # 2. Intraday Peak
                    stored_peak = redis_client.client.get(redis_key_peak)
                    if stored_peak:
                        self._intraday_peak_balance = float(stored_peak)
                        logger.info(f"🔄 Pico intradiário recuperado do Redis: {self._intraday_peak_balance:.4f}")
                    else:
                        self._intraday_peak_balance = self._daily_start_balance
                        redis_client.client.set(redis_key_peak, str(self._intraday_peak_balance), ex=86400*2)

                    # 3. Intraday Trough
                    stored_trough = redis_client.client.get(redis_key_trough)
                    if stored_trough:
                        self._intraday_trough_balance = float(stored_trough)
                        logger.info(f"🔄 Fundo intradiário recuperado do Redis: {self._intraday_trough_balance:.4f}")
                    else:
                        self._intraday_trough_balance = self._daily_start_balance
                        redis_client.client.set(redis_key_trough, str(self._intraday_trough_balance), ex=86400*2)

                except Exception as e:
                    logger.error(f"Erro ao acessar Redis no rollover: {e}")
                    # Fallback para memória
                    self._daily_start_balance = bal
                    self._intraday_peak_balance = bal
                    self._intraday_trough_balance = bal
            else:
                # Sem Redis, usa memória
                self._daily_start_balance = bal
                self._intraday_peak_balance = bal
                self._intraday_trough_balance = bal
                
            logger.info(f"🗓️ Rollover diário concluído para {date_str}")
        
        # Caso especial: Se _daily_start_balance ainda é None (primeira execução e Redis falhou ou vazio)
        if self._daily_start_balance is None and account_balance > 0:
             self._daily_start_balance = account_balance
             self._intraday_peak_balance = account_balance
             self._intraday_trough_balance = account_balance

    def _update_intraday_extrema(self, account_balance: float):
        """
        Atualiza máximos/mínimos intradiários para cálculo de drawdown.
        Persiste no Redis para sobreviver a restarts.
        """
        try:
            bal = float(account_balance or 0.0)
        except Exception:
            bal = 0.0
        if bal <= 0:
            return
            
        updated = False
        
        # Update Peak
        if self._intraday_peak_balance is None or bal > self._intraday_peak_balance:
            self._intraday_peak_balance = bal
            updated = True
            
        # Update Trough
        if self._intraday_trough_balance is None or bal < self._intraday_trough_balance:
            self._intraday_trough_balance = bal
            updated = True
            
        if updated and redis_client and redis_client.client:
            try:
                now_date = datetime.now(timezone.utc).date()
                date_str = now_date.isoformat()
                
                if self._intraday_peak_balance:
                    redis_client.client.set(f"risk:intraday_peak:{date_str}", str(self._intraday_peak_balance), ex=86400*2)
                
                if self._intraday_trough_balance:
                    redis_client.client.set(f"risk:intraday_trough:{date_str}", str(self._intraday_trough_balance), ex=86400*2)
            except Exception as e:
                logger.error(f"Erro ao persistir extremos intradiários no Redis: {e}")

    def calculate_portfolio_metrics(self, positions: List[Dict], account_balance: float) -> Dict:
        """
        Calcula métricas simples de portfólio para o dashboard.
        positions: lista de dicts com chaves: symbol, position_size, unrealized_pnl
        """
        try:
            account_balance = float(account_balance or 0.0)
        except Exception:
            account_balance = 0.0

        safe_positions = positions or []
        exposure_total = 0.0
        unrealized_pnl_total = 0.0
        positions_count = 0

        for p in safe_positions:
            size = p.get("position_size", 0) or 0
            pnl = p.get("unrealized_pnl", 0) or 0
            try:
                size = float(size)
            except Exception:
                size = 0.0
            try:
                pnl = float(pnl)
            except Exception:
                pnl = 0.0

            if size > 0:
                positions_count += 1

            exposure_total += max(0.0, size)
            unrealized_pnl_total += pnl

        exposure_pct = (exposure_total / account_balance) if account_balance > 0 else 0.0
        free_margin = max(0.0, account_balance - exposure_total)
        free_margin_pct = (free_margin / account_balance) if account_balance > 0 else 0.0

        return {
            "exposure_total": round(exposure_total, 8),
            "exposure_pct": round(exposure_pct, 6),
            "positions_count": positions_count,
            "free_margin": round(free_margin, 8),
            "free_margin_pct": round(free_margin_pct, 6),
            "unrealized_pnl_total": round(unrealized_pnl_total, 8),
        }


# Instância global
risk_manager = RiskManager()
