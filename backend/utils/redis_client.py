import redis
from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger("redis_client")

class RedisClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.settings = get_settings()
        try:
            self.client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                decode_responses=True,  # Retorna strings ao invés de bytes
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.client.ping()
            logger.info(f"✅ Conectado ao Redis em {self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"❌ Falha ao conectar ao Redis: {e}")
            self.client = None
            
        self._initialized = True

    def get_client(self):
        return self.client
        
    def publish(self, channel: str, message: dict):
        """Publica mensagem JSON em um canal"""
        if self.client:
            try:
                self.client.publish(channel, json.dumps(message))
            except Exception as e:
                logger.error(f"Erro ao publicar no Redis: {e}")

    def get_json(self, key: str):
        """Recupera objeto JSON"""
        if self.client:
            val = self.client.get(key)
            if val:
                try:
                    return json.loads(val)
                except:
                    return val
        return None

    def set_json(self, key: str, value: dict, ttl: int = None):
        """Salva objeto JSON"""
        if self.client:
            try:
                self.client.set(key, json.dumps(value), ex=ttl)
            except Exception as e:
                logger.error(f"Erro ao salvar JSON no Redis: {e}")

# Instância global
redis_client = RedisClient()  # Expose the wrapper, not just the raw client

