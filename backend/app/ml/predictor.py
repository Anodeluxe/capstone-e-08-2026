import pandas as pd
import numpy as np
import pickle
import joblib
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_squared_error, mean_absolute_error
import os

# ==========================================
# FUNGSI EVALUASI CUSTOM
# ==========================================
def asymmetric_error(y_true, y_pred):
    """
    Memberikan penalti 2x lipat lebih besar jika AI menebak RUL lebih tinggi 
    dari aslinya (Telat menguras = Bahaya).
    """
    errors = y_pred.flatten() - y_true.flatten()
    # Jika errors > 0 (Prediksi > Asli), kuadratkan lalu kalikan 2
    penalties = np.where(errors > 0, errors**2 * 2.0, errors**2)
    return np.mean(penalties)

def create_sequences(X, y, time_steps):
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i:(i + time_steps)])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)

print("1. Memuat Dataset Ujian dan Tools Machine Learning...")

# 1. Load Data Mentah
df_test = pd.read_csv('./data_testing_baru.csv')

fitur_x = [
    'ph', 'Solids', 'Turbidity', 'Temperature',
    'Turbidity_MA_3', 'Solids_MA_3', 'ph_MA_3',
    'Turbidity_Diff', 'Solids_Diff', 'ph_Diff',
    'Turbidity_Std_3', 'Solids_Std_3'
]

X_raw = df_test[fitur_x].values
y_true = df_test['RUL'].values

# 2. Load Scaler & Models
# Pastikan path ini sesuai dengan struktur folder Anda
try:
    with open('models/scaler.pkl', 'rb') as file:
        scaler = pickle.load(file)
    model_xgb = joblib.load('models/xgb_model2.pkl')
    model_gru = load_model('models/gru_model2.keras')
except Exception as e:
    print(f"Error memuat file: {e}")
    print("Pastikan Anda sudah meletakkan scaler.pkl, xgb_model2.pkl, dan gru_model2.keras di dalam folder 'models'.")
    exit()

# 3. Transformasi Data (Menggunakan Scaler yang sudah punya "ingatan")
# PENTING: Gunakan .transform(), BUKAN .fit_transform()
X_scaled = scaler.transform(X_raw)

print("2. Proses Prediksi Dimulai...\n")
print("-" * 50)

# ==========================================
# PENGUJIAN XGBOOST (Pendekatan Tabular)
# ==========================================
pred_xgb = model_xgb.predict(X_scaled)

rmse_xgb = np.sqrt(mean_squared_error(y_true, pred_xgb))
mae_xgb = mean_absolute_error(y_true, pred_xgb)
asym_xgb = asymmetric_error(y_true, pred_xgb)

print("HASIL EVALUASI XGBOOST:")
print(f"RMSE             : {rmse_xgb:.2f} hari")
print(f"MAE              : {mae_xgb:.2f} hari")
print(f"Asymmetric Error : {asym_xgb:.2f} (Semakin kecil semakin aman)")
print("-" * 50)

# ==========================================
# PENGUJIAN GRU (Pendekatan Sequence)
# ==========================================
# GRU butuh potongan waktu 5 hari (harus sama dengan saat training)
TIMESTEPS = 5
X_gru, y_true_gru = create_sequences(X_scaled, y_true, TIMESTEPS)

# Proses Prediksi
pred_gru = model_gru.predict(X_gru, verbose=0)

rmse_gru = np.sqrt(mean_squared_error(y_true_gru, pred_gru))
mae_gru = mean_absolute_error(y_true_gru, pred_gru)
asym_gru = asymmetric_error(y_true_gru, pred_gru)

print("HASIL EVALUASI GRU:")
print(f"RMSE             : {rmse_gru:.2f} hari")
print(f"MAE              : {mae_gru:.2f} hari")
print(f"Asymmetric Error : {asym_gru:.2f} (Semakin kecil semakin aman)")
print("-" * 50)

# Kesimpulan Cepat
print("\nKESIMPULAN:")
if mae_gru < mae_xgb:
    print("-> GRU terbukti lebih akurat dalam membaca data harian murni (MAE lebih kecil).")
else:
    print("-> XGBoost ternyata lebih tangguh menghadapi dataset yang benar-benar asing (MAE lebih kecil).")