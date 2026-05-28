"""
MQTT Client
────────────
Wraps paho-mqtt with:
  - Auto-reconnect on disconnect
  - Thread-safe publish
  - Typed topic subscriptions

This client runs in a background thread (paho's loop_start()).
Incoming messages are dispatched to handlers.py via a callback.
"""

import threading
import time
from typing import Callable

import paho.mqtt.client as mqtt

from app.core.config import get_settings

settings = get_settings()


class MQTTClient:
    def __init__(self):
        self._client = mqtt.Client(
            client_id=settings.mqtt_client_id,
            protocol=mqtt.MQTTv5,
        )
        self._message_callbacks: dict[str, list[Callable]] = {}
        self._connected = False
        self._lock = threading.Lock()

        # Attach paho callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Start the background network loop.
        Uses connect_async() so a missing broker does not crash startup —
        paho will keep retrying in the background thread.
        """
        print(f"[MQTT] Connecting to {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
        try:
            self._client.connect_async(
                host=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
                keepalive=60,
            )
            self._client.loop_start()
        except Exception as e:
            print(f"[MQTT] Could not reach broker: {e}. Sensor data will not be received until the broker is available.")

    def stop(self) -> None:
        """Gracefully disconnect."""
        self._client.loop_stop()
        self._client.disconnect()
        print("[MQTT] Disconnected.")

    # ── Subscriptions ──────────────────────────────────────────────────────────

    def subscribe(self, topic: str, callback: Callable, qos: int = 1) -> None:
        """
        Register a handler for a topic. Supports wildcards (+, #).
        Multiple callbacks per topic are allowed.
        """
        with self._lock:
            if topic not in self._message_callbacks:
                self._message_callbacks[topic] = []
                self._client.subscribe(topic, qos=qos)
                print(f"[MQTT] Subscribed to: {topic}")
            self._message_callbacks[topic].append(callback)

    # ── Publishing ─────────────────────────────────────────────────────────────

    def publish_valve_command(self, payload: str) -> None:
        """Publish a valve command to the ESP32."""
        self._publish(settings.mqtt_topic_valve_cmd, payload, qos=1, retain=False)

    def _publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> None:
        with self._lock:
            if self._connected:
                result = self._client.publish(topic, payload, qos=qos, retain=retain)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT] Publish failed on {topic}: rc={result.rc}")
            else:
                print(f"[MQTT] Not connected, dropping publish on {topic}")

    # ── Paho callbacks ─────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == 0:
            self._connected = True
            print("[MQTT] Connected successfully.")
            # Re-subscribe after reconnect
            for topic in self._message_callbacks:
                client.subscribe(topic, qos=1)
        else:
            print(f"[MQTT] Connection failed, rc={rc}. Retrying...")

    def _on_disconnect(self, client, userdata, rc, properties=None) -> None:
        self._connected = False
        if rc != 0:
            print(f"[MQTT] Unexpected disconnect (rc={rc}). Will auto-reconnect.")

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8", errors="replace")

        # Match exact topic and wildcard subscribers
        for subscribed_topic, callbacks in self._message_callbacks.items():
            if _topic_matches(subscribed_topic, topic):
                for cb in callbacks:
                    try:
                        cb(topic, payload)
                    except Exception as e:
                        print(f"[MQTT] Handler error on {topic}: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected


def _topic_matches(subscription: str, topic: str) -> bool:
    """Check if a topic matches a subscription pattern (supports + and #)."""
    sub_parts = subscription.split("/")
    top_parts = topic.split("/")

    for i, sub_part in enumerate(sub_parts):
        if sub_part == "#":
            return True
        if i >= len(top_parts):
            return False
        if sub_part != "+" and sub_part != top_parts[i]:
            return False

    return len(sub_parts) == len(top_parts)


# Singleton — imported by main.py and handlers.py
mqtt_client = MQTTClient()