# Claude Code Context — Toren Monitoring System

Use this file as your complete reference for the project. Read it fully before making any changes.

---

## Project Overview

**Name:** Sistem Monitoring Kualitas dan Pengambilan Keputusan untuk Deteksi Dini dan Kontrol Distribusi Air Toren pada Kebutuhan Rumah Tangga Non-Konsumsi

**What it does:**
An IoT water quality monitoring system for household water tanks (toren). An ESP32 reads 5 sensors and publishes data via MQTT. The backend processes readings in real time, computes quality scores, detects anomalies, predicts water degradation, and controls 4 solenoid valves. A Next.js dashboard displays live data and allows manual valve control. Notifications are sent via email and WhatsApp.

**Team:** 4 members (2x Teknologi Informasi, 1x Teknik Elektro, 1x Teknik Biomedis) — UGM DTETI Capstone 2026, Kelas E Kelompok 08.

---

## Hardware

- **Microcontroller:** ESP32 (WiFi, publishes via MQTT every 10 seconds)
- **Sensors (5 total):**
  - pH sensor (analog, pin 34)
  - Turbidity sensor (analog, pin 35) — NTU
  - TDS sensor (analog, pin 32) — ppm
  - DS18B20 temperature sensor (OneWire, pin 4) — °C
  - Water level sensor (analog, pin 33) — % of tank
- **Actuators:** 4 solenoid valves via relay module
  - `bathroom` (pin 25) — highest quality standard
  - `kitchen` (pin 26) — highest quality standard
  - `laundry` (pin 27) — medium standard
  - `garden` (pin 14) — lowest standard

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| UI Components | shadcn/ui, Recharts, Lucide React |
| State / Data | Zustand, TanStack Query (React Query) |
| Backend | FastAPI (Python 3.12), Uvicorn |
| IoT Protocol | MQTT (paho-mqtt) via Mosquitto broker |
| Real-time | FastAPI WebSocket → Next.js |
| Database | PostgreSQL + TimescaleDB extension |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Background Jobs | APScheduler (async, in-process) |
| ML / Prediction | scikit-learn, ruptures, statsmodels, numpy, pandas |
| Notifications | fastapi-mail (email SMTP) + Fonnte HTTP API (WhatsApp) |
| Containerization | Docker Compose (TimescaleDB, Mosquitto, backend, frontend, Nginx) |

---

## Repository Structure

```
toren-monitoring/
├── backend/
│   ├── app/
│   │   ├── main.py                         ✅ DONE
│   │   ├── api/v1/
│   │   │   ├── sensors.py                  ✅ DONE
│   │   │   ├── valves.py                   ✅ DONE
│   │   │   ├── predictions.py              ✅ DONE
│   │   │   └── dashboard.py                ✅ DONE
│   │   ├── core/
│   │   │   ├── config.py                   ✅ DONE
│   │   │   ├── database.py                 ✅ DONE
│   │   │   └── websocket_manager.py        ✅ DONE
│   │   ├── mqtt/
│   │   │   ├── client.py                   ✅ DONE
│   │   │   └── handlers.py                 ✅ DONE
│   │   ├── models/
│   │   │   ├── sensor_reading.py           ✅ DONE
│   │   │   └── valve.py                    ✅ DONE  (ValveState, ValveOverrideLog, NotificationLog, PredictionResult)
│   │   ├── schemas/
│   │   │   ├── sensor.py                   ✅ DONE
│   │   │   └── valve.py                    ✅ DONE
│   │   ├── services/
│   │   │   ├── scoring_service.py          ✅ DONE
│   │   │   ├── anomaly_service.py          ✅ DONE
│   │   │   ├── prediction_service.py       ✅ DONE
│   │   │   ├── notification_service.py     ✅ DONE
│   │   │   └── valve_service.py            ✅ DONE
│   │   ├── tasks/
│   │   │   └── scheduler.py                ✅ DONE
│   │   └── ml/
│   │       ├── predictor.py                ❌ TODO
│   │       └── trainer.py                  ❌ TODO
│   ├── alembic/                            ❌ TODO — needs env.py configured
│   ├── tests/                              ❌ TODO
│   ├── .env.example                        ✅ DONE
│   ├── requirements.txt                    ✅ DONE
│   └── Dockerfile                          ✅ DONE
│
├── frontend/                               ❌ TODO — needs to be scaffolded
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── sensors/page.tsx
│   │   ├── valves/page.tsx
│   │   ├── predictions/page.tsx
│   │   └── notifications/page.tsx
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── SensorScoreCard.tsx
│   │   │   ├── AlertBanner.tsx
│   │   │   └── SystemStatus.tsx
│   │   ├── sensors/
│   │   │   ├── SensorChart.tsx
│   │   │   └── SensorTable.tsx
│   │   ├── valves/
│   │   │   ├── ValveCard.tsx
│   │   │   └── OverrideModal.tsx
│   │   └── predictions/
│   │       ├── ETACard.tsx
│   │       └── TrendChart.tsx
│   ├── hooks/
│   │   ├── useSensorWebSocket.ts
│   │   ├── useSensorData.ts
│   │   └── useValveControl.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── utils.ts
│   └── types/index.ts
│
├── mosquitto/config/mosquitto.conf         ✅ DONE
├── docker-compose.yml                      ✅ DONE
└── esp32_reference/main.cpp               ✅ DONE
```

