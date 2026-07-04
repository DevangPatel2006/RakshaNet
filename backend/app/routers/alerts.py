from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt
from app.core.config import settings
from app.services.event_bus import manager

router = APIRouter(tags=["alerts"])

@router.websocket("/alerts/stream")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Authenticate token
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        role: str = payload.get("role")
        username: str = payload.get("sub")
        if role is None or username is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, role)
    try:
        while True:
            # Keep-alive receive loop
            # Clients do not need to send data, but we must listen for connection closing
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, role)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, role)
