"""
ML Prediction Service — v2 Horizon (early-warning 30 hari)
═════════════════════════════════════════════════════════

Jembatan antara pipeline ML (`app/ml`) dan jalur prediksi produksi
(`app/services/prediction_service`).

Keputusan desain (mengikuti catatan fase peninjauan):

1. Model XGBoost `xgb_model_hourly_v2_horizon` → RUL 0–720 jam (30 hari),
   bergerak bersama `score_overall <= 60`. Dipakai saat skor mulai MENURUN
   dan sisa-waktu <= 30 hari.
2. Bila memori fitur belum cukup (jam < MIN_HOURLY_ROWS=72) ATAU `score_overall`
   tidak tersedia, kita FALLBACK ke regresi ETA lama (predict_eta) — model
   linear/polynomial yang sudah dipakai predictions.py & scheduler.
3. `elapsed_fraction` diambil dari `DrainLog` via `MLConfig` (DB-backed).
   Model dilatih dengan `elapsed_hours` normalisasi [0, 1] = fraksi siklus.

Service ini TIDAK menyentuh jalur lama — hanya menambah jalur prioritas-ML
di depan `predict_eta`.
"""

from datetime import datetime, timedelta
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import (
    FEATURE_COLUMNS,
    MIN_HOURLY_ROWS,
    SCORE_THRESHOLD,
    aggregate_hourly_readings,
    build_feature_matrix,
    load_model as load_xgb_bundle,
)
from app.services.ml_config import get_elapsed_fraction
from app.core.config import get_settings

# Ambang saat produksi memutuskan memakai XGBoost (dibawahnya = kritis/degrading)
SCORE_LOOKS_DEGRADING = 60.0

# Horizon model (jam) — RUL yang diprediksi TIDAK boleh melebihi ini karena
# target dilatih dengan cap 720 jam.
RUL_CAP_HOURS = 720.0

# Kalau model tidak bisa dipakai → fallback ke regresi lama
MODEL_FALLBACK = "linear_or_poly_regression"

# Ambang untuk memberi tahu "sehari lagi" di dashboard (hari, bukan jam)
DAYS_CAP = 30.0


def _rul_to_display(rul_hours: float) -> dict[str, Any]:
    """Ubah RUL jam → struktur konsisten yang dipakai dashboard."""
    days = rul_hours / 24.0
    if days > DAYS_CAP:
        # Di luar horizon 30 hari: dashboard show score + jadwal pakar (3-4 bln),
        # BUKAN angka RUL (karena model target di-cap 30 hari).
        return {
            "rul_hours": None,
            "rul_days": None,
            "days_until_threshold": None,
            "predicted_date": None,
            "within_30d_window": False,
            "display_hint": "expert_schedule_3_4_months",
        }

    predicted_date = datetime.utcnow() + timedelta(hours=rul_hours)
    return {
        "rul_hours": round(float(rul_hours), 1),
        "rul_days": round(float(days), 2),
        "days_until_threshold": round(float(days), 2),
        "predicted_date": predicted_date,
        "within_30d_window": True,
        "display_hint": "machine_learning_rul",
    }


async def predict_rul_ml(
    db: AsyncSession,
    lookback_hours: int = 169,
    elapsed_fraction: float | None = None,
    overall_scores: list[float] | None = None,
) -> dict[str, Any] | None:
    """
    Path PREFERRED (produksi): XGBoost horizon → RUL 0–720 jam.

    Mengembalikan dict hasil, atau `None` bila data/model belum siap
    (caller harus fallback ke predict_eta).

    `elapsed_fraction` → fraksi siklus [0.0, 1.0] dari `MLConfig` (DB-backed).
    Bila `None`, akan diambil otomatis dari `DrainLog` via `MLConfig`.

    `overall_scores` → deret skor per jam (produksi memproduksi lewat
    scoring_service). Bila `None`, model tetap bisa jalan dengan skor
    fallback 100 (akan prediksi RUL besar — aman, tidak memicu alarm).
    """
    bundle = load_xgb_bundle()
    if bundle is None:
        print("[ML] Bundle XGBoost tidak tersedia → fallback regresi.")
        return None

    # Get elapsed fraction from DB-backed config if not provided
    if elapsed_fraction is None:
        elapsed_fraction = await get_elapsed_fraction(db)

    features_df = await get_latest_features_async(
        db,
        lookback_hours=lookback_hours,
        elapsed_fraction=elapsed_fraction,
        overall_scores=overall_scores,
    )
    if features_df is None or features_df.empty:
        return None

    model = bundle["model"]
    # The trainer stores metadata at the bundle root, not under `metadata`.
    metadata = bundle.get("metadata", bundle)

    X = features_df[FEATURE_COLUMNS].values
    rul_raw = float(model.predict(X)[0])
    label_cap = float(metadata.get("target_cap_hours", RUL_CAP_HOURS))
    if not np.isfinite(rul_raw):
        return None

    rul_hours = max(0.0, min(rul_raw, label_cap))
    metrics = metadata.get("metrics", {})

    # Pilih metrik sesuai horizon prediksi: R2 pada subset EWS (<=10 hari)
    # jauh lebih relevan untuk prediksi mendesak daripada R2 30 hari.
    settings = get_settings()
    if (
        rul_hours <= settings.early_warning_hours
        and metrics.get("r2_ews") is not None
    ):
        confidence = metrics["r2_ews"]
        confidence_metric = "r2_ews"
    elif metrics.get("r2_actionable") is not None:
        confidence = metrics["r2_actionable"]
        confidence_metric = "r2_actionable"
    else:
        confidence = metrics.get("r2")
        confidence_metric = "r2"

    return {
        "rul_hours": rul_hours,
        "rul_days": round(rul_hours / 24.0, 2),
        "predicted_date": datetime.utcnow() + timedelta(hours=rul_hours),
        "model_used": "xgb_v2_horizon_30d",
        "confidence": confidence,
        "confidence_metric": confidence_metric,
        "within_30d_window": 0.0 <= rul_raw <= label_cap,
        "raw_rul_hours": rul_raw,
        "days_until_threshold": round(rul_hours / 24.0, 2),
        "already_below_threshold": float(
            features_df["score_overall"].iloc[-1]
        ) <= SCORE_THRESHOLD,
    }


