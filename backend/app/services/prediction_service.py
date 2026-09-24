"""
Prediction Service
───────────────────
Predicts how many days until the water quality score drops below a
threshold (i.e., valve will auto-close / water becomes unfit).

Approach:
  1. Load last N hours of score_overall from the DB
  2. Fit a linear regression (or polynomial if curvature detected)
  3. Extrapolate to find when the score crosses the threshold
  4. Return ETA in days + confidence based on R²

This module is called:
  a. On-demand via GET /predictions/
  b. Periodically by the APScheduler job (every hour)
"""

from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import PolynomialFeatures

from app.core.config import get_settings

settings = get_settings()

# Score threshold below which overall quality is considered unfit.
# Matches the strictest valve threshold (kitchen = 65).
DEFAULT_SCORE_THRESHOLD = 60.0

# Minimum number of data points needed to make a prediction
MIN_DATA_POINTS = 12  # ~1 hour at 5-min intervals

# XGBoost v2 Production Model Features
FEATURE_COLUMNS = [
    "elapsed_hours", "ph_raw", "tds_raw", "turbidity_raw", "temperature_raw",
    "score_overall", "score_drop_24", "score_drop_72", "score_drop_168",
    "score_MA_24", "score_MA_72", "score_STD_24",
    "turbidity_raw_MA24", "tds_raw_MA24", "ph_raw_MA24",
    "turbidity_raw_drop24", "tds_raw_drop24", "ph_raw_drop24",
    "turbidity_raw_drop72", "tds_raw_drop72", "ph_raw_drop72",
    "hour_of_day",
]

_XGB_BUNDLE = None
_XGB_LOAD_ATTEMPTED = False


def _get_xgb_bundle():
    global _XGB_BUNDLE, _XGB_LOAD_ATTEMPTED
    if not _XGB_LOAD_ATTEMPTED:
        _XGB_LOAD_ATTEMPTED = True
        model_path = Path(__file__).resolve().parents[1] / "ml" / "models" / "xgb_model_hourly_v2_horizon.pkl"
        if model_path.exists():
            try:
                _XGB_BUNDLE = joblib.load(str(model_path))
                print(f"[PredictionService] Loaded XGBoost model bundle: {model_path.name}")
            except Exception as e:
                print(f"[PredictionService] Warning: Failed to load XGBoost model bundle: {e}")
                _XGB_BUNDLE = None
    return _XGB_BUNDLE


