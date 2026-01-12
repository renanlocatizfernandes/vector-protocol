# Guia Completo do Telegram

## 📱 Visão Geral

O projeto possui **dois componentes de Telegram** integrados:

### 1. **Telegram Bot (Controle)** - `backend/modules/telegram_bot.py`
Permite que você **controle** o bot enviando comandos:
- Inicie e pare o bot remotamente
- Verifique status e balance em tempo real
- Feche posições manualmente
- Execute comandos de gestão

### 2. **Telegram Notifier (Notificações)** - `backend/utils/telegram_notifier.py`
Envia **notificações automáticas** para o seu Telegram:
- Trades abertos/fechados
- Stop loss e take profit atingidos
- Pyramiding e DCA executados
- Breakeven e trailing stop
- Erros críticos e alertas
- Relatórios diários e de portfólio

## 🔗 Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram                           │
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │   Comandos (Bot)    │  │  Notificações       │   │
│  │  /start, /stop...   │←→│  Trades, SL, TP...  │   │
│  └──────────────────────┘  └──────────────────────┘   │
└────────────┬────────────────────────┬─────────────────┘
             │                        │
    ┌────────▼────────┐      ┌───────▼──────────┐
    │ telegram_bot.py │      │telegram_notifier  │
    │  (Handler)     │      │    (Sender)      │
    └────────┬───────┘      └───────┬──────────┘
             │                      │
    ┌────────▼──────────────────────▼──────────┐
    │      Sistema de Trading (Backend)          │
    └───────────────────────────────────────────┘
```

## 🔧 Configuração Inicial

### 1. Criar um Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie o comando `/newbot`
3. Escolha um nome para o bot (ex: "Vector Protocol Bot")
4. Escolha um username para o bot (ex: `@vector_protocol_bot`)
5. **Copie o TOKEN** fornecido (algo como `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Obter seu Chat ID

Você precisa saber seu Chat ID para que o bot aceite apenas seus comandos:

**Método 1 - Usando @userinfobot:**
1. Procure por **@userinfobot** no Telegram
2. Inicie uma conversa com `/start`
3. O bot responderá com seu **ID numérico**

**Método 2 - Via API:**
```bash
# Substitua SEU_BOT_TOKEN pelo token obtido
curl https://api.telegram.org/botSEU_BOT_TOKEN/getUpdates

# Envie uma mensagem qualquer para o seu bot no Telegram
# Execute o curl novamente e procure por "chat":{"id":123456789}
# O número depois de "id" é seu Chat ID
```

### 3. Configurar Variáveis de Ambiente

Edite o arquivo `.env` na raiz do projeto:

```bash
# Telegram Configuration
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

**Importante:**
- O bot só aceitará comandos do Chat ID configurado
- Mantenha essas informações seguras - nunca commit o `.env`
- Se usar Docker, certifique-se de que as variáveis estão disponíveis no container

### 4. Iniciar o Bot com Telegram

```bash
# Se estiver usando Docker Compose
docker compose up --build -d

# Ou se estiver rodando localmente
# O bot será iniciado automaticamente quando o autonomous_bot.start() for chamado
```

## 🤖 Comandos de Controle (Bot Handler)

### `/start`
Inicia o bot de trading autônomo.

### `/start`
Inicia o bot de trading autônomo.

**Uso:**
```
/start
```

**Resposta:**
- Se bot já rodando: `⚠️ O bot já está rodando!`
- Se bot parado: `🚀 Iniciando o bot...`

**Exemplo:**
```
/start
```

---

### `/stop`
Para o bot de trading autônomo.

**Uso:**
```
/stop
```

**Resposta:**
- Se bot já parado: `⚠️ O bot já está parado.`
- Se bot rodando: `🛑 Parando o bot...` → `✅ Bot parado com sucesso.`

**Exemplo:**
```
/stop
```

---

### `/status`
Mostra o status atual do bot, incluindo:
- Estado (ONLINE/OFFLINE)
- Modo (DRY RUN/LIVE)
- Score mínimo configurado
- Posições abertas vs máximo permitido

**Uso:**
```
/status
```

**Resposta Exemplo:**
```
🤖 STATUS DO BOT

