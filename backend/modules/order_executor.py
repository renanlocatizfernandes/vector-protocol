"""
Order Executor - PROFESSIONAL VERSION v4.0
🔴 CORREÇÃO CRÍTICA #2: LIMIT orders com proteção de slippage
✅ Validação de maxQty ANTES de calcular margem
✅ Filtro de spread bid/ask (rejeita > 0.3%)
✅ Retry inteligente com backoff exponencial (3 tentativas)
✅ Ordens ICEBERG para grandes volumes (> $5000)
✅ Validação de liquidez antes da execução
✅ NOVO v4.0: Métricas estruturadas de execução (LIMIT vs MARKET, maker vs taker, slippage, tempo)
✅ NOVO v4.0: Logs estruturados (JSON) para análise
✅ NOVO v4.0: Dashboard de métricas de execução
"""
import asyncio
import time
import json
from typing import Dict, Optional, List
from datetime import datetime, timezone

from utils.binance_client import binance_client
from utils.logger import setup_logger
from config.settings import get_settings
from modules.risk_calculator import risk_calculator
from modules.risk_manager import risk_manager
from api.database import SessionLocal
from api.models.trades import Trade
from utils.telegram_notifier import telegram_notifier
from utils.helpers import round_step_size

logger = setup_logger("order_executor")


