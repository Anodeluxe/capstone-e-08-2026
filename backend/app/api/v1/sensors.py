from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sensor_reading import SensorReading
from app.schemas.sensor import SensorReadingOut

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("/latest", response_model=SensorReadingOut)
async def get_latest_reading(db: AsyncSession = Depends(get_db)):
    """Get the most recent sensor reading."""
    result = await db.execute(
        select(SensorReading)
        .order_by(SensorReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No sensor readings yet.")
    return reading


@router.get("/history", response_model=list[SensorReadingOut])
async def get_sensor_history(
    hours: int = Query(default=24, ge=1, le=720),
    parameter: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return sensor readings for the last `hours` hours.
    Optionally filter to show only readings where a specific parameter changed.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.timestamp >= since)
        .order_by(SensorReading.timestamp.asc())
    )
    return list(result.scalars().all())


@router.get("/anomalies", response_model=list[SensorReadingOut])
async def get_anomaly_events(
    hours: int = Query(default=72, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    """Return all readings flagged as sudden changes in the last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.timestamp >= since)
        .where(SensorReading.is_sudden_change == True)  # noqa: E712
        .order_by(SensorReading.timestamp.desc())
    )
    return list(result.scalars().all())