Estado: 🟢 ONLINE
Modo: DRY RUN
Score Min: 70
Posições: 2/4
```

---

### `/balance`
Mostra o saldo disponível em USDT na conta da Binance.

**Uso:**
```
/balance
```

**Resposta Exemplo:**
```
💰 Saldo Disponível: 1234.56 USDT
```

**Nota:** Se houver erro ao consultar, será exibido uma mensagem de erro.

---

### `/force_exit [SYMBOL|ALL]`
Força o fechamento de uma posição específica ou de todas as posições.

**Uso:**
```
/force_exit SYMBOL    # Fecha posição específica
/force_exit ALL       # Fecha todas as posições
```

**Exemplos:**
```
/force_exit BTCUSDT
/force_exit ALL
```

**Resposta:**
- Se não informar símbolo: `⚠️ Uso: /force_exit SYMBOL (ou ALL)`
- Se SYMBOL: `⚠️ Fechamento forçado de BTCUSDT ainda não implementado via comando.`
- Se ALL: `⚠️ Fechando TODAS as posições... (Implementar lógica)`

**Nota:** Este comando está parcialmente implementado. Para fechar posições específicas, recomenda-se usar a API REST diretamente.

---

### `/help`
Mostra a lista de comandos disponíveis.

**Uso:**
```
/help
```

**Resposta:**
```
🤖 COMANDOS DISPONÍVEIS

/start - Inicia o bot
/stop - Para o bot
/status - Ver status atual
/balance - Ver saldo USDT
/help - Ajuda
```

## 🔐 Segurança

### Autenticação
O bot possui autenticação baseada em **Chat ID**:
- Apenas o Chat ID configurado pode enviar comandos
- Tentativas de outros usuários são registradas nos logs com aviso de acesso negado

### Logs
Todos os comandos são registrados:
```python
logger.warning(f"Acesso negado: Chat ID {update.effective_chat.id}")
```

### Boas Práticas
1. **Nunca compartilhe** seu BOT_TOKEN ou CHAT_ID
2. **Nunca commit** o arquivo `.env`
3. Use **testnet** antes de produção
4. Verifique logs regularmente para detectar tentativas de acesso não autorizadas

## 🧪 Testando a Configuração

### 1. Testar Comando `/help`
Após iniciar o bot, envie `/help` para verificar se está respondendo:

```
/help
```

**Resultado esperado:**
```
🤖 COMANDOS DISPONÍVEIS

/start - Inicia o bot
/stop - Para o bot
/status - Ver status atual
/balance - Ver saldo USDT
/help - Ajuda
```

### 2. Verificar Logs
Verifique se o bot está rodando corretamente nos logs:

```bash
# Docker
docker logs -f trading-bot-api | grep telegram

# Local
# Procure por mensagens como:
# 🤖 Telegram Bot Command Handler iniciado!
```

### 3. Testar Conexão com Binance
Use `/balance` para testar a conexão:

```
/balance
```

**Resultado esperado:**
```
💰 Saldo Disponível: XXXX.XX USDT
```

**Se der erro:**
```
❌ Erro ao consultar saldo: [detalhes do erro]
```

Verifique as credenciais da Binance no `.env`.

## 🚨 Solução de Problemas

### Bot não responde aos comandos

**Possíveis causas:**
1. `TELEGRAM_ENABLED=False` no `.env`
2. BOT_TOKEN ou CHAT_ID incorretos
3. Bot não iniciado (autonomous_bot não chamou `telegram_bot.start()`)
4. Problema de conexão com API do Telegram

**Soluções:**
```bash
# 1. Verifique se está habilitado
grep TELEGRAM_ENABLED .env

# 2. Verifique os logs
docker logs -f trading-bot-api | grep -i telegram

# 3. Teste o token manualmente
curl https://api.telegram.org/botSEU_TOKEN/getMe

# 4. Verifique se o bot está rodando
/status  # No Telegram
```

### "Acesso negado" ao enviar comandos

**Causa:** Chat ID incorreto no `.env`

**Solução:**
1. Obtenha seu Chat ID novamente usando @userinfobot
2. Atualize `TELEGRAM_CHAT_ID` no `.env`
3. Reinicie o bot

### Erro ao consultar saldo

**Possíveis causas:**
1. Credenciais Binance incorretas
2. Problema de conexão com Binance API
3. Taxa limite excedida (rate limit)

**Soluções:**
1. Verifique `BINANCE_API_KEY` e `BINANCE_API_SECRET`
2. Verifique se `BINANCE_TESTNET=True` está correto
3. Aguarde alguns minutos e tente novamente
4. Consulte logs: `docker logs trading-bot-api | grep binance`

## 📊 Notificações Automáticas (Telegram Notifier)

O sistema envia automaticamente notificações para o seu Telegram quando eventos importantes ocorrem.

### 🚀 Eventos de Ciclo de Vida

#### `notify_startup(version, mode)`
Notifica quando o bot é iniciado.

```
🚀 BOT INICIADO

