"""
Data Generator v2 — Granularitas Per Jam, RUL berancor skor produksi
──────────────────────────────────────────────────────────────────────
Menghasilkan data time-series sintetis untuk training model RUL dengan
satuan PER JAM dan siklus 90–120 hari (2160–2880 jam), sesuai riset:
toren wajib dikuras minimal 3 bulan sekali.

PEMBEDA UTAMA dibanding data_generator_hourly.py (v1):
  1. RUL TIDAK lagi "jam sampai rata-rata air kotor", melainkan
     "jam sampai score_overall pertama kali <= 60" — persis ambang
     early-warning di `app/services/prediction_service.py` dan logika
     skoring `app/services/scoring_service.py`. Target model kini sama
     dengan momen keputusan sistem produksi.
  2. Profil nilai sensor diambil dari distribusi nyata dataset
     `watera.csv` per BAND skor (bukan dari label `potability` yang
     imbalanced & noisy). Statistik tiap band dibuat dari median baris
     dataset yang sub-scorenya berada di band tsb.
  3. Dinamika lebih realistis:
     - Suhu: siklus diurnal sinusoid (bukan uniform konstan).
     - Noise: AR(1) autocorrelated (bukan iid) = drift sensor asli.
     - Sebagian siklus mendapat event kontaminasi/pengisian yang pulih.
     - Arah degradasi pH (ke asam / ke basa) dipilih acak per siklus.
  4. Tingkat keparahan akhir bervariasi per siklus (ringan/sedang/berat)
     namun SELALU menjamin crossing score <= 60 di akhir siklus.

Skoring memakai `app/ml/scoring_model.py`, mirror dari
`app/services/scoring_service.py` (diverifikasi oleh pytest).

Output:
  - data/processed/data_toren_hourly_v2.csv  (dataset siap training)
  - models/scaler_hourly_v2.pkl              (MinMaxScaler 8 fitur)
"""

import os
import pickle

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from scoring_model import overall_scores

# ============================================================================
# 1. KONSTANTA GENERATOR
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(BASE_DIR, "data", "raw", "watera.csv")
OUT_CSV = os.path.join(BASE_DIR, "data", "processed", "data_toren_hourly_v2.csv")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler_hourly_v2.pkl")

JUMLAH_SIKLUS = 1000
RUL_CAP = 2880  # jam (120 hari)

# Patokan geometri siklus: suhu air toren Indonesia.
TEMP_BASE = 27.0
TEMP_AMPLITUDE = 2.5
TEMP_PEAK_HOUR = 14  # terpanas sekitar pukul 14.00
PHI_AR1 = 0.80  # autoregresi noise sensor
NOISE_SIGMA = {"ph": 0.06, "turbidity": 0.12, "tds": 10.0, "temperature": 0.30}

# Tingkat keparahan akhir siklus (target sub-score tiap parameter).
# Semua kombinasi menjamin score_overall akhir <= 60 (lihat docstring).
END_SCORES = {
    "heavy": {"ph": 0, "turbidity": 0, "tds": 0},
    "medium": {"ph": 0, "turbidity": 25, "tds": 20},
    "mild": {"ph": 40, "turbidity": 55, "tds": 50},
}

# Kadang siklus mulai dengan kondisi yang tidak 100% sempurna (realistis).
START_SCORES = {
    "ph": 100,
    "turbidity": 100,
    "tds": 100,
}

FITUR_X = [
    "elapsed_hours", "ph", "tds", "turbidity", "temperature",
    "ph_MA_24", "tds_MA_24", "turbidity_MA_24",
]


# ============================================================================
# 2. PEMBERSIHAN & PROFIL BAND (dari dataset nyata)
# ============================================================================
def remove_extreme_outliers(dataframe):
    """Bersihkan data mentah — batas bawah fisik + batas atas ekstrem."""
    df_clean = dataframe.copy()

    Q1_ph = df_clean["ph"].quantile(0.25)
    Q3_ph = df_clean["ph"].quantile(0.75)
    IQR_ph = Q3_ph - Q1_ph
    df_clean = df_clean[
        (df_clean["ph"] >= max(0.0, Q1_ph - 1.5 * IQR_ph))
        & (df_clean["ph"] <= min(14.0, Q3_ph + 1.5 * IQR_ph))
    ]

    for col in ["tds", "turbidity"]:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        df_clean = df_clean[
            (df_clean[col] > 0) & (df_clean[col] <= Q3 + 1.5 * IQR)
        ]
    return df_clean


