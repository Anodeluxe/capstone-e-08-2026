"""
Unit tests for app/services/scoring_service.py

Tests each sub-scorer in isolation, then the full compute_scores() pipeline
including valve auto-close logic.
"""

import pytest

from app.schemas.sensor import ESP32SensorPayload
from app.services.scoring_service import (
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

    def test_anchors(self):
        assert _ph_score(6.0) == pytest.approx(70.0)
        assert _ph_score(9.0) == pytest.approx(70.0)
        assert _ph_score(5.5) == pytest.approx(40.0)
        assert _ph_score(9.5) == pytest.approx(40.0)

    def test_linear_between_anchors(self):
        assert _ph_score(6.25) == pytest.approx(85.0)
        assert _ph_score(8.75) == pytest.approx(85.0)
        assert _ph_score(5.75) == pytest.approx(55.0)
        assert _ph_score(9.25) == pytest.approx(55.0)

    def test_unacceptable(self):
        assert _ph_score(5.0) == 0.0
        assert _ph_score(10.0) == 0.0
        assert _ph_score(0.0) == 0.0
        assert _ph_score(14.0) == 0.0


# ─── Turbidity sub-scorer ──────────────────────────────────────────────────────

class TestTurbidityScore:
    def test_excellent(self):
        assert _turbidity_score(0.5) == 100.0
        assert _turbidity_score(1.0) == 100.0

    def test_anchors(self):
        assert _turbidity_score(5.0) == pytest.approx(80.0)
        assert _turbidity_score(10.0) == pytest.approx(55.0)
        assert _turbidity_score(25.0) == pytest.approx(25.0)
        assert _turbidity_score(50.0) == 0.0

    def test_linear_between_anchors(self):
        assert _turbidity_score(3.0) == pytest.approx(90.0)
        assert _turbidity_score(7.5) == pytest.approx(67.5)
        assert _turbidity_score(17.5) == pytest.approx(40.0)
        assert _turbidity_score(37.5) == pytest.approx(12.5)

    def test_unacceptable(self):
        assert _turbidity_score(60.0) == 0.0
        assert _turbidity_score(100.0) == 0.0


# ─── TDS sub-scorer ────────────────────────────────────────────────────────────

class TestTdsScore:
    def test_excellent(self):
        assert _tds_score(100.0) == 100.0
        assert _tds_score(300.0) == 100.0

    def test_anchors(self):
        assert _tds_score(500.0) == pytest.approx(80.0)
        assert _tds_score(900.0) == pytest.approx(50.0)
        assert _tds_score(1200.0) == pytest.approx(20.0)
        assert _tds_score(1500.0) == 0.0

    def test_linear_between_anchors(self):
        assert _tds_score(400.0) == pytest.approx(90.0)
        assert _tds_score(700.0) == pytest.approx(65.0)
        assert _tds_score(1050.0) == pytest.approx(35.0)
        assert _tds_score(1350.0) == pytest.approx(10.0)

    def test_unacceptable(self):
        assert _tds_score(1800.0) == 0.0


# ─── Temperature sub-scorer ────────────────────────────────────────────────────

class TestTemperatureScore:
    def test_comfortable(self):
        assert _temperature_score(25.0) == 100.0
        assert _temperature_score(20.0) == 100.0
        assert _temperature_score(30.0) == 100.0

    def test_anchors(self):
        assert _temperature_score(15.0) == pytest.approx(75.0)
        assert _temperature_score(35.0) == pytest.approx(75.0)
        assert _temperature_score(10.0) == pytest.approx(50.0)
        assert _temperature_score(40.0) == pytest.approx(50.0)
        assert _temperature_score(5.0) == pytest.approx(25.0)
        assert _temperature_score(45.0) == pytest.approx(25.0)

    def test_linear_between_anchors(self):
        assert _temperature_score(17.5) == pytest.approx(87.5)
        assert _temperature_score(32.5) == pytest.approx(87.5)
        assert _temperature_score(12.5) == pytest.approx(62.5)
        assert _temperature_score(37.5) == pytest.approx(62.5)
        assert _temperature_score(7.5) == pytest.approx(37.5)
        assert _temperature_score(42.5) == pytest.approx(37.5)

    def test_extreme_clamped(self):
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

    def test_class_b_closes_kitchen_only(self, borderline_reading):
        """Firmware class B: bathroom/laundry/garden open, kitchen closed."""
        result = compute_scores(borderline_reading)
        assert result.valves_to_close == ["kitchen"]

    @pytest.mark.parametrize("ph,turbidity,tds,expected", [
        (7.2, 0.5, 180.0, []),
        (6.2, 2.0, 350.0, ["kitchen"]),
        (9.2, 12.0, 750.0, ["bathroom", "kitchen", "laundry"]),
        (4.0, 30.0, 1200.0, ["bathroom", "kitchen", "laundry", "garden"]),
    ])
    def test_valves_follow_firmware_class(self, ph, turbidity, tds, expected):
        reading = ESP32SensorPayload(
            ph=ph, turbidity=turbidity, tds=tds,
            temperature=28.0, water_level=50.0,
        )
        assert compute_scores(reading).valves_to_close == expected

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
