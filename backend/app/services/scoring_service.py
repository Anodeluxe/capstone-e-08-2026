"""
Weighted Quality Scoring Service
─────────────────────────────────
Computes the same 0–100 WQI score and A–E valve classes as the ESP32
firmware, so the cloud and the device always agree on which valves may
be open:

  - A (score >= 80) → all valves open
  - B (score >= 65) → bathroom closed
  - C (score >= 45) → bathroom and kitchen closed
  - D (score >= 25) → only garden open
  - E (score < 25)  → all valves closed

The score is shared by every use point; only the class rule differs.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.sensor import ESP32SensorPayload

settings = get_settings()


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _ph_score(ph: float) -> float:
    """Mirror of firmware calcWaterScore() pH term."""
    diff = abs(ph - 7.0)
    if diff <= 1.5:
        return _clamp_score(100.0 - (diff / 1.5) * 20.0)
    if diff <= 3.0:
        return _clamp_score(80.0 - ((diff - 1.5) / 1.5) * 80.0)
    return 0.0


def _temperature_score(celsius: float) -> float:
    """Mirror of firmware calcWaterScore() temperature term."""
    return _clamp_score(100.0 - (abs(celsius - 26.5) / 13.5) * 100.0)


def _turbidity_score(ntu: float) -> float:
    """Mirror of firmware calcWaterScore() turbidity term."""
    if ntu <= 25.0:
        return _clamp_score(100.0 - (ntu / 25.0) * 30.0)
    if ntu <= 100.0:
        return _clamp_score(70.0 - ((ntu - 25.0) / 75.0) * 70.0)
    return 0.0


def _tds_score(ppm: float) -> float:
    """Mirror of firmware calcWaterScore() TDS term."""
    if ppm <= 300.0:
        return _clamp_score(100.0 - (ppm / 300.0) * 30.0)
    if ppm <= 1000.0:
        return _clamp_score(70.0 - ((ppm - 300.0) / 700.0) * 70.0)
    return 0.0


USE_POINTS = ("bathroom", "kitchen", "laundry", "garden")

# Firmware class thresholds.
USE_POINT_THRESHOLDS = {
    "bathroom": 80.0,
    "kitchen": 65.0,
    "laundry": 45.0,
    "garden": 25.0,
}


def _weighted_score(
    ph_s: float,
    turbidity_s: float,
    tds_s: float,
    temp_s: float,
) -> float:
    """Same weights and order as the firmware WQI."""
    return (
        ph_s * settings.weight_ph
        + temp_s * settings.weight_temperature
        + turbidity_s * settings.weight_turbidity
        + tds_s * settings.weight_tds
    )


@dataclass
class ScoringResult:
    overall: float
    bathroom: float
    kitchen: float
    laundry: float
    garden: float

    # Which valves the firmware rule requires to be closed
    valves_to_close: list[str]

    # Sub-scores for transparency
    ph_score: float
    turbidity_score: float
    tds_score: float
    temperature_score: float


def compute_scores(reading: ESP32SensorPayload) -> ScoringResult:
    """
    Compute the firmware WQI for a raw reading and apply its class rule.
    Returns ScoringResult with per-valve scores and close recommendations.
    """
    ph_s = _ph_score(reading.ph)
    turb_s = _turbidity_score(reading.turbidity)
    tds_s = _tds_score(reading.tds)
    temp_s = _temperature_score(reading.temperature)

    score = round(_weighted_score(ph_s, turb_s, tds_s, temp_s), 2)
    scores: dict[str, float] = dict.fromkeys(USE_POINTS, score)

    overall = round(sum(scores.values()) / len(scores), 2)

    valves_to_close = [
        point
        for point in USE_POINTS
        if scores[point] < USE_POINT_THRESHOLDS[point]
    ]

    return ScoringResult(
        overall=overall,
        bathroom=scores["bathroom"],
        kitchen=scores["kitchen"],
        laundry=scores["laundry"],
        garden=scores["garden"],
        valves_to_close=valves_to_close,
        ph_score=round(ph_s, 2),
        turbidity_score=round(turb_s, 2),
        tds_score=round(tds_s, 2),
        temperature_score=round(temp_s, 2),
    )