🤖 Versão: v4.0
🌍 Modo: LIVE
⏰ Hora: 14:30:45

✅ Sistema online e monitorando o mercado.
```

#### `notify_shutdown(reason)`
Notifica quando o bot é parado.

```
🛑 BOT PARADO

📌 Motivo: Manual
⏰ Hora: 18:45:20

⚠️ O monitoramento foi interrompido.
```

### 📈 Eventos de Trades

#### `notify_trade_opened(trade_data)`
Notifica quando uma posição é aberta.

**Dados incluídos:**
- Símbolo
- Direção (LONG/SHORT)
- Preço de entrada
- Quantidade
- Alavancagem
- Stop Loss
- Take Profit
- Estratégia de TP

```
🟢 TRADE ABERTO

📊 Símbolo: BTCUSDT
📈 Direção: LONG
💰 Entry: 42350.500000
📦 Qtd: 0.0235
⚡ Lev: 10x

🛑 SL: 42000.000000
🎯 TP: 43000.000000
✨ Strategy: FIBONACCI
```

#### `notify_trade_closed(trade_data)`
Notifica quando uma posição é fechada.

**Dados incluídos:**
- Símbolo e direção
- Preço de entrada e saída
- P&L em USDT e porcentagem
- Motivo do fechamento

```
✅ TRADE FECHADO

📊 Símbolo: ETHUSDT
📈 Direção: LONG
💵 Entry: 3250.500000
💵 Exit: 3300.000000

💰 P&L: +12.45 USDT (+1.46%)
📌 Motivo: Take Profit
```

### 🎯 Eventos de Take Profit

#### `notify_take_profit_hit(symbol, tp_level, price)`
Notifica quando um nível de TP é atingido.

```
🎯 TAKE PROFIT ATINGIDO

📊 Símbolo: SOLUSDT
📌 Nível: Parcial
💵 Preço: 125.500000

✅ Lucro parcial realizado.
```

### 🛑 Eventos de Stop Loss

#### `notify_stop_loss_hit(symbol, entry_price, exit_price, pnl, pnl_pct, reason)`
Notifica quando o Stop Loss é acionado.

```
🛑 STOP LOSS ATINGIDO

📊 Símbolo: BTCUSDT
📌 Motivo: Stop Loss

💵 Entry: 42350.500000
💵 Exit: 42000.000000

💸 P&L: -8.24 USDT (-1.96%)
```

#### `notify_emergency_stop(symbol, pnl_pct)`
Notifica quando um Emergency Stop é ativado.

```
🚨 EMERGENCY STOP LOSS

📊 Símbolo: DOGEUSDT
📉 Prejuízo: -5.50%

⚠️ Posição fechada forçadamente para limitar danos.
```

### 🛡️ Eventos de Breakeven

#### `notify_breakeven_activated(symbol, entry_price, breakeven_price, pnl_pct)`
Notifica quando o stop é movido para breakeven.

```
🛡️ BREAKEVEN STOP ATIVADO

📊 Símbolo: LINKUSDT
💰 Entry: 15.250000
🔒 Breakeven: 15.250000
📈 Lucro Atual: +8.00%

✅ Ganho protegido! Risco zero a partir de agora.
```

#### `notify_breakeven_hit(symbol, entry_price, breakeven_price, exit_price, pnl_pct)`
Notifica quando o breakeven stop é acionado.

```
🛡️ BREAKEVEN STOP EXECUTADO

📊 Símbolo: LINKUSDT
📈 Entry: 15.250000
🔒 Breakeven: 15.250000
📉 Exit: 15.250000

💰 P&L Final: +0.02%

✅ Posição fechada em breakeven - nenhuma perda!
```

### 🏃 Eventos de Trailing Stop

#### `notify_trailing_activated(symbol, pnl_pct)`
Notifica quando o trailing stop é ativado.

```
🏃 TRAILING STOP ATIVADO

📊 Símbolo: AVAXUSDT
💰 Lucro Atual: +15.50%

🔒 Lucro será protegido dinamicamente.
```

#### `notify_trailing_executed(symbol, peak_price, close_price, pnl)`
Notifica quando o trailing stop executa.

```
✅ TRAILING STOP EXECUTADO

📊 Símbolo: AVAXUSDT
📈 Pico: 42.500000
📉 Exit: 41.750000

