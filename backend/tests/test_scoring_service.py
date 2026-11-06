"""
Unit tests for app/services/scoring_service.py

The formula and class thresholds below must match the ESP32 firmware
(calcWaterScore + VALVE_RULE).
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


class TestPhScore:
    def test_ideal(self):
        assert _ph_score(7.0) == 100.0

    def test_first_band(self):
        assert _ph_score(6.5) == pytest.approx(93.33, abs=0.01)
        assert _ph_score(8.0) == pytest.approx(86.67, abs=0.01)
        assert _ph_score(5.5) == pytest.approx(80.0)

    def test_second_band(self):
        assert _ph_score(6.0) == pytest.approx(86.67, abs=0.01)
        assert _ph_score(9.0) == pytest.approx(53.33, abs=0.01)
        assert _ph_score(5.0) == pytest.approx(53.33, abs=0.01)

    def test_out_of_range(self):
        assert _ph_score(4.0) == 0.0
        assert _ph_score(10.0) == 0.0
        assert _ph_score(0.0) == 0.0
        assert _ph_score(14.0) == 0.0


class TestTurbidityScore:
    def test_anchors(self):
        assert _turbidity_score(0.0) == 100.0
        assert _turbidity_score(5.0) == pytest.approx(94.0)
        assert _turbidity_score(25.0) == pytest.approx(70.0)
        assert _turbidity_score(50.0) == pytest.approx(46.67, abs=0.01)
        assert _turbidity_score(100.0) == 0.0

    def test_clamped(self):
        assert _turbidity_score(150.0) == 0.0
        assert _turbidity_score(-1.0) == 100.0


class TestTdsScore:
    def test_anchors(self):
        assert _tds_score(0.0) == 100.0
        assert _tds_score(180.0) == pytest.approx(82.0)
        assert _tds_score(300.0) == pytest.approx(70.0)
        assert _tds_score(500.0) == pytest.approx(50.0)
        assert _tds_score(1000.0) == 0.0

    def test_clamped(self):
        assert _tds_score(1500.0) == 0.0
        assert _tds_score(-1.0) == 100.0


class TestTemperatureScore:
    def test_anchors(self):
        assert _temperature_score(26.5) == 100.0
        assert _temperature_score(25.0) == pytest.approx(88.89, abs=0.01)
        assert _temperature_score(20.0) == pytest.approx(51.85, abs=0.01)
        assert _temperature_score(40.0) == 0.0
        assert _temperature_score(13.0) == 0.0


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
        assert compute_scores(good_reading).valves_to_close == []

    def test_bad_reading_low_scores(self, bad_reading):
        assert compute_scores(bad_reading).overall < 50.0

    def test_bad_reading_all_valves_closed(self, bad_reading):
        assert compute_scores(bad_reading).valves_to_close == [
            "bathroom", "kitchen", "laundry", "garden",
        ]

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

    def test_thresholds_match_firmware(self):
        assert USE_POINT_THRESHOLDS == {
            "bathroom": 80.0,
            "kitchen": 65.0,
            "laundry": 45.0,
            "garden": 25.0,
        }

    def test_borderline_reading_stays_open(self, borderline_reading):
        """Firmware WQI ~83 → class A, so no valve is closed."""
        assert compute_scores(borderline_reading).valves_to_close == []

    @pytest.mark.parametrize("ph,turbidity,tds,temperature,expected", [
        (7.2, 0.5, 180.0, 26.0, []),
        (9.5, 0.0, 180.0, 26.5, ["bathroom"]),
        (10.0, 10.0, 180.0, 26.5, ["bathroom", "kitchen"]),
        (10.0, 30.0, 180.0, 40.0, ["bathroom", "kitchen", "laundry"]),
        (4.0, 30.0, 1000.0, 45.0,
         ["bathroom", "kitchen", "laundry", "garden"]),
    ])
    def test_valves_follow_firmware_classes(
        self, ph, turbidity, tds, temperature, expected
    ):
        reading = ESP32SensorPayload(
            ph=ph, turbidity=turbidity, tds=tds,
            temperature=temperature, water_level=50.0,
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
