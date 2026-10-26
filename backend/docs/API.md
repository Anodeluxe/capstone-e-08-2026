# API Reference — Toren Monitoring Backend

Dokumen ini adalah **sumber acuan tunggal** untuk semua endpoint HTTP & WebSocket
yang disediakan backend FastAPI. Tujuannya: siapa pun (manusia atau AI agent) bisa
memelihara, memanggil, dan mengubah API hanya dengan membaca file ini — tanpa harus
membaca ulang seluruh kode.

| | |
|---|---|
| Versi API | `1.0.0` (dari `FastAPI(version="1.0.0")` di `app/main.py`) |
| Total endpoint | **22 REST** + `GET /health` + `WS /ws` |
| Sumber kebenaran | `backend/app/api/v1/*.py` + `backend/app/main.py` |
| Spesifikasi mesin | `GET /openapi.json` (runtime), Swagger: `GET /docs`, Redoc: `GET /redoc` |
| Terakhir disinkronkan | 26 Oktober 2026 (diverifikasi terhadap server produksi) |

> Jika dokumen ini dan kode berbeda, **kode menang**. Perbarui dokumen ini pada
> commit yang sama saat mengubah endpoint (lihat §12).

---

## 1. Ringkasan cepat

```bash
# Health
curl http://localhost:8005/health

# Data terakhir + semua yang dibutuhkan dashboard
curl http://localhost:8005/api/v1/dashboard/summary

# Riwayat 24 jam
curl "http://localhost:8005/api/v1/sensors/history?hours=24"

# Buka/tutup valve (butuh X-API-Key bila API_KEY diset)
curl -X POST http://localhost:8005/api/v1/valves/bathroom/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"action":"close","reason":"Perbaikan pipa"}'
```

---

## 2. Base URL & lingkungan

| Lingkungan | Base URL |
|---|---|
| Development (host) | `http://localhost:8000` |
| Docker Compose (host-only) | `http://localhost:8005` → container `backend:8000` |
| Produksi (Cloudflare Tunnel) | `https://aminu.irsad.site` |

- Prefix semua endpoint bisnis: **`/api/v1`**.
- Pengecualian (tanpa prefix): `GET /health`, `WS /ws`, `GET /docs`, `GET /redoc`, `GET /openapi.json`.
- Frontend memakai `NEXT_PUBLIC_API_URL` (contoh: `https://aminu.irsad.site/api/v1`) sebagai `baseURL` axios di `frontend/lib/api.ts`.
- CORS diatur oleh `ALLOWED_ORIGINS` (dipisah koma). `allow_credentials=true`, semua method & header diizinkan.

---

## 3. Konvensi

### 3.1 Autentikasi

Ada **dua mekanisme independen**, dan hanya satu endpoint yang memakainya:

| Mekanisme | Header | Dipakai di |
|---|---|---|
| JWT Bearer | `Authorization: Bearer <token>` | `GET /api/v1/auth/me` (wajib), `POST /api/v1/valves/{id}/command` (opsional) |
| API Key | `X-API-Key: <key>` | `POST /api/v1/valves/{id}/command` |

Detail:

- JWT dibuat oleh `POST /api/v1/auth/login`, algoritma **HS256**, umur **24 jam**,
  payload `{ "sub": <username>, "role": <role>, "iat": ..., "exp": ... }`,
  ditandatangani dengan `SECRET_KEY`.
- Endpoint lain (sensors, dashboard, predictions, drain-logs, notifications)
  **tidak memerlukan autentikasi** (sesuai desain dashboard internal).
- `POST /valves/{id}/command` memakai `verify_api_key`:
  - `API_KEY` **kosong** → autentikasi dimatikan, `triggered_by` jatuh ke `user:operator_local`.
  - `API_KEY` **diset** dan header `X-API-Key` salah/tidak ada → **403**.
  - `API_KEY` diset dan cocok → `triggered_by = user:<nilai header>`.
  - Bila Bearer token valid dikirim, identitas JWT yang dipakai (`user:<username>`).
- Akun demo terdaftar di `DEFAULT_USERS` pada `app/core/security.py` (user: `admin`, `operator`).
  Password masih hardcoded untuk keperluan demo — **wajib diganti sebelum produksi**
  (ganti hash di `DEFAULT_USERS` atau pindahkan ke DB).

> ⚠️ **Cek produksi:** bila `API_KEY` kosong di `backend/.env`, siapa pun yang bisa
> menjangkau backend dapat membuka/menutup valve. Pastikan `API_KEY` terisi dan
> `X-API-Key` dikirim frontend.

### 3.2 Timestamp & timezone

- Semua waktu di database disimpan sebagai **naive UTC** (`datetime.utcnow()`).
- Saat diserialisasi, backend menambahkan offset UTC sehingga JSON selalu ISO-8601 UTC:

  | Jalur serialisasi | Contoh output |
  |---|---|
  | Pydantic schema (`SensorReadingOut`, `ValveStateOut`, `PredictionResultOut`, dll.) | `"2026-10-23T21:31:05.104878Z"` |
  | `model.to_dict()` / `utc_to_iso()` (dipakai `/dashboard/summary`, `/drain-logs/*`, `/sensors/export`, WS) | `"2026-10-23T21:31:05.104878+00:00"` |

  Keduanya UTC; perbedaan hanya suffix `+00:00` vs `Z`. Frontend wajib mem-parse ISO-8601
  dan mengonversi ke WIB (+07:00).
