from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sensor_reading import SensorReading
from app.models.valve import PredictionResult, ValveState
from app.services.valve_service import get_all_valve_states

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Single endpoint for the main dashboard page.
    Returns: latest sensor reading, valve states, latest prediction,
    24h score trend, and recent anomaly count.
    """

    # ── Latest reading ────────────────────────────────────────────────────────
    latest_result = await db.execute(
        select(SensorReading).order_by(SensorReading.timestamp.desc()).limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    # ── 24-hour trend (hourly averages) ───────────────────────────────────────
    since_24h = datetime.utcnow() - timedelta(hours=24)
    trend_result = await db.execute(
        select(
            func.date_trunc("hour", SensorReading.timestamp).label("hour"),
            func.avg(SensorReading.score_overall).label("avg_score"),
            func.avg(SensorReading.ph).label("avg_ph"),
            func.avg(SensorReading.turbidity).label("avg_turbidity"),
            func.avg(SensorReading.tds).label("avg_tds"),
        )
        .where(SensorReading.timestamp >= since_24h)
        .group_by("hour")
        .order_by("hour")
    )
    trend_rows = trend_result.all()
    trend = [
        {
            "hour": row.hour.isoformat(),
            "avg_score": round(row.avg_score, 2) if row.avg_score else None,
            "avg_ph": round(row.avg_ph, 2) if row.avg_ph else None,
            "avg_turbidity": round(row.avg_turbidity, 2) if row.avg_turbidity else None,
            "avg_tds": round(row.avg_tds, 2) if row.avg_tds else None,
        }
        for row in trend_rows
    ]

    # ── Anomaly count (last 24h) ───────────────────────────────────────────────
    anomaly_result = await db.execute(
        select(func.count(SensorReading.id))
        .where(SensorReading.timestamp >= since_24h)
        .where(SensorReading.is_sudden_change == True)  # noqa: E712
    )
    anomaly_count = anomaly_result.scalar() or 0

    # ── Valve states ──────────────────────────────────────────────────────────
    valves = await get_all_valve_states(db)

    # ── Latest prediction ─────────────────────────────────────────────────────
    pred_result = await db.execute(
        select(PredictionResult).order_by(PredictionResult.computed_at.desc()).limit(1)
    )
    prediction = pred_result.scalar_one_or_none()

    return {
        "latest_reading": latest.to_dict() if latest else None,
        "valve_states": [v.to_dict() for v in valves],
        "prediction": prediction.to_dict() if prediction else None,
        "trend_24h": trend,
        "anomaly_count_24h": anomaly_count,
        "system_status": {
            "mqtt_connected": _get_mqtt_status(),
            "last_reading_age_seconds": (
                (datetime.utcnow() - latest.timestamp).total_seconds()
                if latest else None
            ),
        },
    }


def _get_mqtt_status() -> bool:
    try:
        from app.mqtt.client import mqtt_client
        return mqtt_client.is_connected
    except Exception:
        return False