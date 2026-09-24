"""
Tests for ESP32 Hardware Simulator logic.
"""

from unittest.mock import MagicMock
from scripts.simulate_esp32 import ESP32Simulator


def test_simulator_init():
    sim = ESP32Simulator(scenario="normal", tank_id="tank-test")
    assert sim.tank_id == "tank-test"
    assert sim.scenario == "normal"
    assert sim.valves["drain"] == "closed"
    assert sim.valves["inlet"] == "open"
    assert sim.valves["outlet"] == "open"


def test_simulator_normal_physics():
    sim = ESP32Simulator(scenario="normal")
    sim.update_sensor_physics()
    assert 6.5 <= sim.ph <= 8.0
    assert 0.0 <= sim.turbidity <= 3.0
    assert 50.0 <= sim.tds <= 300.0
    assert 20.0 <= sim.temperature <= 35.0


def test_simulator_gradual_physics():
    sim = ESP32Simulator(scenario="gradual")
    for _ in range(10):
        sim.update_sensor_physics()
    assert sim.turbidity > 1.0
    assert sim.step_count == 10


def test_simulator_spike_physics():
    sim = ESP32Simulator(scenario="spike")
    for _ in range(5):
        sim.update_sensor_physics()
    # Spike kicks in after step 3
    assert sim.turbidity > 20.0
    assert sim.ph < 6.0


def test_simulator_valve_command_ack():
    sim = ESP32Simulator()
    sim.client = MagicMock()

    payload = {
        "valve_type": "drain",
        "action": "open",
        "operator": "test_operator",
        "reason": "flushing",
    }
    sim._handle_valve_command(payload)

    assert sim.valves["drain"] == "open"
    sim.client.publish.assert_called_once()
    args, kwargs = sim.client.publish.call_args
    assert args[0] == "toren/valves/status"
    assert "acknowledged" in args[1]
    assert "drain" in args[1]