- Parameter `hours` selalu berarti **jam ke belakang dari `utcnow()`**.

### 3.3 Format error

Format standar FastAPI:

```json
{ "detail": "Pesan error yang bisa ditampilkan ke operator." }
```

Error validasi query/body (tipe salah, di luar rentang, enum tidak valid) dikembalikan
sebagai **422** dengan struktur `{"detail":[{"loc":[...],"msg":"...","type":"..."}]}`.

| Kode | Kapan |
|---|---|
| 200 | Sukses |
| 307 | Path tanpa trailing slash untuk resource yang dideklarasikan `"/"` (`/valves`, `/drain-logs`) — ikuti `Location`, atau kirim trailing slash |
| 400 | `valve_id` tidak valid pada endpoint valves |
| 401 | `GET /auth/me` tanpa/invalid Bearer token |
| 403 | `X-API-Key` salah/tidak ada saat `API_KEY` diset |
| 404 | Resource tidak ada (mis. `/sensors/latest` saat belum ada data, valve/drain log tidak ditemukan) |
| 422 | Validasi query/body gagal |
| 500 | Bug server — lihat `docker logs toren_backend` |

### 3.4 Nilai & enum yang dipakai lintas endpoint

| Istilah | Nilai valid | Keterangan |
|---|---|---|
| `valve_id` | `bathroom`, `kitchen`, `laundry`, `garden` | 4 titik pemakaian air |
| `action` (valve) | `open`, `close` | |
| `channel` (notifikasi) | `whatsapp`, `email`, `all` | |
| `mode` (prediksi) | `auto`, `ml`, `linear` | `auto` = coba XGBoost lalu fallback regresi |
| Skor kualitas | `0.0 – 100.0` | 2 desimal; makin tinggi makin baik |
| Ambang tutup otomatis | bathroom `< 60`, kitchen `< 65`, laundry `< 45`, garden `< 30` | lihat `app/services/scoring_service.py` |
| `is_open` | `true` = valve terbuka (air mengalir) | |

### 3.5 Trailing slash & redirect

`GET /api/v1/valves` → **307** ke `/api/v1/valves/` (sama untuk `/drain-logs`).
Gunakan `curl -L` atau kirim trailing slash agar tidak bingung saat debugging.

### 3.6 Side effect per endpoint

API ini bukan API baca-saja. Ringkasan efek samping:

| Endpoint | DB | MQTT publish | WS broadcast | Kirim notifikasi |
|---|---|---|---|---|
| `GET /sensors/*`, `/dashboard/*`, `/predictions/latest`, `/drain-logs/active`, `/drain-logs/readiness`, `/drain-logs/` | baca | – | – | – |
| `GET /predictions/run` | **tulis** `prediction_results` | – | – | – |
| `POST /valves/{id}/command` | **tulis** `valve_states` + `valve_override_logs` | ✅ `toren/valves/cmd` | ✅ `valve_status` | – |
| `POST /drain-logs/start` | **tulis** `drain_logs` (menutup siklus aktif) | – | – | – |
| `POST /drain-logs/{id}/end` | **tulis** `drain_logs` | – | – | – |
| `POST /notifications/test` | – (lihat §11) | – | – | ✅ |
| `POST /notifications/trigger-ews` | – (lihat §11) | – | – | ✅ |
| `POST /auth/login` | – | – | – | – |

---

## 4. Indeks endpoint

### Auth — `app/api/v1/auth.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| POST | `/api/v1/auth/login` | – | Tukar username/password dengan JWT 24 jam |
| GET | `/api/v1/auth/me` | Bearer **wajib** | Profil user yang sedang login |

### Sensors — `app/api/v1/sensors.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/sensors/latest` | – | Reading terakhir |
| GET | `/api/v1/sensors/history` | – | Deret reading dalam N jam |
| GET | `/api/v1/sensors/anomalies` | – | Reading yang ditandai sudden change |
| GET | `/api/v1/sensors/export` | – | Unduh CSV untuk analisis ML offline |

### Valves — `app/api/v1/valves.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/valves/` | – | Status 4 valve |
| GET | `/api/v1/valves/{valve_id}` | – | Status satu valve |
| POST | `/api/v1/valves/{valve_id}/command` | API Key / Bearer | Buka/tutup manual (override) |
| GET | `/api/v1/valves/{valve_id}/overrides` | – | Riwayat override satu valve |
| GET | `/api/v1/valves/overrides/all` | – | Riwayat override semua valve |

### Predictions — `app/api/v1/predictions.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/predictions/latest` | – | 10 hasil prediksi terakhir |
| GET | `/api/v1/predictions/run` | – | Jalankan prediksi on-demand (menulis DB) |

