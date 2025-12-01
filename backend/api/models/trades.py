"""
Trade Model - FINAL VERSION
✅ Campos novos: trailing, pyramiding, partial TP
"""
import sys
import os

current_file = os.path.abspath(__file__)
models_dir = os.path.dirname(current_file)
api_dir = os.path.dirname(models_dir)
backend_dir = os.path.dirname(api_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from models.database import Base


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}  # ← FIX!
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=True)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    
    status = Column(String, default='open', nullable=False)
    pnl = Column(Float, default=0.0, nullable=False)
    pnl_percentage = Column(Float, default=0.0, nullable=False)
    
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    order_id = Column(String, nullable=True)
    
    # ✅ NOVOS CAMPOS
    max_pnl_percentage = Column(Float, nullable=True, default=0.0)
    trailing_peak_price = Column(Float, nullable=True)
    pyramided = Column(Boolean, nullable=True, default=False)
    partial_taken = Column(Boolean, nullable=True, default=False)
    dca_count = Column(Integer, nullable=True, default=0)  # ✅ NOVO: Contador de DCA
    
    # Campos adicionais para historico
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    
