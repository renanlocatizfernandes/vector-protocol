import logging
import sys
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Evitar duplicidade de handlers se logger já existir
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Formatter
    # Check if we want JSON or Text (could be env var, default to JSON for Phase 3)
    formatter = JSONFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(
        f'/logs/{name}_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
