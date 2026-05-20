from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.connection_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/{mayorista_id}")
async def websocket_endpoint(websocket: WebSocket, mayorista_id: UUID):
    await manager.connect(mayorista_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(mayorista_id, websocket)
