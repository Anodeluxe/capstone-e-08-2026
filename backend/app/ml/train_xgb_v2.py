"""Train the production-oriented XGBoost v2 RUL model.

The application only needs an actionable early-warning horizon (30 days),
so targets above 720 hours are intentionally censored.  The feature set uses
only values available at prediction time: current sensor values, the current
production score, and causal history within the current drain cycle.
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_toren_hourly_v2.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "xgb_model_hourly_v2_horizon.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "models", "xgb_model_hourly_v2_horizon.json")

TARGET_CAP_HOURS = 30 * 24
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


def main() -> None:
    print("Loading v2 dataset...")
    df = pd.read_csv(DATA_PATH)
    features = build_features(df)
    X = features[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = np.clip(features["RUL"].to_numpy(), 0, TARGET_CAP_HOURS)

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
        random_state=42,
        n_jobs=-1,
    )
    print(f"Training {len(X):,} rows with {len(FEATURE_COLUMNS)} causal features...")
    model.fit(X, y)

    bundle = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "target_cap_hours": TARGET_CAP_HOURS,
        "score_threshold": 60.0,
        "training_dataset": "data_toren_hourly_v2.csv",
        "feature_version": "v2_horizon_30d",
    }
    joblib.dump(bundle, MODEL_PATH)
    with open(METADATA_PATH, "w", encoding="ascii") as handle:
        json.dump({k: v for k, v in bundle.items() if k != "model"}, handle, indent=2)

    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metadata: {METADATA_PATH}")
    print(f"Target: min(RUL, {TARGET_CAP_HOURS}) hours")


if __name__ == "__main__":
    main()