"""
Data Generator v3 — Granularitas Per Jam, RUL berancor skor produksi
──────────────────────────────────────────────────────────────────────
Menghasilkan data time-series sintetis untuk training model RUL dengan
satuan PER JAM dan siklus 90–120 hari (2160–2880 jam), sesuai riset:
toren wajib dikuras minimal 3 bulan sekali.

PEMBEDA UTAMA dibanding data_generator_hourly.py (v1):
  1. RUL TIDAK lagi "jam sampai rata-rata air kotor", melainkan
     "jam sampai score_overall bertahan <= 80 selama 24 jam" (rolling
     mean 24 jam) — persis ambang early-warning di
     `app/services/prediction_service.py` dan logika skoring
     `app/services/scoring_service.py`. Target model kini sama dengan
     momen keputusan sistem produksi.
  2. Profil nilai sensor diambil dari distribusi nyata dataset
     `watera.csv` per JENDELA SKOR (bukan dari label `potability` yang
     imbalanced & noisy). Nilai tiap anchor = median baris dataset yang
     sub-score-nya berada dalam ±12.5 dari anchor tsb.
  3. Dinamika lebih realistis:
     - Suhu: siklus diurnal sinusoid (bukan uniform konstan).
     - Noise: AR(1) autocorrelated (bukan iid) = drift sensor asli.
     - Sebagian siklus mendapat event kontaminasi/pengisian yang pulih.
     - Sebagian siklus mendapat heatwave / cold snap.
     - Arah degradasi pH (ke asam / ke basa) dipilih acak per siklus.
  4. Tingkat keparahan akhir bervariasi per siklus (ringan/sedang/berat)
     namun SELALU menjamin crossing score <= 80 di akhir siklus.

Skoring memakai `app/ml/scoring_model.py`, mirror dari
`app/services/scoring_service.py` (diverifikasi oleh pytest).

Output:
  - data/processed/data_toren_hourly_v3.csv  (9 kolom siap training)
    Cycle_ID, Jam, RUL, elapsed_hours, ph, tds, turbidity, temperature,
    score_overall
"""

import os

import numpy as np
import pandas as pd

from scoring_model import (overall_scores, ph_score, tds_score,
                           turbidity_score)

# ============================================================================
# 1. KONSTANTA GENERATOR
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(BASE_DIR, "data", "raw", "watera.csv")
OUT_CSV = os.path.join(BASE_DIR, "data", "processed", "data_toren_hourly_v3.csv")

# Kontrak output: hanya kolom yang dipakai training XGB.
OUT_COLUMNS = [
    "Cycle_ID", "Jam", "RUL", "elapsed_hours",
    "ph", "tds", "turbidity", "temperature", "score_overall",
]

JUMLAH_SIKLUS = 1000
RUL_CAP = 2880  # jam (120 hari)
SUSTAIN_HOURS = 24  # skor harus bertahan <= 80 selama 24 jam

# Patokan geometri siklus: suhu air toren Indonesia.
TEMP_BASE = 27.0
TEMP_AMPLITUDE = 2.5
TEMP_PEAK_HOUR = 14  # terpanas sekitar pukul 14.00
PHI_AR1 = 0.80  # autoregresi noise sensor
NOISE_SIGMA = {"ph": 0.06, "turbidity": 0.12, "tds": 10.0, "temperature": 0.30}

# Tingkat keparahan akhir siklus (target sub-score tiap parameter).
# Semua kombinasi menjamin score_overall akhir <= 80 (lihat docstring).
END_SCORES = {
    "heavy": {"ph": 0, "turbidity": 0, "tds": 0},
    "medium": {"ph": 0, "turbidity": 25, "tds": 20},
    "mild": {"ph": 40, "turbidity": 55, "tds": 20},
}

# Kadang siklus mulai dengan kondisi yang tidak 100% sempurna (realistis).
START_SCORES = {
    "ph": 100,
    "turbidity": 100,
    "tds": 100,
}


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


def _score_window_median(df, col, score_fn, scores, fallbacks, arm=None, tol=12.5):
    """Median nilai sensor pada jendela ±tol di sekitar tiap anchor skor."""
    base = df[col].values
    mask = np.ones(len(base), dtype=bool) if arm is None else (
        base < 7.5 if arm == "acid" else base > 7.5)
    values = base[mask]
    scored = score_fn(values)

    out = []
    for score, fallback in zip(scores, fallbacks):
        vals = values[np.abs(scored - score) <= tol]
        out.append(float(np.median(vals)) if len(vals) >= 30 else fallback)
    return np.array(out)


def build_inverse_maps(df):
    """
    Bangun peta inverse sub-score -> nilai sensor.
    Map: (xp ascending sub-score, fp nilai sensor) untuk np.interp.
    Nilai anchor = median watera.csv pada jendela skor ±12.5; bila jendela
    terlalu kosong (<30 baris), pakai nilai standar sebagai fallback.
    """
    maps = {}

    # Turbidity: 100(<=1) 80(5) 55(10) 25(25) 0(50)
    maps["turbidity"] = (
        np.array([0, 25, 55, 80, 100]),
        _score_window_median(df, "turbidity", turbidity_score,
                             [0, 25, 55, 80, 100],
                             [50.0, 25.0, 10.0, 5.0, 0.7]),
    )

    # TDS: 100(<=300) 80(500) 50(900) 20(1200) 0(1500)
    maps["tds"] = (
        np.array([0, 20, 50, 80, 100]),
        _score_window_median(df, "tds", tds_score,
                             [0, 20, 50, 80, 100],
                             [1500.0, 1200.0, 900.0, 500.0, 220.0]),
    )

    # pH: dua lengan (asam / basa) dari pusat ~7.15.
    for arm, fallbacks in (
        ("acid", [5.0, 5.5, 6.0, 7.15]),
        ("base", [10.0, 9.5, 9.0, 7.15]),
    ):
        maps[f"ph_{arm}"] = (
            np.array([0, 40, 70, 100]),
            _score_window_median(df, "ph", ph_score, [0, 40, 70, 100],
                                 fallbacks, arm=arm),
        )
    return maps