### Dashboard — `app/api/v1/dashboard.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | – | Semua data halaman utama dalam 1 request |

### Drain Logs — `app/api/v1/drain_logs.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/drain-logs/active` | – | Siklus drain aktif (atau `null`) |
| GET | `/api/v1/drain-logs/readiness` | – | Kesiapan data untuk inferensi ML |
| GET | `/api/v1/drain-logs/` | – | Riwayat siklus drain |
| POST | `/api/v1/drain-logs/start` | – | Mulai siklus baru |
| POST | `/api/v1/drain-logs/{drain_log_id}/end` | – | Tutup siklus |

### Notifications — `app/api/v1/notifications.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/api/v1/notifications/status` | – | Status kanal email/WAHA/Fonnte |
| POST | `/api/v1/notifications/test` | – | Kirim pesan uji |
| POST | `/api/v1/notifications/trigger-ews` | – | Simulasi alert early warning |

### System — `app/main.py`
| Method | Path | Auth | Ringkas |
|---|---|---|---|
| GET | `/health` | – | Status aplikasi, MQTT, jumlah klien WS |
| WS | `/ws` | – | Stream real-time ke dashboard |

---

## 5. Referensi per grup

### 5.1 Auth

#### `POST /api/v1/auth/login`

Body:

| Field | Tipe | Wajib | Catatan |
|---|---|---|---|
| `username` | string | ✅ | di-`strip()` dan di-lowercase |
| `password` | string | ✅ | |

```bash
curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"operator","password":"<password>"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....",
  "token_type": "bearer",
  "user": { "username": "operator", "role": "operator", "full_name": "Toren Operator" }
}
```

Error: **401** `{"detail":"Username atau password tidak sesuai."}`

#### `GET /api/v1/auth/me`

Header: `Authorization: Bearer <token>`

```json
{ "username": "operator", "role": "operator", "full_name": "Toren Operator" }
```

Error: **401** `{"detail":"Authentication required. Provide a valid Bearer token."}`

---

### 5.2 Sensors

Model respons `SensorReadingOut`:

| Field | Tipe | Keterangan |
|---|---|---|
| `id` | int | PK auto-increment |
| `timestamp` | ISO-8601 UTC | Waktu sampel (dari RTC ESP32 atau waktu server) |
| `ph` | float | 0–14 |
| `turbidity` | float | NTU |
| `tds` | float | ppm |
| `temperature` | float | °C |
| `water_level` | float | % (0–100) |
| `score_overall` | float \| null | Rata-rata 4 skor titik pemakaian |
| `score_bathroom` / `score_kitchen` / `score_laundry` / `score_garden` | float \| null | 0–100 |
| `is_sudden_change` | bool | Diisi oleh `anomaly_service` |
| `anomaly_parameter` | string \| null | Nama parameter pemicu (`ph`, `tds`, `turbidity`, `temperature`, `water_level`) |

#### `GET /api/v1/sensors/latest`

Tanpa parameter. Mengembalikan 1 objek `SensorReadingOut`.

```json
{
  "id": 10609,
  "timestamp": "2026-10-23T21:31:05.104878Z",
  "ph": 7.34, "turbidity": 1698.23, "tds": 716.22,
  "temperature": 28.25, "water_level": 80.0,
  "score_overall": 53.75, "score_bathroom": 57.5, "score_kitchen": 55.0,
  "score_laundry": 47.5, "score_garden": 55.0,
  "is_sudden_change": false, "anomaly_parameter": null
}
```

Error: **404** `{"detail":"No sensor readings yet."}` bila tabel kosong.

#### `GET /api/v1/sensors/history`

| Query | Tipe | Default | Rentang | Keterangan |
|---|---|---|---|---|
| `hours` | int | `24` | 1–720 | Jendela lookback |
| `parameter` | string \| null | `null` | – | **Diterima tetapi belum diimplementasikan** (lihat §11) |

Respons: `SensorReadingOut[]`, urut **timestamp ASC**.

```bash
curl "http://localhost:8005/api/v1/sensors/history?hours=6"
```

#### `GET /api/v1/sensors/anomalies`

| Query | Tipe | Default | Rentang |
|---|---|---|---|
| `hours` | int | `72` | 1–720 |

Respons: `SensorReadingOut[]` dengan `is_sudden_change=true`, urut **timestamp DESC**.

#### `GET /api/v1/sensors/export`

| Query | Tipe | Default | Rentang |
|---|---|---|---|
| `hours` | int | `720` (30 hari) | 1–2160 (90 hari) |

Respons: `text/csv` dengan header `Content-Disposition: attachment; filename=sensor-readings.csv`.

Kolom CSV (urutan tetap):

```
timestamp,ph,tds,turbidity,temperature,water_level,score_overall,
score_bathroom,score_kitchen,score_laundry,score_garden,
is_sudden_change,anomaly_parameter
```

Catatan: `timestamp` pada CSV memakai format ISO dari `utc_to_iso()` (`...+00:00`),
urut ASC, dan kolom boolean ditulis sebagai `True`/`False` (Python), bukan `true`/`false`.

---

### 5.3 Valves

