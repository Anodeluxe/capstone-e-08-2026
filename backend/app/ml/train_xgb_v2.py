"""Train the production-oriented XGBoost v2 RUL model.

The application only needs an actionable early-warning horizon (30 days),
so targets above 720 hours are intentionally censored.  The feature set uses
only values available at prediction time: current sensor values, the current
production score, and causal history within the current drain cycle.
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
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_toren_hourly_v2.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "xgb_model_hourly_v2_horizon.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "xgb_model_hourly_v2_horizon.json")

TARGET_CAP_HOURS = 30 * 24
TEST_SIZE = 0.2
RANDOM_STATE = 42
EWS_HOURS = 10 * 24  # 10 hari — ambang peringatan dini

# Kolom CSV yang benar-benar dipakai (mengurangi memori saat load 469 MB).
DATASET_COLUMNS = [
    "Cycle_ID", "Jam", "RUL", "elapsed_hours",
    "ph", "tds", "turbidity", "temperature",
    "ph_raw", "tds_raw", "turbidity_raw", "temperature_raw",
    "score_overall",
]

FEATURE_COLUMNS = [
    "elapsed_hours", "ph_raw", "tds_raw", "turbidity_raw", "temperature_raw",
    "score_overall", "score_drop_24", "score_drop_72", "score_drop_168",
    "score_MA_24", "score_MA_72", "score_STD_24",
    "turbidity_raw_MA24", "tds_raw_MA24", "ph_raw_MA24",
    "turbidity_raw_drop24", "tds_raw_drop24", "ph_raw_drop24",
    "turbidity_raw_drop72", "tds_raw_drop72", "ph_raw_drop72",
    "hour_of_day",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build causal features and reset history at every Cycle_ID boundary."""
    out = df.sort_values(["Cycle_ID", "Jam"]).copy()
    grouped = out.groupby("Cycle_ID", sort=False)
    out["hour_of_day"] = out["Jam"] % 24

    for lag in (24, 72, 168):
        out[f"score_drop_{lag}"] = grouped["score_overall"].diff(lag)

    out["score_MA_24"] = grouped["score_overall"].transform(
        lambda values: values.rolling(24, min_periods=1).mean()
    )
    out["score_MA_72"] = grouped["score_overall"].transform(
        lambda values: values.rolling(72, min_periods=1).mean()
    )
    out["score_STD_24"] = grouped["score_overall"].transform(
        lambda values: values.rolling(24, min_periods=1).std()
    )

    for column in ("turbidity_raw", "tds_raw", "ph_raw"):
        out[f"{column}_MA24"] = grouped[column].transform(
            lambda values: values.rolling(24, min_periods=1).mean()
        )
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


def main() -> None:
    print("Loading v2 dataset...")
    df = pd.read_csv(DATA_PATH, usecols=DATASET_COLUMNS)
    print(f"Rows: {len(df):,} | Cycles: {df['Cycle_ID'].nunique():,}")
    print(f"RUL range: {df['RUL'].min():.0f} - {df['RUL'].max():.0f} hours")

    features = build_features(df)
    del df
    gc.collect()

    X = features[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    rul_raw = features["RUL"].to_numpy(dtype=np.float32)  # sebelum di-cap
    groups = features["Cycle_ID"].to_numpy()
    y = np.clip(rul_raw, 0, TARGET_CAP_HOURS)
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
    model.fit(X[train_idx], y[train_idx])

    print("Evaluating on holdout cycles...")
    pred = np.clip(model.predict(X[test_idx]), 0, TARGET_CAP_HOURS)
    y_test = y[test_idx]
    raw_test = rul_raw[test_idx]

    metrics_all = _evaluate(
        y_test, pred, np.ones_like(raw_test, dtype=bool)
    )
    metrics_actionable = _evaluate(
        y_test, pred, raw_test <= TARGET_CAP_HOURS
    )
    metrics_ews = _evaluate(y_test, pred, raw_test <= EWS_HOURS)

    metrics = {
        # Angka utama yang dibaca dashboard sebagai "Kepercayaan".
        "r2": metrics_actionable["r2"],
        "mae_hours": metrics_actionable["mae_hours"],
        "mae_days": metrics_actionable["mae_days"],
        "rmse_hours": metrics_actionable["rmse_hours"],
        # Pembanding transparan untuk seluruh test set (termasuk RUL ter-cap).
        "r2_all": metrics_all["r2"],
        "mae_days_all": metrics_all["mae_days"],
        # Khusus horizon peringatan dini <= 10 hari.
        "r2_ews": metrics_ews["r2"],
        "mae_days_ews": metrics_ews["mae_days"],
        "n_test_rows": int(len(test_idx)),
        "n_test_actionable": metrics_actionable["n"],
        "n_test_ews": metrics_ews["n"],
        "n_train_cycles": int(len(train_cycles)),
        "n_test_cycles": int(len(test_cycles)),
        "split": "GroupShuffleSplit 80/20 by Cycle_ID",
        "random_state": RANDOM_STATE,
        "confidence_definition": (
            "Holdout R2 on cycles with uncapped true RUL: "
            f"r2_ews for RUL <= {EWS_HOURS:.0f}h, "
            f"r2_actionable for RUL <= {TARGET_CAP_HOURS:.0f}h"
        ),
        "xgboost_version": xgboost.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "target_cap_hours": TARGET_CAP_HOURS,
        "score_threshold": 60.0,
        "training_dataset": "data_toren_hourly_v2.csv",
        "feature_version": "v2_horizon_30d",
        "metrics": metrics,
    }
    joblib.dump(bundle, MODEL_PATH)
    with open(METADATA_PATH, "w", encoding="ascii") as handle:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, handle, indent=2)

    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metadata: {METADATA_PATH}")
    print(f"Target: min(RUL, {TARGET_CAP_HOURS}) hours")
    print("Metrics (holdout cycles):")
    print(f"  all rows        : R2={metrics_all['r2']:.4f} "
          f"MAE={metrics_all['mae_days']:.2f} hari "
          f"(n={metrics_all['n']:,})")
    print(f"  actionable <=30d: R2={metrics_actionable['r2']:.4f} "
          f"MAE={metrics_actionable['mae_days']:.2f} hari "
          f"(n={metrics_actionable['n']:,})")
    print(f"  EWS <=10d       : R2={metrics_ews['r2']:.4f} "
          f"MAE={metrics_ews['mae_days']:.2f} hari "
          f"(n={metrics_ews['n']:,})")


if __name__ == "__main__":
    main()