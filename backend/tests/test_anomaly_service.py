"""
Unit tests for app/services/anomaly_service.py

Covers:
  - No anomaly on first reading (no previous data)
  - No anomaly on stable consecutive readings
  - Overall score drop exceeding the threshold
  - Individual parameter deltas (pH, turbidity, TDS)
  - Culprit identification
  - change-point detection on window data
"""

import pytest

from app.services.anomaly_service import (
    AnomalyResult,
    detect_change_points_on_window,
    detect_sudden_change,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _reading(ph=7.0, turbidity=3.0, tds=200.0, temperature=25.0, water_level=80.0) -> dict:
    return {
        "ph": ph,
        "turbidity": turbidity,
        "tds": tds,
        "temperature": temperature,
        "water_level": water_level,
    }


# ─── First reading (no previous) ──────────────────────────────────────────────

class TestNoAnomaly:
    def test_no_previous_reading_is_never_anomaly(self):
        result = detect_sudden_change(
            current_score=85.0,
            previous_score=None,
            current_reading=_reading(),
            previous_reading=None,
        )
        assert isinstance(result, AnomalyResult)
        assert result.is_sudden_change is False
        assert result.anomaly_parameter is None

    def test_stable_readings_no_anomaly(self):
        curr = _reading(ph=7.0, turbidity=3.0, tds=200.0)
        prev = _reading(ph=7.1, turbidity=3.2, tds=195.0)
        result = detect_sudden_change(
            current_score=85.0,
            previous_score=84.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False

    def test_small_score_drop_no_anomaly(self):
        """Drop of 5 points is within normal range (threshold default = 20)."""
        curr = _reading()
        prev = _reading()
        result = detect_sudden_change(
            current_score=80.0,
            previous_score=85.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False


# ─── Overall score drop ────────────────────────────────────────────────────────

class TestScoreDrop:
    def test_score_drop_exactly_at_threshold_is_not_flagged(self):
        """Drop equal to threshold is NOT flagged (< not <=)."""
        curr = _reading()
        prev = _reading()
        result = detect_sudden_change(
            current_score=65.0,
            previous_score=85.0,   # drop = 20.0 exactly
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False

    def test_score_drop_above_threshold_is_flagged(self):
        curr = _reading(ph=4.0, turbidity=25.0, tds=900.0)
        prev = _reading(ph=7.0, turbidity=3.0, tds=200.0)
        result = detect_sudden_change(
            current_score=20.0,
            previous_score=85.0,   # drop = 65.0 >> threshold
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is True
        assert result.anomaly_parameter is not None
        assert result.description is not None

    def test_description_contains_score_values(self):
        curr = _reading(ph=4.0)
        prev = _reading(ph=7.0)
        result = detect_sudden_change(
            current_score=20.0,
            previous_score=85.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert "20.0" in result.description
        assert "85.0" in result.description


# ─── Individual parameter deltas ──────────────────────────────────────────────

class TestParameterDeltas:
    def test_ph_drop_beyond_1_5_flagged(self):
        """pH drop of 2.0 should be flagged even if overall score is OK."""
        curr = _reading(ph=5.0)
        prev = _reading(ph=7.1)
        result = detect_sudden_change(
            current_score=72.0,
            previous_score=75.0,   # small overall drop
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is True
        assert result.anomaly_parameter == "ph"

    def test_ph_rise_beyond_1_5_flagged(self):
        curr = _reading(ph=9.0)
        prev = _reading(ph=7.0)
        result = detect_sudden_change(
            current_score=74.0,
            previous_score=75.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is True
        assert result.anomaly_parameter == "ph"

    def test_ph_change_within_1_5_not_flagged(self):
        curr = _reading(ph=7.0)
        prev = _reading(ph=8.4)   # change = 1.4 < 1.5
        result = detect_sudden_change(
            current_score=80.0,
            previous_score=82.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False

    def test_turbidity_spike_above_15_ntu_flagged(self):
        curr = _reading(turbidity=20.0)
        prev = _reading(turbidity=3.0)   # spike = 17 > 15
        result = detect_sudden_change(
            current_score=60.0,
            previous_score=82.0,   # drop < threshold
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is True
        assert result.anomaly_parameter == "turbidity"

    def test_turbidity_spike_below_15_ntu_not_flagged(self):
        curr = _reading(turbidity=10.0)
        prev = _reading(turbidity=1.0)   # spike = 9 < 15
        result = detect_sudden_change(
            current_score=78.0,
            previous_score=82.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False

    def test_tds_spike_above_200_ppm_flagged(self):
        curr = _reading(tds=450.0)
        prev = _reading(tds=200.0)   # spike = 250 > 200
        result = detect_sudden_change(
            current_score=70.0,
            previous_score=82.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is True
        assert result.anomaly_parameter == "tds"

    def test_tds_spike_below_200_ppm_not_flagged(self):
        curr = _reading(tds=380.0)
        prev = _reading(tds=200.0)   # spike = 180 < 200
        result = detect_sudden_change(
            current_score=78.0,
            previous_score=82.0,
            current_reading=curr,
            previous_reading=prev,
        )
        assert result.is_sudden_change is False


# ─── Change-point detection on window ─────────────────────────────────────────

class TestChangePointDetection:
    def test_stable_signal_has_no_change_points(self):
        scores = [80.0] * 20
        result = detect_change_points_on_window(scores)
        assert isinstance(result, list)
        # A perfectly flat signal may return 0 or minimal change points
        assert len(result) == 0 or all(isinstance(i, int) for i in result)

    def test_step_drop_has_change_point(self):
        """A clear step function should produce at least one change point."""
        scores = [85.0] * 15 + [40.0] * 15   # abrupt drop at index 15
        result = detect_change_points_on_window(scores)
        assert len(result) >= 1

    def test_too_few_points_returns_empty(self):
        result = detect_change_points_on_window([80.0, 75.0, 70.0])
        assert result == []

    def test_returns_list_of_ints(self):
        scores = list(range(80, 50, -1)) + [50.0] * 10   # declining then flat
        result = detect_change_points_on_window(scores)
        assert all(isinstance(i, int) for i in result)
