"""
Standalone Mirror of Production Scoring Service
────────────────────────────────────────────────
Replicates the exact weighted scoring logic of
``app/services/scoring_service.py`` so that data generators and
standalone (Kaggle) training scripts can compute quality scores
without pulling in the FastAPI / config stack.

⚠️  KEEP IN SYNC: any change to ``scoring_service.py`` (sub-score
functions, weights, firmware valve rules) must be mirrored here, and vice
versa. ``tests/test_scoring_consistency.py`` verifies both produce
identical results.

Bathroom weights below match the `.env` defaults:
WEIGHT_PH=0.306, WEIGHT_TURBIDITY=0.222, WEIGHT_TDS=0.194, WEIGHT_TEMPERATURE=0.278
All use points share the same weights; valve decisions use the firmware
class rule (LIM_A/B/C + VALVE_RULE), not the score.
"""

import numpy as np

# ─── Sub-score functions (identical to scoring_service) ─────────────────────
# Linear interpolation between standards-based anchors; np.interp clamps.

PH_X = np.array([5.0, 5.5, 6.0, 6.5, 8.5, 9.0, 9.5, 10.0])
PH_Y = np.array([0.0, 40.0, 70.0, 100.0, 100.0, 70.0, 40.0, 0.0])
TURB_X = np.array([0.0, 1.0, 5.0, 10.0, 25.0, 50.0])
TURB_Y = np.array([100.0, 100.0, 80.0, 55.0, 25.0, 0.0])
TDS_X = np.array([0.0, 300.0, 500.0, 900.0, 1200.0, 1500.0])
TDS_Y = np.array([100.0, 100.0, 80.0, 50.0, 20.0, 0.0])
TEMP_X = np.array([5.0, 10.0, 15.0, 20.0, 30.0, 35.0, 40.0, 45.0])
TEMP_Y = np.array([25.0, 50.0, 75.0, 100.0, 100.0, 75.0, 50.0, 25.0])


def _interp(x, xs, ys) -> np.ndarray:
    """Same arithmetic order as scoring_service._interp, vectorised."""
    x = np.asarray(x, dtype=float)
    i = np.clip(np.searchsorted(xs, x, side="right"), 1, len(xs) - 1)
    x0, x1 = xs[i - 1], xs[i]
    y0, y1 = ys[i - 1], ys[i]
    out = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    out = np.where(x <= xs[0], ys[0], out)
    return np.where(x >= xs[-1], ys[-1], out)


def ph_score(ph) -> np.ndarray:
    """Ideal 6.5–8.5 (100), drops linearly to 0 at pH 5.0 / 10.0."""
    return _interp(ph, PH_X, PH_Y)


def turbidity_score(ntu) -> np.ndarray:
    """Ideal ≤ 1 NTU (100), drops linearly to 0 at 50 NTU."""
    return _interp(ntu, TURB_X, TURB_Y)


def tds_score(ppm) -> np.ndarray:
    """Ideal ≤ 300 ppm (100), drops linearly to 0 at 1500 ppm."""
    return _interp(ppm, TDS_X, TDS_Y)


def temperature_score(celsius) -> np.ndarray:
    """Ideal 20–30 °C (100), drops linearly to 25 at 5 °C / 45 °C."""
    return _interp(celsius, TEMP_X, TEMP_Y)


# ─── Weights & thresholds (identical to scoring_service) ─────────────────────

# Same weights for every use point; only the thresholds differ.
PARAMETER_WEIGHTS: dict[str, float] = {
    "ph": 0.306, "turbidity": 0.222, "tds": 0.194, "temperature": 0.278,
}

USE_POINT_WEIGHTS: dict[str, dict[str, float]] = {
    point: PARAMETER_WEIGHTS
    for point in ("bathroom", "kitchen", "laundry", "garden")
}

# Same limits as esp32_waterq_cloud_mqtt.txt: (ph_min, ph_max, ntu_max, tds_max)
FIRMWARE_LIMITS: dict[str, tuple[float, float, float, float]] = {
    "A": (6.5, 8.5, 3.0, 300.0),
    "B": (6.0, 9.0, 25.0, 1000.0),
    "C": (5.0, 10.0, 100.0, 2000.0),
}

# Same VALVE_RULE order as the firmware: bathroom, kitchen, laundry, garden.
VALVE_RULE: dict[str, tuple[bool, bool, bool, bool]] = {
    "A": (True, True, True, True),
    "B": (True, False, True, True),
    "C": (False, False, False, True),
    "D": (False, False, False, False),
}

USE_POINTS = ("bathroom", "kitchen", "laundry", "garden")


def firmware_class(ph, turbidity, tds):
    """Classify water exactly like the firmware (temperature is ignored)."""
    ph = np.asarray(ph, dtype=float)
    turbidity = np.asarray(turbidity, dtype=float)
    tds = np.asarray(tds, dtype=float)
    out = np.full(np.broadcast(ph, turbidity, tds).shape, "D", dtype="<U1")
    unset = np.ones(out.shape, dtype=bool)
    for cls, (ph_min, ph_max, ntu_max, tds_max) in FIRMWARE_LIMITS.items():
        hit = (
            unset
            & (ph >= ph_min) & (ph <= ph_max)
            & (turbidity <= ntu_max) & (tds <= tds_max)
        )
        out[hit] = cls
        unset &= ~hit
    return out


def valves_to_close(ph, turbidity, tds) -> list[str]:
    """Firmware VALVE_RULE → valve IDs that must be closed for this reading."""
    cls = str(firmware_class(ph, turbidity, tds))
    return [p for p, allowed in zip(USE_POINTS, VALVE_RULE[cls]) if not allowed]

# Overall-quality threshold used by prediction_service for early warning / RUL.
DEFAULT_SCORE_THRESHOLD = 80.0


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
    for point, w in USE_POINT_WEIGHTS.items():
        scores[point] = round(
            float(ph_s) * w["ph"]
            + float(turb_s) * w["turbidity"]
            + float(tds_s) * w["tds"]
            + float(temp_s) * w["temperature"],
            2,
        )

    overall = round(float(np.mean(list(scores.values()))), 2)

    valves = valves_to_close(ph, turbidity, tds)

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
        for point, w in USE_POINT_WEIGHTS.items()
    }
    return np.round(np.mean(list(point_scores.values()), axis=0), 2)