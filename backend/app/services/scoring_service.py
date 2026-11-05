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

from bisect import bisect_right
from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.sensor import ESP32SensorPayload

settings = get_settings()


# ─── Per-parameter scoring lookup ─────────────────────────────────────────────
# Maps a raw sensor value → a 0–100 sub-score by linear interpolation between
# standards-based anchors. Values outside the outermost anchors are clamped.
# Thresholds are based on WHO / Indonesian drinking-water standards adapted
# for non-consumption domestic use.

def _interp(value: float, xs: tuple[float, ...], ys: tuple[float, ...]) -> float:
    """Piecewise-linear lookup between anchors; clamps outside the range."""
    if value <= xs[0]:
        return ys[0]
    if value >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, value)
    x0, x1 = xs[i - 1], xs[i]
    y0, y1 = ys[i - 1], ys[i]
    return y0 + (value - x0) * (y1 - y0) / (x1 - x0)


_PH_X = (5.0, 5.5, 6.0, 6.5, 8.5, 9.0, 9.5, 10.0)
_PH_Y = (0.0, 40.0, 70.0, 100.0, 100.0, 70.0, 40.0, 0.0)
_TURB_X = (0.0, 1.0, 5.0, 10.0, 25.0, 50.0)
_TURB_Y = (100.0, 100.0, 80.0, 55.0, 25.0, 0.0)
_TDS_X = (0.0, 300.0, 500.0, 900.0, 1200.0, 1500.0)
_TDS_Y = (100.0, 100.0, 80.0, 50.0, 20.0, 0.0)
_TEMP_X = (5.0, 10.0, 15.0, 20.0, 30.0, 35.0, 40.0, 45.0)
_TEMP_Y = (25.0, 50.0, 75.0, 100.0, 100.0, 75.0, 50.0, 25.0)


def _ph_score(ph: float) -> float:
    """Ideal 6.5–8.5 (100), drops linearly to 0 at pH 5.0 / 10.0."""
    return _interp(ph, _PH_X, _PH_Y)


def _turbidity_score(ntu: float) -> float:
    """Ideal ≤ 1 NTU (100), drops linearly to 0 at 50 NTU."""
    return _interp(ntu, _TURB_X, _TURB_Y)


def _tds_score(ppm: float) -> float:
    """Ideal ≤ 300 ppm (100), drops linearly to 0 at 1500 ppm."""
    return _interp(ppm, _TDS_X, _TDS_Y)


def _temperature_score(celsius: float) -> float:
    """Ideal 20–30 °C (100), drops linearly to 25 at 5 °C / 45 °C."""
    return _interp(celsius, _TEMP_X, _TEMP_Y)


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