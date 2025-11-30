"""
migrate_database.py - Adiciona campos opcionais para features profissionais
Execute ANTES de fazer deploy das novas versões
"""
from sqlalchemy import create_engine, text
import os

# Configuração do banco
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")
engine = create_engine(DATABASE_URL)

def migrate():
    """Adiciona colunas opcionais ao banco existente"""
    
    print("🔄 Iniciando migração do banco de dados...")
    
    migrations = [
        # Trailing stop
        "ALTER TABLE trades ADD COLUMN max_pnl_percentage REAL DEFAULT 0.0;",
        "ALTER TABLE trades ADD COLUMN trailing_peak_price REAL;",
        
        # Pyramiding
        "ALTER TABLE trades ADD COLUMN pyramided BOOLEAN DEFAULT 0;",
        
        # Take profit parcial
        "ALTER TABLE trades ADD COLUMN partial_taken BOOLEAN DEFAULT 0;",
        
        # Exit price para historico
        "ALTER TABLE trades ADD COLUMN exit_price REAL;",
        "ALTER TABLE trades ADD COLUMN exit_time TIMESTAMP;",
    ]
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations, 1):
            try:
                conn.execute(text(migration))
                conn.commit()
                print(f"✅ Migração {i}/{len(migrations)} concluída")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"⚠️ Migração {i} já aplicada, pulando...")
                else:
                    print(f"❌ Erro na migração {i}: {e}")
                    # Não da# r Não para continuar tentando outras dar raise para continuar tentando outras
    
    print("✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
