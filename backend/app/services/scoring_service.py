"""
Weighted Quality Scoring Service
─────────────────────────────────
Computes a 0–100 quality score for each use point (bathroom, kitchen,
laundry, garden) based on the multi-parameter weighted scoring approach
described in the project proposal.

Each use point uses the same parameter weights; only the acceptance
threshold differs:
  - Bathroom → strictest (valve closes below 80)
  - Kitchen  → 65
  - Laundry  → 45
  - Garden   → most lenient (25)

Because the weights are shared, every use point gets the same score, so
`overall` equals each per-point score and the valve decisions are nested
(bathroom closes first, garden last).
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.sensor import ESP32SensorPayload

settings = get_settings()


# ─── Per-parameter scoring lookup ─────────────────────────────────────────────
# Maps a raw sensor value → a 0–100 sub-score.
# Thresholds are based on WHO / Indonesian drinking-water standards adapted
# for non-consumption domestic use.

def _ph_score(ph: float) -> float:
    """Ideal range 6.5–8.5. Outside → rapidly drops."""
    if 6.5 <= ph <= 8.5:
        return 100.0
    elif 6.0 <= ph < 6.5 or 8.5 < ph <= 9.0:
        return 70.0
    elif 5.5 <= ph < 6.0 or 9.0 < ph <= 9.5:
        return 40.0
    else:
        return 0.0


def _turbidity_score(ntu: float) -> float:
    """WHO guideline < 1 NTU for drinking; ≤ 5 NTU acceptable for domestic."""
    if ntu <= 1.0:
        return 100.0
    elif ntu <= 5.0:
        return 80.0
    elif ntu <= 10.0:
        return 55.0
    elif ntu <= 25.0:
        return 25.0
    else:
        return 0.0


def _tds_score(ppm: float) -> float:
    """WHO guideline ≤ 500 ppm acceptable; ≤ 300 ppm good."""
    if ppm <= 300:
        return 100.0
    elif ppm <= 500:
        return 80.0
    elif ppm <= 900:
        return 50.0
    elif ppm <= 1200:
        return 20.0
    else:
        return 0.0


def _temperature_score(celsius: float) -> float:
    """Comfortable range 20–30 °C. High temp accelerates bacterial growth."""
    if 20 <= celsius <= 30:
        return 100.0
    elif 15 <= celsius < 20 or 30 < celsius <= 35:
        return 75.0
    elif 10 <= celsius < 15 or 35 < celsius <= 40:
        return 50.0
    else:
        return 25.0


@dataclass
class UsePointThresholds:
    """
    Defines the minimum acceptable overall score per use point
    before its valve is automatically closed.
    """
    bathroom: float = 80.0
    kitchen: float = 65.0
    laundry: float = 45.0
    garden: float = 25.0


USE_POINT_THRESHOLDS = UsePointThresholds()

USE_POINTS = ("bathroom", "kitchen", "laundry", "garden")


def _weighted_score(
    ph_s: float,
    turbidity_s: float,
    tds_s: float,
    temp_s: float,
) -> float:
    """Shared weighted sum — identical for every use point."""
    return (
        ph_s * settings.weight_ph
        + turbidity_s * settings.weight_turbidity
        + tds_s * settings.weight_tds
        + temp_s * settings.weight_temperature
    )


@dataclass
class ScoringResult:
    overall: float
    bathroom: float
    kitchen: float
    laundry: float
    garden: float

    # Which valves should be automatically closed based on scores
    valves_to_close: list[str]

    # Sub-scores for transparency
    ph_score: float
    turbidity_score: float
    tds_score: float
    temperature_score: float


def compute_scores(reading: ESP32SensorPayload) -> ScoringResult:
    """
    Compute weighted quality scores for all 4 use points from a raw reading.
    Returns ScoringResult with per-valve scores and close recommendations.
    """
    ph_s = _ph_score(reading.ph)
    turb_s = _turbidity_score(reading.turbidity)
    tds_s = _tds_score(reading.tds)
    temp_s = _temperature_score(reading.temperature)

    score = round(_weighted_score(ph_s, turb_s, tds_s, temp_s), 2)
    scores: dict[str, float] = dict.fromkeys(USE_POINTS, score)

    overall = round(
        sum(scores.values()) / len(scores), 2
    )

    # Determine which valves should auto-close
    thresholds = USE_POINT_THRESHOLDS
    valves_to_close = []
    if scores["bathroom"] < thresholds.bathroom:
        valves_to_close.append("bathroom")
    if scores["kitchen"] < thresholds.kitchen:
        valves_to_close.append("kitchen")
    if scores["laundry"] < thresholds.laundry:
        valves_to_close.append("laundry")
    if scores["garden"] < thresholds.garden:
        valves_to_close.append("garden")

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