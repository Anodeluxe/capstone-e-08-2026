/*
 * ESP32 Firmware Reference — Toren Monitoring
 * ─────────────────────────────────────────────
 * This is a reference sketch showing the expected MQTT payload format
 * and topic structure that the FastAPI backend expects.
 *
 * Libraries needed (install via PlatformIO / Arduino Library Manager):
 *   - PubSubClient         (MQTT)
 *   - ArduinoJson          (JSON serialization)
 *   - OneWire + DallasTemperature (DS18B20 temp sensor)
 *   - WiFi (built-in ESP32)
 *
 * platformio.ini:
 *   [env:esp32dev]
 *   platform = espressif32
 *   board = esp32dev
 *   framework = arduino
 *   lib_deps =
 *     knolleary/PubSubClient@^2.8
 *     bblanchon/ArduinoJson@^7.0
 *     paulstoffregen/OneWire@^2.3.8
 *     milesburton/DallasTemperature@^3.11.0
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ── WiFi & MQTT config ────────────────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER   = "192.168.1.100";   // IP of your Mosquitto server
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT   = "esp32_toren_01";
const char* DEVICE_ID     = "toren_01";

// ── MQTT Topics (must match .env on backend) ──────────────────────────────────
const char* TOPIC_SENSORS      = "toren/sensors";
const char* TOPIC_VALVE_CMD    = "toren/valves/cmd";
const char* TOPIC_VALVE_STATUS = "toren/valves/status";

// ── Sensor & actuator pins ────────────────────────────────────────────────────
#define PIN_PH_SENSOR      34   // Analog
#define PIN_TURBIDITY      35   // Analog
#define PIN_TDS_SENSOR     32   // Analog
#define PIN_DS18B20        4    // OneWire digital
#define PIN_WATER_LEVEL    33   // Analog (ultrasonic or float)

// Solenoid valve relay pins (LOW = open for most relay modules)
#define PIN_VALVE_BATHROOM  25
#define PIN_VALVE_KITCHEN   26
#define PIN_VALVE_LAUNDRY   27
#define PIN_VALVE_GARDEN    14

#define PUBLISH_INTERVAL_MS  10000  // Send readings every 10 seconds

// ── Globals ───────────────────────────────────────────────────────────────────
WiFiClient   espClient;
PubSubClient mqtt(espClient);
OneWire      oneWire(PIN_DS18B20);
DallasTemperature tempSensor(&oneWire);

unsigned long lastPublish = 0;

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    // Valve relay pins
    pinMode(PIN_VALVE_BATHROOM, OUTPUT); digitalWrite(PIN_VALVE_BATHROOM, LOW);
    pinMode(PIN_VALVE_KITCHEN,  OUTPUT); digitalWrite(PIN_VALVE_KITCHEN,  LOW);
    pinMode(PIN_VALVE_LAUNDRY,  OUTPUT); digitalWrite(PIN_VALVE_LAUNDRY,  LOW);
    pinMode(PIN_VALVE_GARDEN,   OUTPUT); digitalWrite(PIN_VALVE_GARDEN,   LOW);

    tempSensor.begin();

    connectWiFi();
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(onMqttMessage);
    mqtt.setBufferSize(512);
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    if (!mqtt.connected()) reconnectMQTT();
    mqtt.loop();

    unsigned long now = millis();
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = now;
        publishSensorReading();
    }
}

// ── Sensor reading & publish ──────────────────────────────────────────────────
void publishSensorReading() {
    float ph          = readPH();
    float turbidity   = readTurbidity();
    float tds         = readTDS();
    float temperature = readTemperature();
    float waterLevel  = readWaterLevel();

    // Build JSON payload — matches ESP32SensorPayload schema
    JsonDocument doc;
    doc["device_id"]   = DEVICE_ID;
    doc["timestamp"]   = 0;         // Set to 0; server uses its own UTC time
    doc["ph"]          = ph;
    doc["turbidity"]   = turbidity;
    doc["tds"]         = tds;
    doc["temperature"] = temperature;
    doc["water_level"] = waterLevel;

    char payload[256];
    serializeJson(doc, payload);

    mqtt.publish(TOPIC_SENSORS, payload, false);
    Serial.printf("[ESP32] Published: %s\n", payload);
}

// ── Incoming MQTT message handler ─────────────────────────────────────────────
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

    if (String(topic) == TOPIC_VALVE_CMD) {
        handleValveCommand(msg);
    }
}

void handleValveCommand(const String& msg) {
    JsonDocument doc;
    if (deserializeJson(doc, msg)) return;

    String valveId = doc["valve_id"].as<String>();
    String action  = doc["action"].as<String>();
    bool   isOpen  = (action == "open");

    // Relay: LOW = energized (open valve), HIGH = de-energized (closed)
    int pin = -1;
    if      (valveId == "bathroom") pin = PIN_VALVE_BATHROOM;
    else if (valveId == "kitchen")  pin = PIN_VALVE_KITCHEN;
    else if (valveId == "laundry")  pin = PIN_VALVE_LAUNDRY;
    else if (valveId == "garden")   pin = PIN_VALVE_GARDEN;

    if (pin >= 0) {
        digitalWrite(pin, isOpen ? LOW : HIGH);

        // Acknowledge back to backend
        JsonDocument ack;
        ack["valve_id"] = valveId;
        ack["is_open"]  = isOpen;
        char ackBuf[128];
        serializeJson(ack, ackBuf);
        mqtt.publish(TOPIC_VALVE_STATUS, ackBuf);

        Serial.printf("[ESP32] Valve %s → %s\n", valveId.c_str(), isOpen ? "OPEN" : "CLOSED");
    }
}

// ── Sensor read functions (calibrate these for your hardware) ─────────────────
float readPH() {
    int raw = analogRead(PIN_PH_SENSOR);
    float voltage = raw * (3.3f / 4095.0f);
    return 3.5f * voltage + 0.0f;  // Calibration: y = m*x + b
}

float readTurbidity() {
    int raw = analogRead(PIN_TURBIDITY);
    float voltage = raw * (3.3f / 4095.0f);
    // Higher voltage = clearer water (inverted for most sensors)
    return max(0.0f, -1120.4f * voltage * voltage + 5742.3f * voltage - 4352.9f);
}

float readTDS() {
    int raw = analogRead(PIN_TDS_SENSOR);
    float voltage = raw * (3.3f / 4095.0f);
    float comp = 1.0f + 0.02f * (readTemperature() - 25.0f);
    float compV = voltage / comp;
    return (133.42f * compV * compV * compV
          - 255.86f * compV * compV
          + 857.39f * compV) * 0.5f;
}

float readTemperature() {
    tempSensor.requestTemperatures();
    return tempSensor.getTempCByIndex(0);
}

float readWaterLevel() {
    int raw = analogRead(PIN_WATER_LEVEL);
    return map(raw, 0, 4095, 0, 100);  // % of tank capacity
}

// ── WiFi & MQTT helpers ───────────────────────────────────────────────────────
void connectWiFi() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("[ESP32] Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.printf("\n[ESP32] WiFi connected. IP: %s\n", WiFi.localIP().toString().c_str());
}

void reconnectMQTT() {
    while (!mqtt.connected()) {
        Serial.print("[ESP32] MQTT connecting...");
        if (mqtt.connect(MQTT_CLIENT)) {
            Serial.println(" connected.");
            mqtt.subscribe(TOPIC_VALVE_CMD);
        } else {
            Serial.printf(" failed (rc=%d). Retry in 5s\n", mqtt.state());
            delay(5000);
        }
    }
}