Model `ValveStateOut`:

```json
{
  "id": "bathroom",
  "is_open": true,
  "last_changed_at": "2026-10-23T21:31:05.117201Z",
  "last_changed_by": "esp32_ack",
  "quality_score_at_close": 53.75
}
```

`last_changed_by` berisi salah satu: `system` (otomatis), `user:<id>` (manual),
`esp32_ack` (konfirmasi perangkat).

#### `GET /api/v1/valves/`

Respons: `ValveStateOut[]` (4 baris, **tanpa jaminan urutan** — jangan andalkan urutan,
index sendiri berdasarkan `id`).

#### `GET /api/v1/valves/{valve_id}`

Error: **404** `{"detail":"Valve '<id>' not found."}`.
Catatan: `valve_id` tidak divalidasi sebagai enum di sini — id sembarang akan 404.

#### `POST /api/v1/valves/{valve_id}/command`

Body:

| Field | Tipe | Wajib | Catatan |
|---|---|---|---|
| `action` | `"open"` \| `"close"` | ✅ | |
| `reason` | string \| null | – | Maks 300 karakter; disimpan di `valve_override_logs.reason` |

Alur yang terjadi:

1. Validasi `valve_id` terhadap `{bathroom, kitchen, laundry, garden}` → jika tidak valid: **400**.
2. Publish MQTT ke `toren/valves/cmd` dengan payload
   `{"valve_id": "...", "action": "open|close", "triggered_by": "user:<id>"}` (QoS 1, non-retained).
3. Update `valve_states` secara **optimistis** (tanpa menunggu ack).
4. Catat override ke `valve_override_logs` (hanya jika `triggered_by` diawali `user:`).
5. Broadcast WS `valve_status` ke semua klien.

```bash
curl -X POST http://localhost:8005/api/v1/valves/kitchen/command \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"action":"close","reason":"TDS tinggi"}'
```

Respons: `ValveStateOut` (state setelah perubahan).

Error: **400** `{"detail":"Invalid valve_id: <x>"}`, **403** (API key salah).

> State akhir yang benar tetap datang dari ESP32 lewat `toren/valves/status`
> yang men-set `last_changed_by = "esp32_ack"`. Jika ESP32 offline, state DB
> tetap berubah (optimistis) tetapi perangkat tidak benar-benar bergerak.

#### `GET /api/v1/valves/{valve_id}/overrides`

| Query | Tipe | Default | Rentang |
|---|---|---|---|
| `limit` | int | `50` | bebas (tidak divalidasi) |

Respons: `ValveOverrideLogOut[]`, urut `overridden_at` DESC:

```json
[{
  "id": 4, "valve_id": "bathroom", "action": "open",
  "reason": "Perbaikan pipa", "score_at_override": 53.75,
  "overridden_at": "2026-10-26T07:58:40.237478Z",
  "user_id": "operator_local"
}]
```

Error: **400** bila `valve_id` tidak valid.

#### `GET /api/v1/valves/overrides/all`

Sama seperti di atas, tetapi lintas valve. `limit` default `100`.

---

### 5.4 Predictions

Model `PredictionResultOut`:

| Field | Tipe | Keterangan |
|---|---|---|
| `id` | int | |
| `computed_at` | ISO-8601 UTC | Waktu prediksi dijalankan |
| `target_parameter` | string | Saat ini selalu `"score_overall"` |
| `valve_id` | string \| null | `null` untuk prediksi agregat |
| `days_until_threshold` | float \| null | `null` = di luar horizon / sudah di bawah ambang |
| `predicted_date` | ISO-8601 UTC \| null | Perkiraan tanggal melewati ambang |
| `confidence` | float \| null | 0.0–1.0 (untuk jalur ML = R²) |
| `model_used` | string | `xgb_v2_horizon_30d`, `linear_or_poly_regression`, atau `none` |
| `rul_hours` | float \| null | Remaining Useful Life (jam), khusus jalur ML |
| `notification_sent` | bool | Apakah early-warning sudah dikirim |

#### `GET /api/v1/predictions/latest`

Tanpa parameter. Mengembalikan **10** baris terakhir urut `computed_at` DESC.
Dijalankan otomatis tiap jam oleh APScheduler (`prediction_job`).

#### `GET /api/v1/predictions/run`

| Query | Tipe | Default | Rentang/Enum | Keterangan |
|---|---|---|---|---|
| `hours` | int | `169` | 6–720 | Lookback data skor |
| `mode` | string | `auto` | `auto` \| `ml` \| `linear` | Paksa jalur model |

Efek: **menulis** satu baris baru ke `prediction_results`.

```json
{
  "data_points": 168,
  "current_score": 53.75,
  "prediction": {
    "rul_hours": 420.0,
    "rul_days": 17.5,
    "days_until_threshold": 17.5,
    "predicted_date": "2026-11-13T04:00:00",
    "within_30d_window": true,
    "display_hint": "machine_learning_rul",
    "confidence": 0.91,
    "model_used": "xgb_v2_horizon_30d",
    "already_below_threshold": false,
    "trend_direction": "degrading",
    "is_early_warning_active": false
  }
}
```

