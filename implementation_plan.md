# Feature: Slots Dedicados para Reversão (Smart Reversal Buckets)

## Objetivo

Implementar um sistema de gerenciamento de slots (vagas para posições) segmentado, onde operações de Reversão (contra-tendência 4h) possuem um "balde" de slots dedicado e adicional, independente dos slots padrão de tendência.

## Regras de Negócio

1. **Segregação de Slots**:
    - `Trend Slots`: Padrão (ex: 10). Usado para operações a favor da tendência.
    - `Reversal Slots`: Adicional (ex: 50% de Trend, = 5). Usado apenas para Smart Reversal.
2. **Independência**:
    - O número de posições de reversão respeita seu próprio limite, independente do total geral estar cheio ou vazio.
3. **Gestão de Mudança de Tendência**:
    - Se a tendência mudar (ex: Alta -> Baixa), as posições antigas (Long) NÃO são fechadas forçadamente.
    - Elas continuam abertas e são gerenciadas normalmente (Stop Loss, Take Profit, Trailing Stop) até o encerramento natural.
    - Elas continuam ocupando o "slot" original onde foram criadas até serem encerradas.

## Mudanças Necessárias

### 1. Configuração (`backend/config/settings.py`)

- Adicionar `REVERSAL_EXTRA_SLOTS_PCT` (default: 0.5).
- Adicionar `REVERSAL_MAX_SLOTS` (opcional, se quiser fixo).

### 2. Geração de Sinal (`backend/modules/signal_generator.py`)

- Formalizar o campo `signal_type` ("TREND" ou "REVERSAL") na saída do sinal.
- Já implementamos a lógica de detecção, agora precisamos garantir que essa tag chegue no Risk Manager.

### 3. Gestão de Risco (`backend/modules/risk_manager.py`)

- **Desafio**: O Risk Manager precisa saber quantas posições *do tipo Reversão* estão abertas.
- **Solução via Redis**:
  - Como não vamos alterar schema do banco agora (Change Map level 1), usaremos Redis para trackear quais símbolos abertos são reversão.
  - Key: `positions:metadata:{symbol}` -> `{"type": "REVERSAL", ...}`.
- **Lógica de Validação**:
  - Ler `MAX_POSITIONS` (Trend).
  - Calcular `LIMIT_REVERSAL = MAX_POSITIONS * REVERSAL_EXTRA_SLOTS_PCT`.
  - Contar `open_trend` e `open_reversal`.
  - Se Sinal == REVERSAL: Validar se `open_reversal < LIMIT_REVERSAL`.
  - Se Sinal == TREND: Validar se `open_trend < MAX_POSITIONS`.

### 4. Execução (`backend/modules/order_executor.py`)

- Ao abrir posição com sucesso, salvar metadata no Redis marcando se foi REVERSAL ou TREND.
- Ao fechar posição, limpar essa metadata.

## Riscos

- **Dessincronia**: Se o Redis for limpo, perdemos a conta de quais são reversão.
  - *Mitigação*: Se metadata não existir, assumir "TREND" (conservador para novas reversões).
- **Complexidade**: Aumenta a lógica de validação.

## Plano de Testes

1. Configurar Max=2, Reversal=50% (1 slot).
2. Abrir 2 posições a favor da tendência (Trend Full).
3. Tentar abrir 3ª a favor -> Deve bloquear.
4. Tentar abrir 3ª contra (Reversão) -> Deve aceitar (Slot Reversal livre).
5. Tentar abrir 4ª contra -> Deve bloquear (Slot Reversal cheio).
