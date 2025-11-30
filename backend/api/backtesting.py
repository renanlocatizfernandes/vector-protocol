# backend/api/backtesting.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from modules.backtester import backtester
from utils.logger import setup_logger

logger = setup_logger("backtesting_routes")

router = APIRouter()


class BacktestRequest(BaseModel):
    """Schema para requisição de backtest"""
    start_date: str = Field(..., description="Data inicial (YYYY-MM-DD)", example="2025-09-22")
    end_date: str = Field(..., description="Data final (YYYY-MM-DD)", example="2025-10-22")
    initial_balance: float = Field(5000, description="Saldo inicial em USDT", example=5000, gt=100)
    symbols: Optional[List[str]] = Field(None, description="Lista de símbolos (None = top 50)", example=None)
    max_positions: int = Field(10, description="Máximo de posições simultâneas", example=10, ge=1, le=20)


class BacktestResponse(BaseModel):
    """Schema para resposta de backtest"""
    success: bool
    data: dict
    message: Optional[str] = None


@router.post("/run", response_model=BacktestResponse, summary="Executar Backtest Customizado")
async def run_backtest(request: BacktestRequest):
    """
    Executa backtest da estratégia com parâmetros customizados
    
    **Parâmetros:**
    - **start_date**: Data inicial (formato: YYYY-MM-DD)
    - **end_date**: Data final (formato: YYYY-MM-DD)
    - **initial_balance**: Saldo inicial em USDT (mínimo: 100)
    - **symbols**: Lista de símbolos para testar (None = top 50 por volume)
    - **max_positions**: Máximo de posições simultâneas (1-20)
    
    **Retorna:**
    - Relatório completo com métricas de performance
    - Win rate, profit factor, max drawdown
    - Lista de todos os trades executados
    - Curva de equity
    
    **Exemplo:**
    ```
    {
        "start_date": "2025-09-22",
        "end_date": "2025-10-22",
        "initial_balance": 5000,
        "max_positions": 10
    }
    ```
    """
    
    try:
        # Validar datas
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        end = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        if end <= start:
            raise HTTPException(
                status_code=400, 
                detail="❌ Data final deve ser maior que data inicial"
            )
        
        if (end - start).days > 90:
            raise HTTPException(
                status_code=400, 
                detail="❌ Período máximo: 90 dias (para performance)"
            )
        
        if start < datetime(2024, 1, 1):
            raise HTTPException(
                status_code=400,
                detail="❌ Data inicial deve ser posterior a 01/01/2024"
            )
        
        logger.info(f"🔬 Iniciando backtest: {request.start_date} → {request.end_date}")
        
        # Executar backtest
        result = await backtester.run_backtest(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_balance=request.initial_balance,
            symbols=request.symbols,
            max_positions=request.max_positions
        )
        
        logger.info(f"✅ Backtest concluído: ROI {result['roi']:.2f}% | Win Rate {result['win_rate']:.2f}%")
        
        return {
            'success': True,
            'data': result,
            'message': f"Backtest executado com sucesso: {result['total_trades']} trades"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"❌ Formato de data inválido: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Erro no backtest: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao executar backtest: {str(e)}"
        )


@router.get("/quick", response_model=BacktestResponse, summary="Backtest Rápido (30 dias)")
async def quick_backtest(
    days: int = Query(30, description="Número de dias para testar", ge=7, le=90),
    initial_balance: float = Query(5000, description="Saldo inicial em USDT", gt=100)
):
    """
    Executa backtest rápido dos últimos N dias
    
    **Parâmetros:**
    - **days**: Número de dias para testar (7-90)
    - **initial_balance**: Saldo inicial em USDT
    
    **Exemplo:**
    ```
    GET /api/backtest/quick?days=30&initial_balance=5000
    ```
    
    **Retorna:**
    - Relatório simplificado com métricas principais
    """
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"⚡ Quick backtest: últimos {days} dias")
        
        result = await backtester.run_backtest(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            initial_balance=initial_balance,
            max_positions=10
        )
        
        return {
            'success': True,
            'data': result,
            'message': f"Quick backtest: {days} dias"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no quick backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-month", response_model=BacktestResponse, summary="Backtest do Último Mês")
async def last_month_backtest():
    """
    Backtest do último mês completo
    
    **Exemplo:**
    ```
    GET /api/backtest/last-month
    ```
    """
    
    try:
        today = datetime.now()
        # Primeiro dia do mês passado
        first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        # Último dia do mês passado
        last_day_last_month = today.replace(day=1) - timedelta(days=1)
        
        logger.info(f"📅 Backtest do último mês: {first_day_last_month.strftime('%Y-%m')}")
        
        result = await backtester.run_backtest(
            start_date=first_day_last_month.strftime("%Y-%m-%d"),
            end_date=last_day_last_month.strftime("%Y-%m-%d"),
            initial_balance=5000,
            max_positions=10
        )
        
        return {
            'success': True,
            'data': result,
            'message': f"Backtest: {first_day_last_month.strftime('%B %Y')}"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no backtest mensal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", summary="Templates de Backtest")
async def get_backtest_templates():
    """
    Retorna templates pré-configurados de backtest
    
    **Retorna:**
    - Lista de períodos comuns para testar
    """
    
    today = datetime.now()
    
    return {
        "templates": [
            {
                "name": "Última Semana",
                "days": 7,
                "start_date": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d")
            },
            {
                "name": "Últimos 30 Dias",
                "days": 30,
                "start_date": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d")
            },
            {
                "name": "Últimos 60 Dias",
                "days": 60,
                "start_date": (today - timedelta(days=60)).strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d")
            },
            {
                "name": "Últimos 90 Dias",
                "days": 90,
                "start_date": (today - timedelta(days=90)).strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d")
            }
        ]
    }