Kunci `prediction` **bervariasi** menurut jalur:
- Jalur ML (`within_30d_window=true`): `rul_hours`, `rul_days`, `predicted_date`, `confidence`, `model_used`, `display_hint="machine_learning_rul"`.
- Jalur regresi: `display_hint="regression_eta"`, `within_30d_window=null`, `is_early_warning_active=false`.
- Di luar horizon 30 hari: `rul_hours`/`days_until_threshold`/`predicted_date` = `null`, `display_hint="expert_schedule_3_4_months"`.

Konsumen harus memperlakukan field sebagai **nullable** dan membaca `display_hint`
untuk memutuskan cara menampilkan.

Tanpa data: HTTP **200** dengan `{"error":"Not enough data for prediction.","data_points":0}`
(bukan 4xx).

---

### 5.5 Dashboard

#### `GET /api/v1/dashboard/summary`

Satu request untuk seluruh halaman utama. Tanpa parameter.

```json
{
  "latest_reading": { "...SensorReadingOut (via to_dict)" : "..." },
  "valve_states": [ { "id": "bathroom", "is_open": true, "...": "..." } ],
  "prediction": { "id": 104, "computed_at": "...Z", "...": "..." },
  "trend_24h": [
    { "hour": "2026-10-23T20:00:00+00:00", "avg_score": 54.1,
      "avg_ph": 7.3, "avg_turbidity": 1690.2, "avg_tds": 716.0 }
  ],
  "anomaly_count_24h": 0,
  "system_status": {
    "mqtt_connected": true,
    "last_reading_age_seconds": 123456.7
  }
}
```

Catatan:
- `latest_reading` = `null` bila belum ada data; `prediction` = `null` bila belum pernah jalan.
- `trend_24h` = agregasi **per jam** (`date_trunc('hour')`) dari 24 jam terakhir;
  hanya jam yang punya data yang muncul. Nilai `null` bila semua sampel jam itu kosong.
- `last_reading_age_seconds` bisa sangat besar bila ESP32 lama offline — ini indikator
  utama untuk mendeteksi device mati.

---

### 5.6 Drain Logs

Konsep: model ML butuh `elapsed_fraction` = `elapsed_hours / cycle_estimate_hours`
dari siklus drain aktif. Endpoint ini mengelola siklus tersebut.

`DrainLog` (bentuk respons):

```json
{
  "id": 1,
  "started_at": "2026-10-21T09:37:49.303003+00:00",
  "ended_at": null,
  "threshold_crossed_at": "2026-10-21T10:02:45.416834+00:00",
  "event_observed": true,
  "event_reason": "score_overall_lte_60",
  "cycle_estimate_hours": 2400.0,
  "created_by": "system:startup",
  "notes": null,
  "created_at": "2026-10-21T09:37:49.303652+00:00",
  "updated_at": "2026-10-21T10:02:45.421983+00:00",
  "is_active": true,
  "elapsed_hours": 118.35
}
```

`is_active` dan `elapsed_hours` adalah **field turunan** (dihitung saat serialisasi).

#### `GET /api/v1/drain-logs/active`

Respons: objek `DrainLog` atau `null`.

#### `GET /api/v1/drain-logs/readiness`

Menjawab: apakah siklus aktif punya cukup data untuk inferensi ML?
Ambang: `MIN_HOURLY_ROWS = 169` baris per jam (`app/ml/features.py`).

```json
{
  "ready_for_ml": false,
  "required_hourly_rows": 169,
  "hourly_rows": 35,
  "raw_rows": 10609,
  "hours_remaining": 134,
  "active_drain_log_id": 1,
  "cycle_started_at": "2026-10-21T09:37:49.303003+00:00",
  "latest_timestamp": "2026-10-23T21:31:05.104878+00:00",
  "latest_score_overall": 53.75,
  "threshold_crossed_at": "2026-10-21T10:02:45.416834+00:00"
}
```

Bila tidak ada siklus aktif: `{"ready_for_ml":false,"reason":"no_active_drain_cycle","required_hourly_rows":169}`.

#### `GET /api/v1/drain-logs/`

| Query | Tipe | Default | Rentang |
|---|---|---|---|
| `limit` | int | `20` | 1–100 |

Respons: `DrainLog[]`, urut `started_at` DESC.

#### `POST /api/v1/drain-logs/start`

Body (semua opsional):

| Field | Tipe | Default | Constraint |
|---|---|---|---|
| `cycle_estimate_hours` | float | `2400.0` | `> 0` |
| `created_by` | string | `"operator"` | maks 50 karakter |
| `notes` | string \| null | `null` | |

Efek samping: **menutup siklus aktif** (set `ended_at`) lalu membuat siklus baru.
Cache `elapsed_fraction` di-invalidate.

#### `POST /api/v1/drain-logs/{drain_log_id}/end`

Tanpa body. `ended_by` selalu diisi `"operator"`.
Bila `threshold_crossed_at` masih `null`, sistem men-set
`event_observed=false` dan `event_reason="cycle_ended_before_quality_threshold"`,
lalu menambahkan catatan penutupan ke `notes`.

