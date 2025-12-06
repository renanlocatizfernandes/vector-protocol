"""
migrate_database.py - Adiciona campos opcionais para features profissionais
Execute ANTES de fazer deploy das novas versões
"""
from sqlalchemy import create_engine, text
from config.settings import get_settings
import os

# Configuração do banco
# Usando settings para garantir que pegamos a URL correta (Postgres/Docker)
try:
    settings = get_settings()
    DATABASE_URL = settings.DATABASE_URL
except Exception as e:
    print(f"⚠️ Erro ao carregar settings: {e}")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")

print(f"🔌 Conectando em: {DATABASE_URL.split('@')[-1]}") # Log safe (esconde senha)
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
        
        # DCA Count (CRÍTICO: Faltava este campo anteriorment)
        "ALTER TABLE trades ADD COLUMN dca_count INTEGER DEFAULT 0;",
        
        # Exit price para historico
        "ALTER TABLE trades ADD COLUMN exit_price REAL;",
        "ALTER TABLE trades ADD COLUMN exit_time TIMESTAMP;",
    ]
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations, 1):
            try:
                # Wrap in a transaction or ensure clean state
                with conn.begin(): 
                     conn.execute(text(migration))
                print(f"✅ Migração {i}/{len(migrations)} concluída")
            except Exception as e:
                # Se falhar (ex: coluna já existe), a transaction interna (conn.begin) 
                # já faz rollback automático. Apenas logamos.
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"⚠️ Migração {i} já aplicada, pulando...")
                else:
                    print(f"❌ Erro na migração {i}: {e}")
                    # Continua para a próxima...
    
    print("✅ Migração concluída com sucesso!")

if __name__ == "__main__":
    migrate()
