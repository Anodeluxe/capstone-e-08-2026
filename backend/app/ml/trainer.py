import pandas as pd
import numpy as np
import joblib
import os
from xgboost import XGBRegressor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input, GRU, Dense, Dropout

print("1. Memuat Dataset Time-Series Realistis...")
# Pastikan membaca file yang baru saja digenerate
df = pd.read_csv('./data/processed/data_toren_v2.csv')

fitur_x = [
    'ph', 'tds', 'turbidity', 'temperature',
    'turbidity_MA_3', 'tds_MA_3', 'ph_MA_3',
    'turbidity_Diff', 'tds_Diff', 'ph_Diff',
    'turbidity_Std_3', 'tds_Std_3'
]

# RUL Capping (Teknik Industri): Memotong RUL maksimal di 60 hari
y_all = np.clip(df['RUL'].values, a_min=0, a_max=60)
X_all = df[fitur_x].values

# ==========================================
# 2. PERSIAPAN DATA GRU (Sliding Window)
# ==========================================
# DINAIKKAN MENJADI 10 HARI agar AI bisa melihat tren dengan lebih jelas
window_size = 10 

def create_sequences(data, target, window):
    X_seq, y_seq = [], []
    for i in range(len(data) - window):
        X_seq.append(data[i:(i + window)])
        y_seq.append(target[i + window])
    return np.array(X_seq), np.array(y_seq)

X_gru, y_gru = create_sequences(X_all, y_all, window_size)

# Untuk XGBoost, kita ratakan datanya (2D) dengan mengambil baris hari terakhir dari setiap window
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
model_xgb = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
model_xgb.fit(X_xgb, y_xgb)

joblib.dump(model_xgb, 'models/xgb_model4.pkl')
print("-> Model XGBoost berhasil disimpan!")

# ==========================================
# 4. TRAINING GRU (Arsitektur Anti-Overfitting)
# ==========================================
print("\nMulai melatih GRU (Estimasi waktu: 1-2 Menit)...")
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
model_gru.fit(X_gru, y_gru, epochs=20, batch_size=64, validation_split=0.2)

model_gru.save('models/gru_model4.keras')
print("-> Model GRU berhasil disimpan!")

print("\n" + "="*50)
print("TRAINING SELESAI!")
print("Sekarang Anda memiliki AI yang jauh lebih cerdas dan realistis.")
print("="*50)