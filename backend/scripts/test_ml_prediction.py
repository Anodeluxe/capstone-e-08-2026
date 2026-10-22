"""
Test & Validate ML Prediction Pipeline (XGBoost RUL v2 Horizon)
Using the isolated test database: toren_ml_test.

Validates:
1. Hourly aggregation over 169+ hours
2. Feature engineering: extraction of 22 rolling & lag features
3. Model selection: activates 'xgb_v2_horizon_30d' instead of fallback
4. RUL estimation, predicted date, and confidence (R^2)

Usage:
    python backend/scripts/test_ml_prediction.py
    python backend/scripts/test_ml_prediction.py --db-name toren_ml_test
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.models.drain_log import DrainLog
from app.models.sensor_reading import SensorReading
from app.services.drain_log_service import get_elapsed_fraction
from app.services.ml_prediction_service import get_latest_features_async, predict_hybrid


def get_async_test_db_url(db_name: str) -> str:
    settings = get_settings()
    parsed = urlparse(settings.database_sync_url)
    user = parsed.username or "postgres"
    password = parsed.password or "password"
    host = parsed.hostname or "timescaledb"
    port = parsed.port or 5432
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"


async def run_test(db_name: str, lookback_hours: int = 169):
    async_url = get_async_test_db_url(db_name)
    print(f"Connecting to test database '{db_name}'...")
    engine = create_async_engine(async_url, echo=False)

    async with AsyncSession(engine) as session:
        # Check total sensor readings
        result = await session.execute(
            select(SensorReading)
            .order_by(SensorReading.timestamp.asc())
        )
        all_readings = result.scalars().all()
        total_count = len(all_readings)

        if total_count == 0:
            print(f"\n❌ ERROR: No sensor readings found in '{db_name}'.")
            print("   Please run: python backend/scripts/seed_ml_test_db.py first.")
            return

        first_ts = all_readings[0].timestamp
        latest_ts = all_readings[-1].timestamp
        time_span_hours = (latest_ts - first_ts).total_seconds() / 3600.0

        print(f"Database Record Stats:")
        print(f"  • Total Readings : {total_count} rows")
        print(f"  • First Reading  : {first_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  • Latest Reading : {latest_ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  • Time Span      : {time_span_hours:.1f} hours ({time_span_hours/24:.1f} days)")

        # Fetch DrainLog elapsed fraction
        elapsed_fraction = await get_elapsed_fraction(session)
        print(f"  • Elapsed Cycle  : {elapsed_fraction * 100:.2f}% of 2400h cycle")

        # Fetch recent readings for predict_hybrid input
        since = datetime.utcnow() - timedelta(hours=lookback_hours)
        recent_result = await session.execute(
            select(SensorReading.timestamp, SensorReading.score_overall)
            .where(SensorReading.timestamp >= since)
            .where(SensorReading.score_overall.isnot(None))
            .order_by(SensorReading.timestamp.asc())
        )
        recent_rows = recent_result.all()
        timestamps = [r[0] for r in recent_rows]
        scores = [r[1] for r in recent_rows]

        print(f"\nRunning ML Hybrid Inference (lookback: {lookback_hours}h, inputs: {len(scores)} data points)...")
        prediction = await predict_hybrid(
            session,
            timestamps=timestamps,
            scores=scores,
            elapsed_fraction=elapsed_fraction,
            mode="auto",
        )

        # Inspect extracted feature vector
        features_df = await get_latest_features_async(
            session,
            lookback_hours=lookback_hours,
            elapsed_fraction=elapsed_fraction,
        )

        print("\n==================================================")
        print("           ML MODEL INFERENCE REPORT              ")
        print("==================================================")
        model_name = prediction.get("model_used")
        days = prediction.get("days_until_threshold")
        rul_h = prediction.get("rul_hours")
        pred_date = prediction.get("predicted_date")
        conf = prediction.get("confidence")
        conf_pct = f"{conf * 100:.1f}%" if conf is not None else "N/A"

        print(f"• Model Terpilih      : {model_name}")
        if model_name == "xgb_v2_horizon_30d":
            print(f"  Status              : ✅ SUCCESS (XGBoost Active, syarat >= 169h terpenuhi)")
        else:
            print(f"  Status              : ⚠️ FALLBACK ({model_name})")

        print(f"• Estimasi Sisa Waktu : {days:.2f} hari ({rul_h:.1f} jam)" if days is not None else "• Estimasi Sisa Waktu : — hari")
        print(f"• Perkiraan Tanggal   : {pred_date.strftime('%d %B %Y %H:%M') if pred_date else '—'}")
        print(f"• Kepercayaan (R^2)   : {conf_pct}")
        print(f"• Skor Terkini        : {scores[-1] if scores else 'N/A'}")
        print("--------------------------------------------------")

        if features_df is not None and not features_df.empty:
            row = features_df.iloc[-1]
            print("Contoh 8 Fitur Kunci yang Dihitung Model XGBoost:")
            print(f"  - score_overall       : {row.get('score_overall', 0):.2f}")
            print(f"  - score_drop_24       : {row.get('score_drop_24', 0):.2f} (penurunan skor dlm 24 jam)")
            print(f"  - score_drop_72       : {row.get('score_drop_72', 0):.2f} (penurunan skor dlm 72 jam)")
            print(f"  - score_drop_168      : {row.get('score_drop_168', 0):.2f} (penurunan skor dlm 7 hari)")
            print(f"  - score_MA_24         : {row.get('score_MA_24', 0):.2f} (moving average 24 jam)")
            print(f"  - turbidity_raw       : {row.get('turbidity_raw', 0):.2f} NTU")
            print(f"  - tds_raw             : {row.get('tds_raw', 0):.1f} ppm")
            print(f"  - ph_raw              : {row.get('ph_raw', 0):.2f}")
        print("==================================================")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Test ML prediction on isolated database")
    parser.add_argument("--db-name", default="toren_ml_test", help="Test database name")
    parser.add_argument("--lookback-hours", type=int, default=169, help="Lookback window in hours (default: 169)")
    args = parser.parse_args()

    asyncio.run(run_test(args.db_name, lookback_hours=args.lookback_hours))


if __name__ == "__main__":
    main()
