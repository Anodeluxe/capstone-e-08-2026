# Firmware ESP32 — Toren Water Quality Monitoring & Control System

**Capstone DTETI FT UGM 2026 — Kelompok E-08**  
**Penanggung Jawab**: Shofiy Alia Rimala (Teknik Elektro) & Azfanova Sammy Rafif Saputra (Teknologi Informasi)

---

## 1. Struktur Folder

```
firmware/esp32/
├── platformio.ini       # Konfigurasi build PlatformIO
├── include/
│   └── config.h         # Definisi pinout GPIO, filter EWMA, dan parameter sistem
├── src/
│   └── main.cpp         # Kode sumber firmware utama
├── test/                # Unit test perangkat keras
└── README.md            # Dokumentasi ini
```

---

## 2. Pemetaan Pinout Perangkat Keras

| Fungsi / Komponen | Tipe Sinyal | Pin GPIO ESP32 | Keterangan |
| :--- | :---: | :---: | :--- |
| **Sensor pH (PH-45002C / SEN0161)** | Analog | **GPIO 34** | ADC1_CH6 (Aman saat Wi-Fi aktif) |
| **Sensor Kekeruhan / Turbidity (SEN0189)** | Analog | **GPIO 35** | ADC1_CH7 |
| **Sensor TDS (SEN0244)** | Analog | **GPIO 32** | ADC1_CH4 |
| **Sensor Suhu DS18B20** | Digital | **GPIO 4** | 1-Wire Bus (Pull-up $4.7\text{ k}\Omega$ ke 3.3V) |
| **Sensor Ultrasonik HC-SR04 (Trig)** | Digital Out | **GPIO 13** | Trigger pulsa 10 us |
| **Sensor Ultrasonik HC-SR04 (Echo)** | Digital In | **GPIO 12** | Echo pulsa (Gunakan voltage divider ke 3.3V) |
| **Modul Relai Valve 1 (Kamar Mandi)** | Digital Out | **GPIO 25** | Aktif LOW (Relai koil 5V optocoupler) |
| **Modul Relai Valve 2 (Dapur)** | Digital Out | **GPIO 26** | Aktif LOW |
| **Modul Relai Valve 3 (Mesin Cuci)** | Digital Out | **GPIO 27** | Aktif LOW |
| **Modul Relai Valve 4 (Taman / Irigasi)** | Digital Out | **GPIO 14** | Aktif LOW |
| **MicroSD Card SPI (CS)** | Digital Out | **GPIO 5** | Chip Select |
| **MicroSD Card SPI (MOSI)** | Digital Out | **GPIO 23** | SPI Master Out |
| **MicroSD Card SPI (MISO)** | Digital In | **GPIO 19** | SPI Master In |
| **MicroSD Card SPI (SCK)** | Digital Out | **GPIO 18** | SPI Clock |

---

## 3. Cara Kompilasi & Flashing

### Opsi A: Menggunakan PlatformIO (Disarankan)
1. Buka folder `firmware/esp32` di VS Code yang telah terpasang ekstensi **PlatformIO IDE**.
2. Sesuaikan kredensial Wi-Fi dan IP MQTT broker pada baris 26-29 di `src/main.cpp`.
3. Hubungkan board ESP32 via kabel Micro-USB ke laptop.
4. Klik tombol **Build** (tanda centang) lalu **Upload** (tanda panah kanan) di status bar PlatformIO.
5. Buka Serial Monitor pada baudrate **115200**.

### Opsi B: Menggunakan Arduino IDE
1. Pasang board package **esp32** by Espressif Systems (v2.x atau v3.x).
2. Pasang library berikut via Library Manager:
   - `PubSubClient` by Nick O'Leary
   - `ArduinoJson` by Benoit Blanchon (v7)
   - `OneWire` by Paul Stoffregen
   - `DallasTemperature` by Miles Burton
3. Buka berkas `src/main.cpp`.
4. Pilih board **ESP32 Dev Module** dan port COM yang sesuai.
5. Klik **Upload**.

---

## 4. Fitur Firmware Utama
1. **Filter Digital EWMA ($\alpha = 0.2$)**: Mereduksi fluktuasi derau pembacaan ADC analog akibat riak air dan interferensi elektromagnetik pompa.
2. **Kompensasi Termal Ultrasonik**: Mengkoreksi variasi kecepatan rambat gelombang suara di udara berdasarkan suhu air aktual ($v = 331.3 + 0.606 \times T$).
3. **Deteksi Anomali Seketika Lokal**: Jika mendadak terjadi lonjakan polutan masif, ESP32 seketika memutus ke-4 relai katup (*emergency failsafe*) tanpa menunggu instruksi cloud.
4. **Pencadangan MicroSD**: Mencatat data telemetri ke kartu MicroSD jika koneksi Wi-Fi/MQTT terputus.
