import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

# Mock env vars BEFORE importing backend modules
os.environ['BINANCE_API_KEY'] = 'mock_key'
os.environ['BINANCE_API_SECRET'] = 'mock_secret'
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/db'
os.environ['POSTGRES_USER'] = 'user'
os.environ['POSTGRES_PASSWORD'] = 'pass'
os.environ['POSTGRES_DB'] = 'db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from backend.modules.autonomous_bot import AutonomousBot
from backend.modules.signal_generator import SignalGenerator
from backend.modules.correlation_filter import correlation_filter
from backend.config.settings import get_settings
from backend.api.models.trades import Trade
from backend.api.database import SessionLocal

async def test_phase2_features():
    print("🚀 Iniciando Teste Phase 2: Execution & Risk Management")
    
    # 1. Testar Sector Guard
    print("\n🛡️ Testando Sector Guard...")
    # Simular posições abertas em L1
    open_positions = [
        {'symbol': 'BTCUSDT', 'positionAmt': '0.1'},
        {'symbol': 'ETHUSDT', 'positionAmt': '1.0'},
        {'symbol': 'SOLUSDT', 'positionAmt': '10.0'}
    ]
    
    # Tentar abrir mais uma L1 (ADA)
    allowed_l1 = correlation_filter.check_sector_exposure('ADAUSDT', open_positions)
    print(f"  ADAUSDT (L1) permitido? {allowed_l1} (Esperado: False, pois já tem 3 L1)")
    
    # Tentar abrir DeFi (UNI)
    allowed_defi = correlation_filter.check_sector_exposure('UNIUSDT', open_positions)
    print(f"  UNIUSDT (DeFi) permitido? {allowed_defi} (Esperado: True)")
    
    # 2. Testar Chandelier Stop
    print("\n🛑 Testando Chandelier Stop...")
    sg = SignalGenerator()
    import pandas as pd
    # Mock DF com ATR
    df = pd.DataFrame({
        'close': [100.0] * 50,
        'high': [105.0] * 50,
        'low': [95.0] * 50,
        'atr': [2.0] * 50  # ATR = 2.0
    })
    
    # Long: Entry 100, ATR 2.0, Mult 3.0 -> Stop = 100 - (2*3) = 94
    sl_long = sg._calculate_stop_loss(df, 'LONG', 100.0)
    print(f"  Long SL (Entry 100, ATR 2): {sl_long} (Esperado: ~94.0)")
    
    # Short: Entry 100, ATR 2.0, Mult 3.0 -> Stop = 100 + (2*3) = 106
    sl_short = sg._calculate_stop_loss(df, 'SHORT', 100.0)
    print(f"  Short SL (Entry 100, ATR 2): {sl_short} (Esperado: ~106.0)")
    
    # 3. Testar Smart DCA Logic (Simulação)
    print("\n📉 Testando Smart DCA Logic (Simulação)...")
    bot = AutonomousBot()
    # Mock RSI calculation
    df_rsi = pd.DataFrame({'close': [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]}) # Price dropping
    rsi = bot._calculate_rsi_quick(df_rsi)
    print(f"  RSI calculado (Price dropping): {rsi:.2f}")
    
    print("\n✅ Teste Phase 2 concluído!")

if __name__ == "__main__":
    asyncio.run(test_phase2_features())