def predict_eta(
    timestamps: list[datetime],
    scores: list[float],
    threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> dict:
    """
    Given a time series of quality scores, predict when the score
    will reach `threshold`.

    Returns a dict:
    {
        "days_until_threshold": float | None,
        "predicted_date": datetime | None,
        "confidence": float,          # R² of the fit (0–1)
        "model_used": str,
        "already_below_threshold": bool,
        "trend_direction": "degrading" | "stable" | "improving",
    }
    """
    if len(scores) < MIN_DATA_POINTS:
        return _insufficient_data_result()

    current_score = scores[-1]

    if current_score <= threshold:
        return {
            "days_until_threshold": 0.0,
            "predicted_date": datetime.utcnow(),
            "confidence": 1.0,
            "model_used": "none",
            "already_below_threshold": True,
            "trend_direction": "degrading",
        }

    # Convert timestamps to numeric (hours from first point)
    t0 = timestamps[0]
    X_hours = np.array([(t - t0).total_seconds() / 3600.0 for t in timestamps]).reshape(-1, 1)
    y = np.array(scores)

    # ── Try linear regression first ──────────────────────────────────────────
    lin_model = LinearRegression()
    lin_model.fit(X_hours, y)
    y_pred_lin = lin_model.predict(X_hours)
    r2_lin = r2_score(y, y_pred_lin)

    # ── Try polynomial (degree 2) if linear R² is poor ───────────────────────
    poly = PolynomialFeatures(degree=2, include_bias=False)
    X_poly = poly.fit_transform(X_hours)
    from sklearn.linear_model import Ridge
    poly_model = Ridge(alpha=1.0)
    poly_model.fit(X_poly, y)
    y_pred_poly = poly_model.predict(X_poly)
    r2_poly = r2_score(y, y_pred_poly)

    use_poly = r2_poly > r2_lin + 0.05  # only use poly if meaningfully better

    if use_poly:
        chosen_model = "polynomial_ridge"
        r2 = r2_poly
        slope_direction = _poly_trend_direction(poly_model, X_hours, poly)
    else:
        chosen_model = "linear_regression"
        r2 = r2_lin
        slope_direction = "degrading" if lin_model.coef_[0] < 0 else (
            "improving" if lin_model.coef_[0] > 0.1 else "stable"
        )

    if slope_direction in ("stable", "improving"):
        return {
            "days_until_threshold": None,
            "predicted_date": None,
            "confidence": round(r2, 3),
            "model_used": chosen_model,
            "already_below_threshold": False,
            "trend_direction": slope_direction,
        }

    # ── Binary search for the crossing point ─────────────────────────────────
    # Search up to 30 days ahead
    max_hours = 30 * 24.0
    last_hours = X_hours[-1, 0]

    def predict_at(h: float) -> float:
        if use_poly:
            xp = poly.transform(np.array([[h]]))
            return float(poly_model.predict(xp)[0])
        else:
            return float(lin_model.predict(np.array([[h]]))[0])

    if predict_at(last_hours + max_hours) > threshold:
        # Won't reach threshold in 30 days
        return {
            "days_until_threshold": None,
            "predicted_date": None,
            "confidence": round(r2, 3),
            "model_used": chosen_model,
            "already_below_threshold": False,
            "trend_direction": slope_direction,
        }

    lo, hi = last_hours, last_hours + max_hours
    for _ in range(50):
        mid = (lo + hi) / 2
        if predict_at(mid) > threshold:
            lo = mid
        else:
            hi = mid

    hours_until = hi - last_hours
    days_until = hours_until / 24.0
    predicted_date = timestamps[-1] + timedelta(hours=hours_until)

    return {
        "days_until_threshold": round(days_until, 2),
        "predicted_date": predicted_date,
        "confidence": round(max(r2, 0.0), 3),
        "model_used": chosen_model,
        "already_below_threshold": False,
        "trend_direction": "degrading",
    }


def _poly_trend_direction(model, X_hours, poly) -> str:
    """Evaluate polynomial at last vs first point to determine direction."""
    try:
        first = float(model.predict(poly.transform(X_hours[:1]))[0])
        last = float(model.predict(poly.transform(X_hours[-1:]))[0])
        diff = last - first
        if diff < -2:
            return "degrading"
        elif diff > 2:
            return "improving"
        return "stable"
    except Exception:
        return "stable"


def _insufficient_data_result() -> dict:
    return {
        "days_until_threshold": None,
        "predicted_date": None,
        "confidence": 0.0,
        "model_used": "none",
        "already_below_threshold": False,
        "trend_direction": "stable",
        "note": f"Need at least {MIN_DATA_POINTS} data points for prediction.",
    }


def predict_rul_from_readings(readings: list[dict] | pd.DataFrame) -> dict:
    """
    Predict Remaining Useful Life (RUL) using the pulled XGBoost v2 horizon model.
    Falls back gracefully to predict_eta() if the XGBoost bundle is unavailable or
    if inputs cannot be processed.
    """
    if isinstance(readings, pd.DataFrame):
        df = readings.copy()
    elif isinstance(readings, list) and len(readings) > 0:
        df = pd.DataFrame(readings)
    else:
        return _insufficient_data_result()

    if df.empty or len(df) < MIN_DATA_POINTS:
        return _insufficient_data_result()

    # Standardize column naming
    rename_map = {
        "ph": "ph_raw",
        "tds": "tds_raw",
        "turbidity": "turbidity_raw",
        "temperature": "temperature_raw",
    }
    for old_col, new_col in rename_map.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]

    if "timestamp" not in df.columns or "score_overall" not in df.columns:
        return _insufficient_data_result()

    df = df.sort_values("timestamp").reset_index(drop=True)
    latest = df.iloc[-1]
    current_score = float(latest["score_overall"])

    if current_score <= DEFAULT_SCORE_THRESHOLD:
        return {
            "days_until_threshold": 0.0,
            "predicted_date": datetime.utcnow(),
            "confidence": 1.0,
            "model_used": "none",
            "already_below_threshold": True,
            "trend_direction": "degrading",
            "is_early_warning_active": True,
        }

    bundle = _get_xgb_bundle()
    if bundle is not None and "model" in bundle:
        try:
            ts_series = pd.to_datetime(df["timestamp"])
            latest_ts = ts_series.iloc[-1]
            first_ts = ts_series.iloc[0]

            elapsed_hours = max(0.0, (latest_ts - first_ts).total_seconds() / 3600.0)
            hour_of_day = int(latest_ts.hour)

            mask_24h = ts_series >= (latest_ts - timedelta(hours=24))
            mask_72h = ts_series >= (latest_ts - timedelta(hours=72))
            mask_168h = ts_series >= (latest_ts - timedelta(hours=168))

            sub_24 = df[mask_24h]
            sub_72 = df[mask_72h]
            sub_168 = df[mask_168h]

            score_drop_24 = float(sub_24.iloc[0]["score_overall"] - current_score)
            score_drop_72 = float(sub_72.iloc[0]["score_overall"] - current_score)
            score_drop_168 = float(sub_168.iloc[0]["score_overall"] - current_score)

            score_MA_24 = float(sub_24["score_overall"].mean())
            score_MA_72 = float(sub_72["score_overall"].mean())
            score_STD_24 = float(sub_24["score_overall"].std(ddof=0)) if len(sub_24) > 1 else 0.0

            turb_MA_24 = float(sub_24["turbidity_raw"].mean())
            tds_MA_24 = float(sub_24["tds_raw"].mean())
            ph_MA_24 = float(sub_24["ph_raw"].mean())

            turb_drop_24 = float(latest["turbidity_raw"] - sub_24.iloc[0]["turbidity_raw"])
            tds_drop_24 = float(latest["tds_raw"] - sub_24.iloc[0]["tds_raw"])
            ph_drop_24 = float(latest["ph_raw"] - sub_24.iloc[0]["ph_raw"])

            turb_drop_72 = float(latest["turbidity_raw"] - sub_72.iloc[0]["turbidity_raw"])
            tds_drop_72 = float(latest["tds_raw"] - sub_72.iloc[0]["tds_raw"])
            ph_drop_72 = float(latest["ph_raw"] - sub_72.iloc[0]["ph_raw"])

            feature_dict = {
                "elapsed_hours": elapsed_hours,
                "ph_raw": float(latest["ph_raw"]),
                "tds_raw": float(latest["tds_raw"]),
                "turbidity_raw": float(latest["turbidity_raw"]),
                "temperature_raw": float(latest["temperature_raw"]),
                "score_overall": current_score,
                "score_drop_24": score_drop_24,
                "score_drop_72": score_drop_72,
                "score_drop_168": score_drop_168,
                "score_MA_24": score_MA_24,
                "score_MA_72": score_MA_72,
                "score_STD_24": score_STD_24,
                "turbidity_raw_MA24": turb_MA_24,
                "tds_raw_MA24": tds_MA_24,
                "ph_raw_MA24": ph_MA_24,
                "turbidity_raw_drop24": turb_drop_24,
                "tds_raw_drop24": tds_drop_24,
                "ph_raw_drop24": ph_drop_24,
                "turbidity_raw_drop72": turb_drop_72,
                "tds_raw_drop72": tds_drop_72,
                "ph_raw_drop72": ph_drop_72,
                "hour_of_day": hour_of_day,
            }

            model_features = bundle.get("feature_columns", FEATURE_COLUMNS)
            X = np.array([[feature_dict.get(col, 0.0) for col in model_features]], dtype=np.float32)
            raw_pred_hours = float(bundle["model"].predict(X)[0])
            cap_hours = float(bundle.get("target_cap_hours", 720.0))
            bounded_hours = max(0.0, min(cap_hours, raw_pred_hours))
            days_until = round(bounded_hours / 24.0, 1)
            pred_date = latest_ts + timedelta(hours=bounded_hours)

            return {
                "days_until_threshold": days_until,
                "predicted_date": pred_date.to_pydatetime() if hasattr(pred_date, "to_pydatetime") else pred_date,
                "confidence": 0.88,
                "model_used": "xgb_model_hourly_v2_horizon",
                "already_below_threshold": False,
                "trend_direction": "degrading" if days_until < 25.0 else "stable",
                "is_early_warning_active": bool(days_until <= 10.0),
            }
        except Exception as e:
            print(f"[PredictionService] XGBoost prediction failed, falling back: {e}")

    # Fallback to linear/polynomial predict_eta
    timestamps = [pd.to_datetime(t).to_pydatetime() for t in df["timestamp"]]
    scores = df["score_overall"].astype(float).tolist()
    res = predict_eta(timestamps, scores, threshold=DEFAULT_SCORE_THRESHOLD)
    days = res.get("days_until_threshold")
    res["is_early_warning_active"] = bool(days is not None and days <= 10.0)
    return res