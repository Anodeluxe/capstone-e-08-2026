"""
Shared test fixtures for the Toren Monitoring backend test suite.
"""

import pytest

from app.schemas.sensor import ESP32SensorPayload


@pytest.fixture
def good_reading() -> ESP32SensorPayload:
    """A reading with ideal water quality across all parameters."""
    return ESP32SensorPayload(
        device_id="toren_01",
        ph=7.2,
        turbidity=0.5,
        tds=180.0,
        temperature=26.0,
        water_level=85.0,
    )


@pytest.fixture
def bad_reading() -> ESP32SensorPayload:
    """A reading with poor water quality — should close all valves."""
    return ESP32SensorPayload(
        device_id="toren_01",
        ph=4.0,
        turbidity=30.0,
        tds=1000.0,
        temperature=28.0,
        water_level=50.0,
    )


@pytest.fixture
def borderline_reading() -> ESP32SensorPayload:
    """A reading that sits near the scoring thresholds."""
    return ESP32SensorPayload(
        device_id="toren_01",
        ph=6.3,        # border: score 40
        turbidity=8.0,  # border: score 55
        tds=450.0,     # border: score 80
        temperature=28.0,
        water_level=60.0,
    )
