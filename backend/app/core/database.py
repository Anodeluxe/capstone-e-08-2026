from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Async engine — used by FastAPI route handlers
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_timescale_hypertable(conn):
    """
    Converts sensor_readings into a TimescaleDB hypertable after table creation.
    Called once during app startup.
    """
    await conn.execute(
        """
        SELECT create_hypertable(
            'sensor_readings',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );
        """
    )


async def init_db():
    """Create all tables and set up TimescaleDB hypertable."""
    from app.models import sensor_reading, valve, notification_log, prediction_result  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # TimescaleDB hypertable setup (requires TimescaleDB extension)
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                """
                CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
                """
            )
            await session.commit()
            raw_conn = await session.connection()
            await create_timescale_hypertable(raw_conn)
            await session.commit()
        except Exception as e:
            # Hypertable may already exist or TimescaleDB not installed
            print(f"[DB] TimescaleDB setup note: {e}")
            await session.rollback()