---

## MQTT Topics

| Topic | Direction | Publisher | Subscriber |
|---|---|---|---|
| `toren/sensors` | ESP32 → Backend | ESP32 | FastAPI (handlers.py) |
| `toren/valves/cmd` | Backend → ESP32 | FastAPI (valve_service.py) | ESP32 |
| `toren/valves/status` | ESP32 → Backend | ESP32 | FastAPI (handlers.py) |

---

## ESP32 Sensor Payload Format

The ESP32 publishes this JSON to `toren/sensors` every 10 seconds.
**The backend validates this with `ESP32SensorPayload` Pydantic schema.**

```json
{
  "device_id": "toren_01",
  "timestamp": 0,
  "ph": 7.2,
  "turbidity": 3.5,
  "tds": 180.0,
  "temperature": 28.1,
  "water_level": 85.0
}
```

`timestamp` is Unix epoch from the ESP32 RTC. If `0` or missing, the backend uses its own UTC time.

---

## Valve Command Payload (Backend → ESP32)

Published to `toren/valves/cmd`:
```json
{
  "valve_id": "bathroom",
  "action": "open",
  "triggered_by": "system"
}
```

## Valve Acknowledgment (ESP32 → Backend)

Published to `toren/valves/status`:
```json
{
  "valve_id": "bathroom",
  "is_open": true,
  "timestamp": 1710000000
}
```

---

## Sensor Data Pipeline (handlers.py)

Every incoming MQTT message on `toren/sensors` runs these steps in order:

1. **Parse** — validate JSON against `ESP32SensorPayload`
2. **Score** — `scoring_service.compute_scores()` → weighted 0–100 score per valve
3. **Anomaly** — `anomaly_service.detect_sudden_change()` → flag if sudden drop
4. **Persist** — insert `SensorReading` row into TimescaleDB
5. **Valve** — `valve_service.process_auto_valve_decisions()` → close/open valves
6. **WebSocket** — `ws_manager.broadcast_sensor_update()` → push to Next.js
7. **Notify** — `notification_service` → email/WhatsApp if threshold hit

---

## Scoring Logic (scoring_service.py)

Each parameter gets a sub-score (0–100) based on thresholds, then weighted:

```
score = ph_score * w_ph + turbidity_score * w_turb + tds_score * w_tds + temp_score * w_temp
```

Default weights (from `.env`): ph=0.30, turbidity=0.30, tds=0.25, temperature=0.15

Per-use-point auto-close thresholds:
- `bathroom`: score < 60
- `kitchen`: score < 65
- `laundry`: score < 45
- `garden`: score < 30

---

## Anomaly Detection (anomaly_service.py)

Two layers:

1. **Delta check** (every reading): compare current vs previous
   - pH change > 1.5 → sudden
   - Turbidity spike > 15 NTU → sudden
   - TDS spike > 200 ppm → sudden
   - Overall score drop > `SUDDEN_CHANGE_THRESHOLD` (default 20 pts) → sudden

2. **Change-point detection** (batch): `ruptures` PELT algorithm on rolling score window
   - Used in `detect_change_points_on_window()` for periodic analysis

---

## Prediction Logic (prediction_service.py)