Error: **404** `{"detail":"Drain cycle not found"}`.

---

### 5.7 Notifications

Kanal yang didukung: **Email** (SMTP), **WhatsApp via WAHA**, dan **Fonnte** (opsional).
Konfigurasi lewat env: `MAIL_*`, `WAHA_*`, `FONNTE_API_KEY`, `NOTIF_WHATSAPP_TARGETS`.

#### `GET /api/v1/notifications/status`

Melakukan HTTP call ke WAHA (`GET {WAHA_BASE_URL}/api/sessions/{session}`, timeout 5 s).

```json
{
  "email": { "configured": false, "server": "smtp.gmail.com", "sender": "" },
  "whatsapp": {
    "provider": "waha",
    "target_count": 1,
    "targets": ["08xxxxxxxxxx"],
    "waha": {
      "base_url": "http://waha:3000",
      "session": "default",
      "api_key_set": true,
      "connection": { "online": true, "session": "default", "status": "WORKING" }
    },
    "fonnte_configured": false
  }
}
```

Nilai `connection.status` yang mungkin: `WORKING`, `SCAN_QR_CODE`, `STOPPED`,
`NOT_FOUND`, `UNREACHABLE`, `HTTP_<kode>`.

#### `POST /api/v1/notifications/test`

Body:

| Field | Tipe | Default | Keterangan |
|---|---|---|---|
| `channel` | `"whatsapp"` \| `"email"` \| `"all"` | `"whatsapp"` | |
| `custom_target` | string \| null | `null` | Nomor (`08...`/`628...`) atau alamat email |
| `message` | string \| null | `null` | Teks kustom; jika kosong memakai template |

```json
{ "status": "completed", "results": { "whatsapp": true } }
```

Catatan penting: HTTP tetap **200** walau pengiriman gagal. Periksa boolean di `results`
(`whatsapp`, `email`) dan kunci `whatsapp_error` bila ada.

#### `POST /api/v1/notifications/trigger-ews`

Simulasi early warning (untuk demo/sidang).

| Field | Tipe | Default | Keterangan |
|---|---|---|---|
| `days_until` | float | `3.5` | Sisa hari menuju ambang |
| `target_valve` | string \| null | `"bathroom"` | Valve yang terdampak |
| `current_score` | float | `52.0` | Skor saat ini |

```json
{
  "status": "dispatched",
  "days_until": 3.5,
  "predicted_date": "29 Oct 2026",
  "results": { "email": false, "whatsapp": true }
}
```

---

### 5.8 System & WebSocket

#### `GET /health`

Tanpa prefix `/api/v1`, tanpa auth.

```json
{ "status": "ok", "mqtt_connected": true, "ws_clients": 0, "env": "production" }
```

Dipakai oleh `HEALTHCHECK` di `backend/Dockerfile` (interval 30 s) dan monitoring eksternal.

#### `WS /ws`

Lihat §6.

---

## 6. Kontrak WebSocket

| Item | Nilai |
|---|---|
| URL dev | `ws://localhost:8000/ws` |
| URL produksi | `wss://aminu.irsad.site/ws` (lewat Cloudflare Tunnel) |
| Auth | Tidak ada |
| Format pesan | JSON `{"type": <string>, "data": <object>}` |
| Keep-alive | Klien mengirim teks `"ping"`, server membalas `"pong"` |
| Reconnect | Tanggung jawab klien (disarankan exponential backoff) |

Tipe event yang dikirim server:

```jsonc
// 1. Setiap reading baru tersimpan
{
  "type": "sensor_update",
  "data": {
    "id": 10609, "timestamp": "2026-10-23T21:31:05.104878Z",
    "ph": 7.34, "turbidity": 1698.23, "tds": 716.22,
    "temperature": 28.25, "water_level": 80.0,
    "score_overall": 53.75, "score_bathroom": 57.5, "score_kitchen": 55.0,
    "score_laundry": 47.5, "score_garden": 55.0,
    "is_sudden_change": false, "anomaly_parameter": null,
    "scores": { "overall": 53.75, "bathroom": 57.5, "kitchen": 55.0, "laundry": 47.5, "garden": 55.0 }
  }
}

// 2. Valve berubah (otomatis, manual, atau ack ESP32)
{
  "type": "valve_status",
  "data": { "valve_id": "kitchen", "is_open": false, "triggered_by": "auto" }
}

// 3. Alert
{
  "type": "alert",
  "data": {
    "alert_type": "sudden_change",       // "sudden_change" | "early_warning" | "valve_closed"
    "message": "TDS naik drastis",
    "details": { "parameter": "tds", "current_score": 48.2, "reading": { "...": "..." } }
  }
}
```

Perhatikan: event `sensor_update` menambahkan objek `scores` (ringkasan skor) yang
**tidak ada** di respons REST `/sensors/*`.

Server tidak mengirim pesan di luar 3 tipe di atas. Broadcast dilakukan oleh
`ws_manager.broadcast_*` (`app/core/websocket_manager.py`).

