"""
Valve Service
──────────────
Handles valve open/close commands from two sources:
  1. Automatic — triggered by the scoring engine after each sensor reading
  2. Manual    — triggered by the user via the frontend (with override log)

Commands are sent to the ESP32 via MQTT (toren/valves/cmd).
The ESP32 acknowledges via toren/valves/status, which updates the DB state.
"""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.valve import ValveOverrideLog, ValveState
from app.schemas.valve import ValveCommandRequest


async def get_all_valve_states(db: AsyncSession) -> list[ValveState]:
    result = await db.execute(select(ValveState))
    return list(result.scalars().all())


async def get_valve_state(db: AsyncSession, valve_id: str) -> ValveState | None:
    result = await db.execute(select(ValveState).where(ValveState.id == valve_id))
    return result.scalar_one_or_none()


async def ensure_valve_states_exist(db: AsyncSession) -> None:
    """Seed valve state rows if they don't exist yet (run on startup)."""
    valve_ids = ["bathroom", "kitchen", "laundry", "garden"]
    for vid in valve_ids:
        existing = await get_valve_state(db, vid)
        if existing is None:
            db.add(ValveState(
                id=vid,
                is_open=True,
                last_changed_at=datetime.utcnow(),
                last_changed_by="system",
            ))
    await db.commit()


async def execute_valve_command(
    db: AsyncSession,
    valve_id: str,
    action: str,            # "open" | "close"
    triggered_by: str,      # "system" | "user:<id>"
    reason: str | None = None,
    score_at_command: float | None = None,
    mqtt_client=None,       # Injected MQTTClient instance
) -> ValveState | None:
    """
    1. Publish MQTT command to ESP32
    2. Optimistically update DB state (confirmed by ESP32 ack handler)
    3. Log override if manually triggered
    """
    valve = await get_valve_state(db, valve_id)
    if valve is None:
        return None

    is_open = action == "open"

    # ── Publish MQTT command ──────────────────────────────────────────────────
    if mqtt_client:
        payload = json.dumps({
            "valve_id": valve_id,
            "action": action,
            "triggered_by": triggered_by,
        })
        mqtt_client.publish_valve_command(payload)

    # ── Update DB state optimistically ───────────────────────────────────────
    valve.is_open = is_open
    valve.last_changed_at = datetime.utcnow()
    valve.last_changed_by = triggered_by
    if not is_open and score_at_command is not None:
        valve.quality_score_at_close = score_at_command

    # ── Log manual override ───────────────────────────────────────────────────
    if triggered_by.startswith("user:"):
        override_log = ValveOverrideLog(
            valve_id=valve_id,
            action=action,
            reason=reason,
            score_at_override=score_at_command,
            overridden_at=datetime.utcnow(),
            user_id=triggered_by.replace("user:", ""),
        )
        db.add(override_log)

    await db.commit()
    await db.refresh(valve)
    return valve


async def process_auto_valve_decisions(
    db: AsyncSession,
    valves_to_close: list[str],
    current_score: float,
    mqtt_client=None,
) -> list[str]:
    """
    Called after each sensor reading.
    Closes valves whose scores are below their thresholds,
    and re-opens valves whose scores have recovered.

    Returns list of valve IDs that changed state.
    """
    all_valve_ids = ["bathroom", "kitchen", "laundry", "garden"]
    valves_to_open = [v for v in all_valve_ids if v not in valves_to_close]
    changed = []

    for valve_id in valves_to_close:
        valve = await get_valve_state(db, valve_id)
        if valve and valve.is_open:
            await execute_valve_command(
                db, valve_id, "close", "system",
                score_at_command=current_score,
                mqtt_client=mqtt_client,
            )
            changed.append(valve_id)

    for valve_id in valves_to_open:
        valve = await get_valve_state(db, valve_id)
        if valve and not valve.is_open and valve.last_changed_by == "system":
            # Only auto-reopen if system closed it (not manual override)
            await execute_valve_command(
                db, valve_id, "open", "system",
                score_at_command=current_score,
                mqtt_client=mqtt_client,
            )
            changed.append(valve_id)

    return changed


async def get_override_log(
    db: AsyncSession,
    valve_id: str | None = None,
    limit: int = 50,
) -> list[ValveOverrideLog]:
    query = select(ValveOverrideLog).order_by(ValveOverrideLog.overridden_at.desc()).limit(limit)
    if valve_id:
        query = query.where(ValveOverrideLog.valve_id == valve_id)
    result = await db.execute(query)
    return list(result.scalars().all())