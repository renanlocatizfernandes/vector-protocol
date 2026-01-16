---
name: test-generator
description: Gera testes unitários seguindo padrões do projeto Vector Protocol. Suporta pytest (backend) e Vitest (frontend).
---

# Test Generator Skill

Este skill auxilia na geração de testes unitários e de integração para o projeto Vector Protocol.

---

## 🎯 Quando Usar

- Ao criar nova funcionalidade
- Ao corrigir bugs (teste de regressão)
- Quando a cobertura de testes é insuficiente
- Para validar refatorações

---

## 🐍 Backend (Python/pytest)

### Estrutura de Testes

```
backend/tests/
├── conftest.py              # Fixtures compartilhadas
├── test_public_endpoints.py # Testes de API
├── test_risk_manager*.py    # Testes de domínio
├── test_system_routes.py    # Testes de sistema
└── test_validations.py      # Testes de validação
```

### Padrão AAA (Arrange-Act-Assert)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import do módulo a testar
from modules.signal_generator import signal_generator


class TestSignalGenerator:
    """Testes para SignalGenerator."""
    
    @pytest.fixture
    def mock_binance_client(self):
        """Fixture para mock do cliente Binance."""
        client = MagicMock()
        client.get_symbol_price = AsyncMock(return_value=50000.0)
        client.get_klines = AsyncMock(return_value=[
            [1234567890, "50000", "51000", "49000", "50500", "1000"]
        ])
        return client
    
    @pytest.fixture
    def sample_scan_result(self):
        """Fixture com resultado de scan de exemplo."""
        return {
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "volume_24h": 1000000000,
            "change_24h": 2.5
        }
    
    @pytest.mark.asyncio
    async def test_generate_signal_happy_path(
        self, 
        mock_binance_client, 
        sample_scan_result
    ):
        """Testa geração de sinal em condições normais."""
        # Arrange
        with patch('modules.signal_generator.binance_client', mock_binance_client):
            # Act
            result = await signal_generator.generate_signal(sample_scan_result)
        
        # Assert
        assert result is not None
        assert "direction" in result
        assert result["direction"] in ["LONG", "SHORT", None]
        assert "score" in result
        assert 0 <= result["score"] <= 100
    
    @pytest.mark.asyncio
    async def test_generate_signal_invalid_symbol(self):
        """Testa comportamento com símbolo inválido."""
        # Arrange
        invalid_data = {"symbol": "INVALID"}
        
        # Act
        result = await signal_generator.generate_signal(invalid_data)
        
        # Assert
        assert result is None or result.get("score", 0) == 0
    
    @pytest.mark.asyncio
    async def test_generate_signal_low_volume(self, sample_scan_result):
        """Testa rejeição de símbolos com volume baixo."""
        # Arrange
        sample_scan_result["volume_24h"] = 100  # Volume muito baixo
        
        # Act
        result = await signal_generator.generate_signal(sample_scan_result)
        
        # Assert
        # Espera-se score baixo ou None
        assert result is None or result.get("score", 0) < 50
    
    @pytest.mark.parametrize("rsi,expected_direction", [
        (25, "LONG"),   # Oversold
        (75, "SHORT"),  # Overbought
        (50, None),     # Neutral
    ])
    @pytest.mark.asyncio
    async def test_rsi_signal_direction(self, rsi, expected_direction):
        """Testa direção do sinal baseado em RSI."""
        # Arrange
        mock_indicators = {"rsi": rsi}
        
        # Act & Assert
        # Implementar lógica específica baseada no módulo
        pass
```

### Fixtures Comuns (conftest.py)

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_settings():
    """Mock das configurações do sistema."""
    settings = MagicMock()
    settings.BINANCE_TESTNET = True
    settings.MAX_POSITIONS = 10
    settings.RISK_PER_TRADE = 0.02
    settings.BOT_MIN_SCORE = 70
    return settings

@pytest.fixture
def mock_redis():
    """Mock do cliente Redis."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis

@pytest.fixture
def mock_db_session():
    """Mock da sessão de banco de dados."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    return session
```

