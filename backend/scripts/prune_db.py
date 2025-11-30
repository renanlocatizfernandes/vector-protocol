import sys
import os
import csv
from datetime import datetime, timedelta
from sqlalchemy import text

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal, engine
from utils.logger import setup_logger

logger = setup_logger("db_pruner")

def prune_old_trades(days_to_keep: int = 30):
    """
    Arquiva trades mais antigos que 'days_to_keep' em CSV e os remove do banco.
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        logger.info(f"🧹 Iniciando limpeza de trades anteriores a {cutoff_date.isoformat()}...")
        
        # Selecionar trades antigos
        query = text("""
            SELECT * FROM trades 
            WHERE exit_time IS NOT NULL 
            AND exit_time < :cutoff
        """)
        result = db.execute(query, {"cutoff": cutoff_date})
        trades = result.fetchall()
        
        if not trades:
            logger.info("✅ Nenhum trade antigo para arquivar.")
            return

        # Arquivar em CSV
        archive_dir = "/home/renan/crypto-trading-bot/data/archive"
        os.makedirs(archive_dir, exist_ok=True)
        filename = f"{archive_dir}/trades_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Escrever header
            if trades:
                writer.writerow(result.keys())
                writer.writerows(trades)
                
        logger.info(f"📦 {len(trades)} trades arquivados em {filename}")
        
        # Deletar do banco
        delete_query = text("""
            DELETE FROM trades 
            WHERE exit_time IS NOT NULL 
            AND exit_time < :cutoff
        """)
        db.execute(delete_query, {"cutoff": cutoff_date})
        db.commit()
        logger.info("🗑️ Trades antigos removidos do banco de dados.")
        
    except Exception as e:
        logger.error(f"❌ Erro ao podar banco de dados: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    prune_old_trades(days_to_keep=30)
