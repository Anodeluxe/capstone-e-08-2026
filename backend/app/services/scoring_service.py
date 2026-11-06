"""
Weighted Quality Scoring Service
─────────────────────────────────
Computes a 0–100 quality score for each use point (bathroom, kitchen,
laundry, garden) based on the multi-parameter weighted scoring approach
described in the project proposal.

Valve decisions follow the firmware class rule (LIM_A/B/C + VALVE_RULE)
so the cloud and the ESP32 close/open the same valves:
  - A → all valves open
  - B → bathroom, laundry, garden open; kitchen closed
  - C → garden only
  - D → all closed

Scores still use the same weights for every use point, so `overall`
equals each per-point score; the score is now informational only.
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


USE_POINTS = ("bathroom", "kitchen", "laundry", "garden")

# Same limits as esp32_waterq_cloud_mqtt.txt: (ph_min, ph_max, ntu_max, tds_max)
_LIMITS = {
    "A": (6.5, 8.5, 3.0, 300.0),
    "B": (6.0, 9.0, 25.0, 1000.0),
    "C": (5.0, 10.0, 100.0, 2000.0),
}

# Same VALVE_RULE order as the firmware: bathroom, kitchen, laundry, garden.
_VALVE_RULE = {
    "A": (True, True, True, True),
    "B": (True, False, True, True),
    "C": (False, False, False, True),
    "D": (False, False, False, False),
}


def _firmware_class(ph: float, turbidity: float, tds: float) -> str:
    """Classify water exactly like the firmware (temperature is ignored)."""
    for cls, (ph_min, ph_max, ntu_max, tds_max) in _LIMITS.items():
        if ph_min <= ph <= ph_max and turbidity <= ntu_max and tds <= tds_max:
            return cls
    return "D"


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

    # Determine which valves should auto-close using the firmware class rule
    water_class = _firmware_class(reading.ph, reading.turbidity, reading.tds)
    valves_to_close = [
        point
        for point, allowed in zip(USE_POINTS, _VALVE_RULE[water_class])
        if not allowed
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