### Comando para Rodar

```bash
# Todos os testes
PYTHONPATH=backend pytest -q backend/tests

# Teste específico
PYTHONPATH=backend pytest backend/tests/test_file.py::TestClass::test_method -v

# Com cobertura (se pytest-cov instalado)
PYTHONPATH=backend pytest --cov=backend --cov-report=html backend/tests
```

---

## ⚛️ Frontend (TypeScript/Vitest)

### Estrutura de Testes

```
frontend/src/
├── App.test.tsx         # Testes do App principal
├── test/
│   └── setup.ts         # Setup do Vitest
└── components/
    └── ComponentName.test.tsx  # Co-localizado com componente
```

### Padrão de Teste React

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TradingDashboard } from './TradingDashboard';

// Mocks
vi.mock('../services/api', () => ({
  tradingApi: {
    getPositions: vi.fn(),
    getBotStatus: vi.fn(),
  },
}));

describe('TradingDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    // Arrange & Act
    render(<TradingDashboard />);
    
    // Assert
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should display positions after loading', async () => {
    // Arrange
    const mockPositions = [
      { symbol: 'BTCUSDT', side: 'LONG', pnl: 150.50 },
      { symbol: 'ETHUSDT', side: 'SHORT', pnl: -25.00 },
    ];
    
    vi.mocked(tradingApi.getPositions).mockResolvedValue(mockPositions);
    
    // Act
    render(<TradingDashboard />);
    
    // Assert
    await waitFor(() => {
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
    });
  });

  it('should handle start bot button click', async () => {
    // Arrange
    render(<TradingDashboard />);
    const startButton = screen.getByRole('button', { name: /start bot/i });
    
    // Act
    fireEvent.click(startButton);
    
    // Assert
    await waitFor(() => {
      expect(tradingApi.startBot).toHaveBeenCalledTimes(1);
    });
  });

  it('should display error message on API failure', async () => {
    // Arrange
    vi.mocked(tradingApi.getPositions).mockRejectedValue(new Error('API Error'));
    
    // Act
    render(<TradingDashboard />);
    
    // Assert
    await waitFor(() => {
      expect(screen.getByText(/error loading/i)).toBeInTheDocument();
    });
  });
});
```

### Comando para Rodar

```bash
cd frontend

# Rodar todos os testes
npm test

# Watch mode
npm run test -- --watch

# Com cobertura
npm run test -- --coverage
```

---

## 📋 Template de Geração

Quando solicitado a gerar testes, siga este template:

### 1. Identificar o Módulo

```markdown
**Módulo**: `backend/modules/risk_calculator.py`
**Classe/Função**: `RiskCalculator.calculate_position_size`
**Dependências**: binance_client, settings
```

### 2. Listar Casos de Teste

```markdown
**Happy Path:**
- [ ] Calcula tamanho correto com balanço suficiente
- [ ] Respeita limite de risco por trade
- [ ] Aplica alavancagem correta

**Edge Cases:**
- [ ] Balanço zero
- [ ] Risco = 0
- [ ] Preço = 0
- [ ] Leverage máximo

**Error Handling:**
- [ ] API Binance indisponível
- [ ] Símbolo inválido
- [ ] Margem insuficiente
```

### 3. Gerar Código de Teste

Seguir padrão AAA com mocks apropriados.

---

## ⚠️ Regras Importantes

1. **NUNCA delete testes existentes** para fazer build passar - corrija o código
2. Use **mocks** para dependências externas (Binance API, Telegram)
3. Testes devem ser **determinísticos** - sem dependência de estado externo
4. Nomeie testes de forma **descritiva**: `test_should_reject_low_volume_signals`
5. Mantenha testes **isolados** - um teste não deve afetar outro
6. Use **fixtures** para dados reutilizáveis
