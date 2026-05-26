"""
Model Trainer
──────────────
Performs full model retraining on a longer historical window and persists
the result via predictor.py. Meant to be called:

  - By the hourly APScheduler job (after predict_eta) to keep the model fresh
  - On-demand via a management command or test

The trainer is separate from prediction_service.py (which re-fits a
short, stateless model every call) so that longer-window training can be
persisted and reused without touching the real-time pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import PolynomialFeatures

from app.ml.predictor import ModelBundle, save_bundle

# Default path for the persisted model
DEFAULT_MODEL_PATH = Path("app/ml/models/quality_model.pkl")

MIN_TRAINING_POINTS = 12


@dataclass
class TrainingResult:
    bundle: ModelBundle
    r2: float
    data_points: int
    model_type: str
    hours_window: float
    trained_at: datetime


def train_model(
    timestamps: list[datetime],
    scores: list[float],
    threshold: float = 60.0,
) -> TrainingResult | None:
    """
    Fit the best available model (linear or polynomial Ridge) on the
    provided time-series data.

    Args:
        timestamps: list of datetime objects, oldest first
        scores:     corresponding quality scores (0–100)
        threshold:  the score below which water is considered unfit

    Returns:
        TrainingResult, or None if there are too few data points.
    """
    if len(scores) < MIN_TRAINING_POINTS:
        print(f"[Trainer] Not enough data ({len(scores)} points). Need {MIN_TRAINING_POINTS}.")
        return None

    t0 = timestamps[0]
    X_hours = np.array(
        [(t - t0).total_seconds() / 3600.0 for t in timestamps]
    ).reshape(-1, 1)
    y = np.array(scores)

    # ── Linear ────────────────────────────────────────────────────────────────
    lin: Any = LinearRegression()
    lin.fit(X_hours, y)
    r2_lin = r2_score(y, lin.predict(X_hours))

    # ── Polynomial (degree 2, Ridge regularisation) ───────────────────────────
    poly = PolynomialFeatures(degree=2, include_bias=False)
    X_poly = poly.fit_transform(X_hours)
    ridge: Any = Ridge(alpha=1.0)
    ridge.fit(X_poly, y)
    r2_poly = r2_score(y, ridge.predict(X_poly))

    use_poly = r2_poly > r2_lin + 0.05

    if use_poly:
        model, poly_out, model_type, r2 = ridge, poly, "polynomial_ridge", r2_poly
    else:
        model, poly_out, model_type, r2 = lin, None, "linear_regression", r2_lin

    hours_window = (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0

    bundle = ModelBundle(
        model=model,
        poly=poly_out,
        model_type=model_type,
        threshold=threshold,
        r2=r2,
        trained_at=datetime.utcnow(),
        hours_window=hours_window,
        data_points=len(scores),
    )

    print(
        f"[Trainer] Trained {model_type} | R²={r2:.3f} "
        f"| points={len(scores)} | window={hours_window:.1f}h"
    )
    return TrainingResult(
        bundle=bundle,
        r2=r2,
        data_points=len(scores),
        model_type=model_type,
        hours_window=hours_window,
        trained_at=bundle.trained_at,
    )


def train_and_save(
    timestamps: list[datetime],
    scores: list[float],
    threshold: float = 60.0,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> TrainingResult | None:
    """
    Train a model and persist it to disk.
    Returns None if training is skipped (insufficient data).
    """
    result = train_model(timestamps, scores, threshold)
    if result is not None:
        save_bundle(result.bundle, model_path)
    return result
