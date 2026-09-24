import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.auth import get_user_by_id
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import User
from app.db.session import get_async_session
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket Real-time"])
settings = get_settings()
logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self, max_connections: int = 1000):
        self.active_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self.connection_metadata: dict[WebSocket, dict[str, Any]] = {}
        self.max_connections = max_connections
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, user_id: int, metadata: dict[str, Any] | None = None) -> bool:
        if sum(len(conns) for conns in self.active_connections.values()) >= self.max_connections:
            await websocket.close(code=1008, reason="Max connections reached")
            return False

        await websocket.accept()
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now(timezone.utc),
            "subscriptions": set(),
            "metadata": metadata or {},
        }
        logger.info(f"WebSocket connected: user_id={user_id}, total={self.total_connections}")
        return True

    def disconnect(self, websocket: WebSocket):
        metadata = self.connection_metadata.get(websocket)
        if metadata:
            user_id = metadata["user_id"]
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected: user_id={user_id}, total={self.total_connections}")

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def send_personal_message(self, user_id: int, message: dict[str, Any]):
        if user_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:  # noqa: BLE001
                    disconnected.add(websocket)
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast(self, message: dict[str, Any], user_ids: list[int] | None = None):
        target_users = user_ids if user_ids else list(self.active_connections.keys())
        for user_id in target_users:
            await self.send_personal_message(user_id, message)

    async def broadcast_to_subscription(self, topic: str, message: dict[str, Any]):
        message["topic"] = topic
        for websocket, metadata in self.connection_metadata.items():
            if topic in metadata["subscriptions"]:
                try:
                    await websocket.send_json(message)
                except Exception:  # noqa: BLE001
                    self.disconnect(websocket)

    def subscribe(self, websocket: WebSocket, topic: str):
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(topic)

    def unsubscribe(self, websocket: WebSocket, topic: str):
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(topic)

    async def start_heartbeat(self, interval: int = 30):
        async def heartbeat():
            while True:
                await asyncio.sleep(interval)
                for websocket in list(self.connection_metadata.keys()):
                    try:
                        await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()})
                    except Exception:  # noqa: BLE001
                        self.disconnect(websocket)

        self._heartbeat_task = asyncio.create_task(heartbeat())

    async def stop_heartbeat(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass


manager = ConnectionManager(max_connections=settings.WS_MAX_CONNECTIONS)


async def get_websocket_user(
    websocket: WebSocket,
    token: str = Query(...),
) -> User:
    from app.core.config import get_settings
    from jose import JWTError, jwt
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        await websocket.close(code=1008, reason="Invalid token")
        raise

    async for session in get_async_session():
        user = await get_user_by_id(session, user_id)
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="User not found or inactive")
            raise RuntimeError("User not found or inactive")

        return user

    await websocket.close(code=1008, reason="Database error")
    raise RuntimeError("Database error")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await get_websocket_user(websocket, token)
    connected = await manager.connect(websocket, user.id, {"email": user.email, "role": user.role.value})
    if not connected:
        return

    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(websocket, user, data)

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        logger.error(f"WebSocket error for user {user.id}: {e}")
    finally:
        manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, user: User, data: dict[str, Any]):
    msg_type = data.get("type")

    if msg_type == "subscribe":
        topic = data.get("topic")
        if topic:
            manager.subscribe(websocket, topic)
            await websocket.send_json({"type": "subscribed", "topic": topic})

    elif msg_type == "unsubscribe":
        topic = data.get("topic")
        if topic:
            manager.unsubscribe(websocket, topic)
            await websocket.send_json({"type": "unsubscribed", "topic": topic})

    elif msg_type == "ping":
        await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})

    elif msg_type == "get_status":
        await websocket.send_json({
            "type": "status",
            "connections": manager.total_connections,
            "user_connections": len(manager.active_connections.get(user.id, [])),
            "subscriptions": list(manager.connection_metadata.get(websocket, {}).get("subscriptions", [])),
        })


# Convenience functions for other services to push updates
async def push_market_update(symbol: str, data: dict[str, Any]):
    await manager.broadcast_to_subscription(f"market.{symbol}", {"type": "market_update", "data": data})


async def push_order_update(user_id: int, order_data: dict[str, Any]):
    await manager.send_personal_message(user_id, {"type": "order_update", "data": order_data})


async def push_position_update(user_id: int, position_data: dict[str, Any]):
    await manager.send_personal_message(user_id, {"type": "position_update", "data": position_data})


async def push_risk_alert(user_id: int, alert_data: dict[str, Any]):
    await manager.send_personal_message(user_id, {"type": "risk_alert", "data": alert_data})


async def push_portfolio_update(user_id: int, portfolio_data: dict[str, Any]):
    await manager.send_personal_message(user_id, {"type": "portfolio_update", "data": portfolio_data})


async def push_agent_message(user_id: int, message: dict[str, Any]):
    await manager.send_personal_message(user_id, {"type": "agent_message", "data": message})


async def push_system_notification(user_ids: list[int], notification: dict[str, Any]):
    await manager.broadcast({"type": "notification", "data": notification}, user_ids)