💰 Lucro Final: +18.45 USDT
```

### 🧱 Eventos de Pyramiding

#### `notify_pyramiding_executed(symbol, pnl_pct, quantity, price)`
Notifica quando pyramiding é executado (adiciona em trade vencedor).

```
🧱 PYRAMIDING EXECUTADO

📊 Símbolo: BTCUSDT
💰 Lucro Atual: +5.20%
📦 Adicionado: 0.0120
💵 Preço: 42500.000000

✅ Aumentando exposição em trade vencedor!
```

### 📉 Eventos de DCA

**Enviado via `send_message()` no position_monitor.py:**

```
📉 SMART DCA #2

BTCUSDT LONG
Motivo: Price dropped -6.0%
Novo Preço Médio: 42250.5000
```

### 📊 Eventos de Portfólio

#### `send_portfolio_update(positions, total_pnl)`
Envia atualização completa do portfólio.

```
📊 PORTFÓLIO ATIVO

🟢 BTCUSDT LONG
   P&L: +25.50 USDT (+1.20%)

🔴 ETHUSDT SHORT
   P&L: -12.30 USDT (-0.45%)

🟢 SOLUSDT LONG
   P&L: +8.75 USDT (+2.10%)

💰 P&L Total: +21.95 USDT
```

#### `send_portfolio_report(portfolio_data)`
Envia relatório detalhado do portfólio.

```
📈 RELATÓRIO DE PORTFÓLIO

💰 Saldo: 5425.50 USDT
📊 Abertas: 3
💵 P&L Total: +45.20 USDT

Posições:
🟢 BTCUSDT: +25.50 USDT (+1.20%)
🔴 ETHUSDT: -12.30 USDT (-0.45%)
🟢 SOLUSDT: +8.75 USDT (+2.10%)
```

### 📅 Relatórios Diários

#### `send_daily_summary(stats)` / `send_daily_report(stats)`
Envia resumo diário de performance.

**Dados incluídos:**
- P&L total
- Número de trades
- Win rate
- Melhor e pior trade
- Saldo atual
- Posições abertas

```
📅 RESUMO DIÁRIO

🟢 P&L Total: +125.50 USDT
📈 Trades: 15 (12 fechados)
🎯 Win Rate: 75.0%

🏆 Melhor: SOLUSDT (+45.20)
📉 Pior: DOGEUSDT (-15.50)

💰 Saldo: 5425.50 USDT
📊 Abertas: 3
```

### ⚠️ Eventos de Erro e Alertas

#### `notify_error(context, error)`
Notifica erro crítico.

```
❌ ERRO CRÍTICO

📂 Contexto: Order Execution
⚠️ Erro: Insufficient margin
⏰ Hora: 14:35:20

🛠️ Verifique os logs imediatamente.
```

#### `notify_info(title, message)`
Notifica informação genérica.

```
ℹ️ CIRCUIT BREAKER RESET

O circuit breaker foi resetado automaticamente.
⏰ 14:35:20
```

#### `notify_risk_alert(symbol, current_price, stop_price, distance_pct)`
Alerta de risco iminente.

```
⚠️ ALERTA DE RISCO

📊 Símbolo: BTCUSDT
📍 Preço: 42150.000000
🛑 Stop: 42000.000000

⚠️ Distância: 0.35%
```

### 🚨 Eventos Especiais

**Circuit Breaker Ativado:**
```
🚨 CIRCUIT BREAKER ATIVADO

❌ Perda consecutiva: 3 trades
📉 P&L Diário: -45.20 USDT (-2.5%)
⏰ Hora: 15:20:30

🛑 Bot parado automaticamente.
```

**Kill Switch Ativado:**
```
🚨 KILL SWITCH ATIVADO

📊 Motivo: Drawdown excedeu limite
📉 Drawdown Atual: -25.0%
⏰ Hora: 16:45:00

🛑 Todas as posições fechadas.
```

**Hedge Ativado:**
```
🛡️ Hedge Ativado

📊 Símbolo: BTCUSDT SHORT
📦 Tamanho: 0.0500
💵 Preço: 42500.000000

🛑 Proteção contra downturn do mercado.
```

**TP Ladder Executado:**
```
💰 TP Ladder Nível 1: BTCUSDT

📊 Nível: 1 de 3
💵 Preço: 43000.000000
📦 Fechado: 30.00% da posição

🎯 Realizando lucro parcial.
```

**Funding Exit:**
```
💰 FUNDING EXIT