def _band_median(df, col, score_fn, score_values, arm=None):
    """Median nilai sensor pada tiap band sub-score (atau arm pH)."""
    medians = {}
    for s in score_values:
        mask = score_fn(df[col].values) == s
        if arm is not None:
            if arm == "acid":
                mask &= df[col].values < 7.5
            else:
                mask &= df[col].values > 7.5
        sub = df.loc[mask, col]
        medians[s] = float(sub.median()) if len(sub) else None
    return medians


def _med(medians, score, fallback):
    """Median band dengan fallback bila band kosong di data (None)."""
    v = medians.get(score)
    return fallback if v is None else v


def build_inverse_maps(df):
    """
    Bangun peta inverse sub-score -> nilai sensor.
    Map: (xp ascending sub-score, fp nilai sensor) untuk np.interp.
    Nilai band yang tidak ada datanya diganti titik spek/penalti.
    """
    maps = {}

    # Turbidity: 100(<=1) 80(1-5) 55(5-10) 25(10-25) 0(>25)
    med = _band_median(df, "turbidity", lambda v: np.where(v <= 1.0, 100.0,
          np.where(v <= 5.0, 80.0, np.where(v <= 10.0, 55.0,
          np.where(v <= 25.0, 25.0, 0.0)))), [100, 80, 55, 25, 0])
    fp_t = [_med(med, 0, 35.0), _med(med, 25, 17.5), _med(med, 55, 7.5),
            _med(med, 80, 3.0), _med(med, 100, 0.7)]
    maps["turbidity"] = (np.array([0, 25, 55, 80, 100]), np.array(fp_t))

    # TDS: 100(<=300) 80(300-500) 50(500-900) 20(900-1200) 0(>1200)
    med = _band_median(df, "tds", lambda v: np.where(v <= 300.0, 100.0,
          np.where(v <= 500.0, 80.0, np.where(v <= 900.0, 50.0,
          np.where(v <= 1200.0, 20.0, 0.0)))), [100, 80, 50, 20, 0])
    fp_s = [_med(med, 0, 1450.0), _med(med, 20, 1050.0), _med(med, 50, 700.0),
            _med(med, 80, 400.0), _med(med, 100, 220.0)]
    maps["tds"] = (np.array([0, 20, 50, 80, 100]), np.array(fp_s))

    # pH: dua lengan (asam / basa) dari pusat ~7.15.
    med_a = _band_median(df, "ph", lambda v: np.where((6.5 <= v) & (v <= 8.5), 100.0,
           np.where(((6.0 <= v) & (v < 6.5)) | ((8.5 < v) & (v <= 9.0)), 70.0,
           np.where(((5.5 <= v) & (v < 6.0)) | ((9.0 < v) & (v <= 9.5)), 40.0, 0.0))),
           [100, 70, 40, 0], arm="acid")
    maps["ph_acid"] = (np.array([0, 40, 70, 100]),
                       np.array([_med(med_a, 0, 5.2), _med(med_a, 40, 5.7),
                                 _med(med_a, 70, 6.25), _med(med_a, 100, 7.15)]))
    med_b = _band_median(df, "ph", lambda v: np.where((6.5 <= v) & (v <= 8.5), 100.0,
           np.where(((6.0 <= v) & (v < 6.5)) | ((8.5 < v) & (v <= 9.0)), 70.0,
           np.where(((5.5 <= v) & (v < 6.0)) | ((9.0 < v) & (v <= 9.5)), 40.0, 0.0))),
           [100, 70, 40, 0], arm="base")
    maps["ph_base"] = (np.array([0, 40, 70, 100]),
                       np.array([_med(med_b, 0, 10.0), _med(med_b, 40, 9.4),
                                 _med(med_b, 70, 8.8), _med(med_b, 100, 7.15)]))
    return maps


def invert_subscore(maps, param, s, arm=None):
    """Mapping sub-score -> nilai sensor via interpolasi band."""
    key = f"ph_{arm}" if param == "ph" else param
    xp, fp = maps[key]
    return np.interp(np.clip(s, 0, 100), xp, fp)


# ============================================================================
# 3. PER-CYCLE SIMULATOR
# ============================================================================
def _ar1(rng, n, phi, sigma_marginal):
    """Noise AR(1) autocorrelated dengan std marginal ~= sigma_marginal."""
    e = rng.normal(0.0, sigma_marginal * np.sqrt(1.0 - phi * phi), n)
    out = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc = phi * acc + e[i]
        out[i] = acc
    return out


