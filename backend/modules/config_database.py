"""
Configuration Database Models
Tabelas para gerenciamento de configurações do sistema com histórico
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Configuration(Base):
    """Tabela de configurações do sistema"""
    __tablename__ = "configurations"
    
    # Chave primária
    key = Column(String(100), primary_key=True)
    
    # Valor (pode ser string, número, JSON, etc)
    value = Column(Text, nullable=True)
    value_type = Column(String(20))  # 'string', 'int', 'float', 'bool', 'json'
    
    # Metadados
    description = Column(Text, nullable=True)
    category = Column(String(50))  # 'bot', 'sniper', 'risk', 'scanner', 'general'
    is_sensitive = Column(Boolean, default=False)  # Para ocultar em logs/exports
    
    # Histórico e controle de versão
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), default='system')  # 'api', 'admin', 'migration', 'system'
    version = Column(Integer, default=1)
    
    # Validação
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    allowed_values = Column(JSON, nullable=True)  # Para enums (ex: [True, False])
    
    def __repr__(self):
        return f"<Configuration(key='{self.key}', value='{self.value}', type='{self.value_type}')>"


class ConfigurationHistory(Base):
    """Histórico de mudanças de configuração para audit trail"""
    __tablename__ = "configuration_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    changed_by = Column(String(100))  # Quem fez a mudança
    reason = Column(Text, nullable=True)  # Motivo da mudança (opcional)
    
    def __repr__(self):
        return f"<ConfigurationHistory(key='{self.config_key}', at='{self.changed_at}', by='{self.changed_by}')>"
