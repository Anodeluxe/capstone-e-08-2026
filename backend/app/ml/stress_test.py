import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model
import pickle
import os

print("Memulai Simulasi Sabotase Sensor (Stress Test)...")

# Deteksi lokasi file secara otomatis
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

path_data = os.path.join(BASE_DIR, 'data_testing_baru.csv')
path_scaler = os.path.join(BASE_DIR, 'models', 'scaler.pkl')
path_xgb = os.path.join(BASE_DIR, 'models', 'xgb_model3.pkl')
path_gru = os.path.join(BASE_DIR, 'models', 'gru_model3.keras')

# Load Data dan Model
df = pd.read_csv(path_data)
with open(path_scaler, 'rb') as file:
    scaler = pickle.load(file)
model_xgb = joblib.load(path_xgb)
model_gru = load_model(path_gru)

fitur_x = [
    'ph', 'Solids', 'Turbidity', 'Temperature',
    'Turbidity_MA_3', 'Solids_MA_3', 'ph_MA_3',
    'Turbidity_Diff', 'Solids_Diff', 'ph_Diff',
    'Turbidity_Std_3', 'Solids_Std_3'
]

# ==========================================
# 1. AMBIL KONDISI NORMAL 
# (Kita uji di Hari ke-20, saat air masih cukup bersih)
# ==========================================
hari_test = 20
window_size = 5
idx_akhir = hari_test
idx_awal = hari_test - window_size

X_normal_raw = df.iloc[idx_awal:idx_akhir][fitur_x].copy()
X_normal_scaled = scaler.transform(X_normal_raw.values)

# Prediksi Normal GRU (3D Array)
X_gru_3d_normal = X_normal_scaled.reshape((1, window_size, len(fitur_x)))
rul_gru_normal = model_gru.predict(X_gru_3d_normal, verbose=0)[0][0]

# Prediksi Normal XGBoost (Hanya butuh 1 baris terakhir)
X_xgb_normal = X_normal_scaled[-1].reshape(1, -1)
rul_xgb_normal = model_xgb.predict(X_xgb_normal)[0]


# ==========================================
# 2. LAKUKAN SABOTASE SENSOR
# ==========================================
X_sabotase_raw = X_normal_raw.copy()

# Kita kalikan kekeruhan 5x lipat dan kepadatan 3x lipat tepat di Hari ke-20
idx_turbidity = X_sabotase_raw.columns.get_loc('Turbidity')
idx_solids = X_sabotase_raw.columns.get_loc('Solids')

X_sabotase_raw.iloc[-1, idx_turbidity] *= 5.0 
X_sabotase_raw.iloc[-1, idx_solids] *= 3.0

X_sabotase_scaled = scaler.transform(X_sabotase_raw.values)

# Prediksi Setelah Sabotase GRU
X_gru_3d_sabotase = X_sabotase_scaled.reshape((1, window_size, len(fitur_x)))
rul_gru_sabotase = model_gru.predict(X_gru_3d_sabotase, verbose=0)[0][0]

# Prediksi Setelah Sabotase XGBoost
X_xgb_sabotase = X_sabotase_scaled[-1].reshape(1, -1)
rul_xgb_sabotase = model_xgb.predict(X_xgb_sabotase)[0]


# ==========================================
# 3. CETAK BUKTI VALIDASI
# ==========================================
print("\n" + "="*60)
print(f"HASIL UJI SABOTASE DI HARI KE-{hari_test} (RUL ASLI: {df.iloc[idx_akhir-1]['RUL']:.1f} Hari)")
print("="*60)

print("[ MODEL GRU ]")
print(f"Kondisi Air Normal : RUL ditebak {rul_gru_normal:.1f} Hari")
print(f"Kondisi Disabotase : RUL turun menjadi {rul_gru_sabotase:.1f} Hari")
print("-" * 60)

print("[ MODEL XGBOOST ]")
print(f"Kondisi Air Normal : RUL ditebak {rul_xgb_normal:.1f} Hari")
print(f"Kondisi Disabotase : RUL turun menjadi {rul_xgb_sabotase:.1f} Hari")
print("="*60)
print("Kesimpulan: Jika angka RUL pada kondisi sabotase anjlok drastis,")
print("maka AI Anda terbukti membaca kualitas air, bukan sekadar menghitung kalender!")