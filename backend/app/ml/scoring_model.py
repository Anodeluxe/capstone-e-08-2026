"""
Standalone Mirror of Production Scoring Service
────────────────────────────────────────────────
Replicates the exact WQI scoring and A–E valve rule of
``app/services/scoring_service.py`` and the ESP32 firmware, so data
generators and standalone (Kaggle) training scripts can compute quality
scores without pulling in the FastAPI / config stack.

⚠️  KEEP IN SYNC: any change to ``scoring_service.py`` (sub-score
functions, weights, class thresholds) must be mirrored here, and vice
versa. ``tests/test_scoring_consistency.py`` verifies both produce
identical results.

Weights: PH=0.306, TEMPERATURE=0.278, TURBIDITY=0.222, TDS=0.194.
"""

import numpy as np

PARAMETER_WEIGHTS: dict[str, float] = {
    "ph": 0.306, "temperature": 0.278, "turbidity": 0.222, "tds": 0.194,
}

USE_POINT_WEIGHTS: dict[str, dict[str, float]] = {
    point: PARAMETER_WEIGHTS
    for point in ("bathroom", "kitchen", "laundry", "garden")
}

# Minimum WQI per use point before the firmware class rule closes its valve.
USE_POINT_THRESHOLDS: dict[str, float] = {
    "bathroom": 80.0,
    "kitchen": 65.0,
    "laundry": 45.0,
    "garden": 25.0,
}

DEFAULT_SCORE_THRESHOLD = 80.0


def _clamp(value) -> np.ndarray:
    return np.clip(value, 0.0, 100.0)


def ph_score(ph) -> np.ndarray:
    diff = np.abs(np.asarray(ph, dtype=float) - 7.0)
    return _clamp(np.where(
        diff <= 1.5, 100.0 - (diff / 1.5) * 20.0,
        np.where(diff <= 3.0, 80.0 - ((diff - 1.5) / 1.5) * 80.0, 0.0),
    ))


def temperature_score(celsius) -> np.ndarray:
    diff = np.abs(np.asarray(celsius, dtype=float) - 26.5)
    return _clamp(100.0 - (diff / 13.5) * 100.0)


def turbidity_score(ntu) -> np.ndarray:
    ntu = np.asarray(ntu, dtype=float)
    return _clamp(np.where(
        ntu <= 25.0, 100.0 - (ntu / 25.0) * 30.0,
        np.where(ntu <= 100.0, 70.0 - ((ntu - 25.0) / 75.0) * 70.0, 0.0),
    ))


def tds_score(ppm) -> np.ndarray:
    ppm = np.asarray(ppm, dtype=float)
    return _clamp(np.where(
        ppm <= 300.0, 100.0 - (ppm / 300.0) * 30.0,
        np.where(ppm <= 1000.0, 70.0 - ((ppm - 300.0) / 700.0) * 70.0, 0.0),
    ))


def _weighted_score(ph_s, temp_s, turb_s, tds_s) -> np.ndarray:
    w = PARAMETER_WEIGHTS
    return ph_s * w["ph"] + temp_s * w["temperature"] + turb_s * w["turbidity"] + tds_s * w["tds"]


def valves_to_close_from_score(score: float) -> list[str]:
    return [
        point for point, threshold in USE_POINT_THRESHOLDS.items()
        if score < threshold
    ]


def score_reading(ph: float, tds: float, turbidity: float, temperature: float) -> dict:
    """Mirror of `app.services.scoring_service.compute_scores`."""
    ph_s = ph_score(ph)
    turb_s = turbidity_score(turbidity)
    tds_s = tds_score(tds)
    temp_s = temperature_score(temperature)

    overall = round(float(_weighted_score(ph_s, temp_s, turb_s, tds_s)), 2)
    scores = {point: overall for point in USE_POINT_WEIGHTS}

    return {
        "overall": overall,
        "bathroom": scores["bathroom"],
        "kitchen": scores["kitchen"],
        "laundry": scores["laundry"],
        "garden": scores["garden"],
        "valves_to_close": valves_to_close_from_score(overall),
        "ph_score": round(float(ph_s), 2),
        "turbidity_score": round(float(turb_s), 2),
        "tds_score": round(float(tds_s), 2),
        "temperature_score": round(float(temp_s), 2),
    }


def valves_to_close(ph, turbidity, tds, temperature) -> list[str]:
    """WQI → valve IDs the firmware rule closes for a raw reading."""
    score = score_reading(ph, tds, turbidity, temperature)["overall"]
    return valves_to_close_from_score(score)


def overall_scores(ph, tds, turbidity, temperature) -> np.ndarray:
    """Vectorised WQI for the generator / RUL simulation."""
    score = _weighted_score(
        ph_score(ph), temperature_score(temperature),
        turbidity_score(turbidity), tds_score(tds),
    )
    return np.round(score, 2)
