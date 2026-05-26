"""
Model Persistence — Predictor
──────────────────────────────
Saves and loads trained sklearn model bundles to/from disk as .pkl files
so the prediction service does not need to refit from scratch on every call.

Usage flow:
  1. trainer.py calls train_model() → ModelBundle
  2. save_bundle(bundle, path) writes it to disk
  3. load_bundle(path) restores it for fast inference
  4. predict_score_at_hour(bundle, hours) runs inference
"""

import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ModelBundle:
    """
    A fully self-contained, serialisable model state.
    Contains everything needed to make a prediction without re-fitting.
    """
    model: Any                   # LinearRegression or Ridge
    poly: Any | None             # PolynomialFeatures (None for linear model)
    model_type: str              # "linear_regression" | "polynomial_ridge"
    threshold: float             # score threshold the model targets
    r2: float                    # R² of the fit (confidence proxy)
    trained_at: datetime = field(default_factory=datetime.utcnow)
    hours_window: float = 72.0   # training data window in hours
    data_points: int = 0


def save_bundle(bundle: ModelBundle, path: str | Path) -> None:
    """Pickle a ModelBundle to disk. Creates parent directories as needed."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[Predictor] Model saved → {dest}")


def load_bundle(path: str | Path) -> ModelBundle | None:
    """
    Load a ModelBundle from disk.
    Returns None if the file doesn't exist or can't be loaded
    (graceful fallback so the app always starts).
    """
    src = Path(path)
    if not src.exists():
        return None
    try:
        with open(src, "rb") as f:
            bundle = pickle.load(f)
        if not isinstance(bundle, ModelBundle):
            return None
        print(f"[Predictor] Model loaded ← {src} (trained {bundle.trained_at.isoformat()})")
        return bundle
    except Exception as e:
        print(f"[Predictor] Failed to load model from {src}: {e}")
        return None


def predict_score_at_hour(bundle: ModelBundle, hours_from_t0: float) -> float:
    """
    Predict the quality score at `hours_from_t0` hours after the training
    window's first data point.

    Args:
        bundle: loaded ModelBundle
        hours_from_t0: hours elapsed from the first training sample

    Returns:
        Predicted score (may be < 0 or > 100 for extreme extrapolation).
    """
    import numpy as np

    X = np.array([[hours_from_t0]])
    if bundle.poly is not None:
        X = bundle.poly.transform(X)
    return float(bundle.model.predict(X)[0])