def invert_subscore(maps, param, s, arm=None):
    """Mapping sub-score -> nilai sensor via interpolasi anchor."""
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


def _event_window(rng, n):
    """Bobot event 0..1 dengan ekor eksponensial, mulai di 10–50% siklus."""
    start_i = int(n * (0.10 + 0.40 * rng.random()))
    dur = int(rng.integers(24, 73))
    w = np.zeros(n)
    seg = np.arange(start_i, min(start_i + dur, n))
    w[seg] = np.exp(-np.arange(len(seg)) / (dur / 3.0))
    return w


def _sustained_crossing(overall, hours=SUSTAIN_HOURS):
    """Indeks pertama saat rolling mean `hours` <= 80, atau None."""
    rolling = pd.Series(overall).rolling(hours, min_periods=hours).mean()
    below = (rolling <= 80.0).to_numpy()
    return int(np.argmax(below)) if below.any() else None


def generate_cycle(rng, siklus, maps):
    """Bangun satu siklus toren; kembalikan (DataFrame 9 kolom, severity)."""
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
    temp = _diurnal_temperature(jam, rng) + rng.normal(0.0, 1.0)

    # Event kontaminasi singkat yang pulih (bump turbidity + tds ringan).
    if rng.random() < 0.12:
        peak = 2.0 + 0.8 * rng.random()
        w = _event_window(rng, total_jam)
        turb = turb * (1.0 + (peak - 1.0) * w)
        tds = tds * (1.0 + 0.30 * (peak - 1.0) * w)

    # Event suhu ekstrem: heatwave (15%) atau cold snap (5%).
    temp_event = rng.random()
    if temp_event < 0.15:
        temp = temp + rng.uniform(6.0, 14.0) * _event_window(rng, total_jam)
    elif temp_event < 0.20:
        temp = temp - rng.uniform(8.0, 15.0) * _event_window(rng, total_jam)

    # Clamp fisik.
    ph = np.clip(ph, 3.0, 11.0)
    turb = np.clip(turb, 0.05, 60.0)
    tds = np.clip(tds, 10.0, 1800.0)
    temp = np.clip(temp, 5.0, 45.0)

    # Skor produksi aktual per jam (persis seperti di backend).
    overall = overall_scores(ph, tds, turb, temp)

    # RUL = jam tersisa sampai score_overall bertahan <= 80 selama 24 jam.
    # Siklus yang tidak pernah menyeberang ditolak (di-resample di main).
    crossing_elapsed = _sustained_crossing(overall)
    if crossing_elapsed is None:
        return None, None

    # Truncate siklus TEPAT di jam alarm (rolling mean <= 80 -> RUL 0).
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
    elapsed_fraction = elapsed_hours / max(total_jam - 1, 1)

    df = pd.DataFrame({
        "Cycle_ID": siklus,
        "Jam": jam,
        "RUL": rul.astype(int),
        "elapsed_hours": elapsed_fraction,
        "ph": ph,
        "tds": tds,
        "turbidity": turb,
        "temperature": temp,
        "score_overall": overall,
    })
    return df, severity


# ============================================================================
# 4. PIPELINE UTAMA
# ============================================================================
def main():
    print("=" * 62)
    print("DATA GENERATOR v3 — RUL BERANCOR SKOR PRODUKSI (SUSTAINED 24J <= 80)")
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
    severity_by_cycle = {}
    for siklus in range(1, JUMLAH_SIKLUS + 1):
        for _ in range(20):
            df_cycle, severity = generate_cycle(rng, siklus, maps)
            if df_cycle is not None:
                break
        if df_cycle is None:
            raise RuntimeError(f"Siklus {siklus} tidak pernah menyeberang skor 80")
        frames.append(df_cycle)
        severity_by_cycle[siklus] = severity
        if siklus % 250 == 0:
            print(f"   ... {siklus}/{JUMLAH_SIKLUS}")
    df_timeseries = pd.concat(frames, ignore_index=True)
    print(f"   -> {len(df_timeseries):,} baris dibuat.")

    print("\n4. Menyiapkan 9 kolom output...")
    df_timeseries = df_timeseries.sort_values(["Cycle_ID", "Jam"], ascending=[True, True])

    # elapsed_hours sudah berupa fraksi per siklus (0-1).
    df_out = df_timeseries[OUT_COLUMNS]

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df_out.to_csv(OUT_CSV, index=False)

    # Laporan ringkas.
    crossing = df_timeseries.groupby("Cycle_ID")["RUL"].max()
    print("\n" + "=" * 62)
    print("PROSES SELESAI!")
    print(f"  Dataset : {OUT_CSV} ({len(df_out):,} baris, {len(OUT_COLUMNS)} kolom)")
    print(f"  Siklus  : {df_timeseries['Cycle_ID'].nunique()}")
    print(f"  RUL max : {df_timeseries['RUL'].max()} jam "
          f"({df_timeseries['RUL'].max() / 24:.0f} hari)")
    print(f"  RUL=0 (detik alarm)      : {(df_timeseries['RUL'] == 0).mean() * 100:.1f}% baris")
    print(f"  Waktu crossing (median)  : {crossing.median():.0f} jam / siklus")
    severity_counts = pd.Series(list(severity_by_cycle.values())).value_counts().to_dict()
    print(f"  Severity                : {severity_counts}")
    print("=" * 62)


if __name__ == "__main__":
    main()