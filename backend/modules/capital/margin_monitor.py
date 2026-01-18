"""
Margin Utilization Monitor
"""
from datetime import datetime
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger("margin_monitor")

class MarginUtilizationMonitor:
    """Monitors margin usage and prevents margin calls"""
    
    def analyze_margin_status(self, margin_used_pct: float, unrealized_pnl: float, wallet_balance: float) -> Dict:
        """Analyze current margin status"""
        if margin_used_pct > 90:
            zone = 'RED_ZONE'
            action = 'EMERGENCY_CLOSE'
            alert = 'CRITICAL: Close worst positions immediately'
        elif margin_used_pct > 75:
            zone = 'ORANGE_ZONE'
            action = 'REDUCE_POSITIONS'
            alert = 'DANGER: Reduce positions by 30%'
        elif margin_used_pct > 50:
            zone = 'YELLOW_ZONE'
            action = 'PAUSE_NEW_ENTRIES'
            alert = 'WARNING: Stop opening new positions'
        else:
            zone = 'GREEN_ZONE'
            action = 'NORMAL'
            alert = 'OK: Normal operation'
        
        safety_buffer = 100 - margin_used_pct
        
        return {
            'margin_used_pct': margin_used_pct,
            'zone': zone,
            'recommended_action': action,
            'alert_message': alert,
            'safety_buffer_pct': round(safety_buffer, 2),
            'can_open_new': margin_used_pct < 75,
            'timestamp': datetime.now().isoformat()
        }

margin_monitor = MarginUtilizationMonitor()
