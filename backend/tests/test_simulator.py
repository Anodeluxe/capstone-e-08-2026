"""
Tests for ESP32 Hardware Simulator logic.

Beyond the physics, these tests pin the simulator's MQTT payloads to the
backend schemas (ESP32SensorPayload / ESP32ValveAck). That is the contract
the simulator must satisfy for the dev pipeline to accept its data.
"""

import json
from unittest.mock import MagicMock

from scripts.simulate_esp32 import VALVE_IDS, ESP32Simulator
from app.schemas.sensor import ESP32SensorPayload, ESP32ValveAck


def test_simulator_init():
    sim = ESP32Simulator(scenario="normal", device_id="device-test")
    assert sim.device_id == "device-test"
    assert sim.tank_id == "device-test"  # backward-compat alias
    assert sim.scenario == "normal"
    assert set(sim.valves) == set(VALVE_IDS)
    assert all(state == "open" for state in sim.valves.values())
    assert 0.0 <= sim.water_level <= 100.0


def test_simulator_normal_physics():
    sim = ESP32Simulator(scenario="normal")
    sim.update_sensor_physics()
    assert 6.5 <= sim.ph <= 8.0
    assert 0.0 <= sim.turbidity <= 3.0
    assert 50.0 <= sim.tds <= 300.0
    assert 20.0 <= sim.temperature <= 35.0
    assert 0.0 <= sim.water_level <= 100.0


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


def test_water_level_drops_when_valves_open_and_refills_when_closed():
    sim = ESP32Simulator(scenario="normal")
    start_level = sim.water_level

    sim.update_sensor_physics()  # all valves open -> consumption
    assert sim.water_level < start_level

    for valve_id in sim.valves:
        sim.valves[valve_id] = "closed"
    drained_level = sim.water_level
    sim.update_sensor_physics()  # all closed -> refill
    assert sim.water_level > drained_level


# ─── Payload contract with the backend ────────────────────────────────────────

def test_telemetry_payload_matches_backend_schema():
    """The telemetry payload must validate as ESP32SensorPayload."""
    sim = ESP32Simulator(scenario="normal")
    sim.client = MagicMock()
    sim.update_sensor_physics()
    sim.publish_telemetry()

    topic, raw_payload = sim.client.publish.call_args.args[:2]
    assert topic == "toren/sensors"

    data = json.loads(raw_payload)
    # Raises ValidationError if the simulator drifts from the backend schema.
    payload = ESP32SensorPayload(**data)
    assert payload.device_id == sim.device_id
    assert isinstance(payload.timestamp, int)
    assert payload.water_level == sim.water_level


def test_telemetry_epoch_timestamp_is_real_utc():
    sim = ESP32Simulator(scenario="normal")
    sim.client = MagicMock()
    sim.publish_telemetry()

    data = json.loads(sim.client.publish.call_args.args[1])
    assert data["timestamp"] > 1_600_000_000  # sane epoch, not 0


def test_telemetry_server_timestamp_mode_mimics_firmware():
    sim = ESP32Simulator(scenario="normal", use_server_timestamp=True)
    sim.client = MagicMock()
    sim.publish_telemetry()

    data = json.loads(sim.client.publish.call_args.args[1])
    assert data["timestamp"] == 0


def test_valve_command_ack_matches_backend_schema():
    """The valve ack must validate as ESP32ValveAck for the same valve ids."""
    sim = ESP32Simulator()
    sim.client = MagicMock()

    for valve_id in VALVE_IDS:
        sim.client.reset_mock()
        sim._handle_valve_command({"valve_id": valve_id, "action": "close"})

        assert sim.valves[valve_id] == "closed"
        topic, raw_payload = sim.client.publish.call_args.args[:2]
        assert topic == "toren/valves/status"

        ack = ESP32ValveAck(**json.loads(raw_payload))
        assert ack.valve_id == valve_id
        assert ack.is_open is False


def test_valve_command_ignores_unknown_valve_id():
    sim = ESP32Simulator()
    sim.client = MagicMock()

    sim._handle_valve_command({"valve_id": "drain", "action": "open"})

    sim.client.publish.assert_not_called()
