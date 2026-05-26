"""
Anomaly Detection Service
──────────────────────────
Detects two types of water quality degradation:

1. SUDDEN change  — large drop in score/parameter between consecutive
                    readings (indicates inlet contamination).
                    Uses simple delta thresholding + ruptures change-point
                    detection for confirmation on rolling windows.

2. GRADUAL change — handled by the prediction service (trend → ETA).
                    This module only flags if a parameter is already
                    in a deteriorating trend and below warning level.
"""

from dataclasses import dataclass

import numpy as np

from app.core.config import get_settings
from app.services.scoring_service import ScoringResult

settings = get_settings()


@dataclass
class AnomalyResult:
    is_sudden_change: bool
    anomaly_parameter: str | None  # which sensor triggered the flag
    description: str | None


def detect_sudden_change(
    current_score: float,
    previous_score: float | None,
    current_reading: dict,   # {"ph": ..., "turbidity": ..., ...}
    previous_reading: dict | None,
) -> AnomalyResult:
    """
    Compare the current score/reading against the immediately previous one.
    Flags a sudden change if the overall score drops by more than
    `SUDDEN_CHANGE_THRESHOLD` points in a single interval.

    Also checks individual parameter deltas for more granular attribution.
    """
    if previous_score is None or previous_reading is None:
        return AnomalyResult(is_sudden_change=False, anomaly_parameter=None, description=None)

    score_drop = previous_score - current_score

    if score_drop < settings.sudden_change_threshold:
        # No sudden overall drop — check individual parameters
        param_anomaly = _check_parameter_deltas(current_reading, previous_reading)
        if param_anomaly:
            return AnomalyResult(
                is_sudden_change=True,
                anomaly_parameter=param_anomaly,
                description=f"Sudden change in {param_anomaly} detected",
            )
        return AnomalyResult(is_sudden_change=False, anomaly_parameter=None, description=None)

    # Overall score dropped sharply — identify which parameter caused it
    culprit = _identify_culprit(current_reading, previous_reading)
    return AnomalyResult(
        is_sudden_change=True,
        anomaly_parameter=culprit,
        description=(
            f"Overall quality score dropped by {score_drop:.1f} points "
            f"(prev={previous_score:.1f}, curr={current_score:.1f}). "
            f"Likely caused by: {culprit or 'multiple parameters'}."
        ),
    )


def _check_parameter_deltas(
    current: dict,
    previous: dict,
) -> str | None:
    """
    Check each individual sensor for sudden changes even if the overall
    score didn't move enough. Returns the parameter name or None.
    """
    # pH drop > 1.5 or rise > 1.5 is considered sudden
    if abs(current.get("ph", 0) - previous.get("ph", 0)) > 1.5:
        return "ph"

    # Turbidity spike > 15 NTU sudden
    if current.get("turbidity", 0) - previous.get("turbidity", 0) > 15.0:
        return "turbidity"

    # TDS spike > 200 ppm sudden
    if current.get("tds", 0) - previous.get("tds", 0) > 200.0:
        return "tds"

    return None


def _identify_culprit(current: dict, previous: dict) -> str | None:
    """Return the parameter with the largest relative change."""
    deltas = {
        "ph": abs(current.get("ph", 7) - previous.get("ph", 7)) / 14.0,
        "turbidity": abs(current.get("turbidity", 0) - previous.get("turbidity", 0)) / 100.0,
        "tds": abs(current.get("tds", 0) - previous.get("tds", 0)) / 1500.0,
        "temperature": abs(current.get("temperature", 25) - previous.get("temperature", 25)) / 50.0,
    }
    return max(deltas, key=deltas.get) if any(v > 0 for v in deltas.values()) else None


def detect_change_points_on_window(score_history: list[float]) -> list[int]:
    """
    Run ruptures PELT algorithm on a rolling window of scores to detect
    structural change points. Used for periodic batch analysis.

    Args:
        score_history: list of overall quality scores, oldest first

    Returns:
        List of indices where change points were detected
    """
    try:
        import ruptures as rpt

        if len(score_history) < 10:
            return []

        signal = np.array(score_history).reshape(-1, 1)
        model = rpt.Pelt(model="rbf").fit(signal)
        # pen=3 balances sensitivity vs. false positives
        change_points = model.predict(pen=3)
        # ruptures returns the end index of each segment; exclude last (= len)
        return change_points[:-1]

    except ImportError:
        # ruptures not installed — skip
        return []
    except Exception as e:
        print(f"[Anomaly] ruptures error: {e}")
        return []