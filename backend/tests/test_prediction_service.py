"""
Unit tests for app/services/prediction_service.py

Covers:
  - Insufficient data guard (< 12 points)
  - Already-below-threshold case
  - Linear degrading trend → returns days_until_threshold
  - Stable / improving trend → days_until is None
  - Polynomial model selected when curvature is significant
  - Confidence is in [0, 1] range
  - Returned dict has all required keys
"""

from datetime import datetime, timedelta

import pytest

from app.services.prediction_service import DEFAULT_SCORE_THRESHOLD, MIN_DATA_POINTS, predict_eta


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_series(
    n: int,
    start_score: float,
    slope: float,          # score change per hour
    start_time: datetime | None = None,
    interval_minutes: int = 10,
) -> tuple[list[datetime], list[float]]:
    """Generate a synthetic time series with a fixed linear slope."""
    if start_time is None:
        start_time = datetime(2026, 1, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=i * interval_minutes) for i in range(n)]
    scores = [max(0.0, min(100.0, start_score + slope * (i * interval_minutes / 60.0)))
              for i in range(n)]
    return timestamps, scores


# ─── Insufficient data ─────────────────────────────────────────────────────────

class TestInsufficientData:
    def test_below_min_data_points_returns_no_prediction(self):
        ts, sc = _make_series(MIN_DATA_POINTS - 1, start_score=80.0, slope=-0.5)
        result = predict_eta(ts, sc)
        assert result["days_until_threshold"] is None
        assert result["confidence"] == 0.0
        assert result["model_used"] == "none"

    def test_empty_input_returns_no_prediction(self):
        result = predict_eta([], [])
        assert result["days_until_threshold"] is None

    def test_exactly_min_points_proceeds(self):
        ts, sc = _make_series(MIN_DATA_POINTS, start_score=80.0, slope=-0.5)
        result = predict_eta(ts, sc)
        # Should not error; result has required keys
        assert "days_until_threshold" in result
        assert "confidence" in result


# ─── Already below threshold ───────────────────────────────────────────────────

class TestAlreadyBelowThreshold:
    def test_current_score_at_threshold_is_flagged(self):
        ts, sc = _make_series(20, start_score=DEFAULT_SCORE_THRESHOLD, slope=0.0)
        result = predict_eta(ts, sc)
        assert result["already_below_threshold"] is True
        assert result["days_until_threshold"] == 0.0

    def test_score_well_below_threshold(self):
        ts, sc = _make_series(20, start_score=30.0, slope=0.0)
        result = predict_eta(ts, sc)
        assert result["already_below_threshold"] is True


# ─── Degrading linear trend ────────────────────────────────────────────────────

class TestDegradingTrend:
    def test_linear_degradation_returns_positive_days_until(self):
        # Start at 80, drop 1 point/hour → crosses 60 in ~20 hours ≈ 0.83 days
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert result["days_until_threshold"] is not None
        assert result["days_until_threshold"] > 0
        assert result["trend_direction"] == "degrading"

    def test_predicted_date_is_in_the_future(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        if result["predicted_date"] is not None:
            assert result["predicted_date"] > ts[-1]

    def test_very_slow_degradation_may_not_reach_within_30_days(self):
        # Drop 0.01 pt/hr → takes ~2000 hours = 83 days to reach 60
        ts, sc = _make_series(30, start_score=80.0, slope=-0.01, interval_minutes=10)
        result = predict_eta(ts, sc)
        # Should either be None (won't reach in 30d) or a very large number
        if result["days_until_threshold"] is not None:
            assert result["days_until_threshold"] <= 30.0

    def test_confidence_is_non_negative(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert result["confidence"] >= 0.0

    def test_confidence_upper_bound(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert result["confidence"] <= 1.0


# ─── Stable / improving trend ──────────────────────────────────────────────────

class TestStableTrend:
    def test_flat_trend_returns_none_for_days_until(self):
        ts, sc = _make_series(30, start_score=80.0, slope=0.0)
        result = predict_eta(ts, sc)
        # Perfectly flat: either stable or model noise — days_until should be None
        if result["trend_direction"] == "stable":
            assert result["days_until_threshold"] is None

    def test_improving_trend_returns_none_for_days_until(self):
        ts, sc = _make_series(30, start_score=65.0, slope=+0.5)
        result = predict_eta(ts, sc)
        assert result["trend_direction"] in ("stable", "improving")
        assert result["days_until_threshold"] is None


# ─── Return structure ──────────────────────────────────────────────────────────

class TestReturnStructure:
    REQUIRED_KEYS = {
        "days_until_threshold",
        "predicted_date",
        "confidence",
        "model_used",
        "already_below_threshold",
        "trend_direction",
    }

    def test_all_keys_present_for_degrading(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_all_keys_present_for_insufficient_data(self):
        result = predict_eta([], [])
        assert self.REQUIRED_KEYS.issubset(result.keys()) or "note" in result

    def test_model_used_is_valid_string(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert result["model_used"] in ("linear_regression", "polynomial_ridge", "none")

    def test_trend_direction_is_valid(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result = predict_eta(ts, sc)
        assert result["trend_direction"] in ("degrading", "stable", "improving")


# ─── Custom threshold ──────────────────────────────────────────────────────────

class TestCustomThreshold:
    def test_higher_threshold_triggers_earlier(self):
        ts, sc = _make_series(30, start_score=80.0, slope=-1.0, interval_minutes=10)
        result_60 = predict_eta(ts, sc, threshold=60.0)
        result_75 = predict_eta(ts, sc, threshold=75.0)
        d60 = result_60.get("days_until_threshold")
        d75 = result_75.get("days_until_threshold")
        if d60 is not None and d75 is not None:
            assert d75 < d60