def _diurnal_temperature(jam, rng):
    """Suhu sinusoid diurnal 24 jam + noise kecil."""
    wave = TEMP_BASE + TEMP_AMPLITUDE * np.cos(
        2.0 * np.pi * (jam - TEMP_PEAK_HOUR) / 24.0
    )
    return wave + _ar1(rng, len(jam), PHI_AR1, NOISE_SIGMA["temperature"])


def generate_cycle(rng, siklus, maps):
    """Bangun satu siklus toren; kembalikan DataFrame per-jam."""
    total_jam = int(rng.integers(2160, 2881))  # 90-120 hari
    pattern = rng.choice(["linear", "stabil"], p=[0.6, 0.4])
    ph_arm = rng.choice(["acid", "base"])
    severity = rng.choice(["heavy", "medium", "mild"], p=[0.25, 0.35, 0.40])

    jam = np.arange(1, total_jam + 1)
    pos = jam / total_jam

    if pattern == "linear":
        ramp = pos
    else:  # stabil di 60% pertama, menurun di 40% terakhir
        ramp = np.where(pos < 0.6, 0.0, (pos - 0.6) / 0.4)

    # Kadang siklus mulai sedikit tidak sempurna (skor awal bukan 100).
    start_turb = rng.choice([100, 100, 85])
    start_tds = rng.choice([100, 100, 90])
    start = {"ph": 100, "turbidity": start_turb, "tds": start_tds}
    end = END_SCORES[severity]

    # Trajektori sub-score tiap parameter.
    ph_s = start["ph"] + (end["ph"] - start["ph"]) * ramp
    turb_s = start["turbidity"] + (end["turbidity"] - start["turbidity"]) * ramp
    tds_s = start["tds"] + (end["tds"] - start["tds"]) * ramp

    # Inverse ke nilai sensor + noise AR(1).
    ph = invert_subscore(maps, "ph", ph_s, ph_arm) + _ar1(rng, total_jam, PHI_AR1, NOISE_SIGMA["ph"])
    turb = invert_subscore(maps, "turbidity", turb_s) + _ar1(rng, total_jam, PHI_AR1, NOISE_SIGMA["turbidity"])
    tds = invert_subscore(maps, "tds", tds_s) + _ar1(rng, total_jam, PHI_AR1, NOISE_SIGMA["tds"])
    temp = _diurnal_temperature(jam, rng)

    # Event kontaminasi singkat yang pulih (bump turbidity + tds ringan).
    if rng.random() < 0.12:
        start_i = int(total_jam * (0.65 + 0.20 * rng.random()))
        dur = int(rng.integers(24, 73))
        peak = 2.0 + 0.8 * rng.random()
        seg_idx = np.arange(start_i, min(start_i + dur, total_jam))
        tail = np.exp(-np.arange(len(seg_idx)) / (dur / 3.0))
        w = np.zeros(total_jam)
        w[seg_idx] = tail
        turb = turb * (1.0 + (peak - 1.0) * w)
        tds = tds * (1.0 + 0.30 * (peak - 1.0) * w)

    # Clamp fisik.
    ph = np.clip(ph, 3.0, 11.0)
    turb = np.clip(turb, 0.05, 60.0)
    tds = np.clip(tds, 10.0, 1800.0)
    temp = np.clip(temp, 20.0, 34.0)

    # Skor produksi aktual per jam (persis seperti di backend).
    overall = overall_scores(ph, tds, turb, temp)

    # RUL = jam tersisa sampai score_overall pertama <= 60.
    le = overall <= 60.0
    crossing_elapsed = int(np.argmax(le)) if le.any() else total_jam

    # Truncate siklus TEPAT di jam alarm (skor<=60 -> RUL 0 di baris terakhir).
    # Baris setelah crossing tidak dipakai: si toren sudah "alarm", bukan lagi
    # horison prediksi. Ini membuat distribusi cadangan mirip v1 sekaligus
    # tetap berancor pada skor produksi.
    upto = crossing_elapsed + 1
    jam = jam[:upto]
    ph = ph[:upto]
    turb = turb[:upto]
    tds = tds[:upto]
    temp = temp[:upto]
    overall = overall[:upto]

    elapsed_hours = jam - 1
    rul = crossing_elapsed - elapsed_hours

    df = pd.DataFrame({
        "Cycle_ID": siklus,
        "Jam": jam,
        "RUL": rul.astype(int),
        "elapsed_hours": elapsed_hours,
        "ph": ph,
        "tds": tds,
        "turbidity": turb,
        "temperature": temp,
        "ph_raw": ph,
        "tds_raw": tds,
        "turbidity_raw": turb,
        "temperature_raw": temp,
        "score_overall": overall,
        "pattern": pattern,
        "ph_arm": ph_arm,
        "severity": severity,
    })
    return df


