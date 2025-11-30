import math

def round_step_size(quantity: float, step_size: float) -> float:
    """Arredonda quantidade de acordo com step_size da Binance"""
    if step_size == 0:
        return quantity
    
    precision = int(round(-math.log(step_size, 10), 0))
    rounded = math.floor(quantity * (10 ** precision)) / (10 ** precision)
    
    return rounded

def format_quantity(quantity: float, step_size: float) -> float:
    """Formata quantidade removendo zeros desnecessários"""
    rounded = round_step_size(quantity, step_size)
    
    # Remover zeros à direita
    formatted = f"{rounded:.8f}".rstrip('0').rstrip('.')
    
    return float(formatted)
