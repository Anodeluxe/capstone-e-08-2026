"""
Seed realistic water quality degradation time-series data into the isolated
test database (toren_ml_test) for ML model validation.

Generates 8-10 days of sensor data with:
- Diurnal temperature cycle (sinusoidal)
- Gradual deterioration in turbidity, TDS, and pH
- Dynamic sub-score computation via scoring_service
- Active DrainLog entry for accurate elapsed_fraction calculation

Usage:
    python backend/scripts/seed_ml_test_db.py --days 9 --step-minutes 30
"""

import argparse
import asyncio
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.models.drain_log import DrainLog
from app.models.sensor_reading import SensorReading
from app.schemas.sensor import ESP32SensorPayload
from app.services.scoring_service import compute_scores


def get_async_test_db_url(db_name: str) -> str:
    settings = get_settings()
    parsed = urlparse(settings.database_sync_url)
    user = parsed.username or "postgres"
    password = parsed.password or "password"
    host = parsed.hostname or "timescaledb"
    port = parsed.port or 5432
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"


async def seed_data(db_name: str, days: int = 9, step_minutes: int = 30):
    async_url = get_async_test_db_url(db_name)
    print(f"Connecting to test database '{db_name}'...")
    engine = create_async_engine(async_url, echo=False)

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    total_minutes = int(days * 24 * 60)
    steps = total_minutes // step_minutes

    print(f"Generating {steps} readings across {days} days ({start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')})...")

    random.seed(42)  # reproducible degradation trajectory

    readings_to_insert = []
    current_time = start_time

    for i in range(steps):
        # Progress fraction: 0.0 (clean start) -> 1.0 (degraded end)
        progress = i / max(1, steps - 1)

        # Diurnal temperature cycle (peaks at 15:00, lowest at 03:00)
        hour_val = current_time.hour + current_time.minute / 60.0
        diurnal = math.sin(2 * math.pi * (hour_val - 9.0) / 24.0)
        temperature = 27.0 + 3.0 * diurnal + random.gauss(0, 0.25)
        temperature = max(21.0, min(33.0, round(temperature, 2)))

        # pH: starts at 7.35, gradually drifts down to ~6.40
        ph = 7.35 - (0.95 * (progress ** 1.3)) + random.gauss(0, 0.05)
        ph = max(6.1, min(7.8, round(ph, 2)))

        # Turbidity (NTU): starts clear (1.2 NTU), drifts up to ~10.5 NTU
        turbidity = 1.2 + (9.3 * (progress ** 1.8)) + random.gauss(0, 0.2)
        turbidity = max(0.5, min(25.0, round(turbidity, 2)))

        # TDS (ppm): starts at 150 ppm, gradually accumulates to ~450 ppm
        tds = 150.0 + (300.0 * (progress ** 1.4)) + random.gauss(0, 5.0)
        tds = max(80.0, min(800.0, round(tds, 1)))

        # Water level (%): normal usage fluctuations
        water_level = 88.0 + 7.0 * math.cos(2 * math.pi * hour_val / 24.0) + random.gauss(0, 1.5)
        water_level = max(65.0, min(98.0, round(water_level, 1)))

        # Compute multi-point quality scores using production scoring engine
        payload = ESP32SensorPayload(
            device_id="toren_01",
            timestamp=int(current_time.timestamp()),
            ph=ph,
            turbidity=turbidity,
            tds=tds,
            temperature=temperature,
            water_level=water_level,
        )
        scores = compute_scores(payload)

        # Build SensorReading ORM object
        reading = SensorReading(
            timestamp=current_time,
            ph=ph,
            turbidity=turbidity,
            tds=tds,
            temperature=temperature,
            water_level=water_level,
            score_overall=scores.overall,
            score_bathroom=scores.bathroom,
            score_kitchen=scores.kitchen,
            score_laundry=scores.laundry,
            score_garden=scores.garden,
            is_sudden_change=False,
            anomaly_parameter=None,
        )
        readings_to_insert.append(reading)

        current_time += timedelta(minutes=step_minutes)

    print(f"Sample readings generated:")
    print(f"  Start (Clean)   : pH={readings_to_insert[0].ph}, Turb={readings_to_insert[0].turbidity} NTU, TDS={readings_to_insert[0].tds} ppm -> Score={readings_to_insert[0].score_overall}")
    print(f"  Mid (Moderate)  : pH={readings_to_insert[len(readings_to_insert)//2].ph}, Turb={readings_to_insert[len(readings_to_insert)//2].turbidity} NTU, TDS={readings_to_insert[len(readings_to_insert)//2].tds} ppm -> Score={readings_to_insert[len(readings_to_insert)//2].score_overall}")
    print(f"  End (Degraded)  : pH={readings_to_insert[-1].ph}, Turb={readings_to_insert[-1].turbidity} NTU, TDS={readings_to_insert[-1].tds} ppm -> Score={readings_to_insert[-1].score_overall}")

    async with AsyncSession(engine) as session:
        # Clear existing test data
        print("Clearing prior test readings in 'toren_ml_test'...")
        from sqlalchemy import delete
        await session.execute(delete(SensorReading))
        await session.execute(delete(DrainLog))
        await session.commit()

        # Insert DrainLog representing active cycle started 9 days ago
        print("Inserting active DrainLog cycle...")
        drain_log = DrainLog(
            started_at=start_time,
            ended_at=None,  # active cycle
            cycle_estimate_hours=2400.0,
            created_by="system_ml_seeder",
            notes="Synthetic degradation cycle for ML validation",
        )
        session.add(drain_log)

        # Batch insert sensor readings
        print(f"Inserting {len(readings_to_insert)} sensor readings into 'sensor_readings'...")
        batch_size = 200
        for b in range(0, len(readings_to_insert), batch_size):
            session.add_all(readings_to_insert[b : b + batch_size])
            await session.commit()

    await engine.dispose()
    print(f"✅ Seeding completed! Database '{db_name}' now contains {len(readings_to_insert)} time-series records across {days} days.")


def main():
    parser = argparse.ArgumentParser(description="Seed realistic degradation data into test DB")
    parser.add_argument("--db-name", default="toren_ml_test", help="Test database name")
    parser.add_argument("--days", type=int, default=9, help="Number of days of data to generate (default: 9)")
    parser.add_argument("--step-minutes", type=int, default=30, help="Interval in minutes between readings (default: 30)")
    args = parser.parse_args()

    print("==================================================")
    print("      SEEDING ML TEST DATABASE (toren_ml_test)     ")
    print("==================================================")
    print(f"Database     : {args.db_name}")
    print(f"Span (Days)  : {args.days} days ({args.days * 24} hours)")
    print(f"Step Interval: {args.step_minutes} minutes")
    print("--------------------------------------------------")

    asyncio.run(seed_data(args.db_name, days=args.days, step_minutes=args.step_minutes))


if __name__ == "__main__":
    main()
