#!/usr/bin/env python3
"""
Script para migrar configurações do .env para o database

Este script pode ser executado COM O BOT RODANDO (zero downtime).
As configurações serão importadas do .env para o database PostgreSQL.

Uso:
    python scripts/migrate_to_database_config.py [--auto-confirm]

Features:
    ✅ Zero downtime - bot continua rodando
    ✅ Preserva histórico do .env
    ✅ Rollback imediato via reload-from-env
    ✅ Validação antes de importar
"""
import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.config_database import Base
from models.database import engine
from sqlalchemy import text
from modules.config_manager import ConfigManager
from config.settings import get_settings
from models.database import SessionLocal
from utils.logger import setup_logger

logger = setup_logger("migration")


def print_separator():
    """Imprime linha separadora"""
    print("\n" + "=" * 60)


async def check_prerequisites():
    """Verifica pré-requisitos antes de migrar"""
    print("\n🔍 Verificando pré-requisitos...")
    
    # 1. Verificar se database está acessível
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL Database acessível")
    except Exception as e:
        print(f"❌ PostgreSQL não acessível: {e}")
        print("\n💡 Solução: Verifique DATABASE_URL no .env")
        return False
    
    # 2. Verificar configurações importantes (já estão carregadas em settings)
    settings = get_settings()
    important_configs = [
        'BOT_MIN_SCORE', 'MAX_POSITIONS', 'RISK_PER_TRADE',
        'SNIPER_EXTRA_SLOTS', 'SNIPER_TP_PCT', 'SNIPER_SL_PCT'
    ]
    
    missing = []
    for config in important_configs:
        if not hasattr(settings, config):
            missing.append(config)
    
    if missing:
        print(f"⚠️  Alerta: Configurações não encontradas:")
        for config in missing:
            print(f"   • {config}")
        print("\n💡 Continuando mesmo assim (algumas configs podem ficar vazias)...")
    else:
        print(f"✅ Todas as configurações importantes disponíveis")
    
    return True


async def show_current_status():
    """Mostra status atual antes de migrar"""
    print_separator()
    print("📊 STATUS ATUAL")
    print_separator()
    
    try:
        db = SessionLocal()
        from modules.config_database import Configuration
        configs = db.query(Configuration).all()
        db.close()
        
        if not configs:
            print("📭 Database de configurações está VAZIO")
            print("   Esta é a primeira migração.")
        else:
            print(f"📋 Database já contém {len(configs)} configuração(ões):")
            print()
            for i, config in enumerate(configs[:10], 1):
                from modules.config_manager import ConfigManager
                cm = ConfigManager(db=db, env_settings=get_settings())
                value = cm._parse_value(config.value, config.value_type)
                print(f"   {i:2d}. {config.key:35s} = {value}")
            
            if len(configs) > 10:
                print(f"   ... e mais {len(configs) - 10} configurações")
    except Exception as e:
        print(f"❌ Erro ao verificar status atual: {e}")
        return False
    
    return True


async def confirm_migration(auto_confirm: bool = False):
    """Solicita confirmação do usuário"""
    print_separator()
    print("⚠️  MIGRAÇÃO DE CONFIGURAÇÕES")
    print_separator()
    print()
    print("Este script irá:")
    print("  1. Importar configurações do .env para o PostgreSQL")
    print("  2. Criar histórico inicial das configurações")
    print("  3. Atualizar cache do ConfigManager")
    print()
    print("✅ O BOT CONTINUARÁ RODANDO (zero downtime)")
    print("✅ Você pode fazer rollback imediato com: curl -X POST /api/database-config/reload-from-env")
    print()
    
    if auto_confirm:
        print("🤖 Auto-confirm ativado - prosseguindo...")
    else:
        try:
            response = input("Deseja continuar? (yes/no): ").strip().lower()
            
            if response not in ['yes', 'y', 'sim']:
                print("\n❌ Migração cancelada pelo usuário")
                return False
        except (EOFError, OSError):
            print("\n⚠️  Entrada não disponível (executando via Docker)")
            print("🤖 Usando auto-confirm")
    
    print("\n✅ Prosseguindo com migração...")
    return True