def _to_native(obj):
    """
    Converte numpy scalars/arrays para tipos Python nativos (float/int/list/dict).
    Evita erros de binding no PostgreSQL como 'schema "np" does not exist'.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None  # type: ignore

    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(x) for x in obj]

    if np is not None:
        try:
            if isinstance(obj, np.generic):  # numpy scalar
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except Exception:
            pass
    return obj


class OrderExecutor:
    def __init__(self):
        self.client = binance_client.client
        self.settings = get_settings()
        # Política de margem dinâmica
        self.default_margin_crossed = bool(getattr(self.settings, "DEFAULT_MARGIN_CROSSED", True))
        self.auto_isolate_min_leverage = int(getattr(self.settings, "AUTO_ISOLATE_MIN_LEVERAGE", 10))
        self.allow_margin_override = bool(getattr(self.settings, "ALLOW_MARGIN_MODE_OVERRIDE", True))
        
        # ✅ NOVO: Configurações de slippage e spread
        self.max_spread_pct = 0.3  # Máximo 0.3% de spread (menos restritivo para testnet)
        self.limit_order_buffer_pct = 0.05  # ✅ v5.0: Smart Entry - Buffer reduzido para 0.05% (antes 0.1%)
        self.limit_order_timeout = int(getattr(self.settings, "ORDER_TIMEOUT_SEC", 2))  # ✅ v5.0: Timeout mais rápido (2s)
        
        # ✅ NOVO: Retry configuration
        self.max_retries = 5  # ✅ v5.0: Mais tentativas de chase (antes 3)
        self.retry_delay_base = 0.5  # ✅ v5.0: Delay menor (0.5s)
        
        # ✅ NOVO: ICEBERG orders para grandes volumes
        self.iceberg_threshold = 5000  # $5000 USD
        self.iceberg_chunk_size = 2000  # $2000 por chunk
        
        # ✅ NOVO v4.0: Métricas estruturadas de execução
        self._metrics = {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "limit_orders": 0,
            "market_orders": 0,
            "iceberg_orders": 0,
            "maker_orders": 0,
            "taker_orders": 0,
            "total_slippage": 0.0,
            "total_execution_time": 0.0,
            "retry_count": 0,
            "re_quotes": 0,
            "order_details": []  # Últimas 100 execuções para análise
        }
        
        logger.info("✅ Order Executor PROFISSIONAL v4.0 inicializado")
        logger.info(f"📊 Max Spread: {self.max_spread_pct}%")
        logger.info(f"🎯 LIMIT Order Buffer: {self.limit_order_buffer_pct}%")
        logger.info(f"🔄 Max Retries: {self.max_retries}")
        logger.info(f"🧊 ICEBERG Threshold: ${self.iceberg_threshold}")
        logger.info(f"🧮 Margem: default={'CROSSED' if self.default_margin_crossed else 'ISOLATED'} • auto-isolate ≥ {self.auto_isolate_min_leverage}x • override={self.allow_margin_override}")
        logger.info(f"📊 Métricas estruturadas: ATIVAS")
    
    async def _validate_spread(self, symbol: str) -> tuple[bool, str]:
        """
        Valida se o spread bid/ask está dentro do limite aceitável.
        Evita entrar em momentos de alta volatilidade/baixa liquidez.
        """
        try:
            ticker = await asyncio.to_thread(self.client.futures_orderbook_ticker, symbol=symbol)
            bid = float(ticker.get('bidPrice', 0))
            ask = float(ticker.get('askPrice', 0))
            
            if bid <= 0 or ask <= 0:
                return False, "Orderbook vazio ou inválido"
                
            spread_pct = ((ask - bid) / ask) * 100
            
            if spread_pct > self.max_spread_pct:
                return False, f"Spread alto: {spread_pct:.3f}% > {self.max_spread_pct}%"
                
            return True, "Spread OK"
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao validar spread para {symbol}: {e}")
            # Em caso de erro de rede, assumimos risco e permitimos (fail open) 
            # ou bloqueamos (fail close)? 
            # Fail open para não travar o bot, mas logamos warning.
            return True, f"Spread check ignored: {e}"
    
    async def execute_signal(
        self,
        signal: Dict,
        account_balance: float,
        open_positions: int = 0,
        dry_run: bool = True
    ) -> Dict:
        """
        Executa sinal de trading com todas as validações e proteções
        """
        
        # Sanitizar sinal para remover numpy types (np.float64, etc.)
        signal = _to_native(signal)

        symbol = signal['symbol']
        direction = signal['direction']
        
        # ✅ NOVO v4.0: Iniciar tracking de métricas
        execution_start_time = time.time()
        order_type_used = None
        is_maker = False
        slippage = 0.0
        
        logger.info(f"🎯 Executando sinal: {symbol} {direction} (Score: {signal['score']:.0f})")
        
        try:
            # ================================
            # 1. VALIDAÇÕES INICIAIS
            # ================================
            
            # ✅ NOVO: Validar spread bid/ask ANTES de tudo
            spread_valid, spread_msg = await self._validate_spread(symbol)
            if not spread_valid:
                logger.warning(f"❌ {symbol}: {spread_msg}")
                return {'success': False, 'reason': spread_msg}
            
            # Obter informações do símbolo
            symbol_info = await binance_client.get_symbol_info(symbol)
            
            if not symbol_info:
                return {'success': False, 'reason': 'Símbolo não encontrado'}
            
            # ✅ CORREÇÃO CRÍTICA: Validar maxQty ANTES de calcular position size
            max_qty = float(symbol_info.get('max_quantity', 0))
            if max_qty == 0:
                logger.warning(f"❌ {symbol}: maxQty não disponível")
                return {'success': False, 'reason': 'maxQty não disponível'}
            
            # ================================
            # 2. CALCULAR POSITION SIZE
            # ================================
            
            # 2.1 Cálculo inicial com a alavancagem do sinal
            if signal.get('force') and signal.get('user_quantity'):
                # ✅ MANUAL TRADE: Usar quantidade definida pelo usuário
                quantity = float(signal['user_quantity'])
                margin_required = (quantity * signal['entry_price']) / signal['leverage']
                logger.info(f"🔧 Trade Manual: Usando quantidade definida {quantity}")
                risk_calc = {'approved': True, 'quantity': quantity, 'margin_required': margin_required}
            else:
                # Automático
                risk_calc = risk_calculator.calculate_position_size(
                    symbol=symbol,
                    direction=direction,
                    entry_price=signal['entry_price'],
                    stop_loss=signal['stop_loss'],
                    leverage=signal['leverage'],
                    account_balance=account_balance,
                    score=signal.get('score', 50)  # ✅ NOVO: Passar score
                )
            
            if not risk_calc['approved']:
                logger.warning(f"❌ {symbol}: {risk_calc['reason']}")
                return {'success': False, 'reason': risk_calc['reason']}
            
            quantity = risk_calc.get('quantity', quantity if 'quantity' in locals() else 0)
            margin_required = risk_calc.get('margin_required', margin_required if 'margin_required' in locals() else 0)

            # 2.2 Ajuste por Leverage Brackets (garantir alavancagem permitida para o notional)
            try:
                notional_est = float(signal['entry_price']) * float(quantity)
                max_lev_allowed = await binance_client.get_max_leverage_for_notional(symbol, notional_est)
                lev_used = int(signal['leverage'])
                if max_lev_allowed < lev_used:
                    logger.info(f"🛡️ {symbol}: Capping leverage {lev_used}x → {max_lev_allowed}x por leverage brackets (notional ~ {notional_est:.2f})")
                    # Recalcular tamanho com alavancagem permitida
                    rc2 = risk_calculator.calculate_position_size(
                        symbol=symbol,
                        direction=direction,
                        entry_price=signal['entry_price'],
                        stop_loss=signal['stop_loss'],
                        leverage=max_lev_allowed,
                        account_balance=account_balance
                    )
                    if rc2.get('approved'):
                        risk_calc = rc2
                        quantity = rc2['quantity']
                        margin_required = rc2['margin_required']
                        lev_used = max_lev_allowed
                    else:
                        logger.warning(f"⚠️ {symbol}: Recalculo com leverage {max_lev_allowed}x não aprovado ({rc2.get('reason')}) — mantendo cálculo anterior")
                effective_leverage = lev_used
            except Exception as e:
                logger.warning(f"⚠️ {symbol}: Falha ao aplicar leverage brackets: {e}")
                effective_leverage = int(signal['leverage'])
            
            # ✅ CORREÇÃO: Validar quantity vs maxQty ANTES de prosseguir
            if quantity > max_qty:
                logger.warning(
                    f"❌ {symbol}: Quantidade calculada ({quantity:.4f}) excede maxQty ({max_qty:.4f})"
                )
                # Ajustar para maxQty
                quantity = max_qty * 0.95  # 95% do máximo por segurança
                logger.info(f"📊 Ajustando quantidade para {quantity:.4f}")
            
            # Arredondar quantity
            quantity = round_step_size(quantity, symbol_info['step_size'])
            
            # ✅ Guard 1: quantidade após arredondamento não pode ser zero/negativa
            if quantity <= 0:
                logger.warning(f"❌ {symbol}: Quantity <= 0 após arredondamento; trade abortado.")
                return {'success': False, 'reason': 'Quantidade zero após arredondamento'}
            
            # ✅ Guard 2: notional mínimo exigido pelo símbolo
            try:
                min_notional = float(symbol_info.get('min_notional', 0) or 0)
            except Exception:
                min_notional = 0.0
            notional_now = float(quantity) * float(signal['entry_price'])
            if min_notional and notional_now < min_notional:
                logger.warning(f"❌ {symbol}: Notional {notional_now:.4f} < minNotional {min_notional:.4f}; trade abortado.")
                return {'success': False, 'reason': 'Notional abaixo do mínimo do símbolo'}
            
            # ================================
            # 3. VALIDAR COM RISK MANAGER (com bypass opcional para força)
            # ================================
            allow_bypass = bool(getattr(self.settings, "ALLOW_RISK_BYPASS_FOR_FORCE", False))
            if signal.get("force") and allow_bypass:
                validation = {"approved": True}
            else:
                validation = risk_manager.validate_trade(
                    signal=signal,
                    account_balance=account_balance,
                    open_positions=open_positions
                )
            
            if not validation['approved']:
                logger.warning(f"❌ {symbol}: {validation['reason']}")
                return {'success': False, 'reason': validation['reason']}
            
            # ================================
            # 4. Política de MARGEM (Cross/Isolated)
            #   - Padrão: DEFAULT_MARGIN_CROSSED
            #   - Auto-Isolate: quando leverage >= AUTO_ISOLATE_MIN_LEVERAGE
            # ================================
            desired_isolated = not self.default_margin_crossed
            try:
                if float(signal.get('leverage', 0) or 0) >= float(self.auto_isolate_min_leverage):
                    desired_isolated = True
            except Exception:
                pass
            planned_margin_txt = "ISOLATED" if desired_isolated else "CROSSED"

            # ================================
            # 5. DRY RUN
            # ================================
            
            if dry_run:
                logger.info(
                    f"🎯 DRY RUN: {symbol} {direction}\n"
                    f"  Entry: {signal['entry_price']:.4f}\n"
                    f"  Qty: {quantity:.4f}\n"
                    f"  Leverage: {signal['leverage']}x\n"
                    f"  Margin: {margin_required:.2f} USDT\n"
                    f"  Stop Loss: {signal['stop_loss']:.4f}\n"
                    f"  Take Profit: {signal['take_profit_1']:.4f}\n"
                    f"  Margin Mode (plano): {planned_margin_txt}"
                )
                
                return {
                    'success': True,
                    'dry_run': True,
                    'symbol': symbol,
                    'direction': direction,
                    'quantity': quantity,
                    'margin_required': margin_required
                }
            
            # ================================
            # 6. EXECUTAR ORDEM REAL
            # ================================
            
            # Garantir modo de margem conforme política antes de abrir ordem
            try:
                if self.allow_margin_override:
                    changed = await binance_client.ensure_margin_type(symbol=symbol, isolated=desired_isolated)
                    logger.info(f"✅ Margin type {'ajustado' if changed else 'confirmado'} para {symbol}: {planned_margin_txt}")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao garantir margin mode {planned_margin_txt} para {symbol}: {e}")

            # Configurar leverage (após ajuste por leverage brackets)
            try:
                await asyncio.to_thread(
                    self.client.futures_change_leverage,
                    symbol=symbol,
                    leverage=effective_leverage
                )
                logger.info(f"✅ Leverage configurado: {effective_leverage}x")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao configurar leverage: {e}")
            
            # ✅ NOVO: Verificar se deve usar ICEBERG
            position_value = signal['entry_price'] * quantity
            
            if position_value > self.iceberg_threshold:
                logger.info(f"🧊 Valor ${position_value:.0f} > ${self.iceberg_threshold} - Usando ICEBERG")
                order_result = await self._execute_iceberg_order(
                    symbol=symbol,
                    direction=direction,
                    quantity=quantity,
                    entry_price=signal['entry_price'],
                    symbol_info=symbol_info
                )
                order_type_used = "ICEBERG"
            else:
                # 🔴 CORREÇÃO CRÍTICA #2: Usar LIMIT orders (não MARKET)
                order_result = await self._execute_limit_order(
                    symbol=symbol,
                    direction=direction,
                    quantity=quantity,
                    entry_price=signal['entry_price'],
                    symbol_info=symbol_info
                )
                order_type_used = order_result.get('order_type', 'LIMIT')
                is_maker = order_result.get('is_maker', False)
                slippage = order_result.get('slippage', 0.0)
            
            if not order_result['success']:
                # ✅ NOVO v4.0: Tracking de falhas
                self._track_order_failure(symbol, order_type_used or "UNKNOWN", order_result.get('reason', 'Unknown'))
                return order_result
            
            # ================================
            # 6. PROTEÇÕES: SL (e opcionalmente TP em batch) + Trailing Stop
            # ================================
            side_opp = 'SELL' if direction == 'LONG' else 'BUY'
            working_type = 'MARK_PRICE' if self.settings.USE_MARK_PRICE_FOR_STOPS else 'CONTRACT_PRICE'

            placed_sl = False
            placed_tp = False

            if getattr(self.settings, "ENABLE_BRACKET_BATCH", False):
                try:
                    batch_orders = []
                    # SL obrigatório
                    sl_price = round_step_size(signal['stop_loss'], symbol_info['tick_size'])
                    batch_orders.append({
                        "symbol": symbol,
                        "side": side_opp,
                        "type": "STOP_MARKET",
                        "stopPrice": sl_price,
                        "workingType": working_type,
                        "reduceOnly": True,
                        "quantity": quantity
                    })
                    # TP ladder com frações configuráveis
                    tp_levels = [signal.get('take_profit_1'), signal.get('take_profit_2'), signal.get('take_profit_3')]
                    tp_levels = [float(x) for x in tp_levels if x is not None]
                    try:
                        parts = [float(x) for x in str(getattr(self.settings, "TAKE_PROFIT_PARTS", "0.5,0.3,0.2")).split(",") if str(x).strip()]
                    except Exception:
                        parts = []
                    if not parts:
                        parts = [1.0]
                    m = min(len(tp_levels), len(parts))
                    tp_levels = tp_levels[:m]
                    parts = parts[:m]
                    sum_parts = sum(parts) if parts else 1.0
                    remaining_qty = quantity
                    tp_txt = []
                    for idx, tp in enumerate(tp_levels):
                        price_i = round_step_size(tp, symbol_info['tick_size'])
                        if idx < len(tp_levels) - 1:
                            qty_i = round_step_size(quantity * (parts[idx] / sum_parts), symbol_info['step_size'])
                            qty_i = min(qty_i, remaining_qty)
                        else:
                            qty_i = round_step_size(remaining_qty, symbol_info['step_size'])
                        if qty_i <= 0:
                            continue
                        remaining_qty = max(0.0, remaining_qty - qty_i)
                        batch_orders.append({
                            "symbol": symbol,
                            "side": side_opp,
                            "type": "LIMIT",
                            "price": price_i,
                            "timeInForce": "GTC",
                            "reduceOnly": True,
                            "quantity": qty_i
                        })
                        tp_txt.append(f"{qty_i:.4f}@{price_i:.4f}")
                    # Enviar em uma única chamada
                    self.client.futures_place_batch_order(batchOrders=batch_orders)
                    placed_sl = True
                    placed_tp = len(tp_txt) > 0
                    logger.info(f"✅ Bracket (batch) enviado: SL @ {sl_price:.4f}" + (f" | TPs: {', '.join(tp_txt)}" if placed_tp else ""))
                except Exception as e:
                    logger.warning(f"⚠️ Falha no batch (SL/TP). Fallback para ordens individuais: {e}")

            if not placed_sl:
                stop_result = await self._set_stop_loss(
                    symbol=symbol,
                    direction=direction,
                    quantity=quantity,
                    stop_price=signal['stop_loss'],
                    symbol_info=symbol_info
                )
                if not stop_result['success']:
                    logger.warning(f"⚠️ Stop loss não configurado: {stop_result['reason']}")
                else:
                    placed_sl = True

            if (not placed_tp) and signal.get('take_profit_1'):
                try:
                    tp_levels = [signal.get('take_profit_1'), signal.get('take_profit_2'), signal.get('take_profit_3')]
                    tp_levels = [float(x) for x in tp_levels if x is not None]
                    try:
                        parts = [float(x) for x in str(getattr(self.settings, "TAKE_PROFIT_PARTS", "0.5,0.3,0.2")).split(",") if str(x).strip()]
                    except Exception:
                        parts = []
                    if not parts:
                        parts = [1.0]
                    m = min(len(tp_levels), len(parts))
                    tp_levels = tp_levels[:m]
                    parts = parts[:m]
                    sum_parts = sum(parts) if parts else 1.0
                    remaining_qty = quantity
                    tp_ok = 0
                    for idx, tp in enumerate(tp_levels):
                        if idx < len(tp_levels) - 1:
                            qty_i = round_step_size(quantity * (parts[idx] / sum_parts), symbol_info['step_size'])
                            qty_i = min(qty_i, remaining_qty)
                        else:
                            qty_i = round_step_size(remaining_qty, symbol_info['step_size'])
                        if qty_i <= 0:
                            continue
                        remaining_qty = max(0.0, remaining_qty - qty_i)
                        tp_res = await self._set_take_profit_limit(
                            symbol=symbol,
                            direction=direction,
                            quantity=qty_i,
                            take_profit=float(tp),
                            symbol_info=symbol_info
                        )
                        if tp_res.get('success'):
                            tp_ok += 1
                        else:
                            logger.warning(f"⚠️ TP parcial falhou: {tp_res.get('reason')}")
                    placed_tp = tp_ok > 0
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao configurar TPs parciais: {e}")

            # Trailing Stop opcional (reduceOnly) — adicional ao SL/TP
            if getattr(self.settings, "ENABLE_TRAILING_STOP", False):
                try:
                    tsl_res = await self._set_trailing_stop(
                        symbol=symbol,
                        direction=direction,
                        quantity=quantity,
                        entry_price=signal['entry_price'],
                        symbol_info=symbol_info
                    )
                    if not tsl_res['success']:
                        logger.warning(f"⚠️ Trailing Stop não configurado: {tsl_res['reason']}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao configurar Trailing Stop: {e}")
            
            # ================================
            # 6.1 P1 RISCO: Ajuste de headroom pós-abertura (trim reduceOnly)
            # ================================
            try:
                risk_info = await binance_client.get_position_risk(symbol)
                liq = float(risk_info.get("liquidationPrice", 0) or 0)
                ep = float(risk_info.get("entryPrice", 0) or 0)
                headroom_before = abs((ep - liq) / ep) * 100 if (ep and liq) else 999.0
                min_headroom = float(getattr(self.settings, "HEADROOM_MIN_PCT", 35.0))
                step_pct = float(getattr(self.settings, "REDUCE_STEP_PCT", 10.0))
                reduced_total = 0.0

                if headroom_before < min_headroom:
                    logger.info(f"🛡️ {symbol}: Headroom {headroom_before:.1f}% < {min_headroom:.1f}% — iniciando redução reduceOnly")
                    for _ in range(3):
                        if headroom_before >= min_headroom or quantity <= 0:
                            break
                        reduce_qty = round_step_size(quantity * (step_pct / 100.0), symbol_info['step_size'])
                        reduce_qty = min(reduce_qty, quantity)
                        if reduce_qty <= 0:
                            break
                        # Enviar ordem reduce-only MARKET no lado oposto
                        try:
                            await asyncio.to_thread(
                                self.client.futures_create_order,
                                symbol=symbol,
                                side=side_opp,
                                type='MARKET',
                                quantity=reduce_qty,
                                reduceOnly=True
                            )
                            quantity -= reduce_qty
                            reduced_total += reduce_qty
                            await asyncio.sleep(0.3)
                            # Reavaliar headroom
                            risk_info = await binance_client.get_position_risk(symbol)
                            liq = float(risk_info.get("liquidationPrice", 0) or 0)
                            ep = float(risk_info.get("entryPrice", 0) or 0)
                            headroom_before = abs((ep - liq) / ep) * 100 if (ep and liq) else min_headroom
                        except Exception as _e:
                            logger.warning(f"Falha ao reduzir posição: {_e}")
                            break
                    try:
                        from utils.telegram_notifier import telegram_notifier as _tn
                        await _tn.send_message(
                            f"🛡️ Ajuste de Risco\n\n"
                            f"Symbol: {symbol}\n"
                            f"Headroom final: {headroom_before:.1f}%\n"
                            f"Reduzido: {reduced_total:.4f} contratos"
                        )
                    except Exception:
                        pass
            except Exception as _e:
                logger.debug(f"Ajuste de headroom ignorado: {_e}")

            # ================================
            # 7. SALVAR NO BANCO DE DADOS
            # ================================
            
            db = SessionLocal()
            
            try:
                trade = Trade(
                    symbol=str(symbol),
                    direction=str(direction),
                    entry_price=float(order_result['avg_price']),
                    current_price=float(order_result['avg_price']),
                    quantity=float(quantity),
                    leverage=int(signal['leverage']),
                    stop_loss=float(signal['stop_loss']),
                    take_profit_1=(float(signal.get('take_profit_1')) if signal.get('take_profit_1') is not None else None),
                    take_profit_2=(float(signal.get('take_profit_2')) if signal.get('take_profit_2') is not None else None),
                    take_profit_3=(float(signal.get('take_profit_3')) if signal.get('take_profit_3') is not None else None),
                    status='open',
                    pnl=0.0,
                    pnl_percentage=0.0,
                    order_id=str(order_result['order_id'])
                )
                
                db.add(trade)
                db.commit()
                
                logger.info(
                    f"✅ Trade salvo no DB:\n"
                    f"  {symbol} {direction}\n"
                    f"  Entry: {order_result['avg_price']:.4f}\n"
                    f"  Qty: {quantity:.4f}\n"
                    f"  Margin: {margin_required:.2f} USDT"
                )
                
            finally:
                db.close()
            
            # ================================
            # 8. NOTIFICAR TELEGRAM
            # ================================
            
            try:
                await telegram_notifier.notify_trade_opened({
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": float(order_result['avg_price']),
                    "quantity": float(quantity),
                    "leverage": int(signal.get('leverage', 0) or 0),
                    "stop_loss": float(signal.get('stop_loss', 0) or 0),
                    "take_profit_1": float(signal.get('take_profit_1', 0) or 0)
                })
            except Exception as e:
                logger.warning(f"⚠️ Erro ao notificar Telegram: {e}")
            
            # ✅ NOVO v4.0: Finalizar tracking de métricas
            execution_time = time.time() - execution_start_time
            self._track_order_success(
                symbol=symbol,
                direction=direction,
                order_type=order_type_used or "UNKNOWN",
                is_maker=is_maker,
                slippage=slippage,
                execution_time=execution_time,
                quantity=quantity,
                entry_price=order_result['avg_price'],
                expected_price=signal['entry_price']
            )
            
            return {
                'success': True,
                'symbol': symbol,
                'direction': direction,
                'entry_price': order_result['avg_price'],
                'quantity': quantity,
                'margin_required': margin_required,
                'order_id': order_result['order_id']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar trade {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # ✅ NOVO v4.0: Tracking de erro
            execution_time = time.time() - execution_start_time
            self._track_order_failure(symbol, order_type_used or "UNKNOWN", str(e))
            
            return {
                'success': False,
                'reason': str(e)
            }
    
    
    async def _execute_limit_order(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: float,
        symbol_info: Dict
    ) -> Dict:
        """
        🔴 CORREÇÃO CRÍTICA #2: Executar LIMIT order com proteção de slippage
        """
        
        side = 'BUY' if direction == 'LONG' else 'SELL'
        
        # Calcular preço LIMIT com buffer
        if direction == 'LONG':
            limit_price = entry_price * (1 + self.limit_order_buffer_pct / 100)
        else:
            limit_price = entry_price * (1 - self.limit_order_buffer_pct / 100)
        
        # Arredondar preço
        limit_price = round_step_size(limit_price, symbol_info['tick_size'])
        
        logger.info(
            f"📊 LIMIT Order: {symbol} {side}\n"
            f"  Mark Price: {entry_price:.4f}\n"
            f"  Limit Price: {limit_price:.4f} (+{self.limit_order_buffer_pct}%)\n"
            f"  Quantity: {quantity:.4f}"
        )
        
        # ✅ NOVO: Retry com backoff exponencial
        for attempt in range(1, self.max_retries + 1):
            try:
                # Post-only (maker) opcional com decisão automática por spread
                tif = 'GTC'
                place_price = limit_price
                try:
                    ticker_po = await asyncio.to_thread(self.client.futures_orderbook_ticker, symbol=symbol)
                    bid_po = float(ticker_po.get('bidPrice') or 0)
                    ask_po = float(ticker_po.get('askPrice') or 0)
                    spread_bps = ((ask_po - bid_po) / (ask_po or 1)) * 10000 if (ask_po and bid_po) else 0.0

                    auto_post_only = bool(getattr(self.settings, "AUTO_POST_ONLY_ENTRIES", False))
                    spread_threshold = float(getattr(self.settings, "AUTO_MAKER_SPREAD_BPS", 3.0))
                    force_post_only = bool(getattr(self.settings, "USE_POST_ONLY_ENTRIES", False))
                    use_post_only = force_post_only or (auto_post_only and spread_bps >= spread_threshold)

                    if use_post_only and bid_po > 0 and ask_po > 0:
                        # Garantir maker-only (GTX): posicionar no book do lado passivo
                        if direction == 'LONG':
                            # Comprar como maker próximo ao bid (ligeiramente abaixo)
                            place_price = round_step_size(min(limit_price, bid_po * (1 - 0.0001)), symbol_info['tick_size'])
                        else:
                            # Vender como maker próximo ao ask (ligeiramente acima)
                            place_price = round_step_size(max(limit_price, ask_po * (1 + 0.0001)), symbol_info['tick_size'])
                        tif = 'GTX'
                except Exception as _e:
                    logger.debug(f"Ajuste maker automático falhou, usando GTC: {_e}")
                    place_price = limit_price
                    tif = 'GTC'

                order = await asyncio.to_thread(
                    self.client.futures_create_order,
                    symbol=symbol,
                    side=side,
                    type='LIMIT',
                    price=place_price,
                    quantity=quantity,
                    timeInForce=tif  # GTC ou GTX (post-only)
                )
                
                order_id = order['orderId']
                
                logger.info(f"✅ LIMIT Order criada: {order_id}")
                
                # Aguardar execução (timeout 10s)
                start_time = time.time()
                
                while time.time() - start_time < self.limit_order_timeout:
                    order_status = await asyncio.to_thread(
                        self.client.futures_get_order,
                        symbol=symbol,
                        orderId=order_id
                    )
                    
                    if order_status['status'] == 'FILLED':
                        avg_price = float(order_status['avgPrice'])
                        
                        logger.info(
                            f"✅ Ordem executada:\n"
                            f"  Order ID: {order_id}\n"
                            f"  Avg Price: {avg_price:.4f}"
                        )
                        
                        # ✅ NOVO v4.0: Calcular slippage e determinar se é maker
                        slippage_pct = abs((avg_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                        is_maker_order = (tif == 'GTX')
                        
                        return {
                            'success': True,
                            'order_id': order_id,
                            'avg_price': avg_price,
                            'order_type': 'LIMIT',
                            'is_maker': is_maker_order,
                            'slippage': slippage_pct
                        }
                    
                    await asyncio.sleep(0.5)
                
                # Timeout: cancelar e decidir próximo passo (re-quote ou fallback)
                logger.warning(f"⏱️ LIMIT order timeout após {self.limit_order_timeout}s")
                # ✅ NOVO v4.0: Tracking de re-quotes
                self._metrics["re_quotes"] += 1
                try:
                    await asyncio.to_thread(self.client.futures_cancel_order, symbol=symbol, orderId=order_id)
                    logger.info(f"🗑️ LIMIT order cancelada: {order_id}")
                except Exception as _e:
                    logger.debug(f"Cancelamento da LIMIT falhou/ignorado: {_e}")

                if attempt < self.max_retries:
                    # Re-quote inteligente: atualizar preço com base no book atual
                    try:
                        book = await asyncio.to_thread(self.client.futures_orderbook_ticker, symbol=symbol)
                        bid = float(book.get('bidPrice') or 0)
                        ask = float(book.get('askPrice') or 0)
                        if tif == 'GTX' and bid > 0 and ask > 0:
                            # Maker-only: ficar no lado passivo novamente
                            if direction == 'LONG':
                                limit_price = round_step_size(min(limit_price, bid * (1 - 0.0001)), symbol_info['tick_size'])
                            else:
                                limit_price = round_step_size(max(limit_price, ask * (1 + 0.0001)), symbol_info['tick_size'])
                        else:
                            # GTC: aproximar do mid para aumentar chance de fill
                            mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else limit_price
                            limit_price = round_step_size(mid, symbol_info['tick_size'])
                        logger.info(f"🔁 Re-quote {attempt+1}/{self.max_retries}: novo LIMIT @ {limit_price:.4f} (tif={tif})")
                    except Exception as _e:
                        logger.debug(f"Falha ao re-quotar, mantendo preço: {_e}")
                    # Voltar ao início do loop para nova tentativa
                    continue

                # Última tentativa: fallback para MARKET
                logger.info(f"🔄 Última tentativa: MARKET fallback...")
                market_order = await asyncio.to_thread(
                    self.client.futures_create_order,
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
                # ✅ Corrigir preço de entrada: buscar avg real da execução
                try:
                    avg_from_api = await binance_client.get_order_avg_price(symbol, market_order['orderId'])
                except Exception:
                    avg_from_api = 0.0
                avg_price = float(market_order.get('avgPrice') or 0) or float(avg_from_api or 0) or float(entry_price)

                logger.info(f"✅ MARKET order executada: {market_order['orderId']} @ {avg_price:.4f}")
                
                # ✅ NOVO v4.0: Calcular slippage para MARKET
                slippage_pct = abs((avg_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0

                return {
                    'success': True,
                    'order_id': market_order['orderId'],
                    'avg_price': avg_price,
                    'order_type': 'MARKET',
                    'is_maker': False,
                    'slippage': slippage_pct
                }
                
            except Exception as e:
                logger.error(f"❌ Tentativa {attempt}/{self.max_retries} falhou: {e}")
                # ✅ NOVO v4.0: Tracking de retries
                self._metrics["retry_count"] += 1
                
                if attempt < self.max_retries:
                    # Backoff exponencial
                    delay = self.retry_delay_base * (2 ** (attempt - 1))
                    logger.info(f"⏳ Aguardando {delay}s antes de retry...")
                    await asyncio.sleep(delay)
                else:
                    return {
                        'success': False,
                        'reason': f'Falha após {self.max_retries} tentativas: {str(e)}',
                        'order_type': 'LIMIT',
                        'is_maker': False,
                        'slippage': 0.0
                    }
    
    async def _execute_iceberg_order(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: float,
        symbol_info: Dict
    ) -> Dict:
        """
        ✅ NOVO: Executar ordem em chunks (ICEBERG)
        Para grandes volumes > $5000
        """
        
        logger.info(f"🧊 Executando ICEBERG order para {symbol}")
        
        # Calcular número de chunks
        chunk_value = self.iceberg_chunk_size
        total_value = entry_price * quantity
        num_chunks = int(total_value / chunk_value) + 1
        chunk_qty = quantity / num_chunks
        
        # Arredondar chunk_qty
        chunk_qty = round_step_size(chunk_qty, symbol_info['step_size'])
        
        logger.info(
            f"🧊 ICEBERG: {num_chunks} chunks de {chunk_qty:.4f} cada\n"
            f"  Total: {quantity:.4f}\n"
            f"  Chunk value: ~${chunk_value}"
        )
        
        total_filled = 0.0
        total_cost = 0.0
        order_ids = []
        
        for i in range(num_chunks):
            # Última chunk ajusta para completar quantity exata
            if i == num_chunks - 1:
                remaining = quantity - total_filled
                chunk_qty = round_step_size(remaining, symbol_info['step_size'])
            
            logger.info(f"🧊 Executando chunk {i+1}/{num_chunks}: {chunk_qty:.4f}")
            
            # Executar chunk como LIMIT order
            chunk_result = await self._execute_limit_order(
                symbol=symbol,
                direction=direction,
                quantity=chunk_qty,
                entry_price=entry_price,
                symbol_info=symbol_info
            )
            
            if not chunk_result['success']:
                logger.error(f"❌ Chunk {i+1} falhou: {chunk_result['reason']}")
                
                # Se falhou, cancelar chunks anteriores?
                # Por ora, continuar e reportar parcial
                break
            
            total_filled += chunk_qty
            total_cost += chunk_result['avg_price'] * chunk_qty
            order_ids.append(chunk_result['order_id'])
            
            # Aguardar 1s entre chunks (evitar rate limit)
            if i < num_chunks - 1:
                await asyncio.sleep(1)
        
        if total_filled == 0:
            return {
                'success': False,
                'reason': 'Nenhum chunk foi executado'
            }
        
        avg_price = total_cost / total_filled
        
        logger.info(
            f"✅ ICEBERG completado:\n"
            f"  Filled: {total_filled:.4f}/{quantity:.4f}\n"
            f"  Avg Price: {avg_price:.4f}\n"
            f"  Orders: {len(order_ids)}"
        )
        
        return {
            'success': True,
            'order_id': ','.join(map(str, order_ids)),  # Múltiplos IDs
            'avg_price': avg_price,
            'filled_quantity': total_filled,
            'order_type': 'ICEBERG',
            'is_maker': False,  # ICEBERG usa LIMIT, mas pode ser taker
            'slippage': abs((avg_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
        }
    
    async def _set_stop_loss(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        stop_price: float,
        symbol_info: Dict
    ) -> Dict:
        """Configurar stop loss"""
        
        try:
            side = 'SELL' if direction == 'LONG' else 'BUY'
            
            # Arredondar stop price
            stop_price = round_step_size(stop_price, symbol_info['tick_size'])
            
            workingType = 'MARK_PRICE' if self.settings.USE_MARK_PRICE_FOR_STOPS else 'CONTRACT_PRICE'
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                stopPrice=stop_price,
                quantity=quantity,
                reduceOnly=True,
                workingType=workingType
            )
            
            logger.info(f"✅ Stop loss configurado: {stop_price:.4f}")
            
            return {
                'success': True,
                'order_id': order['orderId']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar stop loss: {e}")
            return {
                'success': False,
                'reason': str(e)
            }
    
    async def _set_take_profit_limit(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        take_profit: float,
        symbol_info: Dict
    ) -> Dict:
        """Configurar take profit via LIMIT reduceOnly"""
        try:
            side = 'SELL' if direction == 'LONG' else 'BUY'
            price = round_step_size(take_profit, symbol_info['tick_size'])
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='LIMIT',
                price=price,
                timeInForce='GTC',
                quantity=quantity,
                reduceOnly=True
            )
            logger.info(f"✅ Take Profit LIMIT configurado: {price:.4f}")
            return {"success": True, "order_id": order['orderId']}
        except Exception as e:
            logger.error(f"❌ Erro ao configurar take profit: {e}")
            return {"success": False, "reason": str(e)}

    async def _set_trailing_stop(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: float,
        symbol_info: Dict
    ) -> Dict:
        """Configurar trailing stop com callbackRate calibrado por ATR"""
        try:
            side = 'SELL' if direction == 'LONG' else 'BUY'
            interval = getattr(self.settings, "TSL_ATR_LOOKBACK_INTERVAL", "15m")
            klines = await binance_client.get_klines(symbol, interval=interval, limit=50)
            atr = risk_calculator.calculate_atr(klines) if klines else 0.0
            atr_pct = (atr / entry_price * 100) if entry_price else 0.5
            cb_min = float(getattr(self.settings, "TSL_CALLBACK_PCT_MIN", 0.4))
            cb_max = float(getattr(self.settings, "TSL_CALLBACK_PCT_MAX", 1.2))
            callback_rate = max(cb_min, min(cb_max, atr_pct))
            # Binance aceita 0.1–5.0 com 1 casa; arredondar
            callback_rate = round(callback_rate, 1)

            workingType = 'MARK_PRICE' if self.settings.USE_MARK_PRICE_FOR_STOPS else 'CONTRACT_PRICE'
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='TRAILING_STOP_MARKET',
                callbackRate=callback_rate,
                reduceOnly=True,
                workingType=workingType,
                quantity=quantity
            )
            logger.info(f"✅ Trailing Stop configurado (callback {callback_rate:.1f}% • {workingType})")
            return {"success": True, "order_id": order['orderId']}
        except Exception as e:
            logger.error(f"❌ Erro ao configurar trailing stop: {e}")
            return {"success": False, "reason": str(e)}

    async def close_position(
        self,
        symbol: str,
        quantity: float,
        direction: str
    ) -> Dict:
        """Fechar posição"""
        
        try:
            side = 'SELL' if direction == 'LONG' else 'BUY'
            
            order = await asyncio.to_thread(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly=True
            )
            
            avg_price = float(order.get('avgPrice', 0))
            
            logger.info(
                f"✅ Posição fechada:\n"
                f"  Symbol: {symbol}\n"
                f"  Quantity: {quantity:.4f}\n"
                f"  Avg Price: {avg_price:.4f}"
            )
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'avg_price': avg_price
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao fechar posição: {e}")
            return {
                'success': False,
                'reason': str(e)
            }


    def _track_order_success(
        self,
        symbol: str,
        direction: str,
        order_type: str,
        is_maker: bool,
        slippage: float,
        execution_time: float,
        quantity: float,
        entry_price: float,
        expected_price: float
    ):
        """✅ NOVO v4.0: Rastreia ordem bem-sucedida"""
        self._metrics["total_orders"] += 1
        self._metrics["successful_orders"] += 1
        
        if order_type == "LIMIT":
            self._metrics["limit_orders"] += 1
        elif order_type == "MARKET":
            self._metrics["market_orders"] += 1
        elif order_type == "ICEBERG":
            self._metrics["iceberg_orders"] += 1
        
        if is_maker:
            self._metrics["maker_orders"] += 1
        else:
            self._metrics["taker_orders"] += 1
        
        self._metrics["total_slippage"] += slippage
        self._metrics["total_execution_time"] += execution_time
        
        # Armazenar detalhes (manter apenas últimas 100)
        order_detail = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "direction": direction,
            "order_type": order_type,
            "is_maker": is_maker,
            "slippage_pct": round(slippage, 4),
            "execution_time_sec": round(execution_time, 3),
            "quantity": quantity,
            "entry_price": entry_price,
            "expected_price": expected_price
        }
        
        self._metrics["order_details"].append(order_detail)
        if len(self._metrics["order_details"]) > 100:
            self._metrics["order_details"].pop(0)
        
        # ✅ NOVO v4.0: Log estruturado
        logger.debug(f"📊 Order execution: {json.dumps(order_detail)}")
    
    def _track_order_failure(self, symbol: str, order_type: str, reason: str):
        """✅ NOVO v4.0: Rastreia ordem falhada"""
        self._metrics["total_orders"] += 1
        self._metrics["failed_orders"] += 1
        
        failure_detail = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "order_type": order_type,
            "reason": reason
        }
        
        logger.debug(f"❌ Order failure: {json.dumps(failure_detail)}")
    
    def get_metrics(self) -> Dict:
        """✅ NOVO v4.0: Retorna métricas agregadas de execução"""
        total = self._metrics["total_orders"]
        successful = self._metrics["successful_orders"]
        
        return {
            "total_orders": total,
            "successful_orders": successful,
            "failed_orders": self._metrics["failed_orders"],
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "order_type_distribution": {
                "limit": self._metrics["limit_orders"],
                "market": self._metrics["market_orders"],
                "iceberg": self._metrics["iceberg_orders"]
            },
            "maker_taker_distribution": {
                "maker": self._metrics["maker_orders"],
                "taker": self._metrics["taker_orders"],
                "maker_ratio": (
                    self._metrics["maker_orders"] / successful * 100
                    if successful > 0 else 0.0
                )
            },
            "average_slippage_pct": (
                self._metrics["total_slippage"] / successful
                if successful > 0 else 0.0
            ),
            "average_execution_time_sec": (
                self._metrics["total_execution_time"] / successful
                if successful > 0 else 0.0
            ),
            "retry_metrics": {
                "total_retries": self._metrics["retry_count"],
                "re_quotes": self._metrics["re_quotes"],
                "retry_rate": (
                    self._metrics["retry_count"] / total * 100
                    if total > 0 else 0.0
                )
            },
            "recent_orders": self._metrics["order_details"][-10:]  # Últimas 10
        }


# Instância global
order_executor = OrderExecutor()