1. Fetch last 72h of `score_overall` from DB
2. Fit linear regression; if polynomial R² > linear R² + 0.05, use polynomial Ridge
3. Binary search for when the extrapolated score crosses 60.0 (default threshold)
4. Returns `days_until_threshold`, `predicted_date`, `confidence` (R²), `trend_direction`
5. Minimum 12 data points required

**APScheduler job** in `tasks/scheduler.py` runs this every hour and sends early warning if `days_until_threshold <= EARLY_WARNING_DAYS` (default 3).

---

## WebSocket Event Types

The frontend connects to `ws://localhost:8000/ws` and receives:

```typescript
// New sensor reading
{ type: "sensor_update", data: SensorReading & { scores: ScoreBreakdown } }

// Valve state changed
{ type: "valve_status", data: { valve_id: string, is_open: boolean, triggered_by: string } }

// Alert (anomaly or early warning)
{ type: "alert", data: { alert_type: "sudden_change" | "early_warning" | "valve_closed", message: string, details: object } }
```

Frontend keeps connection alive by sending `"ping"` → backend replies `"pong"`.

---

## REST API Endpoints

Base URL: `http://localhost:8000/api/v1`

### Sensors
| Method | Path | Description |
|---|---|---|
| GET | `/sensors/latest` | Most recent reading |
| GET | `/sensors/history?hours=24` | Historical readings |
| GET | `/sensors/anomalies?hours=72` | Readings flagged as sudden changes |

### Valves
| Method | Path | Description |
|---|---|---|
| GET | `/valves/` | All 4 valve states |
| GET | `/valves/{valve_id}` | Single valve state |
| POST | `/valves/{valve_id}/command` | Open or close a valve (manual override) |
| GET | `/valves/{valve_id}/overrides` | Override history for one valve |
| GET | `/valves/overrides/all` | All override history |

### Predictions
| Method | Path | Description |
|---|---|---|
| GET | `/predictions/latest` | Last saved prediction results |
| GET | `/predictions/run?hours=72` | Run prediction now, save and return result |

### Dashboard
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/summary` | All-in-one: latest reading, valve states, prediction, 24h trend, anomaly count |

### System
| Method | Path | Description |
|---|---|---|
| GET | `/health` | MQTT status, WS client count, env |
| WS | `/ws` | WebSocket connection |

---

## Database Models

### `sensor_readings` (TimescaleDB hypertable, partitioned by timestamp)
```
id, timestamp, ph, turbidity, tds, temperature, water_level,
score_overall, score_bathroom, score_kitchen, score_laundry, score_garden,
is_sudden_change, anomaly_parameter
```

### `valve_states`
```
id (bathroom|kitchen|laundry|garden), is_open, last_changed_at,
last_changed_by, quality_score_at_close
```

### `valve_override_logs`
```
id, valve_id (FK), action, reason, score_at_override, overridden_at, user_id
```

### `notification_logs`
```
id, sent_at, channel, recipient, subject, body, trigger_type, success, error_detail
```

### `prediction_results`
```
id, computed_at, target_parameter, valve_id, days_until_threshold,
predicted_date, confidence, model_used, notification_sent
```

---

## Environment Variables (backend/.env)

All variables, their types, and defaults:

```env
# App
APP_NAME=Toren Monitoring
APP_ENV=development
SECRET_KEY=<random 32-char hex>

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/toren_db
DATABASE_SYNC_URL=postgresql://postgres:password@localhost:5432/toren_db

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_CLIENT_ID=toren-backend
MQTT_TOPIC_SENSORS=toren/sensors
MQTT_TOPIC_VALVE_CMD=toren/valves/cmd
MQTT_TOPIC_VALVE_STATUS=toren/valves/status

# Email (Gmail SMTP)
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False

# WhatsApp (Fonnte)
FONNTE_API_KEY=
FONNTE_API_URL=https://api.fonnte.com/send
NOTIF_WHATSAPP_TARGETS=628xxxxxxxxxx

# Scoring weights (must sum to 1.0)
WEIGHT_PH=0.30
WEIGHT_TURBIDITY=0.30
WEIGHT_TDS=0.25
WEIGHT_TEMPERATURE=0.15

# Alert thresholds
SUDDEN_CHANGE_THRESHOLD=20.0
EARLY_WARNING_DAYS=3

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

---