---

## 7. Kontrak MQTT (sumber data API)

API ini hanya menampilkan data yang masuk lewat MQTT. Untuk maintain, pahami topiknya:

| Topik | Arah | QoS | Retain | Payload |
|---|---|---|---|---|
| `toren/sensors` | ESP32 → backend | 1 | tidak | `{"device_id":"toren_01","timestamp":<unix>,"ph":7.2,"turbidity":3.5,"tds":180.0,"temperature":28.1,"water_level":85.0}` |
| `toren/valves/status` | ESP32 → backend | 1 | tidak | `{"valve_id":"kitchen","is_open":false,"timestamp":<unix>}` |
| `toren/valves/cmd` | backend → ESP32 | 1 | tidak | `{"valve_id":"kitchen","action":"close","triggered_by":"user:operator"}` |
| `toren/status` | ESP32 (LWT) | – | ya | `{"device_id":"toren_01","online":true\|false}` |

Validasi payload sensor (`ESP32SensorPayload`):
`ph` 0–14, `turbidity` ≥ 0, `tds` ≥ 0, `temperature` 0–100, `water_level` 0–100;
semua float dibulatkan 2 desimal. `timestamp` opsional (epoch detik); bila kosong
dipakai waktu server. Payload tidak valid **di-drop** dan hanya muncul di log.

Pipeline tiap pesan sensor (urutan pasti, `app/mqtt/handlers.py`):

```
parse → scoring → anomaly detection → simpan DB → auto valve → WS broadcast → notifikasi
```

---

## 8. Alur data end-to-end

```
ESP32 ──(MQTT toren/sensors)──► broker Mosquitto ──► backend handler
                                                      │
                                                      ├─► TimescaleDB (sensor_readings)
                                                      ├─► auto close/open valve
                                                      │      └─(MQTT toren/valves/cmd)─► ESP32
                                                      ├─► WebSocket /ws ─► dashboard
                                                      └─► notifikasi (WAHA / SMTP)

Frontend ──(HTTPS /api/v1/*)──► FastAPI ──► TimescaleDB
         ──(WSS /ws)──────────► FastAPI
```

---

## 9. Environment variable yang mempengaruhi API

| Variabel | Default | Efek pada API |
|---|---|---|
| `APP_ENV` | `development` | `development` → `/docs` aktif |
| `ENABLE_DOCS` | `false` | `true` → `/docs`, `/redoc`, `/openapi.json` tetap aktif di produksi |
| `SECRET_KEY` | `changeme` | Kunci tanda tangan JWT — ganti di produksi |
| `API_KEY` | kosong | Kosong = proteksi valve command **nonaktif** |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS |
| `DATABASE_URL` / `DATABASE_SYNC_URL` | postgres localhost | Sumber data |
| `MQTT_BROKER_HOST` / `MQTT_BROKER_PORT` | `localhost` / `1883` | Status `mqtt_connected` |
| `ML_ENABLED`, `ML_ACTIVE_MODEL` | `true`, `xgboost` | Menentukan jalur `mode=auto` |
| `ML_LOOKBACK_HOURS` | `169` | Default efektif `hours` pada prediksi |
| `EARLY_WARNING_HOURS` | `240` | Ambang pengiriman early warning oleh scheduler |
| `WAHA_BASE_URL`, `WAHA_API_KEY`, `WAHA_SESSION` | – | `/notifications/status` & pengiriman WA |
| `MAIL_*` | – | Kanal email |
| `NOTIF_WHATSAPP_TARGETS` | kosong | Target default notifikasi (dipisah koma) |

---

## 10. Resep umum (cookbook)

**a. Bootstrap dashboard (1 request + WS)**

```bash
curl http://localhost:8005/api/v1/dashboard/summary
# lalu buka ws://localhost:8005/ws untuk update real-time
```

**b. Cek apakah device masih hidup**

```bash
curl -s http://localhost:8005/api/v1/dashboard/summary \
  | python -c "import sys,json;d=json.load(sys.stdin);print(d['system_status'])"
```

`last_reading_age_seconds > 600` → device kemungkinan offline.

**c. Unduh data 30 hari untuk training**

```bash
curl -OJ "http://localhost:8005/api/v1/sensors/export?hours=720"
```

**d. Tutup valve karena darurat**

```bash
curl -X POST http://localhost:8005/api/v1/valves/bathroom/command \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"action":"close","reason":"Darurat - air keruh"}'
```

**e. Mulai siklus drain baru setelah bak dikuras**

```bash
curl -X POST http://localhost:8005/api/v1/drain-logs/start \
  -H "Content-Type: application/json" \
  -d '{"cycle_estimate_hours":2400,"created_by":"operator","notes":"Kuras bak 26 Okt"}'
```

**f. Uji notifikasi WhatsApp ke nomor tertentu**

```bash
curl -X POST http://localhost:8005/api/v1/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"channel":"whatsapp","custom_target":"08xxxxxxxxxx","message":"Tes"}'
```

---

## 11. Known issues & catatan maintainer

