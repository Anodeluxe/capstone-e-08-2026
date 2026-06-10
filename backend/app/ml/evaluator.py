import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os

print("1. Memuat Data dan Model untuk Evaluasi...")

# Load Data dengan path terbaru
df = pd.read_csv('./data/processed/data_toren_v2.csv')

# Nama kolom terbaru (Solids -> tds, Turbidity -> turbidity, dll)
fitur_x = [
    'ph', 'tds', 'turbidity', 'temperature',
    'turbidity_MA_3', 'tds_MA_3', 'ph_MA_3',
    'turbidity_Diff', 'tds_Diff', 'ph_Diff',
    'turbidity_Std_3', 'tds_Std_3'
]

# Kunci Jawaban dengan RUL Capping yang sama (Maks 60 Hari)
y_all = np.clip(df['RUL'].values, a_min=0, a_max=60)
X_all = df[fitur_x].values

# Memuat Model
model_xgb = joblib.load('models/xgb_model4.pkl')
model_gru = load_model('models/gru_model4.keras')

# ==========================================
# 2. PERSIAPAN DATA (Harus sama dengan saat Training)
# ==========================================
# Ingat: Kita menggunakan window_size 10 di training terbaru
window_size = 10 

def create_sequences(data, target, window):
    X_seq, y_seq = [], []
    for i in range(len(data) - window):
        X_seq.append(data[i:(i + window)])
        y_seq.append(target[i + window])
    return np.array(X_seq), np.array(y_seq)

X_gru, y_gru = create_sequences(X_all, y_all, window_size)

# XGBoost menggunakan bentuk 2D
X_xgb = X_all[window_size:]
y_xgb = y_all[window_size:]

print("2. Menghitung Prediksi...")
# Melakukan prediksi keseluruhan
pred_xgb = model_xgb.predict(X_xgb)
pred_gru = model_gru.predict(X_gru, verbose=0).flatten() 

# ==========================================
# 3. MENGHITUNG METRIK EVALUASI
# ==========================================
print("\n" + "="*50)
print("LAPORAN EVALUASI PERFORMA AI (METRIK REGRESI)")
print("="*50)

# Evaluasi XGBoost
mae_xgb = mean_absolute_error(y_xgb, pred_xgb)
rmse_xgb = np.sqrt(mean_squared_error(y_xgb, pred_xgb))
r2_xgb = r2_score(y_xgb, pred_xgb)

print("[ MODEL XGBOOST ]")
print(f"MAE (Rata-rata Meleset) : {mae_xgb:.2f} Hari")
print(f"RMSE (Penalti Meleset)  : {rmse_xgb:.2f} Hari")
print(f"R2 Score (Akurasi Fit)  : {r2_xgb:.4f} (Mendekati 1.0 semakin baik)")
print("-" * 50)

# Evaluasi GRU
mae_gru = mean_absolute_error(y_gru, pred_gru)
rmse_gru = np.sqrt(mean_squared_error(y_gru, pred_gru))
r2_gru = r2_score(y_gru, pred_gru)

print("[ MODEL GRU ]")
print(f"MAE (Rata-rata Meleset) : {mae_gru:.2f} Hari")
print(f"RMSE (Penalti Meleset)  : {rmse_gru:.2f} Hari")
print(f"R2 Score (Akurasi Fit)  : {r2_gru:.4f} (Mendekati 1.0 semakin baik)")
print("="*50)

# Kesimpulan Otomatis
pemenang = "XGBoost" if mae_xgb < mae_gru else "GRU"
print(f"\nKesimpulan: Secara keseluruhan, model {pemenang} memiliki tingkat kesalahan (MAE) yang lebih rendah.")