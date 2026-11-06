from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from app.core.auth import verify_api_key
from app.core.database import get_db
from app.core.security import UserOut, get_current_user_optional
from app.core.websocket_manager import ws_manager
from app.models.sensor_reading import SensorReading
from app.mqtt.client import mqtt_client
from app.schemas.sensor import ESP32SensorPayload
from app.schemas.valve import ValveCommandRequest, ValveOverrideLogOut, ValveStateOut
from app.services.scoring_service import compute_scores
from app.services.valve_service import (
    execute_valve_command,
    get_all_valve_states,
    get_override_log,
    get_valve_state,
    resume_auto_mode,
)

router = APIRouter(prefix="/valves", tags=["Valves"])

VALID_VALVE_IDS = {"bathroom", "kitchen", "laundry", "garden"}


@router.get("/", response_model=list[ValveStateOut])
async def get_valves(db: AsyncSession = Depends(get_db)):
    """Return current state of all 4 valves."""
    return await get_all_valve_states(db)


@router.post("/auto", response_model=list[ValveStateOut])
async def resume_auto_control(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    """Return every valve to automatic control using the latest reading."""
    latest = (
        await db.execute(
            select(SensorReading).order_by(SensorReading.timestamp.desc()).limit(1)
        )
    ).scalar_one_or_none()

    if latest is None:
        changed = await resume_auto_mode(db, 100.0, [], mqtt_client)
        valves_to_close: list[str] = []
    else:
        scores = compute_scores(ESP32SensorPayload(
            device_id="latest",
            ph=latest.ph,
            turbidity=latest.turbidity,
            tds=latest.tds,
            temperature=latest.temperature,
            water_level=latest.water_level,
        ))
        valves_to_close = scores.valves_to_close
        changed = await resume_auto_mode(
            db, scores.overall, valves_to_close, mqtt_client
        )

    for valve_id in changed:
        await ws_manager.broadcast_valve_status(
            valve_id=valve_id,
            is_open=valve_id not in valves_to_close,
            triggered_by="system",
        )

    return await get_all_valve_states(db)


@router.get("/{valve_id}", response_model=ValveStateOut)
async def get_valve(valve_id: str, db: AsyncSession = Depends(get_db)):
    valve = await get_valve_state(db, valve_id)
    if not valve:
        raise HTTPException(status_code=404, detail=f"Valve '{valve_id}' not found.")
    return valve


@router.post("/{valve_id}/command", response_model=ValveStateOut)
async def send_valve_command(
    valve_id: str,
    body: ValveCommandRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    current_user: Optional[UserOut] = Depends(get_current_user_optional),
):
    """
    Manual override — open or close a specific valve.
    Requires Bearer JWT token or X-API-Key header (falls back to operator_local).
    """
    if valve_id not in VALID_VALVE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid valve_id: {valve_id}")

    if current_user:
        triggered_by = f"user:{current_user.username}"
    elif api_key != "anonymous":
        triggered_by = f"user:{api_key}"
    else:
        triggered_by = "user:operator_local"

    valve = await execute_valve_command(
        db=db,
        valve_id=valve_id,
        action=body.action,
        triggered_by=triggered_by,
        reason=body.reason or "Manual dashboard override",
        mqtt_client=mqtt_client,
    )

    if not valve:
        raise HTTPException(status_code=404, detail=f"Valve '{valve_id}' not found.")

    # Broadcast state change to all connected frontend clients
    await ws_manager.broadcast_valve_status(
        valve_id=valve_id,
        is_open=valve.is_open,
        triggered_by=triggered_by,
    )

    return valve


@router.get("/{valve_id}/overrides", response_model=list[ValveOverrideLogOut])
async def get_valve_overrides(
    valve_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Return the manual override history for a specific valve."""
    if valve_id not in VALID_VALVE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid valve_id: {valve_id}")
    return await get_override_log(db, valve_id=valve_id, limit=limit)


@router.get("/overrides/all", response_model=list[ValveOverrideLogOut])
async def get_all_overrides(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Return override history for all valves."""
    return await get_override_log(db, limit=limit)