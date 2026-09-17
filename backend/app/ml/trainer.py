import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBRegressor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, GRU, Dense, Dropout

print("1. Memuat Dataset Time-Series (Granularity: Per Jam)...")
# Membaca file hasil generate dari data_generator_hourly.py
df = pd.read_csv('./data/processed/data_toren_hourly.csv')

fitur_x = [
    'elapsed_hours', 'ph', 'tds', 'turbidity', 'temperature',
    'ph_MA_24', 'tds_MA_24', 'turbidity_MA_24'
]

# RUL Capping: memotong RUL maksimal di 2880 jam (120 hari)
y_all = np.clip(df['RUL'].values, a_min=0, a_max=2880)
X_all = df[fitur_x].values

# ==========================================
# 2. PERSIAPAN DATA GRU (Sliding Window)
# ==========================================
# Window size 10 jam agar AI bisa melihat tren dalam 10 jam terakhir
window_size = 10 

def create_sequences(data, target, window):
    X_seq, y_seq = [], []
    for i in range(len(data) - window):
        X_seq.append(data[i:(i + window)])
        y_seq.append(target[i + window])
    return np.array(X_seq), np.array(y_seq)

X_gru, y_gru = create_sequences(X_all, y_all, window_size)

# Subsampling untuk GRU: ambil setiap 3 baris (data 2.5M terlalu besar)
# agar training lebih cepat tanpa mengubah distribusi siklus.
X_gru = X_gru[::3]
y_gru = y_gru[::3]

# Untuk XGBoost, kita ratakan datanya (2D) dengan mengambil baris terakhir dari setiap window
X_xgb = X_all[window_size:]
y_xgb = y_all[window_size:]

print(f"Bentuk Input GRU     : {X_gru.shape}")
print(f"Bentuk Input XGBoost : {X_xgb.shape}")

# Membuat folder models jika belum ada
os.makedirs('models', exist_ok=True)

# ==========================================
# 3. TRAINING XGBOOST
# ==========================================
print("\nMulai melatih XGBoost...")
model_xgb = XGBRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
)
model_xgb.fit(X_xgb, y_xgb)

joblib.dump(model_xgb, 'models/xgb_model_hourly.pkl')
print("-> Model XGBoost berhasil disimpan!")

# ==========================================
# 4. TRAINING GRU (Arsitektur Anti-Overfitting)
# ==========================================
print("\nMulai melatih GRU (Estimasi waktu: 5-15 Menit)...")
model_gru = Sequential([
    Input(shape=(window_size, len(fitur_x))),
    
    # Layer 1 dengan Dropout untuk mencegah hafalan buta
    GRU(64, activation='relu', return_sequences=True),
    Dropout(0.2), 
    
    # Layer 2
    GRU(32, activation='relu'),
    Dropout(0.2),
    
    # Layer Output
    Dense(16, activation='relu'),
    Dense(1)
])

model_gru.compile(optimizer='adam', loss='mse', metrics=['mae'])

# Proses Training (20 Epoch)
# Kita pakai validation_split 0.2 untuk melihat nilai loss/mae pada data tes internal
model_gru.fit(X_gru, y_gru, epochs=20, batch_size=1024, validation_split=0.2)

model_gru.save('models/gru_model_hourly.keras')
print("-> Model GRU berhasil disimpan!")

print("\n" + "="*50)
print("TRAINING SELESAI!")
print("Model tersimpan:")
print("  - models/xgb_model_hourly.pkl  (XGBoost)")
print("  - models/gru_model_hourly.keras (GRU)")
print("="*50)
print("\nLangkah selanjutnya: jalankan 'python evaluate_model.py'")