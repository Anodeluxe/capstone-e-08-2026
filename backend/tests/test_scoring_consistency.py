"""
Test Konsistensi Skor — `app/ml/scoring_model.py` vs `scoring_service.py`
─────────────────────────────────────────────────────────────────────────
Mirror skoring di folder ML harus identik persis dengan implementasi
produksi (`backend/app/services/scoring_service.py`). Karena generator v2
menurunkan RUL dari `score_overall <= 60`, ketidaksinkronan di sini akan
membuat target training meleset dari momen alarm asli.

Yang dibandingkan:
  1. Sub-score, per-use-point, overall (selisih < 1e-9)
  2. VALVES_TO_CLOSE
  3. Jaminan generator v2: kombinasi END (akhir siklus) harus
     `overall <= 60` di implementasi produksi → alarm pasti ter-picu.

Menjalankan:  cd backend && venv_fikar/bin/python -m pytest tests/test_scoring_consistency.py -q
"""

import sys
from pathlib import Path

import numpy as np
import pytest

from app.schemas.sensor import ESP32SensorPayload
from app.services.scoring_service import compute_scores

ML_DIR = Path(__file__).resolve().parents[1] / "app" / "ml"
sys.path.insert(0, str(ML_DIR))

# Satu-satunya sumber kebenaran bobot/ambang = mirror ML (scoring_model).
# scoring_service memakai nilai yang sama (MAKA konsisten).
from scoring_model import (  # noqa: E402
    DEFAULT_SCORE_THRESHOLD,
    USE_POINT_THRESHOLDS,
    USE_POINT_WEIGHT_OVERRIDES,
    ph_score,
    tds_score,
    turbidity_score,
    temperature_score,
)

RESULT_KEYS = ("overall", "bathroom", "kitchen", "laundry", "garden",
               "ph_score", "turbidity_score", "tds_score", "temperature_score")


def _mirror(payload: ESP32SensorPayload) -> dict:
    """Skor via mirror ML — logika `scoring_model.py`."""
    ph_s = float(ph_score(payload.ph))
    turb_s = float(turbidity_score(payload.turbidity))
    tds_s = float(tds_score(payload.tds))
    temp_s = float(temperature_score(payload.temperature))

    per_point = {}
    for point, w in USE_POINT_WEIGHT_OVERRIDES.items():
        per_point[point] = round(
            ph_s * w["ph"] + turb_s * w["turbidity"]
            + tds_s * w["tds"] + temp_s * w["temperature"], 2
        )
    overall = round(sum(per_point.values()) / len(per_point), 2)

    valves = [p for p, thr in USE_POINT_THRESHOLDS.items() if per_point[p] < thr]

    return {"overall": overall, "bathroom": per_point["bathroom"],
            "kitchen": per_point["kitchen"], "laundry": per_point["laundry"],
            "garden": per_point["garden"], "valves_to_close": valves,
            "ph_score": round(ph_s, 2), "turbidity_score": round(turb_s, 2),
            "tds_score": round(tds_s, 2), "temperature_score": round(temp_s, 2)}


def _prod(payload: ESP32SensorPayload):
    return compute_scores(payload)


@pytest.mark.parametrize("ph,turb,tds,temperature", [
    (7.2, 0.5, 180.0, 26.0),
    (4.0, 30.0, 1200.0, 28.0),
    (6.2, 2.0, 350.0, 27.0),
    (9.2, 12.0, 750.0, 22.0),
    (5.5, 1.0, 300.0, 24.0),
])
def test_identical_on_fixtures(ph, turb, tds, temperature):
    payload = ESP32SensorPayload(ph=ph, turbidity=turb, tds=tds,
                                 temperature=temperature, water_level=50.0)
    m, p = _mirror(payload), _prod(payload)
    for key in RESULT_KEYS:
        assert abs(m[key] - getattr(p, key)) < 1e-9, key
    assert m["valves_to_close"] == list(getattr(p, "valves_to_close"))


def test_identical_on_random_readings():
    rng = np.random.default_rng(2026)
    n = 6000
    ph = rng.uniform(1.0, 13.5, n)
    turb = rng.uniform(0.05, 55.0, n)
    tds = rng.uniform(10.0, 1800.0, n)
    temperature = rng.uniform(8.0, 45.0, n)
    for i in range(n):
        payload = ESP32SensorPayload(ph=round(float(ph[i]), 2),
                                     turbidity=round(float(turb[i]), 2),
                                     tds=round(float(tds[i]), 2),
                                     temperature=round(float(temperature[i]), 2),
                                     water_level=50.0)
        m, p = _mirror(payload), _prod(payload)
        for key in RESULT_KEYS:
            assert abs(m[key] - getattr(p, key)) < 1e-9, (i, key)
        assert m["valves_to_close"] == list(getattr(p, "valves_to_close")), i


def test_end_of_cycle_always_crosses_threshold():
    """Akhir siklus generator v2 — kombinasi END harus `overall <= 60`.

    Nilai SENSOR di bawah = hasil inverse band sub-score 0/25/40 (hasil
    median data nyata) yang dipakai generator v2 sebagai kondisi akhir:
      heavy  : ph 5.23(0)   turb 34.2(0)  tds 1442(0)
      medium : ph 5.23(0)   turb 18(25)   tds 1021(20)
      mild   : ph 5.74(40)  turb 9.0(55)  tds 612(50)
    Suhu dipakai 29°C (skor 100) — skor bertambah PARAH jika lebih panas.
    """
    end_sensor = [
        (5.23, 34.2, 1442.0),
        (5.23, 18.0, 1021.0),
        (5.74, 9.0, 612.0),
    ]
    for ph, turb, tds in end_sensor:
        payload = ESP32SensorPayload(ph=ph, turbidity=turb, tds=tds,
                                     temperature=29.0, water_level=50.0)
        p = _prod(payload)
        assert p.overall <= DEFAULT_SCORE_THRESHOLD, (ph, turb, tds, p.overall)


def test_clean_start_never_triggers():
    """Kondisi awal siklus (air sehat) TIDAK boleh memicu alarm dini."""
    for ph in (6.5, 7.0, 8.0):
        for turb in (0.1, 0.5, 1.0):
            payload = ESP32SensorPayload(ph=ph, turbidity=turb, tds=180.0,
                                         temperature=26.0, water_level=50.0)
            p = _prod(payload)
            assert p.overall > DEFAULT_SCORE_THRESHOLD, (ph, turb, p.overall)
