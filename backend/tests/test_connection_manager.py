import pytest
import json
from unittest.mock import AsyncMock
from app.services.event_bus import ConnectionManager

@pytest.mark.asyncio
async def test_connection_manager_flow():
    manager = ConnectionManager()
    
    # Mock websockets
    ws_alice = AsyncMock()
    ws_bob = AsyncMock()
    
    # Connect
    await manager.connect(ws_alice, "citizen", "alice")
    await manager.connect(ws_bob, "citizen", "bob")
    
    # Check registration
    assert "alice" in manager.active_connections["citizen"]
    assert "bob" in manager.active_connections["citizen"]
    assert ws_alice in manager.active_connections["citizen"]["alice"]
    
    # Send to user
    payload = {"data": "hello alice"}
    await manager.send_to_user("alice", payload)
    
    ws_alice.send_text.assert_called_once()
    sent_payload = json.loads(ws_alice.send_text.call_args[0][0])
    assert sent_payload["data"] == "hello alice"
    
    ws_bob.send_text.assert_not_called()
    
    # Broadcast to role
    ws_alice.send_text.reset_mock()
    await manager.broadcast_to_role({"data": "broadcast"}, "citizen")
    
    assert ws_alice.send_text.call_count == 1
    assert ws_bob.send_text.call_count == 1
    
    # Disconnect
    manager.disconnect(ws_alice, "citizen", "alice")
    assert "alice" not in manager.active_connections["citizen"]
    assert "bob" in manager.active_connections["citizen"]
