# CETAK BIRU & PANDUAN PENYELESAIAN PROYEK CAPSTONE (KELOMPOK E-08)
## SISTEM MONITORING KUALITAS DAN PENGAMBILAN KEPUTUSAN UNTUK DETEKSI DINI DAN KONTROL DISTRIBUSI AIR TOREN PADA KEBUTUHAN RUMAH TANGGA NON-KONSUMSI

**Departemen Teknik Elektro dan Teknologi Informasi (DTETI)**  
**Fakultas Teknik, Universitas Gadjah Mada — 2026**  
**Dokumen Referensi**: Dokumen C-251-E_08 (Perancangan Produk dan Spesifikasi)  
**Dosen Pembimbing**: Dr. Ir. Guntur Dharma Putra, S.T., M.Sc. (NIP: 111 1991 04 2018 02 102)  
**Pembaruan Terkini**: Pasca-Pull Model XGBoost Horizon (`8ded2e2`), Registri Skoring Lengkap, dan Penataan Direktori Firmware.

---

## DAFTAR ISI
1. [Ringkasan Eksekutif & Struktur Tim](#1-ringkasan-eksekutif--struktur-tim)
2. [Status Model Machine Learning Terkini (Pulled Model)](#2-status-model-machine-learning-terkini-pulled-model)
3. [Registri Lokasi Skoring Sistem (Catatan Lengkap untuk Evaluasi Nanti)](#3-registri-lokasi-skoring-sistem-catatan-lengkap)
4. [Arsitektur & Penataan Folder Firmware (`firmware/`)](#4-arsitektur--penataan-folder-firmware-firmware)
5. [Rencana Penyelesaian Per Sub-Sistem](#5-rencana-penyelesaian-per-sub-sistem)
   - 5.1. [Perangkat Keras & Purwarupa Miniatur (Hardware Rig)](#51-perangkat-keras--purwarupa-miniatur-hardware-rig)
   - 5.2. [Firmware ESP32 & Komputasi Tepi (Edge Processing)](#52-firmware-esp32--komputasi-tepi-edge-processing)
   - 5.3. [Basis Data & Backend Cloud (FastAPI + TimescaleDB)](#53-basis-data--backend-cloud-fastapi--timescaledb)
   - 5.4. [Machine Learning & Early Warning System (Inference Pipeline)](#54-machine-learning--early-warning-system-inference-pipeline)
   - 5.5. [Dashboard Antarmuka Pengguna (Progressive Web App - PWA)](#55-dashboard-antarmuka-pengguna-progressive-web-app---pwa)
   - 5.6. [Sistem Notifikasi Darurat (Email & WhatsApp Fonnte)](#56-sistem-notifikasi-darurat-email--whatsapp-fonnte)
6. [Matriks 12 Kriteria Keberhasilan Terukur IABEE & Rencana Pengujian](#6-matriks-12-kriteria-keberhasilan-terukur-iabee--rencana-pengujian)
7. [Anggaran Biaya & Pengadaan Komponen](#7-anggaran-biaya--pengadaan-komponen)
8. [Daftar Luaran Akhir & Jadwal Menuju Sidang Capstone 2](#8-daftar-luaran-akhir--jadwal-menuju-sidang-capstone-2)

---

## 1. RINGKASAN EKSEKUTIF & STRUKTUR TIM

### 1.1 Deskripsi Masalah & Solusi
Air toren domestik non-konsumsi (sanitasi, mandi, mencuci pakaian, dan menyiram tanaman) rentan mengalami penurunan kualitas akibat degradasi progresif internal (lumut, biofilm, endapan mineral) atau anomali mendadak dari sumber inlet. Setiap titik penggunaan air memiliki toleransi baku mutu yang berbeda sesuai **Permenkes No. 2 Tahun 2023**.

Solusi yang dirancang adalah **Sistem Siber-Fisik (*Cyber-Physical System*)** terpadu:
- **Pengukuran 5 Sensor**: pH, Turbidity, TDS, Suhu (DS18B20), dan Ketinggian Air (Ultrasonik HC-SR04).
- **Pengolahan Tepi (ESP32)**: Filter digital EWMA/FIR, kalibrasi sensor terkompensasi suhu, serta deteksi lonjakan seketika (*Rate of Change*) untuk penutupan darurat lokal (*failsafe*).
- **Kontrol Bertingkat 4 Valve**: Distribusi selektif via relai 4-channel ke 4 titik (Kamar Mandi, Dapur, Mesin Cuci, Taman) berdasarkan *Weighted Quality Index* (WQI).
- **Early Warning System (EWS)**: Model Machine Learning XGBoost Horizon (`xgb_model_hourly_v2_horizon.pkl`) untuk meramalkan sisa umur pakai air (*Remaining Useful Life* / RUL) dalam horizon 30 hari (peringatan jika $\le 10$ hari).
- **Platform Antarmuka**: Progressive Web App (PWA) responsif dengan pembaruan data berlatensi rendah ($< 1000$ ms via WebSocket) serta mekanisme *Manual Override* per katup berlog audit.

### 1.2 Pembagian Peran Anggota Tim (Tabel 9.3 Dokumen C-251)
| Nama Anggota | Program Studi | Peran Utama | Tanggung Jawab Spesifik |
| :--- | :--- | :--- | :--- |
| **Muhammad Rizqi Aminuddin** | Teknik Biomedis | **Ketua & Domain Expert** | Perumusan standar baku mutu air Permenkes, analisis bio-kimia degradasi toren, evaluasi validasi kinerja sensor laboratorium, penyusunan laporan akhir (PIC Dokumen). |
| **Shofiy Alia Rimala** | Teknik Elektro | **Hardware & Firmware Engineer** | Perancangan skematik rangkaian, wiring box kontrol IP65, perakitan pipa 4 valve, kalibrasi sensor, pemrograman firmware ESP32, implementasi filter digital FIR/EWMA & MicroSD logging. |
| **Azfanova Sammy Rafif Saputra** | Teknologi Informasi | **Software & Cloud Engineer** | Arsitektur backend FastAPI, broker MQTT Mosquitto, skema TimescaleDB & PostgreSQL, WebSocket live stream, otentikasi JWT, pengembangan Frontend PWA (Next.js) & UI/UX. |
| **Dzulfikar Rizqi Ramadhani** | Teknologi Informasi | **Machine Learning Engineer** | Sintesis dataset deret waktu degradasi toren, pelatihan & evaluasi model GRU vs XGBoost, kalkulasi metrik regresi (MAE/RMSE/Asymmetric Loss), integrasi inference engine ke scheduler backend. |

---

## 2. STATUS MODEL MACHINE LEARNING TERKINI (PULLED MODEL)

Berdasarkan komit terbaru `8ded2e2` (*feat: data generator horizon* oleh Dzulfikar), repositori telah dilengkapi model produksi terbaru yang siap diintegrasikan ke backend:

### 2.1 Spesifikasi Model `xgb_model_hourly_v2_horizon.pkl`
- **Lokasi Berkas**: `backend/app/ml/models/xgb_model_hourly_v2_horizon.pkl` (57.6 MB)
- **Metadata JSON**: `backend/app/ml/models/xgb_model_hourly_v2_horizon.json`
- **Tipe Algoritma**: `XGBRegressor` (`n_estimators=600`, `learning_rate=0.03`, `max_depth=11`, `tree_method="hist"`)
- **Target Cap Horizon**: $720\text{ jam}$ (30 hari). Nilai RUL di atas 30 hari di-cap secara konsisten karena sistem fokus pada horizon peringatan dini operasional rumah tangga.
- **Ambang Batas Kritis (*Score Threshold*)**: $60.0$ (skor kualitas air di bawah 60 memicu penutupan katup dan toren wajib dikuras).
- **22 Fitur Kausal Input**:
  1. `elapsed_hours`: Durasi jam siklus berjalan
  2. `ph_raw`: Nilai pembacaan pH saat ini
  3. `tds_raw`: Nilai pembacaan TDS (ppm) saat ini
  4. `turbidity_raw`: Nilai pembacaan kekeruhan (NTU) saat ini
  5. `temperature_raw`: Nilai pembacaan suhu (°C) saat ini
  6. `score_overall`: Skor kualitas air gabungan terkini
  7. `score_drop_24`: Penurunan skor dalam 24 jam terakhir
  8. `score_drop_72`: Penurunan skor dalam 72 jam (3 hari) terakhir
  9. `score_drop_168`: Penurunan skor dalam 168 jam (7 hari) terakhir
  10. `score_MA_24`: Moving average skor 24 jam
  11. `score_MA_72`: Moving average skor 72 jam
  12. `score_STD_24`: Standar deviasi bergulir skor 24 jam
  13. `turbidity_raw_MA24`: Moving average kekeruhan 24 jam
  14. `tds_raw_MA24`: Moving average TDS 24 jam
  15. `ph_raw_MA24`: Moving average pH 24 jam
  16. `turbidity_raw_drop24`: Selisih kekeruhan 24 jam
  17. `tds_raw_drop24`: Selisih TDS 24 jam
  18. `ph_raw_drop24`: Selisih pH 24 jam
  19. `turbidity_raw_drop72`: Selisih kekeruhan 72 jam
  20. `tds_raw_drop72`: Selisih TDS 72 jam
  21. `ph_raw_drop72`: Selisih pH 72 jam
  22. `hour_of_day`: Jam dalam hari ($0 - 23$) untuk menangkap pola diurnal suhu

---

## 3. REGISTRI LOKASI SKORING SISTEM (CATATAN LENGKAP)

Sesuai instruksi, **logika skoring saat ini dibiarkan apa adanya (*as-is*) tanpa diubah**. Seluruh titik kode yang mendefinisikan, mengolah, mentransformasi, atau menampilkan skoring dipetakan secara lengkap di bawah ini agar aman saat tim ingin meninjau ulang skoring di masa mendatang:

### 3.1 Backend Core & Services
1. `backend/app/services/scoring_service.py`
   - **Sub-scorer**:
     - `_ph_score(ph)`: 6.5–8.5 $\to$ 100, 6.0–6.5 & 8.5–9.0 $\to$ 70, 5.5–6.0 & 9.0–9.5 $\to$ 40, lainnya 0.
     - `_turbidity_score(ntu)`: $\le 1.0 \to 100$, $\le 5.0 \to 80$, $\le 10.0 \to 55$, $\le 25.0 \to 25$, lainnya 0.
     - `_tds_score(ppm)`: $\le 300 \to 100$, $\le 500 \to 80$, $\le 900 \to 50$, $\le 1200 \to 20$, lainnya 0.
     - `_temperature_score(celsius)`: 20–30 $\to$ 100, 15–20 & 30–35 $\to$ 75, 10–15 & 35–40 $\to$ 50, lainnya 25.
   - **Ambang Penutupan Katup (`USE_POINT_THRESHOLDS`)**:
     - `bathroom`: 60.0
     - `kitchen`: 65.0
     - `laundry`: 45.0
     - `garden`: 30.0
   - **Bobot Override (`_USE_POINT_WEIGHT_OVERRIDES`)**: Pembobotan spesifik untuk masing-masing titik distribusi.
   - **Fungsi Utama**: `compute_scores(payload: ESP32SensorPayload) -> ScoringResult`.

2. `backend/app/services/anomaly_service.py`
   - Membandingkan `current_score` dan `previous_score`.
   - `score_drop = previous_score - current_score`. Jika melebihi ambang batas (`settings.sudden_change_threshold = 20.0`), memicu `is_sudden_change = True`.

3. `backend/app/services/valve_service.py`
   - Menerima objek `ScoringResult`.
   - Mengambil daftar `valves_to_close` berdasarkan perbandingan skor terhadap ambang.
   - Menyimpan `quality_score_at_close` ke dalam tabel relasional `valve_states`.

4. `backend/app/services/prediction_service.py`
   - Menerima deret waktu `scores: list[float]`.
   - Mengevaluasi tren skor (penurunan terhadap ambang batas `DEFAULT_SCORE_THRESHOLD = 60.0`).

### 3.2 Machine Learning & Data Pipeline
5. `backend/app/ml/scoring_model.py`
   - Mirror referensi scoring yang harus selalu identik dengan `scoring_service.py`.
   - Digunakan oleh generator data sintetis agar dataset latih selaras dengan logika produksi.

6. `backend/app/ml/data_generator_hourly.py`
   - Mengimpor fungsi skoring dari `scoring_model.py` untuk mengkalkulasi `score_overall` pada setiap jam simulasi siklus tangki toren.

7. `backend/app/ml/train_xgb_v2.py`
   - Membangun 7 fitur turunan skor: `score_overall`, `score_drop_24`, `score_drop_72`, `score_drop_168`, `score_MA_24`, `score_MA_72`, `score_STD_24`.
   - Menggunakan ambang batas kelayakan: `score_threshold: 60.0`.

8. `backend/app/ml/evaluate_model.py` & `evaluator.py`
   - Mengevaluasi akurasi prediksi RUL berdasarkan persilangan waktu terhadap skor kelayakan kritis.

### 3.3 Penanganan Pesan MQTT & Scheduler Terjadwal
9. `backend/app/mqtt/handlers.py`
   - Memanggil `compute_scores(payload)` pada setiap pesan telemetri masuk dari ESP32.
   - Mengisi field `score_overall`, `score_bathroom`, `score_kitchen`, `score_laundry`, `score_garden`, `ph_score`, `turbidity_score`, `tds_score`, `temperature_score` ke dalam `SensorReading`.
   - Mengirim skor terhitung ke `process_auto_valve_decisions()`.

10. `backend/app/tasks/scheduler.py`
    - Mengambil data `score_overall` dari tabel `sensor_readings` untuk dievaluasi oleh engine prediksi RUL per jam.

### 3.4 Basis Data (Model & Skema)
11. `backend/app/models/sensor_reading.py`
    - Kolom tabel TimescaleDB:
      - `score_overall`, `score_bathroom`, `score_kitchen`, `score_laundry`, `score_garden`
      - `ph_score`, `turbidity_score`, `tds_score`, `temperature_score`

12. `backend/app/models/valve.py`
    - Kolom `ValveState.quality_score_at_close`
    - Kolom `ValveOverrideLog.score_at_override`

13. `backend/app/schemas/sensor.py` & `backend/app/schemas/valve.py`
    - Pydantic models untuk pertukaran data API REST dan payload serialisasi JSON.

### 3.5 Konfigurasi & Lingkungan
14. `backend/app/core/config.py` & `backend/.env.example`
    - `weight_ph = 0.30`, `weight_turbidity = 0.30`, `weight_tds = 0.25`, `weight_temperature = 0.15`
    - `sudden_change_threshold = 20.0`

### 3.6 Antarmuka Frontend (PWA Next.js)
15. `frontend/types/index.ts`
    - Deklarasi tipe antarmuka TypeScript untuk `SensorReading`, `ValveState`, dan `ValveOverrideLog`.

16. `frontend/app/dashboard/page.tsx`
    - Menampilkan live scores 4 valve (`score_bathroom`, `score_kitchen`, `score_laundry`, `score_garden`).

17. `frontend/components/dashboard/SensorScoreCard.tsx`
    - Merender grafik gauge busur (SVG arc) dengan pewarnaan semantik:
      - Hijau/Emerald ($\ge 75$)
      - Amber/Kuning ($50 - 74$)
      - Merah/Rose ($< 50$)

18. `frontend/components/predictions/TrendChart.tsx`
    - Memplot area chart deret waktu riwayat pergerakan skor kualitas air 24 jam terakhir.

19. `frontend/components/valves/ValveCard.tsx` & `OverrideModal.tsx`
    - Menampilkan informasi skor kualitas saat katup tertutup otomatis dan saat pengguna meminta *manual override*.

### 3.7 Suite Pengujian
20. `backend/tests/test_scoring_service.py`
    - Unit test per sub-scorer dan integrasi `compute_scores()`.

21. `backend/tests/test_scoring_consistency.py`
    - Memvalidasi bahwa `scoring_model.py` di folder ML identik persis dengan `scoring_service.py` di backend produksi (selisih $< 10^{-9}$).

---

## 4. ARSITEKTUR & PENATAAN FOLDER FIRMWARE (`firmware/`)

Untuk memfasilitasi kerja tim Hardware (Shofiy Alia Rimala) secara terisolasi dan modular, seluruh aset firmware ESP32 ditempatkan pada folder terdedikasi `firmware/`:

```
capstone-e-08-2026/
├── firmware/
│   └── esp32/
│       ├── platformio.ini       # Konfigurasi PlatformIO (board, framework, libraries)
│       ├── include/
│       │   └── config.h         # Pinout hardware, filter alpha, Wi-Fi & MQTT constants
│       ├── src/
│       │   └── main.cpp         # Firmware utama (akuisisi, filter EWMA, MQTT, offline SD)
│       ├── test/
│       │   ├── test_sensors.cpp # Uji pembacaan masing-masing sensor
│       │   └── test_relays.cpp  # Uji pensaklaran 4 solenoid valve
│       └── README.md            # Panduan wiring, skema daya 12V/5V, & flashing firmware
```

### 4.1 Spesifikasi Pinout (`firmware/esp32/include/config.h`)
```cpp
#pragma once

// Sensor Analog (ADC1 - aman saat Wi-Fi aktif)
#define PIN_PH_SENSOR       34   // ADC1_CH6
#define PIN_TURBIDITY       35   // ADC1_CH7
#define PIN_TDS_SENSOR      32   // ADC1_CH4

// Sensor Digital
#define PIN_DS18B20         4    // OneWire Bus Digital
#define PIN_TRIG_US         13   // Ultrasonic HC-SR04 Trigger
#define PIN_ECHO_US         12   // Ultrasonic HC-SR04 Echo

// Modul MicroSD Card (SPI Bus)
#define PIN_SD_CS           5    // SPI Chip Select
#define PIN_SD_MOSI         23
#define PIN_SD_MISO         19
#define PIN_SD_SCK          18

// Modul Relai 4-Channel Solenoid Valve (Aktif LOW)
#define PIN_VALVE_BATHROOM  25
#define PIN_VALVE_KITCHEN   26
#define PIN_VALVE_LAUNDRY   27
#define PIN_VALVE_GARDEN    14

// Parameter Operasional
#define PUBLISH_INTERVAL_MS 10000 // Pengiriman MQTT setiap 10 detik
#define FILTER_ALPHA        0.20f // Faktor pelunakan EWMA
#define TANK_HEIGHT_CM      50.0f // Tinggi fisik tangki miniatur toren
```

---

## 5. RENCANA PENYELESAIAN PER SUB-SISTEM

### 5.1 Perangkat Keras & Purwarupa Miniatur (Hardware Rig)
1. **Perakitan Hidrolik Miniatur**:
   - Tangki penampung air kapasitas 15–20 Liter (ember toren bertutup).
   - Jalur outlet bawah 1/2 inci bercabang 4 menggunakan pipa PVC, *fitting tee*, dan *knee 90 derajat*.
   - 4 unit *Solenoid Valve Normally Closed (N/C) 12V DC* terpasang pada masing-masing saluran keluar (Kamar Mandi, Dapur, Mesin Cuci, Taman).
2. **Kelistrikan & Manajemen Daya**:
   - Catu daya utama: Adaptor Switching 12V DC 3A.
   - Modul Step-Down / Buck Converter (LM2596) menghasilkan 5V DC 2A untuk ESP32 dan modul sensor.
   - Pemasangan modul relai 4-channel berisolasi optocoupler untuk mencegah lonjakan induktif koil solenoid (*back-EMF*) mereset mikrokontroler.

### 5.2 Firmware ESP32 & Komputasi Tepi (Edge Processing)
1. **Filter Digital EWMA**:
   Mereduksi fluktuasi riak cairan dan derau analog ADC 12-bit:
   $$\hat{Q}[n] = \alpha \cdot Q_{\text{raw}}[n] + (1 - \alpha) \cdot \hat{Q}[n-1]$$
2. **Kompensasi Suhu Sensor Level Ultrasonik**:
   Menghitung kecepatan rambat suara dinamis berdasarkan pembacaan suhu probe DS18B20:
   $$v = 331.3 + 0.606 \times T_{\text{DS18B20}} \quad (\text{m/s})$$
3. **Pencadangan MicroSD saat Offline**:
   Jika jaringan Wi-Fi atau MQTT terputus, data sensor tetap tersimpan ke kartu MicroSD dengan format CSV (`/offline_telemetry.csv`) sehingga tidak ada rekaman hilang saat pengujian jangka panjang.

### 5.3 Basis Data & Backend Cloud (FastAPI + TimescaleDB)
1. **Perbaikan Unit Test Anomaly Service** [SELESAI]:
   Perbaiki baris 51 pada `backend/app/services/anomaly_service.py` dari `<` menjadi `<=` sehingga seluruh 71 pengujian unit lolos (100% passed).
2. **Inisialisasi TimescaleDB Hypertable**:
   Memastikan saat startup dijalankan instruksi DDL:
   ```sql
   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
   SELECT create_hypertable('sensor_readings', 'timestamp', if_not_exists => TRUE);
   ```
3. **Otentikasi Pengguna & Proteksi Override** [SELESAI]:
   - Membangun `backend/app/core/security.py` menggunakan standard library `hashlib.pbkdf2_hmac` dan `python-jose` untuk JWT.
   - Endpoint `POST /api/v1/auth/login` dan `GET /api/v1/auth/me` terdaftar di `backend/app/api/v1/auth.py`.
   - Melindungi endpoint `POST /api/v1/valves/{id}/command` dengan ekstraksi identitas operator via JWT (dengan dev-mode fallback), mencatat `user_id` dan `reason` ke `valve_override_logs`.
   - Mengembangkan skrip simulator hardware ESP32 lengkap `backend/scripts/simulate_esp32.py` (skenario normal, gradual, spike, interactive) beserta uji otomatis di `backend/tests/test_simulator.py`.

### 5.4 Machine Learning & Early Warning System (Inference Pipeline)
1. **Pemuatan Bundle Model Pulled** [SELESAI]:
   - Membaca `xgb_model_hourly_v2_horizon.pkl` (horizon 30 hari, 22 fitur kausal) menggunakan `joblib` dan `xgboost>=2.0.0,<3.0.0`.
   - Mengintegrasikan fungsi `predict_rul_from_readings()` ke `backend/app/services/prediction_service.py`.
2. **Eksekusi Penjadwal Terjadwal (Hourly Job)** [SELESAI]:
   - APScheduler pada `backend/app/tasks/scheduler.py` dan endpoint `backend/app/api/v1/predictions.py` mengeksekusi inferensi multi-parameter (pH, TDS, turbiditas, suhu).
   - Nilai estimasi RUL (jam) dikonversi menjadi sisa hari.
   - Jika $\text{RUL} \le 10\text{ hari}$, tandai peringatan dini dan simpan ke basis data.

### 5.5 Dashboard Antarmuka Pengguna (Progressive Web App - PWA)
1. **Web App Manifest (`frontend/public/manifest.json`)** [SELESAI]:
   Konfigurasi metadata aplikasi PWA (nama, tema `#0891b2`, latar belakang `#0f172a`, ikon 192px dan 512px) terhubung di `frontend/app/layout.tsx`.
2. **Service Worker (`frontend/public/sw.js`)** [SELESAI]:
   Caching app shell secara offline, strategi network-first untuk navigasi, dan penanganan event Web Push notification. Komponen pendaftaran otomatis `frontend/components/PwaRegister.tsx`.
3. **Modal Manual Override (`frontend/components/valves/OverrideModal.tsx`)** [SELESAI]:
   Menyediakan tombol cepat preset alasan (`Pembersihan toren rutin`, `Pengujian katup`, `Kebutuhan mendesak`, `Kuras air terkontaminasi`), peringatan interlock risiko kesehatan saat membuka katup, dan audit trail.
4. **Banner Peringatan Dini EWS (`frontend/components/dashboard/AlertBanner.tsx`)** [SELESAI]:
   Banner amber dengan hitung mundur hari tersisa RUL ($\le 10$ hari) terhubung ke API prediksi, persentase keyakinan model, dan rekomendasi penjadwalan pembersihan toren.

### 5.6 Sistem Notifikasi Darurat (Email & WhatsApp Fonnte)
1. **Kanal Email (SMTP)**:
   Mengirim laporan insiden anomali mendadak beserta nilai sensor terkait.
2. **Kanal WhatsApp (Fonnte API)**:
   Mengirim notifikasi instan langsung ke nomor WhatsApp pemilik rumah tangga saat terdeteksi kontaminasi air mendadak atau sisa hari pengurasan $\le 10$ hari.

---

## 6. MATRIKS 12 KRITERIA KEBERHASILAN TERUKUR IABEE & RENCANA PENGUJIAN

| No | Parameter / Metrik | Target Keberhasilan | Metode & Skenario Pengujian |
| :---: | :--- | :---: | :--- |
| **1** | **Akurasi Pembacaan Sensor** | $\ge 95\%$ | Uji komparasi 10 titik sampel terhadap instrumen laboratorium terkalibrasi. |
| **2** | **Konsistensi Pembacaan Sensor (Deviasi)** | $\le 5\%$ | Perekaman 100 sampel berturut-turut pada larutan statis selama 30 menit ($RSD \le 5\%$). |
| **3** | **Waktu Respons End-to-End** | $\le 3\text{ detik}$ | Latensi dari pemicu anomali hingga penutupan relai fisik dan pembaruan UI dashboard. |
| **4** | **Akurasi Pengambilan Keputusan** | $\ge 85\%$ | Pengujian 50 skenario kombinasi kualitas air vs ground truth logika aturan. |
| **5** | **False Alarm Rate** | $\le 10\%$ | Pengujian stabilitas air normal 24 jam tanpa kontaminasi riil ($FAR \le 10\%$). |
| **6** | **Akurasi Deteksi Pola Penurunan** | $\ge 80\%$ | Evaluasi kemampuan mendeteksi tren penurunan parameter deret waktu. |
| **7** | **Akurasi Prediksi EWS (MAE)** | $\le 1\text{ hari}$ | Evaluasi model XGBoost terhadap dataset uji degradasi ($MAE \le 1.0\text{ hari}$). |
| **8** | **Efektivitas Kontrol 4 Valve** | $\ge 90\%$ | Pengujian 100 siklus switching relai dan solenoid valve tanpa kegagalan mekanik. |
| **9** | **Kesesuaian Distribusi Bertingkat** | $\ge 85\%$ | Verifikasi status selektif (Mandi & Dapur tutup, Taman & Cucian tetap buka saat kualitas sedang). |
| **10** | **Fungsionalitas Manual Override** | $100\%$ | Eksekusi 20 kali intervensi manual dari web; pastikan relai merespon seketika & tercatat di DB. |
| **11** | **Reliabilitas Sistem (Uptime)** | $\ge 95\%$ | Pengujian operasional terhubung selama 7 hari berturut-turut (168 jam) tanpa crash. |
| **12** | **Biaya Total Pembuatan Purwarupa** | $\le \text{Rp}3.000.000$ | Pembukuan nota pengadaan perangkat keras (estimasi realisasi Rp1.334.000). |

---

## 7. ANGGARAN BIAYA & PENGADAAN KOMPONEN

| No | Komponen / Deskripsi | Jumlah | Harga Satuan (Rp) | Total (Rp) | Status Pengadaan |
| :---: | :--- | :---: | :---: | :---: | :---: |
| 1 | ESP32 DEVKITC V4 (ESP-WROOM-32D) | 1 unit | 80.000 | 80.000 | Siap / Tersedia |
| 2 | Sensor Suhu DS18B20 Probe Waterproof | 1 unit | 14.000 | 14.000 | Siap / Tersedia |
| 3 | Sensor Jarak HC-SR04 Ultrasonic Finder | 1 unit | 15.000 | 15.000 | Siap / Tersedia |
| 4 | TDS Meter Module V1.0 Water Quality | 1 unit | 55.000 | 55.000 | Siap / Tersedia |
| 5 | Turbidity Sensor Kit Suspended Particle | 1 unit | 200.000 | 200.000 | Siap / Tersedia |
| 6 | pH Meter Kit Elektroda BNC PH-45002C | 1 unit | 212.000 | 212.000 | Siap / Tersedia |
| 7 | Solenoid Valve N/C 12V DC 1/2 Inci | 4 unit | 46.000 | 184.000 | Perlu Pembelian |
| 8 | Modul Relai 4-Channel 5V Optocoupler | 1 unit | 60.000 | 60.000 | Perlu Pembelian |
| 9 | Adaptor Switching 12V DC 3A + Buck 5V | 1 unit | 65.000 | 65.000 | Perlu Pembelian |
| 10 | Modul MicroSD Card SPI + Kartu SD 16GB | 1 unit | 120.000 | 120.000 | Perlu Pembelian |
| 11 | Tangki Penampung Plastik (Ember Toren) | 1 unit | 20.000 | 20.000 | Siap / Tersedia |
| 12 | Pipa PVC 1/2", Knee 90°, Fitting Tee | 1 set | 105.000 | 105.000 | Perlu Pembelian |
| 13 | Kotak Panel Box Waterproof IP65 | 1 unit | 55.000 | 55.000 | Perlu Pembelian |
| 14 | Kabel Jumper & Kabel Serabut DC | 1 set | 23.000 | 23.000 | Siap / Tersedia |
| 15 | Kebutuhan Expo (X-Banner, Pamflet, Stiker) | 1 paket | 181.000 | 181.000 | Menjelang Expo |
| **TOTAL** | | | | **1.369.000** | **Hemat Rp1.631.000** |

---

## 8. DAFTAR LUARAN AKHIR & JADWAL MENUJU SIDANG CAPSTONE 2

### 8.1 Daftar Luaran Wajib
1. **Purwarupa Fisik Beroperasi Penuh**: Miniatur instalasi toren dengan 5 sensor terpasang, box kontroler ESP32 IP65, 4 katup solenoid yang membuka/menutup sesuai kualitas air secara otomatis dan dapat dioverride dari jarak jauh.
2. **Paket Perangkat Lunak Terintegrasi**:
   - Firmware ESP32 terstruktur di folder `firmware/esp32/`.
   - Backend FastAPI tervirtualisasi (TimescaleDB, Redis, Mosquitto MQTT broker).
   - Pipeline inferensi model `xgb_model_hourly_v2_horizon.pkl` berjalan per jam.
   - Frontend Next.js PWA yang responsif dan dapat diakses di smartphone pengguna.
3. **Dokumen Laporan Akhir Capstone (C-300 / C-400 / C-500)**:
   - Hasil kalibrasi dan validasi ke-5 sensor laboratorium.
   - Grafik kinerja model ML dan confusion matrix aktuasi katup.
   - Bukti capaian seluruh 12 kriteria keberhasilan IABEE.
4. **Materi Expo & Demonstrasi**:
   - Video demonstrasi operasional sistem (durasi 3–5 menit).
   - X-Banner dan poster infografis proyek.
   - Buku panduan pengguna (*User Manual*).

---
*Dokumen ini diperbarui secara berkala sebagai panduan resmi seluruh anggota Kelompok E-08 Capstone DTETI UGM 2026.*
