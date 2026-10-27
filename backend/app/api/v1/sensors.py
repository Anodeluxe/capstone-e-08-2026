from datetime import datetime, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import csv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sensor_reading import SensorReading
from app.schemas.sensor import HourlySensorReadingOut, SensorReadingOut

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("/export")
async def export_sensor_data(
    hours: int = Query(default=720, ge=1, le=2160),
    db: AsyncSession = Depends(get_db),
):
    """Export raw readings and computed scores for offline ML analysis."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.timestamp >= since)
        .order_by(SensorReading.timestamp.asc())
    )
    output = StringIO()
    fields = [
        "timestamp", "ph", "tds", "turbidity", "temperature", "water_level",
        "score_overall", "score_bathroom", "score_kitchen", "score_laundry",
        "score_garden", "is_sudden_change", "anomaly_parameter",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in result.scalars():
        values = row.to_dict()
        writer.writerow({field: values.get(field) for field in fields})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sensor-readings.csv"},
    )


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


@router.get("/hourly", response_model=list[HourlySensorReadingOut])
async def get_hourly_averages(
    hours: int = Query(default=168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    """
    Return one row per hour for the last `hours` hours. Every numeric field is
    the average of all samples inside that hour; `timestamp` is the bucket
    start (e.g. 10:00:00). Hours without any reading are omitted.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    bucket = func.date_trunc("hour", SensorReading.timestamp).label("hour")

    result = await db.execute(
        select(
            bucket,
            func.avg(SensorReading.ph).label("ph"),
            func.avg(SensorReading.turbidity).label("turbidity"),
            func.avg(SensorReading.tds).label("tds"),
            func.avg(SensorReading.temperature).label("temperature"),
            func.avg(SensorReading.water_level).label("water_level"),
            func.avg(SensorReading.score_overall).label("score_overall"),
            func.avg(SensorReading.score_bathroom).label("score_bathroom"),
            func.avg(SensorReading.score_kitchen).label("score_kitchen"),
            func.avg(SensorReading.score_laundry).label("score_laundry"),
            func.avg(SensorReading.score_garden).label("score_garden"),
            func.bool_or(SensorReading.is_sudden_change).label("is_sudden_change"),
            func.min(SensorReading.anomaly_parameter).label("anomaly_parameter"),
            func.count(SensorReading.id).label("sample_count"),
        )
        .where(SensorReading.timestamp >= since)
        .group_by(bucket)
        .order_by(bucket)
    )

    def _round(value: float | None, digits: int = 2) -> float | None:
        return round(value, digits) if value is not None else None

    return [
        HourlySensorReadingOut(
            timestamp=row.hour,
            ph=round(row.ph, 2),
            turbidity=round(row.turbidity, 2),
            tds=round(row.tds, 2),
            temperature=round(row.temperature, 2),
            water_level=round(row.water_level, 2),
            score_overall=_round(row.score_overall),
            score_bathroom=_round(row.score_bathroom),
            score_kitchen=_round(row.score_kitchen),
            score_laundry=_round(row.score_laundry),
            score_garden=_round(row.score_garden),
            is_sudden_change=bool(row.is_sudden_change),
            anomaly_parameter=row.anomaly_parameter,
            sample_count=row.sample_count,
        )
        for row in result.all()
    ]


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