📊 Símbolo: ETHUSDT
🕐 Funding em: 25 minutos
📈 P&L Atual: +2.5%

💰 Fechando antes do funding adverso.
```

### 📍 Mensagens Genéricas

#### `send_message(message, parse_mode="HTML")`
Envia qualquer mensagem formatada.

**Uso em todo o código:**
```python
await telegram_notifier.send_message(
    f"🎯 Sniper loop concluído\n"
    f"Alvo: 5 | Abertas: 3"
)
```

**Exemplos de uso real no código:**
- Notificações de sniper loop
- Mensagens de abertura estratégica
- Alertas de símbolo bloqueado
- Confirmações de circuit breaker resetado
- Mensagens de início/parada do bot

### Logs Estruturados

Todos os eventos são registrados no backend:
```python
logger.info("🤖 Telegram Bot Command Handler iniciado!")
logger.warning("Acesso negado: Chat ID {chat_id}")
```

Acesse os logs via:
```bash
# API REST
curl -sS "http://localhost:8000/api/system/logs?component=telegram&tail=100"

# Docker
docker logs -f trading-bot-api
```

## 🔗 Integração com API REST

Além do Telegram, você pode controlar o bot via API REST:

### Exemplos de Comandos via API:

**Iniciar Bot:**
```bash
curl -sS -X POST "http://localhost:8000/api/trading/bot/start?dry_run=false"
```

**Parar Bot:**
```bash
curl -sS -X POST "http://localhost:8000/api/trading/bot/stop"
```

**Status:**
```bash
curl -sS "http://localhost:8000/api/trading/bot/status"
```

**Fechar Posição:**
```bash
curl -sS -X POST "http://localhost:8000/api/trading/positions/close?symbol=BTCUSDT"
```

## 📝 Checklist de Configuração

- [ ] Criar bot no Telegram via @BotFather
- [ ] Copiar BOT_TOKEN
- [ ] Obter CHAT_ID via @userinfobot ou API
- [ ] Editar arquivo `.env` com:
  - [ ] `TELEGRAM_ENABLED=True`
  - [ ] `TELEGRAM_BOT_TOKEN=seu_token_aqui`
  - [ ] `TELEGRAM_CHAT_ID=seu_chat_id_aqui`
- [ ] Configurar credenciais Binance (se ainda não tiver)
- [ ] Iniciar o bot com `docker compose up --build -d`
- [ ] Testar comando `/help`
- [ ] Testar comando `/balance`
- [ ] Testar comando `/start` (em DRY RUN primeiro)
- [ ] Verificar logs para confirmar funcionamento

## 🎯 Melhores Práticas

1. **Comece em Testnet:**
   ```bash
   BINANCE_TESTNET=True
   BOT_DRY_RUN=True
   ```

2. **Monitore logs regularmente:**
   ```bash
   docker logs -f trading-bot-api
   ```

3. **Use `/status` frequentemente** para verificar saúde do bot

4. **Não use `/force_exit ALL`** em produção sem entender as consequências

5. **Mantenha backup** de suas configurações `.env`

6. **Teste todos os comandos** em ambiente de desenvolvimento antes de produção

## 📚 Arquitetura do Sistema

### Componentes de Telegram

#### 1. **telegram_bot.py** (`backend/modules/telegram_bot.py`)
- **Propósito:** Receber comandos do usuário
- **Comandos implementados:**
  - `/start` - Iniciar bot
  - `/stop` - Parar bot
  - `/status` - Ver status
  - `/balance` - Ver saldo
  - `/force_exit` - Fechar posições
  - `/help` - Ajuda

- **Autenticação:** Baseada em Chat ID
- **Inicia automaticamente:** Quando `autonomous_bot.start()` é chamado

#### 2. **telegram_notifier.py** (`backend/utils/telegram_notifier.py`)
- **Propósito:** Enviar notificações automáticas
- **Métodos principais:**
  - `send_message()` - Envio genérico
  - `send_alert()` - Envio de alertas
  - `notify_trade_opened()` - Trade aberto
  - `notify_trade_closed()` - Trade fechado
  - `notify_take_profit_hit()` - TP atingido
  - `notify_stop_loss_hit()` - SL atingido
  - `notify_breakeven_activated()` - Breakeven ativado
  - `notify_trailing_activated()` - Trailing ativado
  - `notify_pyramiding_executed()` - Pyramiding executado
  - `send_portfolio_update()` - Atualização de portfólio
  - `send_daily_summary()` - Resumo diário
  - E muito mais...

- **Características:**
  - Assíncrono (usando `httpx`)
  - Com retries automáticos (até 3 tentativas)
  - Tratamento de rate limits (429)
  - Formatação HTML suportada
  - Logs detalhados de sucesso/falha

#### 3. **telegram_bot_handler.py** (`backend/utils/telegram_bot_handler.py`)
- **Propósito:** Handler adicional de comandos
- **Comandos:**
  - `/status` - Status detalhado
  - `/portfolio` - Relatório de portfólio

**Nota:** Este arquivo parece ser uma implementação alternativa ou adicional ao `telegram_bot.py`.

### Integração com o Sistema

As notificações são enviadas em vários pontos do sistema:

**Em `position_monitor.py`:**
- Stop loss atingido
- Take profit atingido
- Breakeven ativado/executado
- Trailing stop ativado/executado
- DCA executado
- Time-based exit
- Funding exit
- Emergency stop
- Circuit breaker
- Kill switch

**Em `order_executor.py`:**
- Trade aberto com sucesso
- Erros de execução

**Em `autonomous_bot.py`:**
- Pyramiding executado
- Sniper loop concluído
- Abertura estratégica

**Em `daily_report.py`:**
- Relatório diário agendado

**Em `api/routes/trading.py`:**
- Bot iniciado/parado via API
- Teste de Telegram (`/api/trading/test/telegram`)

### Endpoints API para Telegram

#### Testar Notificação
```bash
curl -sS -X POST "http://localhost:8000/api/trading/test/telegram?text=Teste%20mensagem"
```

#### Resposta:
```json
{
  "success": true,
  "message": "Mensagem enfileirada",
  "text": "Teste mensagem"
}
```

### Configuração de Notificações

As notificações são controladas por variáveis de ambiente:

```bash
# Habilitar/Desabilitar Telegram
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
```

Se `TELEGRAM_ENABLED=False`, todas as notificações são silenciadas (sem erros).

### Formatação de Mensagens

O sistema usa **HTML Parse Mode** para formatação:

**Tags HTML suportadas:**
- `<b>negrito</b>` → **negrito**
- `<i>itálico</i>` → *itálico*
- `<code>código</code>` → `código`
- `<pre>pré-formatado</pre>` → bloco de código
- `<a href="url">link</a>` → link clicável

**Exemplo:**
```python
message = """
📊 <b>SÍMBOLO</b>: BTCUSDT
📈 <b>Direção</b>: <code>LONG</code>
💰 <b>Entry</b>: <a href="https://www.binance.com/en/futures/BTCUSDT">42350.5</a>
"""
```

### Rate Limits e Retries

O `telegram_notifier` possui tratamento robusto de erros:

- **Retries automáticos:** Até 3 tentativas
- **Backoff:** 5, 10 segundos entre tentativas
- **Rate limit (429):** Aguarda e retry automaticamente
- **Server errors (5xx):** Aguarda e retry
- **Outros erros:** Loga e para

**Exemplo de log:**
```
WARNING:telegram_notifier:Telegram HTTP 429; retry em 5s
WARNING:telegram_notifier:Falha Telegram (tentativa 2/3): ConnectionError - retry em 10s
```

## 📚 Recursos Adicionais

- **Documentação Principal:** [README.md](../README.md)
- **Guia de Operações:** [RUNBOOK.md](RUNBOOK.md)
- **Especificação da API:** [API_SPEC.md](API_SPEC.md)
- **Governança:** [GOVERNANCE.md](GOVERNANCE.md)
- **Arquitetura:** [ARCHITECTURE.md](ARCHITECTURE.md)

## 💬 Suporte

Se encontrar problemas:
1. Consulte os logs do bot: `docker logs trading-bot-api`
2. Verifique a documentação em `docs/`
3. Revise os arquivos de configuração
4. Teste a conexão com Binance API manualmente

---

**Última atualização:** 2026-01-10
**Versão:** 2.0.0

## 📝 Histórico de Versões

### v2.0.0 (2026-01-10)
- ✅ Documentação completa de notificações automáticas
- ✅ Integração com `telegram_notifier.py`
- ✅ Documentação de todos os eventos de trading
- ✅ Explicação da arquitetura de Telegram
- ✅ Exemplos de uso reais do código

### v1.0.0 (2026-01-10)
- ✅ Guia básico de configuração
- ✅ Comandos de controle via Telegram
- ✅ Configuração de BOT_TOKEN e CHAT_ID
