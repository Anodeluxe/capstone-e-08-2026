"""
ML Feature Pipeline
───────────────────
Bridges raw sensor data in TimescaleDB with the trained ML model.

Functions:
  - aggregate_hourly_readings()  — 360 raw rows → 1 hourly row
  - build_feature_matrix()       — 4 raw cols → 12 ML features
  - load_models()                — singleton loader for scaler + XGBoost
"""

import os
from datetime import datetime, timedelta
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading

# ── Path to model artifacts ──────────────────────────────────────────────────
_ML_DIR = os.path.dirname(os.path.abspath(__file__))
_SCALER_PATH = os.path.join(_ML_DIR, "models", "scaler_hourly.pkl")
_XGB_PATH = os.path.join(_ML_DIR, "models", "xgb_model_hourly.pkl")

# ── Feature order (must match training exactly) ──────────────────────────────
FEATURE_COLUMNS = [
    "elapsed_hours", "ph", "tds", "turbidity", "temperature",
    "ph_MA_24", "tds_MA_24", "turbidity_MA_24",
]

# Minimum hourly rows needed to build features (need at least 1 for rolling min_periods=1)
MIN_HOURLY_ROWS = 3


# ── Model Loader (Singleton) ─────────────────────────────────────────────────
_scaler = None
_xgb_model = None


def load_models():
    """
    Load scaler and XGBoost model once, reuse across calls.
    Returns (scaler, model) or (None, None) if files missing.
    """
    global _scaler, _xgb_model

    if _scaler is not None and _xgb_model is not None:
        return _scaler, _xgb_model

    if not os.path.exists(_SCALER_PATH):
        print(f"[ML] Scaler not found: {_SCALER_PATH}")
        return None, None

    if not os.path.exists(_XGB_PATH):
        print(f"[ML] XGBoost model not found: {_XGB_PATH}")
        return None, None

    try:
        _scaler = joblib.load(_SCALER_PATH)
        _xgb_model = joblib.load(_XGB_PATH)
        print("[ML] Models loaded successfully.")
        return _scaler, _xgb_model
    except Exception as e:
        print(f"[ML] Failed to load models: {e}")
        return None, None


# ── Hourly Aggregation ───────────────────────────────────────────────────────
async def aggregate_hourly_readings(
    db: AsyncSession,
    since_datetime: datetime,
) -> pd.DataFrame:
    """
    Query raw sensor readings since `since_datetime`, aggregate by hour,
    and return a DataFrame with hourly means of ph, tds, turbidity, temperature.

    Returns columns: ['timestamp', 'ph', 'tds', 'turbidity', 'temperature']
    sorted by timestamp ascending.
    """
    # Truncate timestamp to hour boundary using date_trunc
    hour_trunc = func.date_trunc("hour", SensorReading.timestamp).label("hour")

    stmt = (
        select(
            hour_trunc,
            func.avg(SensorReading.ph).label("ph"),
            func.avg(SensorReading.tds).label("tds"),
            func.avg(SensorReading.turbidity).label("turbidity"),
            func.avg(SensorReading.temperature).label("temperature"),
        )
        .where(SensorReading.timestamp >= since_datetime)
        .group_by(hour_trunc)
        .order_by(hour_trunc.asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return pd.DataFrame(columns=["timestamp", "ph", "tds", "turbidity", "temperature"])

    df = pd.DataFrame(rows, columns=["timestamp", "ph", "tds", "turbidity", "temperature"])
    return df


# ── Feature Engineering ──────────────────────────────────────────────────────
def build_feature_matrix(
    hourly_df: pd.DataFrame,
    elapsed_hours: float = 0.0,
) -> pd.DataFrame | None:
    """
    Given an hourly DataFrame (from aggregate_hourly_readings), compute
    the 8 ML features required by the model.

    elapsed_hours = jam sejak terakhir kuras (diisi oleh caller).

    Returns a DataFrame with FEATURE_COLUMNS, or None if insufficient data.
    """
    if len(hourly_df) < MIN_HOURLY_ROWS:
        print(f"[ML] Need at least {MIN_HOURLY_ROWS} hourly rows, got {len(hourly_df)}")
        return None

    df = hourly_df.copy()

    # ── MA_24: rata-rata 24 jam terakhir per parameter ────────────────────
    for col in ["ph", "tds", "turbidity"]:
        df[f"{col}_MA_24"] = df[col].rolling(window=24, min_periods=1).mean()

    # ── elapsed_hours: waktu terakhir kuras (dari caller, bukan dari DB) ───
    df["elapsed_hours"] = elapsed_hours

    return df[FEATURE_COLUMNS]


# ── Full Pipeline: DB → Features ─────────────────────────────────────────────
async def get_latest_features(
    db: AsyncSession,
    lookback_hours: int = 72,
    elapsed_hours: float = 0.0,
) -> pd.DataFrame | None:
    """
    Convenience function: fetch last `lookback_hours` of sensor data,
    aggregate hourly, and build feature matrix.

    Returns the LAST ROW of the feature matrix (most recent hour),
    or None if data is insufficient.
    """
    since = datetime.utcnow() - timedelta(hours=lookback_hours)
    hourly_df = await aggregate_hourly_readings(db, since)

    if hourly_df.empty:
        print("[ML] No hourly data found.")
        return None

    features = build_feature_matrix(hourly_df, elapsed_hours=elapsed_hours)
    if features is None:
        return None

    # Return only the latest row (most recent hour)
    return features.iloc[[-1]].copy()
