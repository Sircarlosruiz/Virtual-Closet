from uuid import UUID
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, mayorista_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        if mayorista_id not in self._connections:
            self._connections[mayorista_id] = []
        self._connections[mayorista_id].append(websocket)

    def disconnect(self, mayorista_id: UUID, websocket: WebSocket) -> None:
        if mayorista_id in self._connections:
            self._connections[mayorista_id].remove(websocket)
            if not self._connections[mayorista_id]:
                del self._connections[mayorista_id]

    async def send(self, mayorista_id: UUID, message: str) -> None:
        if mayorista_id in self._connections:
            dead_connections = []
            for ws in self._connections[mayorista_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead_connections.append(ws)
            for ws in dead_connections:
                self.disconnect(mayorista_id, ws)


manager = ConnectionManager()
