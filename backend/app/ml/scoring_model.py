"""
Standalone Mirror of Production Scoring Service
────────────────────────────────────────────────
Replicates the exact weighted scoring logic of
``app/services/scoring_service.py`` so that data generators and
standalone (Kaggle) training scripts can compute quality scores
without pulling in the FastAPI / config stack.

⚠️  KEEP IN SYNC: any change to ``scoring_service.py`` (sub-score
functions, weights, valve thresholds) must be mirrored here, and vice
versa. ``tests/test_scoring_consistency.py`` verifies both produce
identical results.

Bathroom weights below match the `.env` defaults:
WEIGHT_PH=0.30, WEIGHT_TURBIDITY=0.30, WEIGHT_TDS=0.25, WEIGHT_TEMPERATURE=0.15
"""

import numpy as np

# ─── Sub-score functions (identical to scoring_service) ─────────────────────

def ph_score(ph) -> np.ndarray:
    """Ideal range 6.5–8.5. Outside → rapidly drops."""
    ph = np.asarray(ph, dtype=float)
    out = np.full_like(ph, 0.0)
    out = np.where((6.5 <= ph) & (ph <= 8.5), 100.0, out)
    out = np.where(((6.0 <= ph) & (ph < 6.5)) | ((8.5 < ph) & (ph <= 9.0)), 70.0, out)
    out = np.where(((5.5 <= ph) & (ph < 6.0)) | ((9.0 < ph) & (ph <= 9.5)), 40.0, out)
    return out


def turbidity_score(ntu) -> np.ndarray:
    """WHO guideline < 1 NTU for drinking; ≤ 5 NTU acceptable for domestic."""
    ntu = np.asarray(ntu, dtype=float)
    out = np.full_like(ntu, 0.0)
    out = np.where(ntu <= 1.0, 100.0, out)
    out = np.where((1.0 < ntu) & (ntu <= 5.0), 80.0, out)
    out = np.where((5.0 < ntu) & (ntu <= 10.0), 55.0, out)
    out = np.where((10.0 < ntu) & (ntu <= 25.0), 25.0, out)
    return out


def tds_score(ppm) -> np.ndarray:
    """WHO guideline ≤ 500 ppm acceptable; ≤ 300 ppm good."""
    ppm = np.asarray(ppm, dtype=float)
    out = np.full_like(ppm, 0.0)
    out = np.where(ppm <= 300.0, 100.0, out)
    out = np.where((300.0 < ppm) & (ppm <= 500.0), 80.0, out)
    out = np.where((500.0 < ppm) & (ppm <= 900.0), 50.0, out)
    out = np.where((900.0 < ppm) & (ppm <= 1200.0), 20.0, out)
    return out


def temperature_score(celsius) -> np.ndarray:
    """Comfortable range 20–30 °C. High temp accelerates bacterial growth."""
    celsius = np.asarray(celsius, dtype=float)
    out = np.full_like(celsius, 25.0)
    out = np.where((20.0 <= celsius) & (celsius <= 30.0), 100.0, out)
    out = np.where((15.0 <= celsius) & (celsius < 20.0)
                   | (30.0 < celsius) & (celsius <= 35.0), 75.0, out)
    out = np.where((10.0 <= celsius) & (celsius < 15.0)
                   | (35.0 < celsius) & (celsius <= 40.0), 50.0, out)
    return out


# ─── Weights & thresholds (identical to scoring_service) ─────────────────────

USE_POINT_WEIGHT_OVERRIDES: dict[str, dict[str, float]] = {
    "bathroom": {"ph": 0.30, "turbidity": 0.30, "tds": 0.25, "temperature": 0.15},
    "kitchen": {"ph": 0.35, "turbidity": 0.35, "tds": 0.20, "temperature": 0.10},
    "laundry": {"ph": 0.25, "turbidity": 0.40, "tds": 0.25, "temperature": 0.10},
    "garden": {"ph": 0.20, "turbidity": 0.30, "tds": 0.30, "temperature": 0.20},
}

# Minimum acceptable overall score per use point before auto-close.
USE_POINT_THRESHOLDS: dict[str, float] = {
    "bathroom": 60.0,
    "kitchen": 65.0,
    "laundry": 45.0,
    "garden": 30.0,
}

# Overall-quality threshold used by prediction_service for early warning / RUL.
DEFAULT_SCORE_THRESHOLD = 60.0


# ─── Scalar score mirror (identical to compute_scores) ───────────────────────

def score_reading(ph: float, tds: float, turbidity: float, temperature: float) -> dict:
    """
    Mirror of `app.services.scoring_service.compute_scores`.
    Applies the exact rounding used in production so the two stay identical.

    Returns dict with keys: overall, bathroom, kitchen, laundry, garden,
    valves_to_close, ph_score, turbidity_score, tds_score, temperature_score.
    """
    ph_s = ph_score(ph)
    turb_s = turbidity_score(turbidity)
    tds_s = tds_score(tds)
    temp_s = temperature_score(temperature)

    scores: dict[str, float] = {}
    for point, w in USE_POINT_WEIGHT_OVERRIDES.items():
        scores[point] = round(
            float(ph_s) * w["ph"]
            + float(turb_s) * w["turbidity"]
            + float(tds_s) * w["tds"]
            + float(temp_s) * w["temperature"],
            2,
        )

    overall = round(float(np.mean(list(scores.values()))), 2)

    valves = [
        point
        for point, thr in USE_POINT_THRESHOLDS.items()
        if scores[point] < thr
    ]

    return {
        "overall": overall,
        "bathroom": scores["bathroom"],
        "kitchen": scores["kitchen"],
        "laundry": scores["laundry"],
        "garden": scores["garden"],
        "valves_to_close": valves,
        "ph_score": round(float(ph_s), 2),
        "turbidity_score": round(float(turb_s), 2),
        "tds_score": round(float(tds_s), 2),
        "temperature_score": round(float(temp_s), 2),
    }


# ─── Vectorised overall score (for generator / RUL simulation) ────────────────

def overall_scores(ph, tds, turbidity, temperature) -> np.ndarray:
    """
    Compute the production `score_overall` for arrays of raw readings.
    Applies the same per-use-point rounding as production, then averages.
    Returns a 1-D array (mean of the 4 per-use-point scores).
    """
    ph_s = ph_score(ph)
    turb_s = turbidity_score(turbidity)
    tds_s = tds_score(tds)
    temp_s = temperature_score(temperature)

    point_scores = {
        point: np.round(
            ph_s * w["ph"]
            + turb_s * w["turbidity"]
            + tds_s * w["tds"]
            + temp_s * w["temperature"],
            2,
        )
        for point, w in USE_POINT_WEIGHT_OVERRIDES.items()
    }
    return np.round(np.mean(list(point_scores.values()), axis=0), 2)


def valves_to_close_from_scores(scores) -> list[str]:
    """Helper mirror of the per-use-point auto-close rule."""
    return [
        point for point, thr in USE_POINT_THRESHOLDS.items()
        if scores[point] < thr
    ]