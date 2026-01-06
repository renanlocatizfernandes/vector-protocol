import logging
import sys
import json
from datetime import datetime
import redis
from config.settings import get_settings

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

class RedisLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.redis_client = None
        self.settings = get_settings()
        self._connect()

    def _connect(self):
        try:
            self.redis_client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
        except Exception:
            self.redis_client = None

    def emit(self, record):
        # Evitar loop infinito se o próprio redis logar
        if record.name == "redis_client":
            return
            
        try:
            if not self.redis_client:
                # Tentar reconectar silenciosamente (ou ignorar)
                self._connect()
                if not self.redis_client:
                    return

            msg = self.format(record)
            # Parse msg back to dict to wrap it, or just send raw string?
            # Prefer sending structured object: {type: 'log', data: JSON-parsed-log}
            try:
                log_data = json.loads(msg)
            except:
                log_data = {"message": msg}

            payload = {
                "type": "log",
                "data": log_data
            }
            
            # Fire and forget
            self.redis_client.publish('bot_events', json.dumps(payload))
            
        except Exception:
            self.handleError(record)

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
    
    # Add Redis Handler (Phase 3)
    # Only add for specific loggers or all? Let's add for all but ignore redis_client in emit
    try:
        redis_handler = RedisLogHandler()
        redis_handler.setFormatter(formatter)
        redis_handler.setLevel(logging.INFO)
        logger.addHandler(redis_handler)
    except Exception:
        pass # Fail safe

    return logger
