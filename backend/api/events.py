import asyncio
import json
import logging
from typing import Set, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from lib.models import close_db, get_session_factory
from lib.repositories.utils import get_redis_client, close_redis
from lib.repositories import scoreboard
from lib.utils.notifier import start_notifier, stop_notifier



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Global Background Task ====================

_listener_task: Optional[asyncio.Task] = None
_listener_lock = asyncio.Lock()


# ==================== Lifespan Events ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _listener_task
    
    logger.info("Starting Events service...")
    try:
        async with _listener_lock:
            if _listener_task is None:
                _listener_task = asyncio.create_task(redis_event_listener())
        
        await start_notifier()
        
        logger.info("Events service started successfully")
    except Exception as e:
        logger.error(f"Failed to start Events service: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Events service...")
    try:
        await stop_notifier()
        
        async with _listener_lock:
            if _listener_task:
                _listener_task.cancel()
                try:
                    await _listener_task
                except asyncio.CancelledError:
                    pass
                _listener_task = None
        
        await close_redis()
        await close_db()
        logger.info("Events service shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="ADArena Events Service",
    description="Real-time WebSocket events for scoreboard and live updates",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== WebSocket Connection Manager ====================

class ConnectionManager:
    def __init__(self):
        self.game_events: Set[WebSocket] = set()
        self.live_events: Set[WebSocket] = set()
    
    async def connect_game_events(self, websocket: WebSocket):
        await websocket.accept()
        self.game_events.add(websocket)
        logger.info(f"New game events connection. Total: {len(self.game_events)}")
    
    def disconnect_game_events(self, websocket: WebSocket):
        self.game_events.discard(websocket)
        logger.info(f"Game events disconnected. Remaining: {len(self.game_events)}")

    async def connect_live_events(self, websocket: WebSocket):
        await websocket.accept()
        self.live_events.add(websocket)
        logger.info(f"New live events connection. Total: {len(self.live_events)}")
    
    def disconnect_live_events(self, websocket: WebSocket):
        self.live_events.discard(websocket)
        logger.info(f"Live events disconnected. Remaining: {len(self.live_events)}")
    
    async def broadcast_game_event(self, message: dict):
        disconnected = set()
        for connection in self.game_events:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting game event: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.game_events.discard(conn)
    
    async def broadcast_live_event(self, message: dict):
        disconnected = set()
        for connection in self.live_events:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting live event: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.live_events.discard(conn)


manager = ConnectionManager()


# ==================== WebSocket Endpoints ====================

@app.websocket("/ws/game_events")
async def websocket_game_events(websocket: WebSocket):
    """
    WebSocket endpoint for scoreboard updates.
    
    On connect, immediately sends current scoreboard state (init_scoreboard event).
    Then receives scoreboard_update events from Redis listener.
    """
    await manager.connect_game_events(websocket)
    
    try:
        factory = get_session_factory()
        async with factory() as db:
            # Send initial scoreboard on connection
            scoreboard_data = await scoreboard.construct_scoreboard(db)
            await websocket.send_json({
                "event": "init_scoreboard",
                "data": scoreboard_data
            })
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from game events client: {data}")
            except WebSocketDisconnect:
                break
            
    except Exception as e:
        logger.error(f"WebSocket error in game_events: {e}")
    finally:
        manager.disconnect_game_events(websocket)


@app.websocket("/ws/live_events")
async def websocket_live_events(websocket: WebSocket):
    await manager.connect_live_events(websocket)
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received from live events client: {data}")
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket error in live_events: {e}")
    finally:
        manager.disconnect_live_events(websocket)


async def redis_event_listener():
    """
    Background task that listens to Redis pub/sub for game events.
    
    Events are published to 'adarena-events' channel by:
    - Submissions API (flag captures)
    - Checker workers (service status updates)
    - Ticker (round changes, scoreboard updates)
    
    This listener routes events to appropriate WebSocket connections:
    - scoreboard_update -> /ws/game_events (for scoreboard page)
    - flag_submission, checker_update -> /ws/live_events (for live feed)
    """
    redis = get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe('adarena-events')
    
    logger.info("Started Redis event listener")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    event_type = data.get('event_type')
                    
                    logger.info(f"Received Redis event: {event_type}")
                    
                    if event_type == 'scoreboard_update':
                        await manager.broadcast_game_event(data)
                        logger.info(f"Broadcasted to {len(manager.game_events)} game clients")
                    elif event_type in ['flag_submission', 'checker_update']:
                        await manager.broadcast_live_event(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from Redis: {message['data']}")

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Redis event listener cancelled")
    except Exception as e:
        logger.error(f"Redis event listener error: {e}")
    finally:
        try:
            await pubsub.unsubscribe('adarena-events')
            await pubsub.close()
        except Exception as e:
            logger.error(f"Error closing pubsub: {e}")


# ==================== HTTP Endpoints ====================

@app.get("/api/events/health/")
async def health_check():
    return {
        "status": "ok",
        "game_connections": len(manager.game_events),
        "live_connections": len(manager.live_events),
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )