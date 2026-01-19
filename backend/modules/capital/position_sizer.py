"""
Smart Position Sizer using Kelly Criterion
"""
import math
from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger("position_sizer")

class SmartPositionSizer:
    """Position sizing using Kelly Criterion with adaptations"""
    
    def __init__(self):
        self.default_win_rate = 0.55
        self.default_win_loss_ratio = 1.5
        self.kelly_fraction = 0.5  # Half-Kelly for safety
    
    def calculate_kelly_size(
        self,
        capital: float,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        market_regime: Optional[str] = None,
        portfolio_heat: int = 0
    ) -> Dict:
        """Calculate position size using Kelly Criterion"""
        try:
            win_loss_ratio = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else 1.5
            kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
            kelly_pct = max(0, min(0.25, kelly_pct))  # Cap at 25%
            kelly_pct *= self.kelly_fraction  # Half-Kelly
            
            # Adjust by capital size
            if capital < 1000:
                capital_adj = 0.7
            elif capital > 5000:
                capital_adj = 1.2
            else:
                capital_adj = 1.0
            
            # Adjust by market regime
            regime_adj = {
                'STRONG_TREND': 1.3, 'TRENDING': 1.0,
                'RANGING': 0.7, 'HIGH_VOLATILITY': 0.5
            }.get(market_regime or '', 1.0)
            
            # Adjust by portfolio heat
            if portfolio_heat > 70:
                heat_adj = 0.3
            elif portfolio_heat > 50:
                heat_adj = 0.5
            elif portfolio_heat > 30:
                heat_adj = 0.8
            else:
                heat_adj = 1.0
            
            final_kelly_pct = kelly_pct * capital_adj * regime_adj * heat_adj
            position_size_usd = capital * final_kelly_pct
            
            return {
                'raw_kelly_pct': round(kelly_pct * 100, 2),
                'adjusted_kelly_pct': round(final_kelly_pct * 100, 2),
                'position_size_usd': round(position_size_usd, 2),
                'capital_adjustment': capital_adj,
                'regime_adjustment': regime_adj,
                'heat_adjustment': heat_adj,
                'recommendation': f"Risk {final_kelly_pct*100:.1f}% of capital (${position_size_usd:.2f})"
            }
        except Exception as e:
            logger.error(f"Kelly calculation error: {e}")
            return {'position_size_usd': capital * 0.02, 'adjusted_kelly_pct': 2.0}

position_sizer = SmartPositionSizer()
