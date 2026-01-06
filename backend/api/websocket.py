import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis 
from config.settings import get_settings

# Use 'api' logger or create a specific one
logger = logging.getLogger("api")

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str | dict):
        if not self.active_connections:
            return
            
        if isinstance(message, dict):
            try:
                message = json.dumps(message)
            except Exception as e:
                logger.error(f"Error serializing message for broadcast: {e}")
                return

        # Broadcast to all connected clients
        # We iterate over a copy to avoid modification during iteration if disconnect happens
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
                # Connection might be dead, disconnect it
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    settings = get_settings()
    if getattr(settings, "API_AUTH_ENABLED", False):
        header_name = getattr(settings, "API_KEY_HEADER", "X-API-Key")
        api_key = websocket.headers.get(header_name)
        query_key = websocket.query_params.get("api_key")
        if not api_key and not query_key:
            await websocket.close(code=4401)
            return
        if api_key != getattr(settings, "API_KEY", "") and query_key != getattr(settings, "API_KEY", ""):
            await websocket.close(code=4401)
            return

    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            # We can enable receiving commands here later
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        manager.disconnect(websocket)

async def redis_event_listener():
    """
    Background task to listen for events from Redis and broadcast to WebSockets.
    """
    logger.info("Starting Redis Event Listener for WebSockets...")
    settings = get_settings()
    
    # Retry loop for connection
    while True:
        try:
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            
            async with r.pubsub() as pubsub:
                await pubsub.subscribe('bot_events')
                logger.info("✅ Subscribed to 'bot_events' channel")
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        # Forward the message data to all connected websockets
                        await manager.broadcast(message['data'])
                        
        except asyncio.CancelledError:
            logger.info("Redis Event Listener cancelled")
            break
        except Exception as e:
            logger.error(f"Redis Listener Error: {e}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
