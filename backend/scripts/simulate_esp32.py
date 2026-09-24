"""
ESP32 Hardware & Telemetry Simulator for DTETI UGM Capstone 2026 (E-08)

This script simulates the physical ESP32 microcontroller, sensors, and solenoid valves:
1. Publishes periodic water quality telemetry to MQTT topic: toren/sensors
2. Subscribes to valve command topic: toren/valves/cmd
3. Simulates physical valve state transitions and publishes acknowledgment to: toren/valves/status
4. Supports scenarios: 'normal', 'gradual' (degradation), 'spike' (contamination), and 'interactive'

Usage:
    python simulate_esp32.py --scenario normal
    python simulate_esp32.py --scenario gradual --interval 3
    python simulate_esp32.py --scenario spike
    python simulate_esp32.py --scenario interactive
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[ERROR] paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ESP32-SIM] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ESP32Simulator")

# Default topics matching backend configuration and firmware
DEFAULT_TOPIC_SENSORS = "toren/sensors"
DEFAULT_TOPIC_VALVES_CMD = "toren/valves/cmd"
DEFAULT_TOPIC_VALVES_STATUS = "toren/valves/status"


class ESP32Simulator:
    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        tank_id: str = "tank-1",
        interval: float = 5.0,
        scenario: str = "normal",
        username: str | None = None,
        password: str | None = None,
    ):
        self.broker = broker
        self.port = port
        self.tank_id = tank_id
        self.interval = interval
        self.scenario = scenario
        self.username = username
        self.password = password

        self.running = False
        self.step_count = 0

        # Physical state of valves
        self.valves = {
            "inlet": "open",
            "outlet": "open",
            "drain": "closed",
        }

        # Current sensor readings baseline
        self.ph = 7.30
        self.turbidity = 1.00
        self.tds = 150.0
        self.temperature = 26.5

        # MQTT client setup
        self.client = mqtt.Client(
            client_id=f"esp32_sim_{random.randint(1000, 9999)}",
            clean_session=True,
        )
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {self.broker}:{self.port} (rc=0)")
            # Subscribe to valve commands
            client.subscribe(DEFAULT_TOPIC_VALVES_CMD, qos=1)
            logger.info(f"Subscribed to valve command topic: '{DEFAULT_TOPIC_VALVES_CMD}'")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}). Will attempt reconnect.")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"<< Received MQTT message on {msg.topic}: {payload}")

            if msg.topic == DEFAULT_TOPIC_VALVES_CMD:
                self._handle_valve_command(payload)
        except Exception as e:
            logger.error(f"Error processing received message: {e}")

    def _handle_valve_command(self, payload: dict):
        valve_type = payload.get("valve_type", "").lower()
        action = payload.get("action", "").lower()
        operator = payload.get("operator", "unknown")
        reason = payload.get("reason", "none")

        if valve_type not in self.valves:
            logger.warning(f"Ignored command for unknown valve type: '{valve_type}'")
            return

        new_state = "open" if action in ("open", "on", "1") else "closed"
        old_state = self.valves[valve_type]
        self.valves[valve_type] = new_state

        logger.info(
            f"[ACTUATOR] Valve '{valve_type}' state changed: {old_state.upper()} -> {new_state.upper()} "
            f"(Operator: {operator}, Reason: {reason})"
        )

        # Simulate physical effect: if drain valve opens during contamination, clean water flushes
        if valve_type == "drain" and new_state == "open":
            logger.info("[SIMULATION] Drain valve OPENED! Flushing contaminated water, recovery accelerated.")
            if self.turbidity > 2.0:
                self.turbidity = max(1.2, self.turbidity - 5.0)
            if self.tds > 200:
                self.tds = max(160.0, self.tds - 100.0)

        # Publish acknowledgment back to broker
        ack_payload = {
            "tank_id": self.tank_id,
            "valve_type": valve_type,
            "state": new_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "acknowledged",
            "valves_state": self.valves,
        }
        self.client.publish(DEFAULT_TOPIC_VALVES_STATUS, json.dumps(ack_payload), qos=1)
        logger.info(f">> Published valve status ACK to {DEFAULT_TOPIC_VALVES_STATUS}: {ack_payload}")

    def update_sensor_physics(self):
        """Update simulated water physics based on active scenario and valve positions."""
        self.step_count += 1
        noise = lambda scale: random.gauss(0, scale)

        if self.scenario == "normal":
            # Stable drinking/clean water
            self.ph = round(max(6.8, min(7.6, 7.35 + noise(0.04))), 2)
            self.turbidity = round(max(0.3, min(2.0, 0.85 + noise(0.08))), 2)
            self.tds = round(max(100.0, min(220.0, 150.0 + noise(3.0))), 1)
            self.temperature = round(max(24.0, min(29.0, 26.5 + noise(0.2))), 1)

        elif self.scenario == "gradual":
            # Gradual degradation over time (simulates sediment accumulation or bio-growth)
            drift = self.step_count * 0.15
            self.turbidity = round(min(25.0, 0.9 + drift + noise(0.1)), 2)
            self.ph = round(max(5.8, 7.3 - (self.step_count * 0.03) + noise(0.05)), 2)
            self.tds = round(min(650.0, 150.0 + (self.step_count * 4.5) + noise(4.0)), 1)
            self.temperature = round(26.0 + noise(0.2), 1)

        elif self.scenario == "spike":
            # Sudden heavy contamination event (e.g. pipe rupture, sewage backflow)
            if self.step_count < 3:
                # Normal initially
                self.ph = 7.3
                self.turbidity = 1.0
                self.tds = 150.0
            else:
                # Severe spike
                self.turbidity = round(min(45.0, 32.0 + noise(1.5)), 2)
                self.ph = round(max(4.5, 5.1 + noise(0.1)), 2)
                self.tds = round(min(950.0, 780.0 + noise(15.0)), 1)
            self.temperature = round(27.2 + noise(0.3), 1)

        # If drain valve is open and fresh inlet is open, water cleans up over time
        if self.valves["drain"] == "open":
            self.turbidity = round(max(0.8, self.turbidity * 0.85), 2)
            self.tds = round(max(140.0, self.tds * 0.90), 1)
            self.ph = round(self.ph + (7.2 - self.ph) * 0.2, 2)

    def publish_telemetry(self):
        """Construct sensor telemetry payload and publish to MQTT."""
        payload = {
            "tank_id": self.tank_id,
            "ph": self.ph,
            "turbidity": self.turbidity,
            "tds": self.tds,
            "temperature": self.temperature,
            "valves": self.valves,
            "scenario": self.scenario,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        json_data = json.dumps(payload)
        self.client.publish(DEFAULT_TOPIC_SENSORS, json_data, qos=0)
        logger.info(
            f">> Telemetry [{self.scenario}] -> pH={self.ph:.2f}, "
            f"Turbidity={self.turbidity:.2f} NTU, TDS={self.tds:.1f} ppm, "
            f"Temp={self.temperature:.1f}°C | Valves: {self.valves}"
        )

    def start(self):
        logger.info(f"Starting ESP32 Simulator (Scenario: {self.scenario}, Tank: {self.tank_id})")
        logger.info(f"Connecting to broker {self.broker}:{self.port}...")

        try:
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as e:
            logger.error(f"Could not connect to MQTT broker: {e}")
            logger.info("Ensure Mosquitto / MQTT broker is running on localhost:1883 or pass --broker.")
            return

        self.client.loop_start()
        self.running = True

        try:
            while self.running:
                self.update_sensor_physics()
                self.publish_telemetry()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Stopping ESP32 Simulator on user interrupt...")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("ESP32 Simulator stopped successfully.")


def interactive_prompt(sim: ESP32Simulator):
    """Auxiliary console thread for interactive scenario switching."""
    time.sleep(1.0)
    print("\n" + "=" * 55)
    print(" INTERACTIVE SIMULATOR COMMANDS:")
    print("   normal   - Set scenario to normal/clean water")
    print("   gradual  - Trigger gradual degradation")
    print("   spike    - Trigger sudden contamination spike")
    print("   flush    - Clean water immediately (simulate manual flush)")
    print("   quit     - Exit simulator")
    print("=" * 55 + "\n")

    while sim.running:
        try:
            cmd = input().strip().lower()
            if cmd == "normal":
                sim.scenario = "normal"
                sim.step_count = 0
                logger.info("[COMMAND] Switched scenario to 'normal'")
            elif cmd == "gradual":
                sim.scenario = "gradual"
                sim.step_count = 0
                logger.info("[COMMAND] Switched scenario to 'gradual'")
            elif cmd == "spike":
                sim.scenario = "spike"
                sim.step_count = 0
                logger.info("[COMMAND] Switched scenario to 'spike'")
            elif cmd == "flush":
                sim.ph = 7.3
                sim.turbidity = 0.8
                sim.tds = 145.0
                logger.info("[COMMAND] Water parameters flushed back to normal baseline!")
            elif cmd in ("quit", "exit"):
                sim.stop()
                break
        except (EOFError, KeyboardInterrupt):
            break


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 MQTT Hardware and Sensor Simulator for Capstone E-08"
    )
    parser.add_argument(
        "--scenario",
        choices=["normal", "gradual", "spike", "interactive"],
        default="normal",
        help="Simulation scenario (default: normal)",
    )
    parser.add_argument(
        "--broker",
        default=os.getenv("MQTT_BROKER_HOST", "localhost"),
        help="MQTT broker host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Telemetry publication interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--tank-id",
        default="tank-1",
        help="Tank ID for sensor readings (default: tank-1)",
    )

    args = parser.parse_args()

    actual_scenario = "normal" if args.scenario == "interactive" else args.scenario

    sim = ESP32Simulator(
        broker=args.broker,
        port=args.port,
        tank_id=args.tank_id,
        interval=args.interval,
        scenario=actual_scenario,
    )

    if args.scenario == "interactive":
        t = threading.Thread(target=interactive_prompt, args=(sim,), daemon=True)
        t.start()

    sim.start()


if __name__ == "__main__":
    main()
