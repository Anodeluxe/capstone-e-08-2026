"""Train the production-oriented XGBoost v3 RUL model.

The model predicts uncapped RUL to the sustained early-warning event
(24-hour rolling mean score <= 80).  The UI only shows RUL when the
prediction is inside the 30-day action window; above that it shows the
water score.  A dedicated 30-day gate metric measures that decision.
"""

import gc
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import xgboost
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBRegressor


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_toren_hourly_v3.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "xgb_model_v3.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "xgb_model_v3.json")

MAX_RUL_HOURS = 120 * 24  # batas fisik siklus; target tidak di-cap ke 30 hari
ACTIONABLE_HOURS = 30 * 24  # ambang tampil RUL di UI
EWS_HOURS = 10 * 24  # ambang peringatan dini
MIN_HISTORY_HOURS = 72  # butuh lag 72 jam; baris awal dibuang
TEST_SIZE = 0.2
RANDOM_STATE = 42

# Kolom CSV v3 (nama ringkas; di-rename ke nama fitur model di build_features).
DATASET_COLUMNS = [
    "Cycle_ID", "Jam", "RUL", "elapsed_hours",
    "ph", "tds", "turbidity", "temperature",
    "score_overall",
]

# Lean A: 17 fitur, history maksimum 72 jam.
FEATURE_COLUMNS = [
    "elapsed_hours", "ph_raw", "tds_raw", "turbidity_raw", "temperature_raw",
    "score_overall", "score_drop_24", "score_drop_72",
    "score_MA_24", "score_STD_24",
    "turbidity_raw_drop24", "tds_raw_drop24", "ph_raw_drop24",
    "turbidity_raw_drop72", "tds_raw_drop72", "ph_raw_drop72",
    "hour_of_day",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build causal features and reset history at every Cycle_ID boundary."""
    out = df.rename(columns={
        "ph": "ph_raw", "tds": "tds_raw",
        "turbidity": "turbidity_raw", "temperature": "temperature_raw",
    }).sort_values(["Cycle_ID", "Jam"]).copy()
    grouped = out.groupby("Cycle_ID", sort=False)
    out["hour_of_day"] = out["Jam"] % 24

    for lag in (24, 72):
        out[f"score_drop_{lag}"] = grouped["score_overall"].diff(lag)

    out["score_MA_24"] = grouped["score_overall"].transform(
        lambda values: values.rolling(24, min_periods=1).mean()
    )
    out["score_STD_24"] = grouped["score_overall"].transform(
        lambda values: values.rolling(24, min_periods=1).std()
    )

    for column in ("turbidity_raw", "tds_raw", "ph_raw"):
        out[f"{column}_drop24"] = grouped[column].diff(24)
        out[f"{column}_drop72"] = grouped[column].diff(72)

    history_columns = [col for col in FEATURE_COLUMNS if col not in {
        "elapsed_hours", "ph_raw", "tds_raw", "turbidity_raw",
        "temperature_raw", "score_overall", "hour_of_day",
    }]
    out[history_columns] = out[history_columns].fillna(0.0)
    return out


def _evaluate(y_true: np.ndarray, y_pred: np.ndarray, mask: np.ndarray) -> dict:
    """Hitung metrik regresi pada subset baris test yang dipilih `mask`."""
    yt = y_true[mask]
    yp = y_pred[mask]
    mae_hours = float(mean_absolute_error(yt, yp))
    return {
        "n": int(mask.sum()),
        "r2": float(r2_score(yt, yp)),
        "mae_hours": mae_hours,
        "mae_days": mae_hours / 24.0,
        "rmse_hours": float(np.sqrt(mean_squared_error(yt, yp))),
    }


def _gate_30d(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Kualitas keputusan tampil-RUL vs tampil-skor pada ambang 30 hari."""
    true_pos = y_true <= ACTIONABLE_HOURS
    pred_pos = y_pred <= ACTIONABLE_HOURS
    tp = int(np.sum(true_pos & pred_pos))
    fp = int(np.sum(~true_pos & pred_pos))
    fn = int(np.sum(true_pos & ~pred_pos))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "true_pos": tp,
        "false_pos": fp,
        "false_neg": fn,
    }


