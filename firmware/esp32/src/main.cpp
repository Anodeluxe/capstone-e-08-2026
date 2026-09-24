/*
 * Firmware Utama ESP32 — Toren Monitoring & Kontrol Distribusi
 * ─────────────────────────────────────────────────────────────
 * Capstone DTETI FT UGM 2026 — Kelompok E-08
 *
 * Fitur:
 *   1. Akuisisi 5 Sensor: pH, TDS, Turbiditas, Suhu (DS18B20), Level Air (HC-SR04)
 *   2. Filter Digital EWMA (Exponential Moving Average) untuk mereduksi derau ADC
 *   3. Kompensasi Suhu Dinamis pada Pengukuran Ultrasonik
 *   4. Deteksi Lonjakan Anomali Lokal (Edge Failsafe Shutoff)
 *   5. Komunikasi Data Dua Arah via Protokol MQTT
 *   6. Kontrol Selektif 4 Solenoid Valve Relai
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <FS.h>
#include <SD.h>
#include <SPI.h>

#include "config.h"

// ── Kredensial Jaringan & Broker MQTT ─────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER   = "192.168.1.100";   // Alamat IP server Mosquitto backend
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT   = "esp32_toren_01";
const char* DEVICE_ID     = "toren_01";

// ── Topik MQTT (Harus selaras dengan konfigurasi backend) ─────────────────────
const char* TOPIC_SENSORS      = "toren/sensors";
const char* TOPIC_VALVE_CMD    = "toren/valves/cmd";
const char* TOPIC_VALVE_STATUS = "toren/valves/status";

// ── Instansiasi Objek Global ──────────────────────────────────────────────────
WiFiClient        espClient;
PubSubClient      mqtt(espClient);
OneWire           oneWire(PIN_DS18B20);
DallasTemperature tempSensor(&oneWire);

unsigned long lastPublish = 0;
bool sdCardAvailable = false;

// ── Variabel State Filter Digital EWMA ────────────────────────────────────────
float filteredPH          = 7.0f;
float filteredTurbidity   = 1.0f;
float filteredTDS         = 150.0f;
float filteredTemp        = 27.0f;
float filteredWaterLevel  = 80.0f;

// ── Deklarasi Prototipe Fungsi ────────────────────────────────────────────────
void connectWiFi();
void reconnectMQTT();
void onMqttMessage(char* topic, byte* payload, unsigned int length);
void handleValveCommand(const String& msg);
void publishSensorReading();
void checkLocalAnomalySpike(float ph, float turb, float tds);
void closeAllValvesEmergency();
void logToSD(const char* payload);

float readRawPH();
float readRawTurbidity();
float readRawTDS(float currentTemp);
float readRawTemperature();
float readRawWaterLevel(float currentTemp);
float applyEWMA(float rawVal, float prevFiltered, float alpha);

// ── SETUP ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== Inisialisasi Firmware ESP32 Toren Monitoring (E-08) ===");

    // Inisialisasi Pin Relai Solenoid Valve (Aktif LOW: HIGH = Tertutup, LOW = Terbuka)
    pinMode(PIN_VALVE_BATHROOM, OUTPUT); digitalWrite(PIN_VALVE_BATHROOM, HIGH);
    pinMode(PIN_VALVE_KITCHEN,  OUTPUT); digitalWrite(PIN_VALVE_KITCHEN,  HIGH);
    pinMode(PIN_VALVE_LAUNDRY,  OUTPUT); digitalWrite(PIN_VALVE_LAUNDRY,  HIGH);
    pinMode(PIN_VALVE_GARDEN,   OUTPUT); digitalWrite(PIN_VALVE_GARDEN,   HIGH);

    // Inisialisasi Pin Ultrasonik
    pinMode(PIN_TRIG_US, OUTPUT);
    pinMode(PIN_ECHO_US, INPUT);
    digitalWrite(PIN_TRIG_US, LOW);

    // Inisialisasi Resolusi ADC 12-bit (0 - 4095)
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db); // Rentang tegangan masukan ~0 s.d. 3.3V

    // Inisialisasi Sensor Suhu 1-Wire DS18B20
    tempSensor.begin();

    // Inisialisasi MicroSD Card (SPI)
    if (SD.begin(PIN_SD_CS)) {
        sdCardAvailable = true;
        Serial.println("[SD] Kartu MicroSD berhasil diinisialisasi.");
    } else {
        Serial.println("[SD] Modul MicroSD tidak terdeteksi (opsional).");
    }

    // Sambungan Nirkabel & MQTT Broker
    connectWiFi();
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(onMqttMessage);
    mqtt.setBufferSize(512);

    Serial.println("=== Inisialisasi Selesai, Memulai Siklus Pengukuran ===");
}

// ── LOOP ──────────────────────────────────────────────────────────────────────
void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!mqtt.connected()) reconnectMQTT();
        mqtt.loop();
    }

    unsigned long now = millis();
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = now;
        publishSensorReading();
    }
}

// ── FUNGSI AKUISISI & FILTERING DATA ──────────────────────────────────────────
void publishSensorReading() {
    // 1. Baca nilai mentah dari sensor
    float rawTemp = readRawTemperature();
    float rawPH   = readRawPH();
    float rawTurb = readRawTurbidity();
    float rawTDS  = readRawTDS(rawTemp);
    float rawLvl  = readRawWaterLevel(rawTemp);

    // 2. Terapkan Digital Low-Pass Filter (EWMA)
    filteredTemp       = applyEWMA(rawTemp, filteredTemp, FILTER_ALPHA);
    filteredPH         = applyEWMA(rawPH, filteredPH, FILTER_ALPHA);
    filteredTurbidity  = applyEWMA(rawTurb, filteredTurbidity, FILTER_ALPHA);
    filteredTDS        = applyEWMA(rawTDS, filteredTDS, FILTER_ALPHA);
    filteredWaterLevel = applyEWMA(rawLvl, filteredWaterLevel, FILTER_ALPHA);

    // 3. Periksa lonjakan anomali seketika lokal (Edge Failsafe)
    checkLocalAnomalySpike(filteredPH, filteredTurbidity, filteredTDS);

    // 4. Susun payload JSON sesuai skema backend ESP32SensorPayload
    JsonDocument doc;
    doc["device_id"]   = DEVICE_ID;
    doc["timestamp"]   = 0; // Waktu diselaraskan oleh backend server UTC
    doc["ph"]          = round(filteredPH * 100.0f) / 100.0f;
    doc["turbidity"]   = round(filteredTurbidity * 10.0f) / 10.0f;
    doc["tds"]         = round(filteredTDS * 10.0f) / 10.0f;
    doc["temperature"] = round(filteredTemp * 10.0f) / 10.0f;
    doc["water_level"] = round(filteredWaterLevel * 10.0f) / 10.0f;

    char payload[256];
    serializeJson(doc, payload);

    // 5. Publikasikan ke broker jika terhubung; cadangkan ke SD jika offline
    if (mqtt.connected()) {
        mqtt.publish(TOPIC_SENSORS, payload, false);
        Serial.printf("[ESP32] Publish MQTT: %s\n", payload);
    } else {
        Serial.printf("[ESP32] Offline, menyimpan lokal: %s\n", payload);
        logToSD(payload);
    }
}

float applyEWMA(float rawVal, float prevFiltered, float alpha) {
    if (isnan(rawVal)) return prevFiltered;
    return (alpha * rawVal) + ((1.0f - alpha) * prevFiltered);
}

// ── DETEKSI ANOMALI LOKAL (EDGE FAILSAFE) ─────────────────────────────────────
void checkLocalAnomalySpike(float ph, float turb, float tds) {
    static float lastPH = 7.0f;
    static float lastTurb = 1.0f;
    static float lastTDS = 150.0f;

    float deltaPH   = abs(ph - lastPH);
    float deltaTurb = turb - lastTurb;
    float deltaTDS  = tds - lastTDS;

    // Jika terjadi lonjakan polutan ekstrem mendadak dari inlet toren
    if (deltaTurb > THRESHOLD_SPIKE_TURB || deltaPH > THRESHOLD_SPIKE_PH || deltaTDS > THRESHOLD_SPIKE_TDS) {
        Serial.printf("[EDGE FAILSAFE] Terdeteksi anomali mendadak (Turb Delta: %.1f, pH Delta: %.2f)! Menutup seluruh katup.\n", 
                      deltaTurb, deltaPH);
        closeAllValvesEmergency();
    }

    lastPH   = ph;
    lastTurb = turb;
    lastTDS  = tds;
}

void closeAllValvesEmergency() {
    digitalWrite(PIN_VALVE_BATHROOM, HIGH);
    digitalWrite(PIN_VALVE_KITCHEN,  HIGH);
    digitalWrite(PIN_VALVE_LAUNDRY,  HIGH);
    digitalWrite(PIN_VALVE_GARDEN,   HIGH);
}

// ── PENGKONDISIAN & KALIBRASI SENSOR ─────────────────────────────────────────
float readRawPH() {
    int raw = analogRead(PIN_PH_SENSOR);
    float voltage = raw * (3.3f / 4095.0f);
    // Kalibrasi kurva Nernst linear: pH = m * V + c (disesuaikan larutan buffer)
    float ph = 3.5f * voltage;
    return constrain(ph, 0.0f, 14.0f);
}

float readRawTurbidity() {
    int raw = analogRead(PIN_TURBIDITY);
    float voltage = raw * (3.3f / 4095.0f);
    // Sensor fototransistor nephelometrik: tegangan tinggi = air jernih
    // Regresi polinomial orde dua (Dokumen C-251 Persamaan 4.3):
    float ntu = -1120.4f * voltage * voltage + 5742.3f * voltage - 4352.9f;
    return max(0.0f, ntu);
}

float readRawTDS(float currentTemp) {
    int raw = analogRead(PIN_TDS_SENSOR);
    float voltage = raw * (3.3f / 4095.0f);
    // Kompensasi termal 2% per °C mengacu pada suhu standar 25 °C
    float compCoeff = 1.0f + 0.02f * (currentTemp - 25.0f);
    float compVoltage = voltage / compCoeff;
    // Formula konversi konduktivitas ke ppm (Dokumen C-251 Persamaan 4.6)
    float tds = (133.42f * compVoltage * compVoltage * compVoltage
               - 255.86f * compVoltage * compVoltage
               + 857.39f * compVoltage) * 0.5f;
    return max(0.0f, tds);
}

float readRawTemperature() {
    tempSensor.requestTemperatures();
    float tempC = tempSensor.getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C || tempC < -10.0f || tempC > 85.0f) {
        return 27.0f; // Nilai default bila sensor terputus
    }
    return tempC;
}

float readRawWaterLevel(float currentTemp) {
    digitalWrite(PIN_TRIG_US, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_TRIG_US, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG_US, LOW);

    long durationUs = pulseIn(PIN_ECHO_US, HIGH, 30000); // Timeout 30ms (~5 meter)
    if (durationUs == 0) return filteredWaterLevel; // Pertahankan nilai sebelumnya bila pantulan gagal

    // Kompensasi suhu kecepatan suara: v = 331.3 + 0.606 * T (m/s)
    float speedOfSound = (SOUND_BASE_SPEED_M_S + TEMP_COEFF_SOUND * currentTemp) * 100.0f / 1000000.0f; // cm/us
    float distanceCm = (durationUs * speedOfSound) / 2.0f;

    // Hitung ketinggian air (persentase kapasitas tangki)
    float waterDepthCm = max(0.0f, TANK_HEIGHT_CM - distanceCm);
    float percentage = (waterDepthCm / TANK_HEIGHT_CM) * 100.0f;
    return constrain(percentage, 0.0f, 100.0f);
}

// ── PENANGANAN PERINTAH KATUP SOLENOID (MQTT CMD) ─────────────────────────────
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

    // Relai aktif LOW: LOW = koil teraliri arus (katup N/C terbuka), HIGH = tertutup
    int pin = -1;
    if      (valveId == "bathroom") pin = PIN_VALVE_BATHROOM;
    else if (valveId == "kitchen")  pin = PIN_VALVE_KITCHEN;
    else if (valveId == "laundry")  pin = PIN_VALVE_LAUNDRY;
    else if (valveId == "garden")   pin = PIN_VALVE_GARDEN;

    if (pin >= 0) {
        digitalWrite(pin, isOpen ? LOW : HIGH);

        // Kirim acknowledgment status katup kembali ke backend
        JsonDocument ack;
        ack["valve_id"] = valveId;
        ack["is_open"]  = isOpen;
        char ackBuf[128];
        serializeJson(ack, ackBuf);
        mqtt.publish(TOPIC_VALVE_STATUS, ackBuf);

        Serial.printf("[ESP32] Katup %s diubah menjadi: %s\n", valveId.c_str(), isOpen ? "BUKA" : "TUTUP");
    }
}

// ── PENCADANGAN OFFLINE KE MICROSD ────────────────────────────────────────────
void logToSD(const char* payload) {
    if (!sdCardAvailable) return;
    File logFile = SD.open("/offline_readings.csv", FILE_APPEND);
    if (logFile) {
        logFile.println(payload);
        logFile.close();
    }
}

// ── HELPER KONEKSI WI-FI & MQTT ───────────────────────────────────────────────
void connectWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("[ESP32] Menghubungkan ke Wi-Fi");
    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) {
        delay(500);
        Serial.print(".");
        retry++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[ESP32] Wi-Fi terhubung. Alamat IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[ESP32] Gagal tersambung Wi-Fi. Beralih ke mode offline.");
    }
}

void reconnectMQTT() {
    if (WiFi.status() != WL_CONNECTED) return;
    while (!mqtt.connected()) {
        Serial.print("[ESP32] Menghubungkan ke MQTT Broker...");
        if (mqtt.connect(MQTT_CLIENT)) {
            Serial.println(" Sukses.");
            mqtt.subscribe(TOPIC_VALVE_CMD);
        } else {
            Serial.printf(" Gagal (kode error=%d). Coba kembali dalam 5 detik.\n", mqtt.state());
            delay(5000);
            break;
        }
    }
}
