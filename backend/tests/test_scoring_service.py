"""
Unit tests for app/services/scoring_service.py

Tests each sub-scorer in isolation, then the full compute_scores() pipeline
including valve auto-close logic.
"""

import pytest

from app.schemas.sensor import ESP32SensorPayload
from app.services.scoring_service import (
    USE_POINT_THRESHOLDS,
    ScoringResult,
    _ph_score,
    _tds_score,
    _temperature_score,
    _turbidity_score,
    compute_scores,
)


# ─── pH sub-scorer ─────────────────────────────────────────────────────────────

class TestPhScore:
    def test_ideal_range_center(self):
        assert _ph_score(7.0) == 100.0

    def test_ideal_range_boundaries(self):
        assert _ph_score(6.5) == 100.0
        assert _ph_score(8.5) == 100.0

    def test_acceptable_range(self):
        assert _ph_score(6.2) == 70.0
        assert _ph_score(8.7) == 70.0

    def test_poor_range(self):
        assert _ph_score(5.7) == 40.0
        assert _ph_score(9.2) == 40.0

    def test_unacceptable(self):
        assert _ph_score(4.0) == 0.0
        assert _ph_score(10.0) == 0.0
        assert _ph_score(0.0) == 0.0
        assert _ph_score(14.0) == 0.0


# ─── Turbidity sub-scorer ──────────────────────────────────────────────────────

class TestTurbidityScore:
    def test_excellent(self):
        assert _turbidity_score(0.5) == 100.0
        assert _turbidity_score(1.0) == 100.0

    def test_acceptable(self):
        assert _turbidity_score(3.0) == 80.0
        assert _turbidity_score(5.0) == 80.0

    def test_poor(self):
        assert _turbidity_score(7.0) == 55.0
        assert _turbidity_score(10.0) == 55.0

    def test_very_poor(self):
        assert _turbidity_score(15.0) == 25.0
        assert _turbidity_score(25.0) == 25.0

    def test_unacceptable(self):
        assert _turbidity_score(30.0) == 0.0
        assert _turbidity_score(100.0) == 0.0


# ─── TDS sub-scorer ────────────────────────────────────────────────────────────

class TestTdsScore:
    def test_excellent(self):
        assert _tds_score(100.0) == 100.0
        assert _tds_score(300.0) == 100.0

    def test_acceptable(self):
        assert _tds_score(400.0) == 80.0
        assert _tds_score(500.0) == 80.0

    def test_poor(self):
        assert _tds_score(600.0) == 50.0
        assert _tds_score(900.0) == 50.0

    def test_very_poor(self):
        assert _tds_score(1000.0) == 20.0
        assert _tds_score(1200.0) == 20.0

    def test_unacceptable(self):
        assert _tds_score(1500.0) == 0.0


# ─── Temperature sub-scorer ────────────────────────────────────────────────────

class TestTemperatureScore:
    def test_comfortable(self):
        assert _temperature_score(25.0) == 100.0
        assert _temperature_score(20.0) == 100.0
        assert _temperature_score(30.0) == 100.0

    def test_cool_or_warm(self):
        assert _temperature_score(17.0) == 75.0
        assert _temperature_score(33.0) == 75.0

    def test_cold_or_hot(self):
        assert _temperature_score(12.0) == 50.0
        assert _temperature_score(37.0) == 50.0

    def test_extreme(self):
        assert _temperature_score(0.0) == 25.0
        assert _temperature_score(50.0) == 25.0


# ─── compute_scores() full pipeline ───────────────────────────────────────────

class TestComputeScores:
    def test_good_reading_high_scores(self, good_reading):
        result = compute_scores(good_reading)
        assert isinstance(result, ScoringResult)
        assert result.overall >= 80.0
        assert result.bathroom >= 80.0
        assert result.kitchen >= 80.0
        assert result.laundry >= 80.0
        assert result.garden >= 80.0

    def test_good_reading_no_valves_closed(self, good_reading):
        result = compute_scores(good_reading)
        assert result.valves_to_close == []

    def test_bad_reading_low_scores(self, bad_reading):
        result = compute_scores(bad_reading)
        assert result.overall < 50.0

    def test_bad_reading_all_valves_closed(self, bad_reading):
        result = compute_scores(bad_reading)
        assert "bathroom" in result.valves_to_close
        assert "kitchen" in result.valves_to_close
        assert "laundry" in result.valves_to_close
        assert "garden" in result.valves_to_close

    def test_scores_are_bounded(self, good_reading, bad_reading):
        for reading in [good_reading, bad_reading]:
            result = compute_scores(reading)
            for score in [result.overall, result.bathroom, result.kitchen,
                          result.laundry, result.garden]:
                assert 0.0 <= score <= 100.0

    def test_sub_scores_exposed(self, good_reading):
        result = compute_scores(good_reading)
        assert 0.0 <= result.ph_score <= 100.0
        assert 0.0 <= result.turbidity_score <= 100.0
        assert 0.0 <= result.tds_score <= 100.0
        assert 0.0 <= result.temperature_score <= 100.0

    def test_valve_threshold_bathroom_stricter_than_garden(self):
        assert USE_POINT_THRESHOLDS.bathroom > USE_POINT_THRESHOLDS.garden

    def test_borderline_reading_selective_close(self, borderline_reading):
        """Strict valves (bathroom/kitchen) may close while garden stays open."""
        result = compute_scores(borderline_reading)
        # Garden threshold is very low (30), so it should stay open
        assert "garden" not in result.valves_to_close

    def test_overall_is_average_of_use_points(self, good_reading):
        result = compute_scores(good_reading)
        expected_avg = round(
            (result.bathroom + result.kitchen + result.laundry + result.garden) / 4, 2
        )
        assert result.overall == expected_avg

    def test_scores_are_rounded_to_2dp(self, good_reading):
        result = compute_scores(good_reading)
        for score in [result.overall, result.bathroom, result.kitchen,
                      result.laundry, result.garden]:
            assert score == round(score, 2)