# ============================================================================
# 4. FEATURE ENGINEERING
# ============================================================================
def add_features(df_full):
    """elapsed_hours (sudah ada) + rolling mean 24 jam per parameter."""
    for col in ["turbidity", "tds", "ph"]:
        df_full[f"{col}_MA_24"] = df_full.groupby("Cycle_ID")[col].transform(
            lambda x: x.rolling(window=24, min_periods=1).mean()
        )
    return df_full


# ============================================================================
# 5. PIPELINE UTAMA
# ============================================================================
def main():
    print("=" * 62)
    print("DATA GENERATOR v2 — RUL BERANCOR SKOR PRODUKSI (<= 60)")
    print("=" * 62)

    print("\n1. Memuat dataset mentah watera.csv...")
    df_raw = pd.read_csv(RAW_CSV)
    df_clean = remove_extreme_outliers(df_raw[["ph", "tds", "turbidity"]].dropna())
    print(f"   watermark: {df_raw.shape[0]} baris -> {len(df_clean)} baris bersih")

    print("\n2. Membangun peta inverse sub-score dari distribusi nyata...")
    maps = build_inverse_maps(df_clean)
    for key, (xp, fp) in maps.items():
        print(f"   {key:10s}: {dict(zip(xp.tolist(), fp.round(3).tolist()))}")

    print(f"\n3. Simulasi {JUMLAH_SIKLUS} siklus (90-120 hari, skor-ancor)...")
    rng = np.random.default_rng(42)
    frames = []
    for siklus in range(1, JUMLAH_SIKLUS + 1):
        frames.append(generate_cycle(rng, siklus, maps))
        if siklus % 250 == 0:
            print(f"   ... {siklus}/{JUMLAH_SIKLUS}")
    df_timeseries = pd.concat(frames, ignore_index=True)
    print(f"   -> {len(df_timeseries):,} baris dibuat.")

    print("\n4. Feature engineering (elapsed_hours + MA_24)...")
    df_timeseries = df_timeseries.sort_values(["Cycle_ID", "Jam"], ascending=[True, True])
    df_timeseries = add_features(df_timeseries)

    # Parametrik: sub-score pH dihitung ulang agar kolom analitis konsisten.
    df_timeseries["ph_score"] = np.where(
        (6.5 <= df_timeseries["ph"]) & (df_timeseries["ph"] <= 8.5), 100.0,
        np.where(((6.0 <= df_timeseries["ph"]) & (df_timeseries["ph"] < 6.5))
                 | ((8.5 < df_timeseries["ph"]) & (df_timeseries["ph"] <= 9.0)), 70.0,
        np.where(((5.5 <= df_timeseries["ph"]) & (df_timeseries["ph"] < 6.0))
                 | ((9.0 < df_timeseries["ph"]) & (df_timeseries["ph"] <= 9.5)), 40.0, 0.0)))

    print("\n5. Normalisasi MinMax pada 8 fitur model...")
    scaler = MinMaxScaler()
    df_scaled = df_timeseries.copy()
    df_scaled[FITUR_X] = scaler.fit_transform(df_scaled[FITUR_X])

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(SCALER_PATH), exist_ok=True)

    with open(SCALER_PATH, "wb") as file:
        pickle.dump(scaler, file)
    df_scaled.to_csv(OUT_CSV, index=False)

    # Laporan ringkas.
    crossing = df_timeseries.groupby("Cycle_ID")["RUL"].max()
    print("\n" + "=" * 62)
    print("PROSES SELESAI!")
    print(f"  Dataset : {OUT_CSV} ({len(df_scaled):,} baris)")
    print(f"  Scaler  : {SCALER_PATH}")
    print(f"  Siklus  : {df_timeseries['Cycle_ID'].nunique()}")
    print(f"  RUL max : {df_timeseries['RUL'].max()} jam "
          f"({df_timeseries['RUL'].max() / 24:.0f} hari)")
    print(f"  RUL=0 (detik alarm)      : {(df_timeseries['RUL'] == 0).mean() * 100:.1f}% baris")
    print(f"  Waktu crossing (median)  : {crossing.median():.0f} jam / siklus")
    print(f"  Severity                : {df_timeseries.groupby('Cycle_ID')['severity'].first().value_counts().to_dict()}")
    print("=" * 62)


if __name__ == "__main__":
    main()