## Alembic Setup (❌ NEEDS TO BE DONE)

After running `alembic init alembic`, the generated `alembic/env.py` must be edited.
Replace its content with the following (or apply these changes):

```python
# At the top of alembic/env.py, add:
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.core.database import Base
from app.models import *  # noqa — registers all models with Base.metadata

settings = get_settings()

# Replace the existing config.set_main_option line with:
config.set_main_option("sqlalchemy.url", settings.database_sync_url)

# Set target_metadata:
target_metadata = Base.metadata
```

Then run:
```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

---

## Frontend Setup (❌ NEEDS TO BE DONE)

### Scaffold command
```bash
npx create-next-app@latest frontend \
  --typescript --tailwind --eslint --app \
  --src-dir=false --import-alias="@/*"
```

### Dependencies to install
```bash
cd frontend
npm install recharts @tanstack/react-query axios zustand lucide-react date-fns
npx shadcn@latest init
```

### `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Key files to create (priority order)

1. **`types/index.ts`** — shared TypeScript types (SensorReading, ValveState, etc.)
2. **`lib/api.ts`** — axios instance pointing to `NEXT_PUBLIC_API_URL`
3. **`hooks/useSensorWebSocket.ts`** — connects to WS, maintains live sensor state in Zustand
4. **`hooks/useSensorData.ts`** — React Query hooks for REST endpoints
5. **`hooks/useValveControl.ts`** — POST to `/valves/{id}/command`
6. **`components/dashboard/SensorScoreCard.tsx`** — circular gauge per valve (0–100 score)
7. **`components/dashboard/AlertBanner.tsx`** — dismissible banner for sudden_change / early_warning alerts
8. **`components/valves/ValveCard.tsx`** — toggle switch + status indicator
9. **`components/valves/OverrideModal.tsx`** — confirmation dialog with risk warning before manual override
10. **`components/sensors/SensorChart.tsx`** — Recharts LineChart for time-series data
11. **`app/dashboard/page.tsx`** — main page: score cards, valve status, alert banner, 24h chart
12. **`app/valves/page.tsx`** — valve control panel + override log table
13. **`app/sensors/page.tsx`** — all sensor parameter charts
14. **`app/predictions/page.tsx`** — ETA card + projected trend chart

---

## TypeScript Types Reference

```typescript
// types/index.ts

export interface SensorReading {
  id: number
  timestamp: string  // ISO 8601
  ph: number
  turbidity: number
  tds: number
  temperature: number
  water_level: number
  score_overall: number | null
  score_bathroom: number | null
  score_kitchen: number | null
  score_laundry: number | null
  score_garden: number | null
  is_sudden_change: boolean
  anomaly_parameter: string | null
}

export type ValveID = 'bathroom' | 'kitchen' | 'laundry' | 'garden'

export interface ValveState {
  id: ValveID
  is_open: boolean
  last_changed_at: string
  last_changed_by: string
  quality_score_at_close: number | null
}

export interface ValveOverrideLog {
  id: number
  valve_id: ValveID
  action: 'open' | 'close'
  reason: string | null
  score_at_override: number | null
  overridden_at: string
  user_id: string | null
}

export interface PredictionResult {
  id: number
  computed_at: string
  target_parameter: string
  valve_id: ValveID | null
  days_until_threshold: number | null
  predicted_date: string | null
  confidence: number | null
  model_used: string
  notification_sent: boolean
}

export interface DashboardSummary {
  latest_reading: SensorReading | null
  valve_states: ValveState[]
  prediction: PredictionResult | null
  trend_24h: Array<{
    hour: string
    avg_score: number | null
    avg_ph: number | null
    avg_turbidity: number | null
    avg_tds: number | null
  }>
  anomaly_count_24h: number
  system_status: {
    mqtt_connected: boolean
    last_reading_age_seconds: number | null
  }
}

// WebSocket event types
export type WSEventType = 'sensor_update' | 'valve_status' | 'alert'

export interface WSEvent {
  type: WSEventType
  data: Record<string, unknown>
}

export interface AlertData {
  alert_type: 'sudden_change' | 'early_warning' | 'valve_closed'
  message: string
  details: Record<string, unknown>
}
```

---

## What Still Needs to Be Done (Priority Order)

