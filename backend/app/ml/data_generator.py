import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv('./data/raw/water_potability.csv')
# Ambil kolom yang dibutuhkan (Potability tetap diambil untuk acuan label kotor)
df_filtered = df[['ph', 'Solids', 'Turbidity', 'Potability']].dropna()

# Simulasi suhu air toren di Indonesia (berkisar antara 24°C hingga 32°C)
# Kita tambahkan sedikit variasi acak (noise)
total_rows = len(df_filtered)
df_filtered['Temperature'] = np.random.uniform(24.0, 32.0, size=total_rows)

# Pisahkan data air bersih dan kotor
df_bersih = df_filtered[df_filtered['Potability'] == 1].copy()
df_kotor = df_filtered[df_filtered['Potability'] == 0].copy()

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
    sampel_bersih = df_bersih.sample(n=HARI_BERSIH).sort_values(by=['Turbidity', 'Solids'])
    sampel_kotor = df_kotor.sample(n=HARI_KOTOR).sort_values(by=['Turbidity', 'Solids'])
    
    # Gabungkan data bersih dan kotor menjadi 1 rentang waktu (14 hari)
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

# Tampilkan 15 baris pertama (Siklus 1 utuh + 1 hari dari Siklus 2)
print(df_timeseries.head(15))

df_timeseries.to_csv('./data/processed/simulated_toren_data.csv', index=False)

print("Dataset berhasil disimpan menjadi 'simulated_toren_data.csv'")