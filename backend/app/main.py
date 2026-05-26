"""
Toren Monitoring — FastAPI Application
───────────────────────────────────────
Entry point. Wires together:
  - FastAPI app with CORS
  - Database init (TimescaleDB hypertable)
  - MQTT client + message handlers
  - APScheduler (hourly prediction jobs)
  - WebSocket endpoint for real-time frontend updates
  - REST API routers (sensors, valves, predictions, dashboard)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.websocket_manager import ws_manager
from app.mqtt.client import mqtt_client
from app.mqtt.handlers import register_handlers
from app.tasks.scheduler import start_scheduler, stop_scheduler

settings = get_settings()


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[App] Starting {settings.app_name} ({settings.app_env})")

    # 1. Initialize database tables + TimescaleDB hypertable
    await init_db()

    # 2. Seed valve states (idempotent)
    from app.core.database import AsyncSessionLocal
    from app.services.valve_service import ensure_valve_states_exist
    async with AsyncSessionLocal() as db:
        await ensure_valve_states_exist(db)

    # 3. Start MQTT client (connects + starts paho background loop)
    mqtt_client.start()

    # 4. Register MQTT message handlers
    register_handlers(mqtt_client)

    # 5. Start APScheduler (hourly prediction job)
    start_scheduler()

    print("[App] Startup complete. Ready to receive data from ESP32.")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print("[App] Shutting down...")
    stop_scheduler()
    mqtt_client.stop()


# ─── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "IoT water quality monitoring and adaptive valve control system. "
        "Receives data from ESP32 sensors via MQTT, computes quality scores, "
        "detects anomalies, predicts degradation, and controls solenoid valves."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST API Routers ──────────────────────────────────────────────────────────

from app.api.v1 import dashboard, predictions, sensors, valves  # noqa: E402

app.include_router(sensors.router, prefix="/api/v1")
app.include_router(valves.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


# ─── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time data stream for the Next.js dashboard.

    Frontend connects to ws://host:8000/ws
    and receives typed JSON events:

      { "type": "sensor_update", "data": { ...SensorReading } }
      { "type": "valve_status",  "data": { "valve_id": ..., "is_open": ... } }
      { "type": "alert",         "data": { "alert_type": ..., "message": ... } }
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; frontend can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ─── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "mqtt_connected": mqtt_client.is_connected,
        "ws_clients": ws_manager.connection_count,
        "env": settings.app_env,
    }