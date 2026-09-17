"""
Model Evaluator — Granularitas Per Jam
───────────────────────────────────────
Evaluasi akurasi model XGBoost dan GRU dengan train/test split
berdasarkan CYCLE (bukan random) untuk mencegah data leakage.

Metrik:
  - MAE  (Mean Absolute Error)
  - RMSE (Root Mean Squared Error)
  - R²   (Coefficient of Determination)
  - Asymmetric Error (penalti 2x untuk over-prediction)

Cara pakai:
  1. Jalankan data_generator_hourly.py dulu
  2. Jalankan trainer.py dulu
  3. Jalankan script ini: python evaluate_model.py
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os

print("=" * 60)
print("MODEL EVALUATOR — GRANULARITAS PER JAM")
print("=" * 60)

# ==========================================
# 1. LOAD DATA
# ==========================================
print("\n1. Memuat data...")

data_path = './data/processed/data_toren_hourly.csv'
if not os.path.exists(data_path):
    print(f"   ERROR: File '{data_path}' tidak ditemukan!")
    print("   Jalankan 'python data_generator_hourly.py' terlebih dahulu.")
    exit(1)

df = pd.read_csv(data_path)
print(f"   Total baris: {len(df)}")
print(f"   Total siklus: {df['Cycle_ID'].nunique()}")

fitur_x = [
    'elapsed_hours', 'ph', 'tds', 'turbidity', 'temperature',
    'ph_MA_24', 'tds_MA_24', 'turbidity_MA_24'
]

# RUL cap harus sama dengan saat training (2880 jam = 120 hari)
y_all = np.clip(df['RUL'].values, a_min=0, a_max=2880)
X_all = df[fitur_x].values

# ==========================================
# 2. TRAIN/TEST SPLIT BY CYCLE
# ==========================================
print("\n2. Memisahkan data train/test (80/20 by cycle)...")

all_cycles = df['Cycle_ID'].unique()
np.random.seed(42)
np.random.shuffle(all_cycles)

split_idx = int(len(all_cycles) * 0.8)
train_cycles = all_cycles[:split_idx]
test_cycles = all_cycles[split_idx:]

print(f"   Train: {len(train_cycles)} siklus")
print(f"   Test : {len(test_cycles)} siklus")

# Split data berdasarkan cycle
train_mask = df['Cycle_ID'].isin(train_cycles)
test_mask = df['Cycle_ID'].isin(test_cycles)

X_train, y_train = X_all[train_mask], y_all[train_mask]
X_test, y_test = X_all[test_mask], y_all[test_mask]

print(f"   Train samples: {len(X_train)}")
print(f"   Test samples : {len(X_test)}")

# ==========================================
# 3. LOAD MODELS
# ==========================================
print("\n3. Memuat model...")

model_xgb_path = 'models/xgb_model_hourly.pkl'
model_gru_path = 'models/gru_model_hourly.keras'

if not os.path.exists(model_xgb_path):
    print(f"   ERROR: File '{model_xgb_path}' tidak ditemukan!")
    print("   Jalankan 'python trainer.py' terlebih dahulu.")
    exit(1)

model_xgb = joblib.load(model_xgb_path)
print(f"   ✓ XGBoost loaded dari {model_xgb_path}")

model_gru = None
if os.path.exists(model_gru_path):
    from tensorflow.keras.models import load_model
    model_gru = load_model(model_gru_path)
    print(f"   ✓ GRU loaded dari {model_gru_path}")
else:
    print(f"   ⚠ GRU tidak ditemukan di {model_gru_path}, skip evaluasi GRU")

# ==========================================
# 4. PREDIKSI
# ==========================================
print("\n4. Menghitung prediksi...")

pred_xgb = model_xgb.predict(X_test)

pred_gru = None
y_gru_test = None
if model_gru is not None:
    # GRU butuh sliding window
    window_size = 10

    def create_sequences(data, target, window):
        X_seq, y_seq = [], []
        for i in range(len(data) - window):
            X_seq.append(data[i:(i + window)])
            y_seq.append(target[i + window])
        return np.array(X_seq), np.array(y_seq)

    # Buat sequence dari test data saja
    X_gru_test, y_gru_test = create_sequences(X_test, y_test, window_size)
    pred_gru = model_gru.predict(X_gru_test, verbose=0).flatten()

# ==========================================
# 5. HITUNG METRIK
# ==========================================
print("\n" + "=" * 60)
print("HASIL EVALUASI (PADA DATA TEST SAJA)")
print("=" * 60)

def asymmetric_error(y_true, y_pred):
    """Penalti 2x jika over-prediction (prediksi > aktual = bahaya)."""
    errors = y_pred - y_true
    penalties = np.where(errors > 0, errors**2 * 2.0, errors**2)
    return np.mean(penalties)

def print_metrics(name, y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    asym = asymmetric_error(y_true, y_pred)

    print(f"\n[ {name} ]")
    print(f"  MAE  (rata-rata meleset)  : {mae:.2f} jam ({mae / 24:.2f} hari)")
    print(f"  RMSE (penalti meleset)    : {rmse:.2f} jam ({rmse / 24:.2f} hari)")
    print(f"  R²   (akurasi fit)        : {r2:.4f}")
    print(f"  Asymmetric Error          : {asym:.2f}")
    print(f"  Over-prediction rate      : {np.mean(y_pred > y_true) * 100:.1f}%")
    print(f"  Under-prediction rate     : {np.mean(y_pred < y_true) * 100:.1f}%")
    return {'mae': mae, 'rmse': rmse, 'r2': r2, 'asym': asym}

metrics_xgb = print_metrics("XGBoost", y_test, pred_xgb)

metrics_gru = None
if pred_gru is not None:
    metrics_gru = print_metrics("GRU", y_gru_test, pred_gru)

# ==========================================
# 6. REKOMENDASI
# ==========================================
print("\n" + "=" * 60)
print("REKOMENDASI")
print("=" * 60)

# Bandingkan XGBoost vs GRU
if metrics_gru is not None:
    if metrics_xgb['mae'] < metrics_gru['mae']:
        print("\n→ XGBoost memiliki MAE lebih rendah (lebih akurat).")
        best_mae = metrics_xgb['mae']
        best_model = "XGBoost"
    else:
        print("\n→ GRU memiliki MAE lebih rendah (lebih akurat).")
        best_mae = metrics_gru['mae']
        best_model = "GRU"
else:
    best_mae = metrics_xgb['mae']
    best_model = "XGBoost"

# Threshold akurasi (relative terhadap range RUL 0-2880 jam)
if best_mae < 72:
    print(f"✓ MAE < 72 jam (3 hari): SANGAT BAIK — model cukup akurat untuk produksi.")
elif best_mae < 144:
    print(f"✓ MAE < 144 jam (6 hari): CUKUP BAIK — model dapat digunakan dengan confidence.")
elif best_mae < 288:
    print(f"⚠ MAE {best_mae:.1f} jam ({best_mae / 24:.1f} hari): LUMAYAN — pertimbangkan untuk improving training data.")
else:
    print(f"✗ MAE {best_mae:.1f} jam ({best_mae / 24:.1f} hari): KURANG — perlu retrain dengan data lebih banyak atau fitur lebih baik.")

# Over-prediction check
over_pct = metrics_xgb.get('over_prediction_rate', 0)
if metrics_gru is not None:
    over_pct = max(over_pct, metrics_gru.get('over_prediction_rate', 0))

if over_pct > 60:
    print(f"⚠ Over-prediction rate tinggi ({over_pct:.1f}%) — model cenderung terlalu optimis.")
    print("  Pertimbangkan untuk menambah penalty pada over-prediction.")

print("\n" + "=" * 60)
print("EVALUASI SELESAI")
print("=" * 60)
