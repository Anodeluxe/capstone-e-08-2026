"""
Drain Log Service
───────────────────
Manages drain cycle logs and computes the elapsed fraction for ML RUL prediction.

The ML model expects `elapsed_fraction` in range [0.0, 1.0] where:
  - 0.0 = just drained (start of cycle)
  - 1.0 = end of expected cycle length

This is derived from the training data where `elapsed_hours` was normalized
to [0, 1] as (hours_since_drain / cycle_length).
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.drain_log import DrainLog

settings = get_settings()

# Default cycle estimate in hours (from training data statistics)
DEFAULT_CYCLE_ESTIMATE_HOURS = 2000.0


async def get_active_drain_log(db: AsyncSession) -> DrainLog | None:
    """
    Get the currently active (not ended) drain log.
    Returns the most recent one if multiple exist (should not happen).
    """
    result = await db.execute(
        select(DrainLog)
        .where(DrainLog.ended_at.is_(None))
        .order_by(DrainLog.started_at.desc())
    )
    return result.scalars().first()


async def get_elapsed_fraction(db: AsyncSession) -> float:
    """
    Compute the elapsed fraction of the current drain cycle.

    Returns:
        float in [0.0, 1.0] representing the fraction of the cycle elapsed.
        0.0 = just drained, 1.0 = reached estimated cycle length.
    """
    active_log = await get_active_drain_log(db)

    if active_log is None:
        # No active drain cycle — assume we're at the start of a new cycle
        return 0.0

    now = datetime.utcnow()
    elapsed_hours = (now - active_log.started_at).total_seconds() / 3600.0
    cycle_estimate = active_log.cycle_estimate_hours or DEFAULT_CYCLE_ESTIMATE_HOURS

    fraction = elapsed_hours / cycle_estimate
    return max(0.0, min(1.0, fraction))


async def get_elapsed_fraction_with_fallback() -> float:
    """
    Standalone function that creates its own DB session.
    Used by services that don't have an existing session (e.g., scheduler).
    """
    async with AsyncSessionLocal() as db:
        return await get_elapsed_fraction(db)


async def start_drain_cycle(
    db: AsyncSession,
    cycle_estimate_hours: float = DEFAULT_CYCLE_ESTIMATE_HOURS,
    created_by: str = "system",
    notes: str | None = None,
) -> DrainLog:
    """
    Start a new drain cycle. Ends any currently active cycle first.
    """
    # End any existing active cycle
    active = await get_active_drain_log(db)
    if active:
        active.ended_at = datetime.utcnow()
        await db.commit()

    # Create new cycle
    new_log = DrainLog(
        started_at=datetime.utcnow(),
        cycle_estimate_hours=cycle_estimate_hours,
        created_by=created_by,
        notes=notes,
    )
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    return new_log


async def end_drain_cycle(
    db: AsyncSession,
    drain_log_id: int,
    ended_by: str = "system",
) -> DrainLog | None:
    """
    End a drain cycle by ID.
    """
    result = await db.execute(select(DrainLog).where(DrainLog.id == drain_log_id))
    log = result.scalars().first()

    if log is None:
        return None

    log.ended_at = datetime.utcnow()
    log.notes = (log.notes or "") + f"\nEnded by {ended_by} at {datetime.utcnow().isoformat()}"
    await db.commit()
    await db.refresh(log)
    return log


async def get_drain_history(
    db: AsyncSession,
    limit: int = 20,
) -> list[DrainLog]:
    """Get recent drain cycles."""
    result = await db.execute(
        select(DrainLog)
        .order_by(DrainLog.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_cycle_statistics(db: AsyncSession) -> dict:
    """
    Get statistics about past drain cycles for analysis.
    """
    logs = await get_drain_history(db, limit=100)

    completed = [log for log in logs if log.ended_at is not None]

    if not completed:
        return {
            "total_cycles": 0,
            "completed_cycles": 0,
            "avg_cycle_hours": None,
            "min_cycle_hours": None,
            "max_cycle_hours": None,
        }

    durations = [
        (log.ended_at - log.started_at).total_seconds() / 3600.0
        for log in completed
    ]

    return {
        "total_cycles": len(logs),
        "completed_cycles": len(completed),
        "avg_cycle_hours": sum(durations) / len(durations),
        "min_cycle_hours": min(durations),
        "max_cycle_hours": max(durations),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: sync wrapper for non-async contexts (rare, but useful for CLI)
# ─────────────────────────────────────────────────────────────────────────────
def get_elapsed_fraction_sync() -> float:
    """
    Synchronous wrapper — creates own event loop.
    Only for CLI scripts or tests, not for FastAPI request handlers.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_elapsed_fraction_with_fallback())