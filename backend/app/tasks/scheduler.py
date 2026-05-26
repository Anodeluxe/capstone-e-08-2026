"""
Scheduled Jobs
───────────────
Runs periodic background tasks using APScheduler.
These are registered on FastAPI startup.

Jobs:
  1. run_prediction_job    — every hour: re-run ETA prediction, send early warning if needed
  2. cleanup_old_readings  — daily: remove readings older than 90 days (optional)
"""

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.websocket_manager import ws_manager
from app.models.sensor_reading import SensorReading
from app.models.valve import PredictionResult
from app.services.notification_service import send_early_warning_notification
from app.services.prediction_service import predict_eta

settings = get_settings()

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    scheduler.add_job(
        run_prediction_job,
        trigger="interval",
        hours=1,
        id="prediction_job",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_readings,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_job",
        replace_existing=True,
    )
    scheduler.start()
    print("[Scheduler] Started. Jobs: prediction (hourly), cleanup (daily 03:00).")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    print("[Scheduler] Stopped.")


async def run_prediction_job() -> None:
    """
    Fetch last 72h of score data, run prediction, persist result,
    and send early warning notification if ETA ≤ EARLY_WARNING_DAYS.
    """
    print(f"[Scheduler] Running prediction job at {datetime.utcnow().isoformat()}")

    async with AsyncSessionLocal() as db:
        since = datetime.utcnow() - timedelta(hours=72)
        result = await db.execute(
            select(SensorReading.timestamp, SensorReading.score_overall)
            .where(SensorReading.timestamp >= since)
            .where(SensorReading.score_overall.isnot(None))
            .order_by(SensorReading.timestamp.asc())
        )
        rows = result.all()

    if len(rows) < 12:
        print("[Scheduler] Not enough data for prediction — skipping.")
        return

    timestamps = [r[0] for r in rows]
    scores = [r[1] for r in rows]

    prediction = predict_eta(timestamps, scores)

    days_until = prediction.get("days_until_threshold")
    predicted_date = prediction.get("predicted_date")
    current_score = scores[-1]

    # ── Persist prediction ────────────────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        pred_row = PredictionResult(
            computed_at=datetime.utcnow(),
            target_parameter="score_overall",
            valve_id=None,
            days_until_threshold=days_until,
            predicted_date=predicted_date,
            confidence=prediction.get("confidence"),
            model_used=prediction.get("model_used", "unknown"),
            notification_sent=False,
        )
        db.add(pred_row)
        await db.commit()
        await db.refresh(pred_row)

        # ── Send early warning if threshold approaching ───────────────────────
        should_warn = (
            days_until is not None
            and days_until <= settings.early_warning_days
            and not pred_row.notification_sent
        )

        if should_warn:
            date_str = predicted_date.strftime("%d %b %Y") if predicted_date else "N/A"
            await send_early_warning_notification(
                days_until=days_until,
                predicted_date=date_str,
                current_score=current_score,
            )
            pred_row.notification_sent = True
            await db.commit()

            # Broadcast alert to frontend
            await ws_manager.broadcast_alert(
                alert_type="early_warning",
                message=f"Water quality predicted to be unfit in {days_until:.1f} days",
                data={
                    "days_until_threshold": days_until,
                    "predicted_date": date_str,
                    "current_score": current_score,
                },
            )

    print(
        f"[Scheduler] Prediction done | days_until={days_until} "
        f"| trend={prediction.get('trend_direction')} "
        f"| notified={should_warn if 'should_warn' in dir() else False}"
    )


async def cleanup_old_readings(days: int = 90) -> None:
    """Remove sensor readings older than `days` days to keep DB size manageable."""
    from sqlalchemy import delete
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(SensorReading).where(SensorReading.timestamp < cutoff)
        )
        await db.commit()
        print(f"[Scheduler] Cleanup: removed {result.rowcount} old readings (before {cutoff.date()})")