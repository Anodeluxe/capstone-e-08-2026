#pragma once

/*
 * Konfigurasi Pinout dan Parameter Operasional ESP32
 * Sistem Monitoring Kualitas & Kontrol Distribusi Air Toren (Kelompok E-08)
 * Departemen Teknik Elektro dan Teknologi Informasi FT UGM 2026
 */

// ── Sensor Analog (ADC1 - Aman digunakan saat Wi-Fi aktif) ────────────────────
#define PIN_PH_SENSOR          34   // ADC1_CH6: Sensor pH elektroda kaca
#define PIN_TURBIDITY          35   // ADC1_CH7: Sensor kekeruhan nephelometrik
#define PIN_TDS_SENSOR         32   // ADC1_CH4: Sensor konduktivitas TDS

// ── Sensor Digital ────────────────────────────────────────────────────────────
#define PIN_DS18B20            4    // 1-Wire Digital: Sensor suhu probe waterproof
#define PIN_TRIG_US            13   // Output: HC-SR04 Ultrasonic Trigger
#define PIN_ECHO_US            12   // Input: HC-SR04 Ultrasonic Echo

// ── Modul MicroSD Card (SPI Bus) ──────────────────────────────────────────────
#define PIN_SD_CS              5    // SPI Chip Select
#define PIN_SD_MOSI            23   // SPI MOSI
#define PIN_SD_MISO            19   // SPI MISO
#define PIN_SD_SCK             18   // SPI Clock

// ── Modul Relai 4-Channel Solenoid Valve (Aktif LOW) ──────────────────────────
#define PIN_VALVE_BATHROOM     25   // Katup 1: Kamar Mandi
#define PIN_VALVE_KITCHEN      26   // Katup 2: Dapur
#define PIN_VALVE_LAUNDRY      27   // Katup 3: Mesin Cuci
#define PIN_VALVE_GARDEN       14   // Katup 4: Taman / Irigasi

// ── Parameter Sistem & Filter Digital ─────────────────────────────────────────
#define PUBLISH_INTERVAL_MS    10000 // Interval kirim data MQTT (10 detik)
#define FILTER_ALPHA           0.20f // Faktor pelunakan Exponential Moving Average (EWMA)
#define TANK_HEIGHT_CM         50.0f // Tinggi fisik tangki toren miniatur (cm)
#define SOUND_BASE_SPEED_M_S   331.3f // Kecepatan suara dasar pada 0 °C (m/s)
#define TEMP_COEFF_SOUND       0.606f // Koefisien kenaikan kecepatan suara per °C

// ── Ambang Batas Lonjakan Anomali Lokal (Edge Failsafe) ────────────────────────
#define THRESHOLD_SPIKE_PH     1.0f  // Perubahan mendadak pH dalam 1 siklus
#define THRESHOLD_SPIKE_TURB   5.0f  // Perubahan mendadak kekeruhan (NTU)
#define THRESHOLD_SPIKE_TDS    50.0f // Perubahan mendadak TDS (ppm)
