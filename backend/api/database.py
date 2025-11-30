"""
Database configuration - API wrapper
Importa de models.database para manter compatibilidade
"""
from models.database import Base, SessionLocal, engine, get_db

__all__ = ['Base', 'SessionLocal', 'engine', 'get_db']
