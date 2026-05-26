from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.sensor_reading import SensorReading
from app.models.valve import PredictionResult
from app.schemas.valve import PredictionResultOut
from app.services.prediction_service import predict_eta

router = APIRouter(prefix="/predictions", tags=["Predictions"])
settings = get_settings()


@router.get("/latest", response_model=list[PredictionResultOut])
async def get_latest_predictions(db: AsyncSession = Depends(get_db)):
    """Return the most recently computed prediction for each valve/parameter."""
    result = await db.execute(
        select(PredictionResult)
        .order_by(PredictionResult.computed_at.desc())
        .limit(10)
    )
    return list(result.scalars().all())


@router.get("/run", response_model=dict)
async def run_prediction_now(
    hours: int = Query(default=72, ge=6, le=720),
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand: fetch recent score history and re-run the prediction model.
    Also saves the result to the DB.
    Returns ETA in days and predicted date.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SensorReading.timestamp, SensorReading.score_overall)
        .where(SensorReading.timestamp >= since)
        .where(SensorReading.score_overall.isnot(None))
        .order_by(SensorReading.timestamp.asc())
    )
    rows = result.all()

    if not rows:
        return {"error": "Not enough data for prediction.", "data_points": 0}

    timestamps = [r[0] for r in rows]
    scores = [r[1] for r in rows]

    prediction = predict_eta(timestamps, scores)

    # Persist the result
    pred_row = PredictionResult(
        computed_at=datetime.utcnow(),
        target_parameter="score_overall",
        valve_id=None,
        days_until_threshold=prediction.get("days_until_threshold"),
        predicted_date=prediction.get("predicted_date"),
        confidence=prediction.get("confidence"),
        model_used=prediction.get("model_used", "unknown"),
        notification_sent=False,
    )
    db.add(pred_row)
    await db.commit()

    return {
        "data_points": len(scores),
        "current_score": scores[-1] if scores else None,
        "prediction": prediction,
    }