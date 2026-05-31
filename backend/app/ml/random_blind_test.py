import pandas as pd
import numpy as np
import pickle
import joblib
import os
from tensorflow.keras.models import load_model

print("1. Menyiapkan Data dan Mengacak Urutan Ujian...")

BASE_DIR = os.getcwd()
path_data = os.path.join(BASE_DIR, 'data_testing_baru.csv')
path_scaler = os.path.join(BASE_DIR, 'models', 'scaler.pkl')
path_xgb = os.path.join(BASE_DIR, 'models', 'xgb_model3.pkl')
path_gru = os.path.join(BASE_DIR, 'models', 'gru_model3.keras')

df = pd.read_csv(path_data)
fitur_x = [
    'ph', 'Solids', 'Turbidity', 'Temperature',
    'Turbidity_MA_3', 'Solids_MA_3', 'ph_MA_3',
    'Turbidity_Diff', 'Solids_Diff', 'ph_Diff',
    'Turbidity_Std_3', 'Solids_Std_3'
]

# Load Scaler & Model
with open(path_scaler, 'rb') as file:
    scaler = pickle.load(file)
model_xgb = joblib.load(path_xgb)
model_gru = load_model(path_gru)

window_size = 5

# Normalisasi Seluruh Data Historis
X_full_raw = df[fitur_x].values
X_full_scaled = scaler.transform(X_full_raw)
y_full_true = df['RUL'].values

# ==========================================
# MEMILIH 5 HARI SECARA ACAK UNTUK UJI BUTA
# ==========================================
# Kita pilih index acak dari rentang hari yang valid (setelah window 5 hari terbentuk)
np.random.seed(None) # Biarkan benar-benar acak setiap kali di-run
hari_acak = np.random.choice(range(window_size, len(df)), size=5, replace=False)

print("\n" + "="*50)
print("HASIL RANDOM BLIND TEST (Menguji AI Tanpa Urutan)")
print("="*50)

for hari in hari_acak:
    idx_akhir = hari
    idx_awal = hari - window_size
    
    # Ambil potongan data (Memori) untuk hari acak ini
    X_gru_3d = X_full_scaled[idx_awal:idx_akhir].reshape((1, window_size, len(fitur_x)))
    X_xgb_scaled = X_full_scaled[idx_akhir-1:idx_akhir]
    
    # Kunci Jawaban
    true_rul = y_full_true[idx_akhir-1]
    
    # Tebakan AI
    pred_gru = model_gru.predict(X_gru_3d, verbose=0)[0][0]
    pred_xgb = model_xgb.predict(X_xgb_scaled)[0]
    
    # Cetak Hasilnya
    print(f"Menguji Data di Hari ke-{hari} (RUL Asli: {true_rul:.1f} Hari)")
    print(f" -> Tebakan XGBoost : {pred_xgb:.1f} Hari")
    print(f" -> Tebakan GRU     : {pred_gru:.1f} Hari")
    print("-" * 50)