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