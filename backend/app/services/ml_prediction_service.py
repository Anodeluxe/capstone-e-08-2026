"""
ML Prediction Service — v3 Lean A (sustained 24 jam, RUL tanpa cap)
═══════════════════════════════════════════════════════════════════

Jembatan antara pipeline ML (`app/ml`) dan jalur prediksi produksi
(`app/services/prediction_service`).

Keputusan desain:

1. Model XGBoost `xgb_model_v3` → RUL penuh sampai event sustained
   (rolling mean 24 jam `score_overall <= 80`). RUL ditampilkan hanya bila
   <= 30 hari; di atas itu dashboard menampilkan skor air saja.
2. Bila memori fitur belum cukup (jam < MIN_HOURLY_ROWS=73), prediksi
   tidak dibuat sampai histori mencukupi.
3. `elapsed_fraction` diambil dari `DrainLog` via `MLConfig` (DB-backed).
   Model dilatih dengan `elapsed_hours` = fraksi siklus [0, 1].

Prediksi produksi hanya menggunakan XGBoost, tanpa fallback regresi.
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
from app.services.drain_log_service import get_active_drain_log
from app.services.ml_config import get_elapsed_fraction
from app.core.config import get_settings

# Ambang saat produksi memutuskan memakai XGBoost (dibawahnya = kritis/degrading)
SCORE_LOOKS_DEGRADING = 80.0

# Batas tampil RUL di UI (30 hari). Model sendiri tidak di-cap ke sini.
RUL_CAP_HOURS = 720.0

# Ambang untuk memberi tahu "sehari lagi" di dashboard (hari, bukan jam)
DAYS_CAP = 30.0


def _rul_to_display(rul_hours: float) -> dict[str, Any]:
    """Ubah RUL jam → struktur konsisten yang dipakai dashboard."""
    days = rul_hours / 24.0
    if days > DAYS_CAP:
        # Di luar horizon 30 hari: tampilkan skor air saja. `rul_hours` tetap
        # dikirim sebagai penanda >30 hari (frontend cek >720).
        return {
            "rul_hours": round(float(rul_hours), 1),
            "rul_days": None,
            "days_until_threshold": None,
            "predicted_date": None,
            "within_30d_window": False,
            "display_hint": "score_only",
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
    lookback_hours: int = 73,
    elapsed_fraction: float | None = None,
    overall_scores: list[float] | None = None,
) -> dict[str, Any]:
    """
    Path PREFERRED (produksi): XGBoost → RUL tanpa cap (clipped di 2880 jam).

    Mengembalikan dict hasil atau status data/model belum siap.

    `elapsed_fraction` → fraksi siklus [0.0, 1.0] dari `MLConfig` (DB-backed).
    Bila `None`, akan diambil otomatis dari `DrainLog` via `MLConfig`.

    `overall_scores` → deret skor per jam (produksi memproduksi lewat
    scoring_service). Bila `None`, model tetap bisa jalan dengan skor
    fallback 100 (akan prediksi RUL besar — aman, tidak memicu alarm).
    """
    bundle = load_xgb_bundle()
    if bundle is None:
        return _not_ready_result("model_unavailable", "Model XGBoost tidak tersedia.")

    # Get elapsed fraction from DB-backed config if not provided
    if elapsed_fraction is None:
        elapsed_fraction = await get_elapsed_fraction(db)

    # Jangan campur data siklus drain sebelumnya.
    active_log = await get_active_drain_log(db)
    cycle_started_at = active_log.started_at if active_log else None

    features_df = await get_latest_features_async(
        db,
        lookback_hours=lookback_hours,
        elapsed_fraction=elapsed_fraction,
        overall_scores=overall_scores,
        cycle_started_at=cycle_started_at,
    )
    if features_df is None or features_df.empty:
        return _not_ready_result(
            "insufficient_history", "Data historis belum cukup. Diperlukan minimal 73 titik data per jam untuk histori 72 jam."
        )

    model = bundle["model"]
    # The trainer stores metadata at the bundle root, not under `metadata`.
    metadata = bundle.get("metadata", bundle)

    X = features_df[FEATURE_COLUMNS].values
    rul_raw = float(model.predict(X)[0])
    max_hours = float(metadata.get("target_cap_hours", 2880.0))
    if not np.isfinite(rul_raw):
        return _not_ready_result("model_unavailable", "Model XGBoost menghasilkan prediksi tidak valid.")

    rul_hours = max(0.0, min(rul_raw, max_hours))
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
    elif metrics.get("r2_30d") is not None:
        confidence = metrics["r2_30d"]
        confidence_metric = "r2_30d"
    elif metrics.get("r2_actionable") is not None:
        confidence = metrics["r2_actionable"]
        confidence_metric = "r2_actionable"
    else:
        confidence = metrics.get("r2")
        confidence_metric = "r2"

    within_30d = rul_hours <= RUL_CAP_HOURS
    return {
        "rul_hours": rul_hours,
        "rul_days": round(rul_hours / 24.0, 2) if within_30d else None,
        "predicted_date": (
            datetime.utcnow() + timedelta(hours=rul_hours) if within_30d else None
        ),
        "model_used": metadata.get("model_name", "xgb_v3_lean_30d"),
        "confidence": confidence,
        "confidence_metric": confidence_metric,
        "within_30d_window": within_30d,
        "raw_rul_hours": rul_raw,
        "days_until_threshold": (
            round(rul_hours / 24.0, 2) if within_30d else None
        ),
        "already_below_threshold": float(
            features_df["score_overall"].iloc[-1]
        ) <= SCORE_THRESHOLD,
        "current_score": float(features_df["score_overall"].iloc[-1]),
    }


async def get_latest_features_async(
    db: AsyncSession,
    lookback_hours: int = 73,
    elapsed_fraction: float = 0.0,
    overall_scores: list[float] | None = None,
    cycle_started_at: datetime | None = None,
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
        cycle_started_at=cycle_started_at,
    )


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
    Jalur XGBoost yang dipanggil scheduler & predictions:
      1. Coba ML XGBoost (bila data & model siap).
      2. Bila hasil ML "within 30d" (RUL <= 30 hari) → pakai hasil ML.
      3. Bila ML ada tapi RUL > 30 hari → tampilkan skor air saja
         (`display_hint="score_only"`), BUKAN angka RUL.
      4. Bila ML belum siap → kembalikan status data/model belum siap.

    Return selalu dict; status menjelaskan bila model/data belum siap.
    """
    # Get elapsed fraction from DB-backed config if not provided
    if elapsed_fraction is None:
        elapsed_fraction = await get_elapsed_fraction(db)

    if mode not in {"auto", "ml"}:
        raise ValueError("mode must be one of: auto, ml")

    settings = get_settings()
    if not settings.ml_enabled or settings.ml_active_model != "xgboost":
        return _not_ready_result("model_unavailable", "Model XGBoost tidak tersedia.")

    ml_result = await predict_rul_ml(
        db,
        lookback_hours=lookback_hours_for_ml(),
        elapsed_fraction=elapsed_fraction,
        overall_scores=overall_scores,
    )

    if ml_result.get("status"):
        return ml_result

    if ml_result.get("within_30d_window"):
        # ML yakin — ini jalur utama (RUL <= 30 hari)
        display = _rul_to_display(ml_result["rul_hours"])
        return {
            **display,
            "confidence": ml_result.get("confidence", 0.0),
            "model_used": ml_result.get("model_used", "xgb_v3_lean_30d"),
            "already_below_threshold": ml_result.get(
                "already_below_threshold", False
            ),
            "trend_direction": "degrading",
            "is_early_warning_active": ml_result["rul_hours"] / 24.0 <= 10.0,
            "current_score": ml_result.get("current_score"),
        }

    # RUL > 30 hari: dashboard cukup menampilkan skor air.
    return {
        "rul_hours": ml_result.get("raw_rul_hours", ml_result["rul_hours"]),
        "rul_days": None,
        "days_until_threshold": None,
        "predicted_date": None,
        "within_30d_window": False,
        "display_hint": "score_only",
        "confidence": ml_result.get("confidence", 0.0),
        "model_used": ml_result.get("model_used", "xgb_v3_lean_30d"),
        "already_below_threshold": ml_result.get("already_below_threshold", False),
        "trend_direction": "stable",
        "is_early_warning_active": False,
        "current_score": ml_result.get("current_score"),
    }


def _not_ready_result(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "rul_hours": None,
        "rul_days": None,
        "days_until_threshold": None,
        "predicted_date": None,
        "confidence": None,
        "model_used": "xgboost",
        "within_30d_window": None,
        "is_early_warning_active": False,
    }


def lookback_hours_for_ml() -> int:
    """Jumlah jam lookback yang dipakai model (MIN_HOURLY_ROWS agar rolling valid)."""
    return max(MIN_HOURLY_ROWS, get_settings().ml_lookback_hours)