async def migrate_configurations():
    """Executa a migração das configurações"""
    print_separator()
    print("🚀 INICIANDO MIGRAÇÃO")
    print_separator()
    
    try:
        # Criar tabelas se não existirem
        print("\n📊 Criando tabelas do database de configurações...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas/verificadas")
        
        # Inicializar ConfigManager
        db = SessionLocal()
        settings = get_settings()
        config_manager = ConfigManager(
            db_session=db,
            env_settings=settings
        )
        
        # Recarregar configurações do .env
        print("\n📝 Importando configurações do .env para o database...")
        updated = await config_manager.reload_from_env()
        
        print(f"✅ {updated} configuração(ões) importada(s) com sucesso")
        
        # Mostrar resumo das configurações migradas
        print()
        print_separator()
        print("📋 RESUMO DAS CONFIGURAÇÕES MIGRADAS")
        print_separator()
        
        configs = await config_manager.get_all()
        
        # Agrupar por categoria
        by_category = {}
        for config in configs:
            cat = config['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(config)
        
        # Exibir por categoria
        for category in sorted(by_category.keys()):
            cat_configs = by_category[category]
            print(f"\n📁 {category.upper()} ({len(cat_configs)} configs)")
            for config in cat_configs:
                value = config['value']
                value_str = str(value)
                if len(value_str) > 40:
                    value_str = value_str[:37] + "..."
                print(f"   • {config['key']:35s} = {value_str}")
        
        db.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        return False


async def show_post_migration_instructions():
    """Mostra instruções pós-migração"""
    print()
    print_separator()
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print_separator()
    print()
    print("📌 PRÓXIMOS PASSOS:")
    print()
    print("1. ✅ Bot continuou rodando sem parar (zero downtime)")
    print("2. 📊 Todas as configurações agora estão no database PostgreSQL")
    print("3. 🔧 Você pode alterar configurações via API:")
    print("      GET  /api/database-config/")
    print("      PUT  /api/database-config/{key}")
    print("      POST /api/database-config/batch-update")
    print()
    print("4. 📋 Histórico de mudanças disponível:")
    print("      GET /api/database-config/history/{key}")
    print()
    print("5. 🔙 ROLLBACK (se necessário):")
    print("      curl -X POST http://localhost:8001/api/database-config/reload-from-env")
    print()
    print("6. 🖥️  Documentação completa:")
    print("      http://localhost:8001/docs#/Database%20Config")
    print()
    print_separator()
    print("⚠️  IMPORTANTE: O bot ainda usa .env como fallback")
    print("   Se você quiser usar APENAS database, edite o código")
    print("   para remover o fallback do ConfigManager.")
    print_separator()


async def main():
    """Função principal"""
    # Parse argumentos
    parser = argparse.ArgumentParser(description='Script de migração de configurações')
    parser.add_argument('--auto-confirm', action='store_true', help='Pula confirmação interativa')
    args = parser.parse_args()
    
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  DATABASE DE CONFIGURAÇÕES - SCRIPT DE MIGRAÇÃO  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("║" + "  Zero Downtime - Bot continua rodando".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.auto_confirm:
        print("  🤖 Auto-confirm: ATIVADO")
    print()
    
    # Verificar pré-requisitos
    if not await check_prerequisites():
        sys.exit(1)
    
    # Mostrar status atual
    if not await show_current_status():
        sys.exit(1)
    
    # Confirmar migração
    if not await confirm_migration(auto_confirm=args.auto_confirm):
        sys.exit(0)
    
    # Executar migração
    if not await migrate_configurations():
        print("\n❌ Migração falhou!")
        print("💡 O bot continua usando .env como fallback.")
        sys.exit(1)
    
    # Mostrar instruções pós-migração
    await show_post_migration_instructions()
    
    print("\n🎉 Sistema pronto para usar Database de Configurações!")
    print()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Migração interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
