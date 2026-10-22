"""
Setup isolated test database in TimescaleDB: toren_ml_test.
Ensures zero pollution of production database (toren_db).

Usage:
    python backend/scripts/setup_test_db.py
    python backend/scripts/setup_test_db.py --db-name toren_ml_test --reset
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.database import Base
from app.models.drain_log import DrainLog  # noqa: F401
from app.models.sensor_reading import SensorReading  # noqa: F401
from app.models.valve import (  # noqa: F401
    NotificationLog,
    PredictionResult,
    ValveOverrideLog,
    ValveState,
)


def get_db_connection_params():
    settings = get_settings()
    sync_url = settings.database_sync_url
    parsed = urlparse(sync_url)
    return {
        "host": parsed.hostname or "timescaledb",
        "port": parsed.port or 5432,
        "user": parsed.username or "postgres",
        "password": parsed.password or "password",
        "default_db": "postgres",
    }


def create_database_if_not_exists(db_name: str, reset: bool = False):
    params = get_db_connection_params()
    print(f"Connecting to Postgres at {params['host']}:{params['port']} as user '{params['user']}'...")
    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=params["default_db"],
    )
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone() is not None

            if exists and reset:
                print(f"Terminating active connections and dropping existing '{db_name}'...")
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                      AND pid <> pg_backend_pid();
                    """,
                    (db_name,),
                )
                cur.execute(f"DROP DATABASE {db_name};")
                exists = False

            if not exists:
                print(f"Creating isolated database '{db_name}'...")
                cur.execute(f"CREATE DATABASE {db_name};")
                print(f"✅ Database '{db_name}' created successfully.")
            else:
                print(f"ℹ️ Database '{db_name}' already exists.")
    finally:
        conn.close()


async def init_test_schema(db_name: str):
    params = get_db_connection_params()
    async_url = f"postgresql+asyncpg://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{db_name}"
    print(f"Connecting to '{db_name}' via asyncpg...")

    engine = create_async_engine(async_url, echo=False)

    async with engine.begin() as conn:
        print("Enabling TimescaleDB extension...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            print("✅ TimescaleDB extension enabled.")
        except Exception as e:
            print(f"⚠️ TimescaleDB extension note: {e}")

        print("Applying table schemas (SensorReading, DrainLog, ValveState, PredictionResult)...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created.")

        print("Setting up TimescaleDB hypertable for sensor_readings...")
        try:
            await conn.execute(
                text(
                    """
                    SELECT create_hypertable(
                        'sensor_readings',
                        'timestamp',
                        if_not_exists => TRUE,
                        chunk_time_interval => INTERVAL '1 day'
                    );
                    """
                )
            )
            print("✅ Hypertable 'sensor_readings' active.")
        except Exception as e:
            print(f"⚠️ Hypertable note: {e}")

    # Seed default valve states
    async with AsyncSession(engine) as session:
        valve_ids = ["bathroom", "kitchen", "laundry", "garden"]
        for vid in valve_ids:
            val = await session.get(ValveState, vid)
            if not val:
                session.add(ValveState(id=vid, is_open=True, last_changed_by="system"))
        await session.commit()
        print("✅ Default valve states initialized (all open).")

    await engine.dispose()
    print(f"\n🎉 SUCCESS: Isolated database '{db_name}' is fully ready for ML testing!")


def main():
    parser = argparse.ArgumentParser(description="Setup isolated test database in TimescaleDB")
    parser.add_argument("--db-name", default="toren_ml_test", help="Name of test database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate database if exists")
    args = parser.parse_args()

    print("==================================================")
    print("      ISOLATED TEST DATABASE SETUP (ML TESTING)    ")
    print("==================================================")
    print(f"Target DB: {args.db_name}")
    print(f"Reset    : {args.reset}")
    print("--------------------------------------------------")

    create_database_if_not_exists(args.db_name, reset=args.reset)
    asyncio.run(init_test_schema(args.db_name))


if __name__ == "__main__":
    main()
