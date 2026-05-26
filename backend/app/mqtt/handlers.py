"""
MQTT Message Handlers
──────────────────────
This is the core data pipeline. Every sensor reading from the ESP32
flows through here in order:

  1. Parse & validate JSON payload (ESP32SensorPayload)
  2. Compute weighted quality scores (scoring_service)
  3. Detect sudden anomalies (anomaly_service)
  4. Persist SensorReading to TimescaleDB
  5. Auto-actuate valves that fall below threshold (valve_service)
  6. Broadcast live update to frontend via WebSocket (ws_manager)
  7. Trigger notifications if needed (notification_service)

Also handles:
  - toren/valves/status  → ESP32 valve acknowledgment
"""

import asyncio
import json
from datetime import datetime

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.websocket_manager import ws_manager
from app.models.sensor_reading import SensorReading
from app.schemas.sensor import ESP32SensorPayload, ESP32ValveAck
from app.services.anomaly_service import detect_sudden_change
from app.services.notification_service import (
    send_sudden_change_notification,
    send_valve_closed_notification,
)
from app.services.scoring_service import compute_scores
from app.services.valve_service import (
    get_all_valve_states,
    process_auto_valve_decisions,
    get_valve_state,
)

settings = get_settings()

# Cache of the previous reading for delta-based anomaly detection
_previous_reading: dict | None = None
_previous_score: float | None = None


def register_handlers(mqtt_client) -> None:
    """
    Called on startup to wire MQTT topics to their handler functions.
    paho callbacks are synchronous; async handlers are dispatched via
    asyncio.run_coroutine_threadsafe().
    """
    loop = asyncio.get_event_loop()

    def on_sensor_message(topic: str, payload: str) -> None:
        asyncio.run_coroutine_threadsafe(
            handle_sensor_reading(payload), loop
        )

    def on_valve_status_message(topic: str, payload: str) -> None:
        asyncio.run_coroutine_threadsafe(
            handle_valve_ack(payload), loop
        )

    mqtt_client.subscribe(settings.mqtt_topic_sensors, on_sensor_message)
    mqtt_client.subscribe(settings.mqtt_topic_valve_status, on_valve_status_message)

    print("[MQTT] Handlers registered.")


# ─── Sensor reading pipeline ───────────────────────────────────────────────────

async def handle_sensor_reading(raw_payload: str) -> None:
    """Main pipeline: parse → score → anomaly → persist → valve → notify → ws."""
    global _previous_reading, _previous_score

    # ── Step 1: Parse & validate ──────────────────────────────────────────────
    try:
        data = json.loads(raw_payload)
        reading = ESP32SensorPayload(**data)
    except Exception as e:
        print(f"[Handler] Invalid sensor payload: {e}\nPayload: {raw_payload}")
        return

    timestamp = (
        datetime.utcfromtimestamp(reading.timestamp)
        if reading.timestamp
        else datetime.utcnow()
    )

    current_raw = {
        "ph": reading.ph,
        "turbidity": reading.turbidity,
        "tds": reading.tds,
        "temperature": reading.temperature,
        "water_level": reading.water_level,
    }

    # ── Step 2: Compute weighted quality scores ───────────────────────────────
    scores = compute_scores(reading)

    # ── Step 3: Detect sudden anomaly ────────────────────────────────────────
    anomaly = detect_sudden_change(
        current_score=scores.overall,
        previous_score=_previous_score,
        current_reading=current_raw,
        previous_reading=_previous_reading,
    )

    # ── Step 4: Persist to DB ─────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        sensor_row = SensorReading(
            timestamp=timestamp,
            ph=reading.ph,
            turbidity=reading.turbidity,
            tds=reading.tds,
            temperature=reading.temperature,
            water_level=reading.water_level,
            score_overall=scores.overall,
            score_bathroom=scores.bathroom,
            score_kitchen=scores.kitchen,
            score_laundry=scores.laundry,
            score_garden=scores.garden,
            is_sudden_change=anomaly.is_sudden_change,
            anomaly_parameter=anomaly.anomaly_parameter,
        )
        db.add(sensor_row)
        await db.commit()
        await db.refresh(sensor_row)

        # ── Step 5: Auto-actuate valves ───────────────────────────────────────
        from app.mqtt.client import mqtt_client

        changed_valves = await process_auto_valve_decisions(
            db=db,
            valves_to_close=scores.valves_to_close,
            current_score=scores.overall,
            mqtt_client=mqtt_client,
        )

    # ── Step 6: Broadcast to frontend via WebSocket ───────────────────────────
    await ws_manager.broadcast_sensor_update({
        **sensor_row.to_dict(),
        "scores": {
            "overall": scores.overall,
            "bathroom": scores.bathroom,
            "kitchen": scores.kitchen,
            "laundry": scores.laundry,
            "garden": scores.garden,
        },
    })

    if anomaly.is_sudden_change:
        await ws_manager.broadcast_alert(
            alert_type="sudden_change",
            message=anomaly.description or "Sudden parameter change detected",
            data={
                "parameter": anomaly.anomaly_parameter,
                "current_score": scores.overall,
                "reading": current_raw,
            },
        )

    for valve_id in changed_valves:
        await ws_manager.broadcast_valve_status(
            valve_id=valve_id,
            is_open=valve_id not in scores.valves_to_close,
            triggered_by="auto",
        )

    # ── Step 7: Notifications ─────────────────────────────────────────────────
    if anomaly.is_sudden_change and anomaly.anomaly_parameter:
        await send_sudden_change_notification(
            parameter=anomaly.anomaly_parameter,
            current_value=current_raw.get(anomaly.anomaly_parameter, 0),
            previous_value=(_previous_reading or {}).get(anomaly.anomaly_parameter, 0),
            current_score=scores.overall,
        )

    for valve_id in changed_valves:
        if valve_id in scores.valves_to_close:
            await send_valve_closed_notification(
                valve_id=valve_id,
                score=getattr(scores, valve_id),
                anomaly_param=anomaly.anomaly_parameter,
            )

    # ── Update cache ──────────────────────────────────────────────────────────
    _previous_reading = current_raw
    _previous_score = scores.overall

    print(
        f"[Handler] Sensor reading saved | score={scores.overall:.1f} "
        f"| anomaly={anomaly.is_sudden_change} "
        f"| valves_changed={changed_valves}"
    )


# ─── Valve acknowledgment handler ─────────────────────────────────────────────

async def handle_valve_ack(raw_payload: str) -> None:
    """
    ESP32 publishes to toren/valves/status after executing a valve command.
    This confirms the physical state and updates the DB accordingly.
    """
    try:
        data = json.loads(raw_payload)
        ack = ESP32ValveAck(**data)
    except Exception as e:
        print(f"[Handler] Invalid valve ack payload: {e}")
        return

    async with AsyncSessionLocal() as db:
        valve = await get_valve_state(db, ack.valve_id)
        if valve:
            valve.is_open = ack.is_open
            valve.last_changed_by = "esp32_ack"
            await db.commit()

    await ws_manager.broadcast_valve_status(
        valve_id=ack.valve_id,
        is_open=ack.is_open,
        triggered_by="esp32_ack",
    )

    print(f"[Handler] Valve ack: {ack.valve_id} → {'OPEN' if ack.is_open else 'CLOSED'}")