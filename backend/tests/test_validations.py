"""
✅ PR1.4: Testes de Validação

Testes unitários e de integração para validações de:
- Consistência de dados (binance_client)
- Estado do sistema (supervisor)
- Validações de latência (trading_loop)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from utils.binance_client import DataValidator, DataValidationError
from modules.supervisor import Supervisor, SystemStateError


class TestDataValidator:
    """Testes para DataValidator (binance_client)"""
    
    def test_validate_required_fields_success(self):
        """Testa validação de campos obrigatórios com sucesso"""
        data = {
            'totalWalletBalance': '1000.0',
            'availableBalance': '800.0',
            'positions': []
        }
        
        valid, missing = DataValidator.validate_required_fields('futures_account', data)
        
        assert valid is True
        assert len(missing) == 0
    
    def test_validate_required_fields_missing(self):
        """Testa validação de campos obrigatórios com campos faltando"""
        data = {
            'totalWalletBalance': '1000.0',
            # availableBalance faltando
            'positions': []
        }
        
        valid, missing = DataValidator.validate_required_fields('futures_account', data)
        
        assert valid is False
        assert 'availableBalance' in missing
    
    def test_validate_required_fields_invalid_value(self):
        """Testa validação de campos obrigatórios com valores inválidos"""
        data = {
            'totalWalletBalance': None,  # Valor inválido
            'availableBalance': '800.0',
            'positions': []
        }
        
        valid, missing = DataValidator.validate_required_fields('futures_account', data)
        
        assert valid is False
        assert 'totalWalletBalance_invalid' in missing
    
    def test_validate_required_fields_not_dict(self):
        """Testa validação quando data não é um dicionário"""
        data = "not a dict"
        
        valid, missing = DataValidator.validate_required_fields('futures_account', data)
        
        assert valid is False
        assert 'response_is_not_dict' in missing
    
    def test_validate_field_types_success(self):
        """Testa validação de tipos com sucesso"""
        data = {
            'totalWalletBalance': '1000.0',
            'availableBalance': 800.0,
            'price': '50000.00'
        }
        
        valid, invalid = DataValidator.validate_field_types(data)
        
        assert valid is True
        assert len(invalid) == 0
    
    def test_validate_field_types_invalid(self):
        """Testa validação de tipos com tipo incorreto"""
        data = {
            'totalWalletBalance': [1000.0],  # Lista invés de num/string
            'availableBalance': 800.0
        }
        
        valid, invalid = DataValidator.validate_field_types(data)
        
        assert valid is False
        assert 'totalWalletBalance_type_list' in invalid
    
    def test_validate_numeric_range_within_bounds(self):
        """Testa validação de range numérico dentro dos limites"""
        data = {'price': '50000.00'}
        
        valid = DataValidator.validate_numeric_range(
            data, 
            'price', 
            min_val=0, 
            max_val=100000
        )
        
        assert valid is True
    
    def test_validate_numeric_range_below_min(self):
        """Testa validação de range numérico abaixo do mínimo"""
        data = {'price': '-100.00'}
        
        valid = DataValidator.validate_numeric_range(
            data, 
            'price', 
            min_val=0
        )
        
        assert valid is False
    
    def test_validate_numeric_range_above_max(self):
        """Testa validação de range numérico acima do máximo"""
        data = {'price': '200000.00'}
        
        valid = DataValidator.validate_numeric_range(
            data, 
            'price', 
            max_val=100000
        )
        
        assert valid is False
    
    def test_validate_api_response_success(self):
        """Testa validação completa de resposta da API com sucesso"""
        data = {
            'totalWalletBalance': '1000.0',
            'availableBalance': '800.0',
            'positions': []
        }
        
        valid, error = DataValidator.validate_api_response('futures_account', data)
        
        assert valid is True
        assert error is None
    
    def test_validate_api_response_failure(self):
        """Testa validação completa de resposta da API com falha"""
        data = {
            'totalWalletBalance': '-100.0',  # Saldo negativo
            'availableBalance': '800.0',
            'positions': []
        }
        
        valid, error = DataValidator.validate_api_response('futures_account', data)
        
        assert valid is False
        assert error is not None
        assert error.field == 'futures_account_negative_balance'
    
    def test_compare_cache_vs_api_consistent(self):
        """Testa comparação cache vs API com valores consistentes"""
        cache_value = 1000.0
        api_value = 1005.0  # 0.5% diferença
        
        consistent = DataValidator.compare_cache_vs_api(
            'test_key',
            cache_value,
            api_value,
            tolerance_pct=5.0
        )
        
        assert consistent is True
    
    def test_compare_cache_vs_api_divergent(self):
        """Testa comparação cache vs API com valores divergentes"""
        cache_value = 1000.0
        api_value = 1100.0  # 10% diferença
        
        consistent = DataValidator.compare_cache_vs_api(
            'test_key',
            cache_value,
            api_value,
            tolerance_pct=5.0
        )
        
        assert consistent is False
    
    def test_compare_cache_vs_api_both_none(self):
        """Testa comparação cache vs API quando ambos são None"""
        cache_value = None
        api_value = None
        
        consistent = DataValidator.compare_cache_vs_api(
            'test_key',
            cache_value,
            api_value,
            tolerance_pct=5.0
        )
        
        assert consistent is True
    
    def test_safe_float_valid(self):
        """Testa conversão segura para float com valor válido"""
        result = DataValidator._safe_float("1000.50")
        
        assert result == 1000.50
    
    def test_safe_float_invalid(self):
        """Testa conversão segura para float com valor inválido"""
        result = DataValidator._safe_float("not_a_number")
        
        assert result is None
    
    def test_safe_float_nan(self):
        """Testa conversão segura para float com NaN"""
        result = DataValidator._safe_float(float('nan'))
        
        assert result is None


class TestSupervisor:
    """Testes para Supervisor (estado do sistema)"""
    
    @pytest.fixture
    def supervisor(self):
        """Fixture para criar supervisor"""
        return Supervisor()
    
    def test_heartbeat_registration(self, supervisor):
        """Testa registro de heartbeat"""
        supervisor.heartbeat("trading_loop")
        
        assert "trading_loop" in supervisor.heartbeats
        assert supervisor.heartbeats["trading_loop"] > 0
    
    def test_health_status_healthy(self, supervisor):
        """Testa status de saúde quando todos os componentes estão OK"""
        supervisor.heartbeat("trading_loop")
        supervisor.heartbeat("position_monitor")
        
        # Simular verificação de saúde (chamada direta)
        asyncio.run(supervisor._check_health())
        
        assert supervisor.system_state['health_status'] == 'healthy'
        assert len(supervisor.system_state['validation_errors']) == 0
    
    def test_health_status_degraded(self, supervisor):
        """Testa status de saúde quando componente está lento"""
        supervisor.heartbeat("trading_loop")
        # Position monitor com heartbeat antigo (simulado)
        supervisor.heartbeats["position_monitor"] = 0  # Muito antigo
        
        asyncio.run(supervisor._check_health())
        
        assert supervisor.system_state['health_status'] in ['degraded', 'critical']
    
    def test_circuit_breaker_activation(self, supervisor):
        """Testa ativação do circuit breaker"""
        asyncio.run(supervisor.trigger_circuit_breaker("Test reason", cooldown_hours=1))
        
        assert supervisor.system_state['circuit_breaker_active'] is True
        assert supervisor.system_state['circuit_breaker_reason'] == "Test reason"
        assert supervisor.system_state['circuit_breaker_triggered_at'] is not None
    
    def test_circuit_breaker_reset(self, supervisor):
        """Testa reset do circuit breaker"""
        # Ativar primeiro
        asyncio.run(supervisor.trigger_circuit_breaker("Test reason"))
        
        # Resetar
        supervisor.reset_circuit_breaker()
        
        assert supervisor.system_state['circuit_breaker_active'] is False
        assert supervisor.system_state['circuit_breaker_reason'] is None
    
    def test_get_status_comprehensive(self, supervisor):
        """Testa retorno completo de status"""
        supervisor.heartbeat("trading_loop")
        
        status = supervisor.get_status()
        
        # Verificar campos principais
        assert 'monitoring' in status
        assert 'restarts' in status
        assert 'components' in status
        assert 'system' in status
        assert 'circuit_breaker' in status
        assert 'health_status' in status
        assert 'last_validation' in status
        assert 'validation_errors' in status
        assert 'recent_state_history' in status
    
    def test_get_status_components(self, supervisor):
        """Testa status detalhado dos componentes"""
        supervisor.heartbeat("trading_loop")
        
        status = supervisor.get_status()
        
        assert "trading_loop" in status['components']
        component = status['components']['trading_loop']
        assert 'status' in component
        assert 'last_heartbeat_ago' in component
        assert 'threshold' in component
    
    def test_get_status_system_resources(self, supervisor):
        """Testa status detalhado de recursos do sistema"""
        status = supervisor.get_status()
        
        system = status['system']
        assert 'cpu_percent' in system
        assert 'cpu_status' in system
        assert 'memory_mb' in system
        assert 'memory_status' in system
        assert 'disk_percent' in system
        assert 'disk_status' in system
        
        # Status deve ser um de: ok, warning, critical, error
        assert system['cpu_status'] in ['ok', 'warning', 'critical', 'error']
        assert system['memory_status'] in ['ok', 'warning', 'critical', 'error']
    
    def test_state_history_management(self, supervisor):
        """Testa gerenciamento de histórico de estados"""
        # Salvar alguns estados
        for i in range(5):
            supervisor._save_state_to_history()
        
        assert len(supervisor.state_history) == 5
        
        # Verificar limites do histórico
        for i in range(200):
            supervisor._save_state_to_history()
        
        # Deve manter apenas max_history (100)
        assert len(supervisor.state_history) <= supervisor.max_history
    
    def test_resource_thresholds(self, supervisor):
        """Testa configuração de thresholds de recursos"""
        assert 'memory_warning_mb' in supervisor.resource_thresholds
        assert 'memory_critical_mb' in supervisor.resource_thresholds
        assert 'cpu_warning_pct' in supervisor.resource_thresholds
        assert 'cpu_critical_pct' in supervisor.resource_thresholds
        assert 'disk_warning_pct' in supervisor.resource_thresholds
        assert 'disk_critical_pct' in supervisor.resource_thresholds
        
        # Verificar valores razoáveis
        assert supervisor.resource_thresholds['memory_warning_mb'] < supervisor.resource_thresholds['memory_critical_mb']
        assert supervisor.resource_thresholds['cpu_warning_pct'] < supervisor.resource_thresholds['cpu_critical_pct']


class TestSystemStateError:
    """Testes para SystemStateError"""
    
    def test_system_state_error_creation(self):
        """Testa criação de SystemStateError"""
        error = SystemStateError("test_component", "test reason", "critical")
        
        assert error.component == "test_component"
        assert error.reason == "test reason"
        assert error.severity == "critical"
    
    def test_system_state_error_string_representation(self):
        """Testa representação string de SystemStateError"""
        error = SystemStateError("test_component", "test reason", "warning")
        
        error_str = str(error)
        assert "[WARNING]" in error_str
        assert "test_component" in error_str
        assert "test reason" in error_str


class TestDataValidationError:
    """Testes para DataValidationError"""
    
    def test_data_validation_error_creation(self):
        """Testa criação de DataValidationError"""
        error = DataValidationError("test_field", "test reason", {"data": "test"})
        
        assert error.field == "test_field"
        assert error.reason == "test reason"
        assert error.data == {"data": "test"}
    
    def test_data_validation_error_string_representation(self):
        """Testa representação string de DataValidationError"""
        error = DataValidationError("test_field", "test reason")
        
        error_str = str(error)
        assert "test_field" in error_str
        assert "test reason" in error_str
        assert "Validação falhou" in error_str


# Testes de integração

@pytest.mark.asyncio
class TestIntegration:
    """Testes de integração entre validações"""
    
    async def test_supervisor_with_validation_errors(self):
        """Testa supervisor com múltiplos erros de validação"""
        supervisor = Supervisor()
        
        # Simular múltiplos componentes com problemas
        supervisor.heartbeats["trading_loop"] = 0  # Morto
        supervisor.heartbeats["position_monitor"] = 0  # Morto
        
        await supervisor._check_health()
        
        # Verificar que status é crítico
        assert supervisor.system_state['health_status'] == 'critical'
        
        # Verificar que erros foram registrados
        assert len(supervisor.system_state['validation_errors']) >= 2
    
    async def test_circuit_breaker_with_cooldown(self):
        """Testa circuit breaker com expiração de cooldown"""
        supervisor = Supervisor()
        
        # Ativar com cooldown curto
        await supervisor.trigger_circuit_breaker("Test", cooldown_hours=0)
        
        assert supervisor.system_state['circuit_breaker_active'] is True
        
        # Verificar cooldown
        await supervisor._check_circuit_breaker()
        
        # Deve ter expirado (cooldown de 0 horas)
        assert supervisor.system_state['circuit_breaker_active'] is False
    
    async def test_supervisor_status_all_components(self):
        """Testa status do supervisor com todos os componentes"""
        supervisor = Supervisor()
        
        # Registrar todos os componentes
        for component in supervisor.thresholds.keys():
            supervisor.heartbeat(component)
        
        # Simular verificação de saúde para atualizar system_state
        await supervisor._check_health()
        
        status = supervisor.get_status()
        
        # Todos os componentes devem estar no status
        for component in supervisor.thresholds.keys():
            assert component in status['components']
        
        # Status geral deve ser healthy
        assert status['health_status'] == 'healthy'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
