import json
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class WebSocketManager:
    """
    Manages active WebSocket connections and broadcasts sensor/valve
    updates to all connected frontend clients in real time.
    """

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        print(f"[WS] Client connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)
        print(f"[WS] Client disconnected. Total: {len(self._connections)}")

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send a typed event to all connected clients."""
        payload = json.dumps({"type": event_type, "data": data})
        dead: list[WebSocket] = []

        for ws in self._connections:
            if ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    print(f"[WS] Failed to send to client: {e}")
                    dead.append(ws)
            else:
                dead.append(ws)

        for ws in dead:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast_sensor_update(self, reading: dict[str, Any]) -> None:
        """Broadcast a new sensor reading to all clients."""
        await self.broadcast("sensor_update", reading)

    async def broadcast_valve_status(self, valve_id: str, is_open: bool, triggered_by: str) -> None:
        """Broadcast a valve state change to all clients."""
        await self.broadcast("valve_status", {
            "valve_id": valve_id,
            "is_open": is_open,
            "triggered_by": triggered_by,  # "auto" | "manual" | "esp32_ack"
        })

    async def broadcast_alert(self, alert_type: str, message: str, data: dict[str, Any]) -> None:
        """Broadcast an anomaly or early-warning alert to all clients."""
        await self.broadcast("alert", {
            "alert_type": alert_type,   # "sudden_change" | "early_warning" | "valve_closed"
            "message": message,
            "details": data,
        })

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton — imported by both main.py and mqtt/handlers.py
ws_manager = WebSocketManager()