"""
Data Generator — Granularitas Per Jam (Siklus 90-120 Hari)
────────────────────────────────────────────────────────────
Menghasilkan data time-series sintetis untuk training model RUL
dengan satuan waktu PER JAM dan siklus 90-120 hari (2160-2880 jam),
sesuai riset: air tandon harus dikuras minimal 3 bulan sekali.

Pola degradasi SINTETIS dicampur dua skenario (tergantung kondisi tandon):
  - 'linear' : degradasi konstan dari awal sampai akhir
  - 'stabil' : kualitas stabil di 60% pertama, menurun di 40% terakhir

Setiap baris = 1 jam pembacaan sensor.
1000 siklus total.

Output:
  - data/processed/data_toren_hourly.csv  (dataset siap training)
  - models/scaler_hourly.pkl              (MinMaxScaler fitted)
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import pickle
import os

print("=" * 60)
print("DATA GENERATOR — GRANULARITAS PER JAM")
print("Siklus: 90-120 hari (2160-2880 jam)")
print("=" * 60)

# ==========================================
# 1. LOAD & FILTER DATASET MENTAH
# ==========================================
print("\n1. Memuat dataset mentah...")

df = pd.read_csv('./data/raw/watera.csv')
df_filtered = df[['ph', 'tds', 'turbidity', 'potability']].dropna()
print(f"   Shape: {df.shape} → setelah filter: {df_filtered.shape}")

# Tambah suhu sintetis (25-32°C, typical Indonesia)
df_filtered['temperature'] = np.random.uniform(25.0, 32.0, size=len(df_filtered))

# ==========================================
# 2. REMOVE OUTLIER EKSTREM
# ==========================================
print("\n2. Menghapus outlier ekstrem...")

def remove_extreme_outliers(dataframe):
    df_clean = dataframe.copy()

    # pH: filter IQR 1.5x, clamp ke [0, 14]
    Q1_ph = df_clean['ph'].quantile(0.25)
    Q3_ph = df_clean['ph'].quantile(0.75)
    IQR_ph = Q3_ph - Q1_ph
    df_clean = df_clean[
        (df_clean['ph'] >= max(0, Q1_ph - 1.5 * IQR_ph)) &
        (df_clean['ph'] <= min(14, Q3_ph + 1.5 * IQR_ph))
    ]

    # TDS & Turbidity: upper-bound only (1.5x IQR), harus > 0
    for col in ['tds', 'turbidity']:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        df_clean = df_clean[
            (df_clean[col] > 0) &
            (df_clean[col] <= Q3 + 1.5 * IQR)
        ]

    return df_clean

df_clean = remove_extreme_outliers(df_filtered)
print(f"   Sebelum: {len(df_filtered)} baris")
print(f"   Sesudah: {len(df_clean)} baris")

# ==========================================
# 3. GENERATE DATA TIME-SERIES (PER JAM)
# ==========================================
print("\n3. Mengekstrak profil kualitas air...")
profil_bersih = df_filtered[df_filtered['potability'] == 1].describe()
profil_kotor = df_filtered[df_filtered['potability'] == 0].describe()

print("   Profil bersih (potability=1):")
print(f"     pH mean={profil_bersih.loc['mean', 'ph']:.2f}, "
      f"TDS mean={profil_bersih.loc['mean', 'tds']:.2f}, "
      f"Turbidity mean={profil_bersih.loc['mean', 'turbidity']:.2f}")
print("   Profil kotor (potability=0):")
print(f"     pH mean={profil_kotor.loc['mean', 'ph']:.2f}, "
      f"TDS mean={profil_kotor.loc['mean', 'tds']:.2f}, "
      f"Turbidity mean={profil_kotor.loc['mean', 'turbidity']:.2f}")

print("\n4. Memulai simulasi degradasi air (1.000 siklus × 2160-2880 jam)...")

jumlah_siklus = 1000
data_time_series = []

np.random.seed(42)

# Nilai referensi (konstan di luar loop agar lebih cepat)
ph_start = profil_bersih.loc['mean', 'ph']
ph_end = profil_kotor.loc['mean', 'ph']
ph_noise_scale = profil_bersih.loc['std', 'ph'] * 0.1

solids_start = profil_bersih.loc['mean', 'tds']
solids_end = profil_kotor.loc['mean', 'tds']
solids_noise_scale = profil_bersih.loc['std', 'tds'] * 0.1

turb_start = profil_bersih.loc['mean', 'turbidity']
turb_end = profil_kotor.loc['mean', 'turbidity']
turb_noise_scale = profil_bersih.loc['std', 'turbidity'] * 0.1

for siklus in range(1, jumlah_siklus + 1):
    total_jam = np.random.randint(2160, 2881)  # 90-120 hari

    # Pilih pola degradasi secara random per siklus
    pola = np.random.choice(['linear', 'stabil'])

    jam_arr = np.arange(1, total_jam + 1)
    posisi = jam_arr / total_jam

    if pola == 'linear':
        # Degradasi konstan dari awal sampai akhir
        rasio_waktu = posisi
    else:
        # Stabil di 60% pertama, menurun di 40% terakhir
        rasio_waktu = np.where(
            posisi < 0.6,
            0.0,
            (posisi - 0.6) / 0.4
        )

    # ── pH: interpolasi sesuai rasio_waktu + noise ─────────────────────
    ph_cycle = ph_start + (ph_end - ph_start) * rasio_waktu + \
        np.random.normal(0, ph_noise_scale, total_jam)

    # ── TDS: interpolasi sesuai rasio_waktu + noise ────────────────────
    solids_cycle = solids_start + (solids_end - solids_start) * rasio_waktu + \
        np.random.normal(0, solids_noise_scale, total_jam)

    # ── Turbidity: interpolasi non-linear (power 1.5) + noise ──────────
    turb_cycle = turb_start + (turb_end - turb_start) * (rasio_waktu ** 1.5) + \
        np.random.normal(0, turb_noise_scale, total_jam)

    # ── Suhu: random uniform (independent dari degradasi) ──────────────
    temp_cycle = np.random.uniform(25.0, 32.0, total_jam)

    # ── RUL = sisa jam sebelum harus dikuras ────────────────────────────
    rul_cycle = total_jam - jam_arr

    for jam in range(total_jam):
        data_time_series.append({
            'Cycle_ID': siklus,
            'Jam': int(jam_arr[jam]),
            'ph': ph_cycle[jam],
            'tds': solids_cycle[jam],
            'turbidity': turb_cycle[jam],
            'temperature': temp_cycle[jam],
            'RUL': int(rul_cycle[jam])
        })

df_timeseries = pd.DataFrame(data_time_series)
print(f"   → Berhasil membuat {len(df_timeseries):,} baris data mentah.")
print(f"   → {jumlah_siklus} siklus × rata-rata ~2520 jam = ~{jumlah_siklus * 2520:,} baris")

# ==========================================
# 4. FEATURE ENGINEERING (SKALA JAM)
# ==========================================
print("\n5. Menerapkan Feature Engineering (elapsed_hours + MA_24)...")

# Sort by chronological order within each cycle
df_timeseries = df_timeseries.sort_values(by=['Cycle_ID', 'Jam'], ascending=[True, True])

# ── elapsed_hours: jam sejak awal siklus (waktu sejak terakhir kuras) ───────
df_timeseries['elapsed_hours'] = df_timeseries['Jam'] - 1

# ── MA_24: rata-rata 24 jam terakhir (menangkap tren degradasi jangka panjang)
for col in ['turbidity', 'tds', 'ph']:
    df_timeseries[f'{col}_MA_24'] = df_timeseries.groupby('Cycle_ID')[col].transform(
        lambda x: x.rolling(window=24, min_periods=1).mean()
    )

print("   Fitur berhasil ditambahkan!")
print(f"   Contoh baris pertama (siklus 1):")
print(df_timeseries[df_timeseries['Cycle_ID'] == 1][
    ['Jam', 'elapsed_hours', 'RUL', 'turbidity', 'turbidity_MA_24',
     'tds', 'tds_MA_24', 'ph', 'ph_MA_24']
].head(5).to_string(index=False))

# ==========================================
# 5. NORMALISASI & SIMPAN
# ==========================================
print("\n6. Melakukan normalisasi skala data (0-1)...")

fitur_x = [
    'elapsed_hours', 'ph', 'tds', 'turbidity', 'temperature',
    'ph_MA_24', 'tds_MA_24', 'turbidity_MA_24'
]

scaler = MinMaxScaler()
df_scaled = df_timeseries.copy()
df_scaled[fitur_x] = scaler.fit_transform(df_scaled[fitur_x])

# Pastikan folder ada
os.makedirs('models', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

# Simpan scaler
with open('models/scaler_hourly.pkl', 'wb') as file:
    pickle.dump(scaler, file)

# Simpan dataset
df_scaled.to_csv('data/processed/data_toren_hourly.csv', index=False)

print("\n" + "=" * 60)
print("PROSES SELESAI!")
print("=" * 60)
print(f"  Dataset  : data/processed/data_toren_hourly.csv ({len(df_scaled):,} baris)")
print(f"  Scaler   : models/scaler_hourly.pkl")
print(f"  Fitur    : {len(fitur_x)} kolom")
print(f"  Siklus   : {jumlah_siklus}")
print(f"  RUL max  : {df_timeseries['RUL'].max()} jam ({df_timeseries['RUL'].max() / 24:.0f} hari)")
print(f"  RUL min  : {df_timeseries['RUL'].min()} jam")
print("\nLangkah selanjutnya: jalankan 'python trainer.py'")
print("=" * 60)