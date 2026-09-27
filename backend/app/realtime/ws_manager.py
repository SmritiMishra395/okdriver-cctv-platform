import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

from app.config import get_settings

logger = logging.getLogger("okdriver.realtime")
settings = get_settings()

REDIS_CHANNEL = "okdriver:events"


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


class ConnectionManager:
    """Broadcasts events to connected dashboard clients.

    Runs in-process by default. When REDIS_URL is set, publishes every
    broadcast to a Redis Pub/Sub channel and relays messages received on
    that channel back out to locally connected sockets, so the event bus
    stays consistent across multiple backend replicas behind a load
    balancer (see SCALABILITY.md).
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis = None
        self._pubsub_task: asyncio.Task | None = None

    async def startup(self) -> None:
        if settings.redis_url:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
                self._pubsub_task = asyncio.create_task(self._redis_listener())
                logger.info("Realtime hub connected to Redis at %s", settings.redis_url)
            except Exception:  # noqa: BLE001
                logger.warning("Redis unavailable, falling back to in-process broadcast", exc_info=True)
                self._redis = None

    async def shutdown(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()
        if self._redis:
            await self._redis.close()

    async def _redis_listener(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await self._local_broadcast(message["data"])

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def _local_broadcast(self, raw: str) -> None:
        dead = []
        async with self._lock:
            targets = list(self._connections)
        for ws in targets:
            try:
                await ws.send_text(raw)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        message = json.dumps(
            {"type": event_type, "payload": payload, "ts": datetime.now(timezone.utc).isoformat()},
            default=_json_default,
        )
        if self._redis:
            try:
                await self._redis.publish(REDIS_CHANNEL, message)
                return
            except Exception:  # noqa: BLE001
                logger.warning("Redis publish failed, broadcasting locally instead", exc_info=True)
        await self._local_broadcast(message)


manager = ConnectionManager()
