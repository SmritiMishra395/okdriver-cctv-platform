from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user_ws
from app.realtime.ws_manager import manager

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def dashboard_socket(websocket: WebSocket, token: str | None = None, db: Session = Depends(get_db)):
    try:
        get_current_user_ws(token, db)
    except Exception:  # noqa: BLE001
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Clients don't need to send anything; keep the connection open
            # and drop it if the browser closes the tab.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
