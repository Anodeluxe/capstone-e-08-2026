import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler

# Load dataset
df = pd.read_csv('./data/raw/water_potability.csv')
# Ambil kolom yang dibutuhkan (Potability tetap diambil untuk acuan label kotor)
df_filtered = df[['ph', 'Solids', 'Turbidity', 'Potability']].dropna()
print(f'shape: {df.shape} --> setelah filter: {df_filtered.shape}')

# Simulasi suhu air toren di Indonesia (berkisar antara 24°C hingga 32°C)
# Kita tambahkan sedikit variasi acak (noise)
total_rows = len(df_filtered)
df_filtered['Temperature'] = np.random.uniform(24.0, 32.0, size=total_rows)
df_filtered.head()
df_filtered.shape

def remove_extreme_outliers(dataframe):
    df_clean = dataframe.copy()
    
    # 1. Pembersihan Kolom pH (Batas Dua Arah)
    # Menggunakan pengali 3.0 (Ekstrem) agar fluktuasi asam/basa yang alami tetap aman
    Q1_ph = df_clean['ph'].quantile(0.25)
    Q3_ph = df_clean['ph'].quantile(0.75)
    IQR_ph = Q3_ph - Q1_ph
    
    batas_bawah_ph = Q1_ph - 3.0 * IQR_ph
    batas_atas_ph = Q3_ph + 3.0 * IQR_ph
    
    # Filter pH (Serta pastikan secara fisik tidak keluar dari rentang standar 0-14)
    df_clean = df_clean[
        (df_clean['ph'] >= max(0, batas_bawah_ph)) & 
        (df_clean['ph'] <= min(14, batas_atas_ph))
    ]
    
    # 2. Pembersihan Kolom Solids & Turbidity (Fokus Longgar pada Batas Atas)
    # Kita ingin mempertahankan air sekotor mungkin, jadi batas atas dinaikkan sangat tinggi (3.0 * IQR)
    for col in ['Solids', 'Turbidity']:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        
        batas_atas_ekstrem = Q3 + 3.0 * IQR
        
        # Filter: Buang nilai minus/nol yang mustahil secara fisik, 
        # dan buang yang di atas batas ekstrem saja
        df_clean = df_clean[
            (df_clean[col] > 0) & 
            (df_clean[col] <= batas_atas_ekstrem)
        ]
        
    return df_clean

# Eksekusi fungsi baru
df_filtered_clean = remove_extreme_outliers(df_filtered)

print(f"Jumlah baris awal: {len(df_filtered)}")
print(f"Jumlah baris setelah membuang outlier ekstrem: {len(df_filtered_clean)}")
print(f"Data yang berhasil diselamatkan: {len(df_filtered_clean) - 2400 if 'tergantung_hasil' else 'Banyak data kotor natural tetap aman!'}")

# Pisahkan data air bersih dan kotor
df_bersih = df_filtered_clean[df_filtered_clean['Potability'] == 1].copy()
df_kotor = df_filtered_clean[df_filtered_clean['Potability'] == 0].copy()

# Parameter Simulasi Siklus
TOTAL_HARI_SIKLUS = 90
HARI_BERSIH = 75  # 75 hari pertama air sangat stabil (bersih)
HARI_KOTOR = 15   # 15 hari terakhir kualitas mulai turun menuju batas toleransi
JUMLAH_SIKLUS = 100 # Misalnya kita mau buat data dari 100 kali toren dikuras

# List untuk menampung semua siklus buatan
semua_siklus = []

# Buat perulangan untuk Siklus Penurunan Kualitas Air
for siklus_ke in range(1, JUMLAH_SIKLUS + 1):
    
    # Susun data agar semakin lama semakin kotor
    # Trik: Ambil sampel acak harian, lalu diurutkan nilainya dari yang paling kecil 
    # (paling bersih) ke paling besar (paling kotor) agar ada tren degradasi/penurunan
    # Tambahkan replace=True agar Pandas boleh mengambil ulang baris yang sama
    sampel_bersih = df_bersih.sample(n=HARI_BERSIH, replace=True).sort_values(by=['Turbidity', 'Solids'])
    sampel_kotor = df_kotor.sample(n=HARI_KOTOR, replace=True).sort_values(by=['Turbidity', 'Solids'])
    
    # Gabungkan data bersih dan kotor menjadi 1 rentang waktu (90 hari)
    data_1_siklus = pd.concat([sampel_bersih, sampel_kotor]).reset_index(drop=True)
    
    # Tambahkan ID Siklus (Sangat penting untuk LSTM/XGBoost)
    # Agar model tahu kapan 1 time-series toren selesai dan mulai toren baru
    data_1_siklus['Cycle_ID'] = siklus_ke
    
    # Langkah 4: Buat kolom target RUL (Remaining Useful Life)
    # Menghasilkan angka menurun dari 13 ke 0
    data_1_siklus['RUL'] = range(TOTAL_HARI_SIKLUS - 1, -1, -1)
    
    # Simpan siklus ke dalam list
    semua_siklus.append(data_1_siklus)

