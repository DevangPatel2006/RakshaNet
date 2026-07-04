import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
import redis.asyncio as aioredis
from app.core.config import settings

class ConnectionManager:
    def __init__(self):
        # Active connections grouped by role: citizen, officer, bank_analyst, telecom_analyst, admin
        self.active_connections: Dict[str, List[WebSocket]] = {
            "citizen": [],
            "officer": [],
            "bank_analyst": [],
            "telecom_analyst": [],
            "admin": []
        }

    async def connect(self, websocket: WebSocket, role: str):
        if role not in self.active_connections:
            role = "citizen"
        await websocket.accept()
        self.active_connections[role].append(websocket)
        print(f"WebSocket client connected with role: {role}")

    def disconnect(self, websocket: WebSocket, role: str):
        if role in self.active_connections and websocket in self.active_connections[role]:
            self.active_connections[role].remove(websocket)
            print(f"WebSocket client disconnected with role: {role}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_role(self, val: dict, target_role: str):
        """
        Sends message to all active connections matching target_role,
        and also broadcasts to 'admin' role connections.
        """
        payload = json.dumps(val)
        
        # Determine target roles (role itself, plus admin)
        roles = {target_role, "admin"}
        
        for role in roles:
            if role in self.active_connections:
                for connection in self.active_connections[role]:
                    try:
                        await connection.send_text(payload)
                    except Exception as e:
                        # Client disconnected or connection dead; clean up happens on disconnect
                        print(f"Failed to push message: {e}")

manager = ConnectionManager()

class RedisEventBus:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis = None
        self.stream_name = "rakshanet:alerts"

    async def connect(self):
        self.redis = aioredis.from_url(self.redis_url, decode_responses=True)

    async def publish_alert(self, title: str, description: str, severity: str, target_role: str):
        """
        Publishes a new alert event to the Redis Stream.
        """
        if not self.redis:
            await self.connect()
        
        payload = {
            "title": title,
            "description": description,
            "severity": severity,
            "target_role": target_role
        }
        # XADD command to publish on Redis Stream
        await self.redis.xadd(self.stream_name, {"data": json.dumps(payload)})

    async def start_consumer(self, db_session_factory):
        """
        Async listener loop reading events from Redis Stream and routing to WebSockets and Postgres.
        """
        if not self.redis:
            await self.connect()

        print("Starting Redis Stream Consumer...")
        
        # Read from end of stream on start, or start from 0 if you want historical
        # '$' means only new messages that arrive after the consumer starts
        last_id = "0-0"
        try:
            # Let's check if stream exists, or create a dummy entry to initialize stream
            await self.redis.xadd(self.stream_name, {"init": "1"})
        except Exception:
            pass

        # Find the latest ID so we don't process history on start
        info = await self.redis.xinfo_stream(self.stream_name) if await self.redis.exists(self.stream_name) else None
        if info:
            last_id = info.get("last-generated-id", "0-0")

        while True:
            try:
                # XREAD block=1000 count=10 streams
                events = await self.redis.xread({self.stream_name: last_id}, count=5, block=1000)
                if not events:
                    await asyncio.sleep(0.1)
                    continue

                for stream, messages in events:
                    for msg_id, data in messages:
                        last_id = msg_id
                        
                        if "init" in data:
                            continue
                        
                        event_data = json.loads(data["data"])
                        print(f"Event Bus consumed alert: {event_data['title']}")

                        # 1. Write to Postgres
                        from app.db import models
                        db = db_session_factory()
                        try:
                            alert = models.Alert(
                                title=event_data["title"],
                                description=event_data["description"],
                                severity=event_data["severity"],
                                status="Unread",
                                target_role=event_data["target_role"]
                            )
                            db.add(alert)
                            db.commit()
                            db.refresh(alert)
                            
                            # Update WebSocket payload to include Postgres database ID
                            event_data["id"] = alert.id
                            event_data["created_at"] = alert.created_at.isoformat()
                        except Exception as e:
                            print(f"Error saving consumed alert to database: {e}")
                            db.rollback()
                        finally:
                            db.close()

                        # 2. Broadcast to role-scoped WebSockets
                        await manager.broadcast_to_role(event_data, event_data["target_role"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in Redis Stream Consumer loop: {e}")
                await asyncio.sleep(2)

_event_bus = None

def get_event_bus() -> RedisEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisEventBus()
    return _event_bus
