import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import time
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense

# 1. Load Data dari Input Kaggle
# Sesuaikan nama folder dengan nama dataset yang Anda buat di Kaggle
DATA_PATH = "/kaggle/input/toren-water-quality/simulated_toren_data.csv"
df = pd.read_csv(DATA_PATH)

X = df[['ph', 'Solids', 'Turbidity', 'Suhu']].values
y = df['RUL'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ==========================================
# EXPERIMEN 1: XGBOOST (Tabular Approach)
# ==========================================
print("Memulai Training XGBoost...")
start_xgb = time.time()
model_xgb = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
model_xgb.fit(X_train, y_train)
xgb_time = time.time() - start_xgb

pred_xgb = model_xgb.predict(X_test)
rmse_xgb = np.sqrt(mean_squared_error(y_test, pred_xgb))
joblib.dump(model_xgb, 'xgb_model.pkl') # Simpan output pkl
print(f"XGBoost Selesai! RMSE: {rmse_xgb:.2f}, Waktu: {xgb_time:.2f}s\n")

# ==========================================
# EXPERIMEN 2: GRU (Time-Series Sequence Approach)
# ==========================================
print("Memulai Training GRU...")
# GRU membutuhkan format input 3D: [samples, timesteps, features]
# Untuk prototipe awal, kita reshape seolah-olah timesteps = 1
X_train_3d = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
X_test_3d = X_test.reshape((X_test.shape[0], 1, X_test.shape[1]))

start_gru = time.time()
model_gru = Sequential([
    GRU(64, activation='relu', input_shape=(1, 4), return_sequences=False),
    Dense(32, activation='relu'),
    Dense(1) # Output nilai RUL kontinu
])
model_gru.compile(optimizer='adam', loss='mse')
model_gru.fit(X_train_3d, y_train, epochs=50, batch_size=32, verbose=0)
gru_time = time.time() - start_gru

pred_gru = model_gru.predict(X_test_3d)
rmse_gru = np.sqrt(mean_squared_error(y_test, pred_gru))
model_gru.save('gru_model.h5') # Simpan output h5
print(f"GRU Selesai! RMSE: {rmse_gru:.2f}, Waktu: {gru_time:.2f}s")