# Gabungkan semua list siklus menjadi satu DataFrame utuh siap training
df_timeseries = pd.concat(semua_siklus).reset_index(drop=True)

# (Opsional) Susun ulang urutan kolom agar lebih enak dibaca
df_timeseries = df_timeseries[['Cycle_ID', 'ph', 'Solids', 'Turbidity', 'Temperature', 'Potability', 'RUL']]
print(df_timeseries.head(10))
print(f'Shape dataset timeseries: {df_timeseries.shape}')
print(df_timeseries.dtypes)

# Pastikan data urut berdasarkan waktu sebelum dihitung
df_timeseries = df_timeseries.sort_values(by=['Cycle_ID', 'RUL'], ascending=[True, False])

# 1. Rolling Averages (Rata-rata bergerak 3 hari terakhir)
# Harus menggunakan groupby('Cycle_ID') agar perhitungan tidak melompat antar siklus yang berbeda
df_timeseries['Turbidity_MA_3'] = df_timeseries.groupby('Cycle_ID')['Turbidity'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
df_timeseries['Solids_MA_3'] = df_timeseries.groupby('Cycle_ID')['Solids'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
df_timeseries['ph_MA_3'] = df_timeseries.groupby('Cycle_ID')['ph'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())

# 2. Rate of Change (Kecepatan perubahan dari 1 hari sebelumnya / selisih harian)
# Menggunakan diff() untuk mencari selisih. fillna(0) digunakan untuk hari pertama di setiap siklus
df_timeseries['Turbidity_Diff'] = df_timeseries.groupby('Cycle_ID')['Turbidity'].diff().fillna(0)
df_timeseries['Solids_Diff'] = df_timeseries.groupby('Cycle_ID')['Solids'].diff().fillna(0)
df_timeseries['ph_Diff'] = df_timeseries.groupby('Cycle_ID')['ph'].diff().fillna(0)

# 3. Volatilitas (Standard Deviation - 3 Hari)
df_timeseries['Turbidity_Std_3'] = df_timeseries.groupby('Cycle_ID')['Turbidity'].transform(lambda x: x.rolling(window=3, min_periods=1).std().fillna(0))
df_timeseries['Solids_Std_3'] = df_timeseries.groupby('Cycle_ID')['Solids'].transform(lambda x: x.rolling(window=3, min_periods=1).std().fillna(0))

print("Fitur/kolom baru berhasil ditambahkan!")
print(df_timeseries[['Cycle_ID', 'RUL', 'Turbidity', 'Turbidity_MA_3', 'Turbidity_Diff', 'Turbidity_Std_3', 'Solids', 'Solids_MA_3', 'Solids_Diff', 'Solids_Std_3', 'ph', 'ph_MA_3', 'ph_Diff']].head())

import pickle
import os

# Memastikan folder 'models' tersedia untuk menyimpan file scaler.pkl
os.makedirs('modelsz', exist_ok=True)

# 1. Tentukan kolom fitur (X) yang akan dinormalisasi
# PENTING: Jangan masukkan 'Cycle_ID', 'RUL', atau 'Potability' (jika masih ada)
fitur_x = [
    'ph', 'Solids', 'Turbidity', 'Temperature',
    'Turbidity_MA_3', 'Solids_MA_3', 'ph_MA_3',
    'Turbidity_Diff', 'Solids_Diff', 'ph_Diff',
    'Turbidity_Std_3', 'Solids_Std_3'
]

# 2. Inisialisasi MinMaxScaler
scaler = MinMaxScaler()

# 3. Fit dan Transform data (Menghitung batas Min-Max dan mengubah skala menjadi 0-1)
# Kita membuat salinan dataframe agar data asli tidak tertimpa jika terjadi error
df_scaled = df_timeseries.copy()
df_scaled[fitur_x] = scaler.fit_transform(df_scaled[fitur_x])

# 4. Simpan objek scaler ke dalam file .pkl untuk digunakan di backend FastAPI nanti
with open('models/scaler.pkl', 'wb') as file:
    pickle.dump(scaler, file)

# 5. Cek hasil akhir
print("\nCuplikan 5 baris pertama data yang sudah dinormalisasi (Rentang 0.0 - 1.0):")
print(df_scaled[['Cycle_ID', 'RUL'] + fitur_x].head())

df_scaled.to_csv('data/processed/simulated_toren_data_scaled.csv', index=False)