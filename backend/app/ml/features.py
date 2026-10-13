"""
ML Feature Pipeline — v2 Horizon (early-warning 30 hari)
═══════════════════════════════════════════════════════

Membangun matriks fitur produksi yang **identik dengan pelatihan** model
`xgb_model_hourly_v2_horizon.pkl`.

Kontrak penting:
  - FEATURE_COLUMNS di bawah harus SELALU cocok urutan/jumlahnya dengan
    `feature_columns` di metadata model — jangan diubah sembarangan.
  - Model dilatih di NILAI MENTAH (raw + score_overall) — TIDAK butuh scaler.
  - Semua fitur rolling/drop dihitung KASUAL per Cycle_ID (reset di tiap
    siklus baru, hanya memakai masa lalu), jadi aman dipakai di inferensi
    produksi tanpa bocor data masa depan.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading

# ── Lokasi artifact model (bundle v2-horizon) ─────────────────────────────────
_ML_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_ML_DIR, "models")
_XGB_BUNDLE_PATH = os.path.join(_MODELS_DIR, "xgb_model_hourly_v2_horizon.pkl")

# Daftar fitur TEPAT seperti metadata bundle (jangan ubah urutan!)
FEATURE_COLUMNS = [
    "elapsed_hours",
    "ph_raw",
    "tds_raw",
    "turbidity_raw",
    "temperature_raw",
    "score_overall",
    "score_drop_24",
    "score_drop_72",
    "score_drop_168",
    "score_MA_24",
    "score_MA_72",
    "score_STD_24",
    "turbidity_raw_MA24",
    "tds_raw_MA24",
    "ph_raw_MA24",
    "turbidity_raw_drop24",
    "tds_raw_drop24",
    "ph_raw_drop24",
    "turbidity_raw_drop72",
    "tds_raw_drop72",
    "ph_raw_drop72",
    "hour_of_day",
]

# Minimum baris hourly agar fitur drop/history bisa dihitung
MIN_HOURLY_ROWS = 169

# Ambang alarm produksi (sama dengan generator/target & EWS)
SCORE_THRESHOLD = 60.0

# Rentang fisis sensor — nilai di luar ini di-clip, bukan untuk extrapolate
_PHYSICAL_CLIP = {
    "ph_raw": (3.0, 11.0),
    "tds_raw": (10.0, 1800.0),
    "turbidity_raw": (0.05, 65.0),
    "temperature_raw": (20.0, 34.0),
}


# ── Model loader (singleton) ─────────────────────────────────────────────────
_model_bundle = None


def load_model() -> dict | None:
    """Load bundle XGBoost (model + metadata). Sekali, di-cache."""
    global _model_bundle
    if _model_bundle is not None:
        return _model_bundle

    if not os.path.exists(_XGB_BUNDLE_PATH):
        print(f"[ML] Bundle model tidak ditemukan: {_XGB_BUNDLE_PATH}")
        return None

    try:
        with open(_XGB_BUNDLE_PATH, "rb") as fh:
            _model_bundle = joblib.load(fh)
        bundle_columns = _model_bundle.get("feature_columns")
        if bundle_columns is not None and bundle_columns != FEATURE_COLUMNS:
            raise ValueError("Model feature_columns do not match production FEATURE_COLUMNS")
        print("[ML] Bundle model v2-horizon dimuat.")
        return _model_bundle
    except Exception as exc:
        print(f"[ML] Gagal memuat bundle XGBoost: {exc}")
        return None


# ── Agregasi read mentah → per jam ───────────────────────────────────────────
async def aggregate_hourly_readings(
    db: AsyncSession,
    since_datetime: datetime,
) -> pd.DataFrame:
    """
    Ambil raw sensor readings sejak `since_datetime`, agregasi per jam
    (rata-rata ph/tds/turbidity/temperature), urut naik.

    Hasil kolom: ['timestamp', 'ph', 'tds', 'turbidity', 'temperature', 'score_overall']
    """
    hour_trunc = func.date_trunc("hour", SensorReading.timestamp).label("hour")

    stmt = (
        select(
            hour_trunc,
            func.avg(SensorReading.ph).label("ph"),
            func.avg(SensorReading.tds).label("tds"),
            func.avg(SensorReading.turbidity).label("turbidity"),
            func.avg(SensorReading.temperature).label("temperature"),
            func.avg(SensorReading.score_overall).label("score_overall"),
        )
        .where(SensorReading.timestamp >= since_datetime)
        .group_by(hour_trunc)
        .order_by(hour_trunc.asc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return pd.DataFrame(columns=["timestamp", "ph", "tds", "turbidity", "temperature", "score_overall"])

    df = pd.DataFrame(rows, columns=["timestamp", "ph", "tds", "turbidity", "temperature", "score_overall"])
    return df


# ── Build Feature Matrix (generator mirror, versi produksi) ──────────────────
def build_feature_matrix(
    hourly_df: pd.DataFrame,
    elapsed_fraction: float = 0.0,
    overall_scores: list[float] | None = None,
) -> pd.DataFrame | None:
    """
    Dari data hourly (agregasi DB) → 22 fitur model.

    Fitur rolling (MA/drop) dihitung pada slice (single cycle). Karena
    `elapsed_hours` di training adalah fraksi 0-1, nilai yang benar
    di produksi juga harus 0-1.

    `elapsed_fraction` → posisi siklus saat ini (0.0 = baru drain, 1.0 = akhir).
    """
    if len(hourly_df) < MIN_HOURLY_ROWS:
        print(f"[ML] Butuh >= {MIN_HOURLY_ROWS} baris hourly, baru ada {len(hourly_df)}.")
        return None

    df = hourly_df.sort_values("timestamp").reset_index(drop=True).copy()

    # ── elapsed_hours sebagai fraksi (0-1) ───────────────────────────────────
    n = max(len(df), 1)
    df["elapsed_hours"] = np.linspace(
        max(0.0, elapsed_fraction - (n - 1) / 2400.0),
        min(1.0, elapsed_fraction),
        n,
    )
    df["hour_of_day"] = df["timestamp"].dt.hour.astype(float)

    # Rename raw sensor → kolom raw_*
    for col in ("ph", "tds", "turbidity", "temperature"):
        df[f"{col}_raw"] = df[col]

    # score_overall: kalau tidak disuplai caller, fallback stabil (kualitas baik)
    if overall_scores is not None and len(overall_scores) == len(df):
        df["score_overall"] = overall_scores
    elif "score_overall" not in df:
        print("[ML] score_overall tidak tersedia — pakai fallback 100 (kualitas baik).")
        df["score_overall"] = 100.0
    elif bool(df["score_overall"].isna().all()):
        print("[ML] score_overall tidak tersedia — pakai fallback 100 (kualitas baik).")
        df["score_overall"] = 100.0
    else:
        df["score_overall"] = df["score_overall"].fillna(100.0)

    # ── Clip fisis (nilai di luar rentang sensor → clamp) ────────────────────
    for col, (lo, hi) in _PHYSICAL_CLIP.items():
        if col in df.columns:
            df[col] = df[col].clip(lower=lo, upper=hi)

    # ── Fitur rolling / drop (rolling dihitung pada SATU cycle berjalan) ─────
    df["score_drop_24"] = df["score_overall"].diff(24).fillna(0.0)
    df["score_drop_72"] = df["score_overall"].diff(72).fillna(0.0)
    df["score_drop_168"] = df["score_overall"].diff(168).fillna(0.0)

    df["score_MA_24"] = df["score_overall"].rolling(24, min_periods=1).mean()
    df["score_MA_72"] = df["score_overall"].rolling(72, min_periods=1).mean()
    df["score_STD_24"] = df["score_overall"].rolling(24, min_periods=1).std().fillna(0.0)

    for col in ("turbidity", "tds", "ph"):
        df[f"{col}_raw_MA24"] = df[col].rolling(24, min_periods=1).mean()
        df[f"{col}_raw_drop24"] = df[col].diff(24).fillna(0.0)
        df[f"{col}_raw_drop72"] = df[col].diff(72).fillna(0.0)

    # Pastikan 22 kolom ada (guard); buang sisanya
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0

    return pd.DataFrame(df.loc[:, FEATURE_COLUMNS])


# ── Pipeline lengkap: DB → Features ──────────────────────────────────────────
async def get_latest_features(
    db: AsyncSession,
    lookback_hours: int = 169,
    elapsed_fraction: float = 0.0,
    overall_scores: list[float] | None = None,
) -> pd.DataFrame | None:
    """
    Convenience: ambil 72 jam terakhir, agregasi hourly, build feature matrix,
    lalu return BARIS TERAKHIR (jam terbaru) berbentuk DataFrame 1-baris.

    `overall_scores` → deret skor per jam sejajar dengan agregasi (dari caller).
    """
    since = datetime.utcnow() - timedelta(hours=lookback_hours)
    hourly_df = await aggregate_hourly_readings(db, since)

    if hourly_df.empty:
        print("[ML] Tidak ada data hourly.")
        return None

    features = build_feature_matrix(hourly_df, elapsed_fraction=elapsed_fraction, overall_scores=overall_scores)
    if features is None:
        return None

    return features.iloc[[-1]].copy()


# =============================================================================
# MAIN (untuk uji cepat fitur sendirian)
# =============================================================================
if __name__ == "__main__":
    print("Fitur produksi v2-horizon (22 kolom):")
    for n, col in enumerate(FEATURE_COLUMNS):
        print(f"  {n:2d}. {col}")