Hal-hal yang **sudah diketahui** dan sengaja didokumentasikan agar tidak mengagetkan
saat maintenance:

1. **`parameter` pada `/sensors/history` belum berfungsi.** Query param diterima
   tetapi tidak dipakai untuk memfilter. Jangan dokumentasikan ke pengguna sebagai
   fitur aktif sampai diimplementasikan (atau hapus parameternya).
2. **`GET /predictions/run` memiliki efek samping** (menulis `prediction_results`).
   Secara REST seharusnya `POST`. Jika diubah, perlu update frontend + dokumen ini.
3. **`GET /valves` dan `GET /drain-logs` mengembalikan 307** karena dideklarasikan
   dengan trailing slash. Klien HTTP harus mengikuti redirect.
4. **`/notifications/test` selalu 200** meski gagal kirim; cek `results`.
5. **`/notifications/status` memanggil WAHA** dengan timeout 5 detik. Bila WAHA mati,
   endpoint bisa lambat 5 detik sebelum mengembalikan `status: "UNREACHABLE"`.
6. **`API_KEY` kosong = valve command terbuka.** Pastikan terisi di produksi
   (verifikasi: `docker exec toren_backend printenv API_KEY`).
7. **Urutan `/valves/` tidak dijamin.** Selalu index berdasarkan `id`.
8. **`days_until_threshold` bisa `0.0` atau `null`** — `0.0` berarti sudah/diprediksi
   segera melewati ambang; `null` berarti di luar horizon 30 hari atau model gagal.
9. **Jangan jalankan uvicorn dengan `--workers > 1`.** APScheduler berjalan in-process,
   sehingga prediksi & notifikasi akan dobel.
10. **Semua endpoint baca bersifat publik.** Jika backend diekspos tanpa Cloudflare
    Access/rate limit, data sensor & status valve dapat dibaca siapa pun.
11. **`notification_logs` tidak pernah diisi.** Model dan schema `NotificationLogOut`
    ada (`app/models/valve.py`, `app/schemas/valve.py`), tetapi tidak ada kode yang
    menulis ke tabel tersebut — `_dispatch_all` hanya mengembalikan boolean.
    Artinya riwayat pengiriman notifikasi saat ini **tidak tersimpan**. Jika dibutuhkan
    untuk audit/evaluasi, tambahkan logging ke `notification_logs` di
    `notification_service._send_email` / `_send_waha` / `_send_fonnte`.

---

## 12. Cara menambah / mengubah endpoint (checklist)

1. Tambah handler di router yang sesuai (`app/api/v1/<grup>.py`) memakai
   `APIRouter(prefix=..., tags=[...])`.
2. Router baru → daftarkan di `app/main.py`:
   ```python
   from app.api.v1 import <modul>
   app.include_router(<modul>.router, prefix="/api/v1")
   ```
3. Tambah/ubah Pydantic schema di `app/schemas/`; pastikan `field_serializer`
   memakai `serialize_utc` agar timestamp konsisten UTC.
4. Perbarui **file ini** (§3.4, §4, §5, §11 bila relevan) di commit yang sama.
5. Tambah test di `backend/tests/` (lihat contoh `test_auth.py`, `test_notifications.py`).
6. Verifikasi kontrak:
   ```bash
   curl -s http://localhost:8005/openapi.json | python -m json.tool | less
   ```
7. Bila endpoint menulis DB / publish MQTT / broadcast WS, tambahkan ke tabel
   **§3.6 Side effect**.

---

## 13. Peta file

| File | Isi |
|---|---|
| `app/main.py` | Instansiasi FastAPI, CORS, registrasi router, `/health`, `/ws`, lifespan (DB init, MQTT, scheduler) |
| `app/api/v1/auth.py` | Login & profil |
| `app/api/v1/sensors.py` | Reading, history, anomaly, export CSV |
| `app/api/v1/valves.py` | Status valve, command, override log |
| `app/api/v1/predictions.py` | Hasil prediksi & on-demand run |
| `app/api/v1/dashboard.py` | Agregasi dashboard |
| `app/api/v1/drain_logs.py` | Siklus drain & readiness ML |
| `app/api/v1/notifications.py` | Status & uji kanal notifikasi |
| `app/schemas/sensor.py`, `valve.py` | Bentuk request/response |
| `app/core/security.py` | JWT, hash password, `DEFAULT_USERS` |
| `app/core/auth.py` | `verify_api_key` (`X-API-Key`) |
| `app/core/websocket_manager.py` | Broadcast WS |
| `app/core/time_utils.py` | Konvensi UTC |
| `app/mqtt/handlers.py`, `client.py` | Pipeline data sensor & valve |
| `app/services/*` | Logika bisnis (scoring, anomaly, valve, ML, notifikasi) |
| `app/tasks/scheduler.py` | Job prediksi per jam & cleanup harian |

---

## Riwayat dokumen

| Tanggal | Perubahan |
|---|---|
| 2026-10-26 | Versi awal: 22 endpoint REST + `/health` + `/ws`, kontrak MQTT, konvensi, known issues. Diverifikasi terhadap `https://aminu.irsad.site` (via backend container). |
