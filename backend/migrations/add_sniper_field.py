"""
Migration: Add is_sniper field to trades table
"""
import sys
import os

# Adicionar backend ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from api.database import engine, SessionLocal
from api.models.trades import Trade
from utils.logger import setup_logger

logger = setup_logger("migration_add_sniper_field")


def migrate():
    """Adiciona a coluna is_sniper à tabela trades"""
    try:
        # Verificar se a coluna já existe (PostgreSQL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.columns
                WHERE table_name = 'trades' 
                AND column_name = 'is_sniper'
            """))
            exists = result.fetchone()[0] > 0
            
            if exists:
                logger.info("✅ Campo is_sniper já existe na tabela trades")
                return True
        
        # Adicionar a coluna (PostgreSQL)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE trades ADD COLUMN is_sniper BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("✅ Campo is_sniper adicionado com sucesso")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 Iniciando migração: Adicionar campo is_sniper")
    success = migrate()
    if success:
        logger.info("✅ Migração concluída com sucesso")
    else:
        logger.error("❌ Migração falhou")
        sys.exit(1)
