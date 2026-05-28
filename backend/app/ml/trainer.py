import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import time
from sklearn.metrics import mean_squared_error
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Input

# 1. Load Data Final yang Sudah di-Scale
# Pastikan path ini sesuai dengan letak file CSV final Anda
DATA_PATH = "data/processed/simulated_toren_data_scaled.csv"
df = pd.read_csv(DATA_PATH)

print("Dataset berhasil dimuat!")

# 2. Pemisahan Data Berdasarkan Siklus (Bukan Random Split)
# Asumsi total 100 siklus: 80 untuk Train, 20 untuk Test
train_cycles = df[df['Cycle_ID'] <= 80]
test_cycles = df[df['Cycle_ID'] > 80]

# Tentukan semua fitur (selain RUL dan Cycle_ID)
fitur_x = [
    'ph', 'Solids', 'Turbidity', 'Temperature',
    'Turbidity_MA_3', 'Solids_MA_3', 'ph_MA_3',
    'Turbidity_Diff', 'Solids_Diff', 'ph_Diff',
    'Turbidity_Std_3', 'Solids_Std_3'
]

# Siapkan X dan y
X_train = train_cycles[fitur_x].values
y_train = train_cycles['RUL'].values

X_test = test_cycles[fitur_x].values
y_test = test_cycles['RUL'].values

# ==========================================
# EXPERIMEN 1: XGBOOST (Tabular Approach)
# ==========================================
print("\nMemulai Training XGBoost...")
start_xgb = time.time()
# Menambah sedikit kompleksitas parameter karena fitur lebih banyak
model_xgb = xgb.XGBRegressor(n_estimators=200, max_depth=7, learning_rate=0.05)
model_xgb.fit(X_train, y_train)
xgb_time = time.time() - start_xgb

pred_xgb = model_xgb.predict(X_test)
rmse_xgb = np.sqrt(mean_squared_error(y_test, pred_xgb))
joblib.dump(model_xgb, 'models/xgb_model.pkl') 
print(f"XGBoost Selesai! RMSE: {rmse_xgb:.2f} hari, Waktu: {xgb_time:.2f}s")

# ==========================================
# EXPERIMEN 2: GRU (Time-Series Sequence Approach)
# ==========================================
print("\nMemulai Training GRU...")
# GRU membutuhkan format input 3D: [samples, timesteps, features]
# Jumlah fitur sekarang adalah len(fitur_x) = 12
jumlah_fitur = len(fitur_x)
X_train_3d = X_train.reshape((X_train.shape[0], 1, jumlah_fitur))
X_test_3d = X_test.reshape((X_test.shape[0], 1, jumlah_fitur))

start_gru = time.time()
model_gru = Sequential([
    Input(shape=(1, jumlah_fitur)),  # Cara baru Keras untuk mendefinisikan input
    GRU(64, activation='relu', return_sequences=False),
    Dense(32, activation='relu'),
    Dense(1) # Output nilai RUL kontinu
])

# Mengurangi sedikit learning rate agar pembelajaran lebih halus
optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
model_gru.compile(optimizer=optimizer, loss='mse')

# Training model
model_gru.fit(X_train_3d, y_train, epochs=50, batch_size=32, verbose=0)
gru_time = time.time() - start_gru

pred_gru = model_gru.predict(X_test_3d, verbose=0)
rmse_gru = np.sqrt(mean_squared_error(y_test, pred_gru))
model_gru.save('models/gru_model.keras') # Disimpan menggunakan format .keras terbaru

print(f"GRU Selesai! RMSE: {rmse_gru:.2f} hari, Waktu: {gru_time:.2f}s")