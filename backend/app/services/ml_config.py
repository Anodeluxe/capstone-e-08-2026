"""
ML Configuration Service
──────────────────────────
Provides runtime ML configuration (elapsed_fraction, model path, etc.)
sourced from the database (DrainLog) rather than static config.

This replaces the static `ml_elapsed_fraction` in Settings with a
database-backed, real-time value computed from the active DrainLog.
"""

from functools import lru_cache
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.drain_log_service import get_elapsed_fraction, get_elapsed_fraction_with_fallback

# Default cycle estimate in hours (fallback if no DrainLog)
DEFAULT_CYCLE_ESTIMATE_HOURS = 2000.0

# Model path (could be moved to DB later)
MODEL_PATH = "backend/app/ml/models/xgb_model_hourly_v2_horizon.pkl"


class MLConfig:
    """
    Singleton-ish service for ML runtime configuration.
    Uses a simple cache with TTL to avoid hitting DB on every prediction.
    """

    _instance: Optional["MLConfig"] = None
    _elapsed_fraction_cache: float = 0.0
    _cache_timestamp: float = 0.0
    _cache_ttl_seconds: int = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_elapsed_fraction(self, db: Optional[AsyncSession] = None) -> float:
        """
        Get the current elapsed fraction, using cache if fresh.
        """
        import time

        now = time.time()
        if now - self._cache_timestamp < self._cache_ttl_seconds:
            return self._elapsed_fraction_cache

        # Cache expired or empty — fetch from DB
        if db is not None:
            fraction = await get_elapsed_fraction(db)
        else:
            fraction = await get_elapsed_fraction_with_fallback()

        self._elapsed_fraction_cache = fraction
        self._cache_timestamp = now
        return fraction

    def invalidate_cache(self) -> None:
        """Force cache refresh on next call."""
        self._cache_timestamp = 0.0

    def get_model_path(self) -> str:
        """Get the path to the XGBoost model bundle."""
        return MODEL_PATH


# Global instance for easy import
ml_config = MLConfig()


# Convenience functions for direct use
async def get_elapsed_fraction(db: Optional[AsyncSession] = None) -> float:
    """Get current elapsed fraction (with caching)."""
    return await ml_config.get_elapsed_fraction(db)


def invalidate_ml_config_cache() -> None:
    """Call after starting/ending a drain cycle."""
    ml_config.invalidate_cache()


# ─────────────────────────────────────────────────────────────────────────────
# Startup hook — call during app initialization to ensure DB is ready
# ─────────────────────────────────────────────────────────────────────────────
async def init_ml_config() -> None:
    """
    Initialize ML config on app startup.
    Ensures there's an active DrainLog or creates a default one.
    """
    from app.services.drain_log_service import get_active_drain_log, start_drain_cycle
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        active = await get_active_drain_log(db)
        if active is None:
            print("[MLConfig] No active drain cycle found — starting default cycle.")
            await start_drain_cycle(db, created_by="system:startup")
        else:
            print(f"[MLConfig] Active drain cycle found (ID={active.id}, started={active.started_at})")