async def get_latest_features_async(
    db: AsyncSession,
    lookback_hours: int = 169,
    elapsed_fraction: float = 0.0,
    overall_scores: list[float] | None = None,
) -> pd.DataFrame | None:
    """
    Bungkus pipeline produksi: ambil raw readings → agregasi hourly → build
    feature matrix. Return baris TERAKHIR (DataFrame 1-baris) atau None.

    Menerima `elapsed_fraction` (fraksi siklus 0.0–1.0) dan
    `overall_scores` (deret skor per jam, sejajar agregasi DB).
    """
    from app.ml.features import get_latest_features

    return await get_latest_features(
        db,
        lookback_hours=lookback_hours,
        elapsed_fraction=elapsed_fraction,
        overall_scores=overall_scores,
    )


def _regression_fallback(
    timestamps: list[datetime],
    scores: list[float],
    threshold: float,
) -> dict[str, Any]:
    """
    Jembatan ke predict_eta lama supaya ML service TIDAK mengganti jalur
    yang dipakai scheduler/predictions — hanya menambah jalur prioritas.
    """
    from app.services.prediction_service import predict_eta

    return predict_eta(timestamps, scores, threshold=threshold)


async def predict_hybrid(
    db: AsyncSession,
    timestamps: list[datetime],
    scores: list[float],
    elapsed_fraction: float | None = None,
    overall_scores: list[float] | None = None,
    threshold: float = SCORE_THRESHOLD,
    mode: str = "auto",
) -> dict[str, Any]:
    """
    Jalur HYBRID yang dipanggil scheduler & predictions:
      1. Coba ML XGBoost horizon (bila data & model siap).
      2. Bila hasil ML "within 30d" (RUL <= 30 hari) → pakai hasil ML.
      3. Bila ML belum siap ATAU RUL > 30 hari → fallback regresi ETA lama.

    Return selalu dict (tidak pernah None); ada key `model_used` untuk
    memberi tahu dashboard jalur mana yang dipakai.
    """
    # Get elapsed fraction from DB-backed config if not provided
    if elapsed_fraction is None:
        elapsed_fraction = await get_elapsed_fraction(db)

    if mode not in {"auto", "ml", "linear"}:
        raise ValueError("mode must be one of: auto, ml, linear")

    settings = get_settings()
    if mode == "linear" or (
        mode == "auto" and (not settings.ml_enabled or settings.ml_active_model != "xgboost")
    ):
        fallback = dict(_regression_fallback(timestamps, scores, threshold))
        fallback["model_used"] = fallback.get("model_used", MODEL_FALLBACK)
        fallback["display_hint"] = "regression_eta"
        fallback["within_30d_window"] = None
        fallback["is_early_warning_active"] = False
        return fallback

    ml_result = await predict_rul_ml(
        db,
        lookback_hours=max(lookback_hours_for_ml(), 72),
        elapsed_fraction=elapsed_fraction,
        overall_scores=overall_scores,
    )

    if ml_result is not None and ml_result.get("within_30d_window"):
        # ML yakin — ini jalur utama (RUL <= 30 hari)
        display = _rul_to_display(ml_result["rul_hours"])
        return {
            **display,
            "confidence": ml_result.get("confidence", 0.0),
            "model_used": ml_result.get("model_used", "xgb_v2_horizon_30d"),
            "already_below_threshold": ml_result.get(
                "already_below_threshold", False
            ),
            "trend_direction": "degrading",
            "is_early_warning_active": ml_result["rul_hours"] / 24.0 <= 10.0,
        }

    # ML tidak bisa / RUL di luar 30 hari → regresi lama (scheduler & predictions)
    fallback = _regression_fallback(timestamps, scores, threshold)
    fallback = dict(fallback)
    fallback["model_used"] = fallback.get("model_used", MODEL_FALLBACK)
    fallback["display_hint"] = "regression_eta"
    fallback["within_30d_window"] = None
    fallback["is_early_warning_active"] = False
    return fallback


def lookback_hours_for_ml() -> int:
    """Jumlah jam lookback yang dipakai model (MIN_HOURLY_ROWS agar rolling valid)."""
    return max(MIN_HOURLY_ROWS, get_settings().ml_lookback_hours)