def main() -> None:
    print("Loading v3 dataset...")
    header = pd.read_csv(DATA_PATH, nrows=0).columns
    if any(col.endswith("_raw") for col in header):
        raise ValueError(
            "Dataset v3 masih skema lama (19 kolom); regenerate dulu: "
            "python app/ml/data_generator_hourly.py"
        )
    df = pd.read_csv(DATA_PATH, usecols=DATASET_COLUMNS)
    print(f"Rows: {len(df):,} | Cycles: {df['Cycle_ID'].nunique():,}")
    print(f"RUL range: {df['RUL'].min():.0f} - {df['RUL'].max():.0f} hours")

    features = build_features(df)
    del df
    gc.collect()

    # Baris dengan history < 72 jam tidak tersedia di produksi.
    features = features[features["Jam"] > MIN_HISTORY_HOURS].reset_index(drop=True)
    print(f"Rows after {MIN_HISTORY_HOURS}h warm-up: {len(features):,}")

    X = features[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    rul_raw = features["RUL"].to_numpy(dtype=np.float32)
    groups = features["Cycle_ID"].to_numpy()
    y = np.clip(rul_raw, 0.0, MAX_RUL_HOURS)
    del features
    gc.collect()

    # Split berdasarkan siklus, bukan baris, agar tidak ada leakage antar siklus.
    splitter = GroupShuffleSplit(
        n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    train_cycles = np.unique(groups[train_idx])
    test_cycles = np.unique(groups[test_idx])
    assert not set(train_cycles).intersection(test_cycles), "Cycle leakage terdeteksi!"

    print(
        f"Split by Cycle_ID: train={len(train_cycles)} cycles "
        f"({len(train_idx):,} rows) | test={len(test_cycles)} cycles "
        f"({len(test_idx):,} rows)"
    )

    # Fokuskan model ke horizon yang benar-benar ditampilkan.
    raw_train = rul_raw[train_idx]
    train_weights = np.ones(len(train_idx), dtype=np.float32)
    train_weights[raw_train <= EWS_HOURS] = 3.0
    train_weights[
        (raw_train > EWS_HOURS) & (raw_train <= ACTIONABLE_HOURS)
    ] = 2.0

    model = XGBRegressor(
        n_estimators=600,
        learning_rate=0.03,
        max_depth=11,
        min_child_weight=1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        tree_method="hist",
        objective="reg:squarederror",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    print(
        f"Training {len(train_idx):,} rows with "
        f"{len(FEATURE_COLUMNS)} causal features..."
    )
    model.fit(X[train_idx], y[train_idx], sample_weight=train_weights)

    print("Evaluating on holdout cycles...")
    pred = np.clip(model.predict(X[test_idx]), 0.0, MAX_RUL_HOURS)
    y_test = y[test_idx]
    raw_test = rul_raw[test_idx]

    metrics_all = _evaluate(y_test, pred, np.ones_like(raw_test, dtype=bool))
    metrics_30d = _evaluate(y_test, pred, raw_test <= ACTIONABLE_HOURS)
    metrics_ews = _evaluate(y_test, pred, raw_test <= EWS_HOURS)
    gate = _gate_30d(raw_test, pred)

    metrics = {
        # Angka utama yang dibaca dashboard sebagai "Kepercayaan".
        "r2": metrics_30d["r2"],
        "mae_hours": metrics_30d["mae_hours"],
        "mae_days": metrics_30d["mae_days"],
        "rmse_hours": metrics_30d["rmse_hours"],
        "r2_30d": metrics_30d["r2"],
        "mae_days_30d": metrics_30d["mae_days"],
        "r2_all": metrics_all["r2"],
        "mae_days_all": metrics_all["mae_days"],
        "r2_ews": metrics_ews["r2"],
        "mae_days_ews": metrics_ews["mae_days"],
        "gate_30d_precision": gate["precision"],
        "gate_30d_recall": gate["recall"],
        "gate_30d_f1": gate["f1"],
        "gate_30d_true_pos": gate["true_pos"],
        "gate_30d_false_pos": gate["false_pos"],
        "gate_30d_false_neg": gate["false_neg"],
        "n_test_rows": int(len(test_idx)),
        "n_test_30d": metrics_30d["n"],
        "n_test_ews": metrics_ews["n"],
        "n_train_cycles": int(len(train_cycles)),
        "n_test_cycles": int(len(test_cycles)),
        "split": "GroupShuffleSplit 80/20 by Cycle_ID",
        "random_state": RANDOM_STATE,
        "confidence_definition": (
            "Holdout R2 on uncapped true RUL: "
            f"r2_ews for RUL <= {EWS_HOURS:.0f}h, "
            f"r2_30d for RUL <= {ACTIONABLE_HOURS:.0f}h"
        ),
        "xgboost_version": xgboost.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "target_cap_hours": MAX_RUL_HOURS,
        "actionable_hours": ACTIONABLE_HOURS,
        "sustain_hours": 24,
        "min_history_hours": MIN_HISTORY_HOURS,
        "model_name": "xgb_v3_lean_30d",
        "score_threshold": 80.0,
        "training_dataset": "data_toren_hourly_v3.csv",
        "feature_version": "v3_lean_30d",
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH)
    with open(METADATA_PATH, "w", encoding="ascii") as handle:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, handle, indent=2)

    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metadata: {METADATA_PATH}")
    print(f"Target: uncapped RUL (clipped at {MAX_RUL_HOURS} hours)")
    print("Metrics (holdout cycles):")
    print(f"  all rows        : R2={metrics_all['r2']:.4f} "
          f"MAE={metrics_all['mae_days']:.2f} hari "
          f"(n={metrics_all['n']:,})")
    print(f"  actionable <=30d: R2={metrics_30d['r2']:.4f} "
          f"MAE={metrics_30d['mae_days']:.2f} hari "
          f"(n={metrics_30d['n']:,})")
    print(f"  EWS <=10d       : R2={metrics_ews['r2']:.4f} "
          f"MAE={metrics_ews['mae_days']:.2f} hari "
          f"(n={metrics_ews['n']:,})")
    print(f"  gate <=30d      : precision={gate['precision']:.3f} "
          f"recall={gate['recall']:.3f} f1={gate['f1']:.3f}")


if __name__ == "__main__":
    main()