### Backend
1. **Alembic env.py** — configure as described above, then run migrations
2. **`app/ml/predictor.py`** — model persistence (save/load `.pkl` files so the model doesn't retrain from scratch every call)
3. **`app/ml/trainer.py`** — periodic full retraining on longer history
4. **`tests/`** — unit tests for scoring_service, anomaly_service, and prediction_service
5. **Auth** — the valve POST endpoint has a `# TODO: add auth` comment; add JWT or simple API key

### Frontend
Everything in the frontend is yet to be built. Follow the priority order in the Frontend section above.

### Infrastructure
- `docker-compose.yml` already written — just run `docker compose up -d`
- No changes needed to `mosquitto/config/mosquitto.conf`

---

## Coding Conventions

- **Python:** follow PEP 8; use type hints everywhere; async/await for all DB and I/O operations
- **TypeScript:** strict mode; no `any`; use the types defined in `types/index.ts`
- **File naming:** Python = `snake_case.py`; TypeScript = `PascalCase.tsx` for components, `camelCase.ts` for hooks/lib
- **Comments:** write comments in **English** (code is English); UI-facing text (labels, notifications, messages) in **Indonesian**
- **Error handling:** all MQTT handlers must catch and log exceptions without crashing the process; all API routes return proper HTTP status codes

---

## How to Run (after setup is complete)

```bash
# Terminal 1 — infrastructure
docker compose up -d

# Terminal 2 — backend (from backend/ with .venv active)
uvicorn app.main:app --reload --port 8000

# Terminal 3 — frontend (from frontend/)
npm run dev
```

**Test the pipeline with a fake ESP32 reading:**
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "toren/sensors" \
  -m '{"device_id":"toren_01","ph":7.2,"turbidity":3.5,"tds":180.0,"temperature":28.1,"water_level":85.0}'
```

**Simulate a sudden anomaly (pH drop):**
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "toren/sensors" \
  -m '{"device_id":"toren_01","ph":4.1,"turbidity":28.0,"tds":950.0,"temperature":28.5,"water_level":84.0}'
```

API docs: `http://localhost:8000/docs`
Frontend: `http://localhost:3000`
Health: `http://localhost:8000/health`

---

## Deployment (Docker Compose)

### Mode development (infra saja)

```bash
docker compose up -d
```

Menjalankan **hanya** `timescaledb` + `mosquitto`. Backend & frontend jalan di host.

### Mode produksi (stack lengkap)

```bash
cp .env.example .env              # root: config compose + build-arg frontend
cp backend/.env.example backend/.env
./deploy.sh                        # = docker compose --profile app up -d --build
```

Service ber-profile `app`: `backend`, `frontend`, `nginx`.

### Aturan penting saat deploy

| Aturan | Alasan |
|---|---|
| `uvicorn --workers 1` (sudah di-set di Dockerfile) | APScheduler in-process → multi-worker = job prediksi dobel + notifikasi berulang |
| `NEXT_PUBLIC_*` dikirim sebagai **build arg** | Di-inline Next.js saat `next build`; ganti URL ⇒ rebuild image frontend |
| `.env` **tidak** di-COPY ke image | Secret dikirim lewat `env_file` di compose |
| Port DB & backend bind ke `127.0.0.1` | Hanya Nginx yang mengekspos ke publik; DB tak terjangkau dari internet |
| `backend/.dockerignore` mengecualikan `app/ml/data/` | 489MB data training tidak perlu masuk image |
| HTTPS wajib | Service worker PWA hanya jalan di secure context |

### Hostname di dalam container

| Service | Hostname (dalam jaringan Docker) |
|---|---|
| Database | `timescaledb` (port 5432) |
| MQTT broker | `mosquitto` (port 1883) |
| Backend (dari Nginx) | `backend` (port 8000) |
| Frontend (dari Nginx) | `frontend` (port 3000) |

### Struktur file deploy

```
.env.example            config compose + build args frontend
deploy.sh                script deploy (up|logs|status|down|backup)
deploy/nginx.conf        reverse proxy HTTP
deploy/nginx-tls.conf    reverse proxy HTTPS (aktif setelah certbot)
deploy/README.md         panduan deploy server lengkap
```

### Backup

```bash
./deploy.sh backup
# = docker compose --profile app exec -T timescaledb pg_dump -U postgres toren_db | gzip > backups/...
```