# Toren Monitoring System

Sistem Monitoring Kualitas dan Pengambilan Keputusan untuk Deteksi Dini dan Kontrol Distribusi Air Toren pada Kebutuhan Rumah Tangga Non-Konsumsi.

UGM DTETI Capstone 2026 — Kelas E Kelompok 08

---

## What This Is

An IoT water quality monitoring system for household water tanks. An ESP32 reads 5 sensors (pH, turbidity, TDS, temperature, water level) and sends data via MQTT every 10 seconds. The backend scores water quality, detects anomalies, predicts degradation, and controls 4 solenoid valves. A Next.js dashboard shows live data and allows manual valve control.

---

## Prerequisites

Install these before anything else:

| Tool | Version | Download |
|---|---|---|
| Python | 3.12 | https://www.python.org/downloads/ |
| Docker Desktop | latest | https://www.docker.com/products/docker-desktop/ |
| Git | any | https://git-scm.com/ |
| Node.js | 18+ | https://nodejs.org/ (needed for frontend later) |

---

## Backend Setup (do this once)

### 1. Clone the repo

```bash
git clone <repo-url>
cd capstone-e-08-2026
```

### 2. Create a virtual environment

```powershell
cd backend
python -m venv .venv
```

This creates an isolated Python environment just for this project inside `backend/.venv`.

### 3. Activate the virtual environment

```powershell
# Windows (PowerShell)
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Your terminal prompt will show `(.venv)` when it is active.
**You must activate it every time you open a new terminal.**

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Create your `.env` file

```powershell
copy .env.example .env
```

The defaults work out of the box for local development — they match the Docker services. You only need to fill in `MAIL_*` and `FONNTE_*` if you want email/WhatsApp notifications.

---

## Running the Project (every time you work on it)

**Terminal 1 — start infrastructure** (from the project root):

```powershell
docker compose up -d
```

This starts three containers:
- **PostgreSQL + TimescaleDB** on port 5432 — stores all sensor data
- **Redis** on port 6379 — background task queue
- **Mosquitto** on port 1883 — MQTT broker that receives data from the ESP32

**Terminal 2 — start the backend** (from `backend/`):

```powershell
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

The backend auto-creates all database tables on first startup. No separate migration step needed.

| URL | What it is |
|---|---|
| http://localhost:8000/docs | Interactive API docs |
| http://localhost:8000/health | Health check |

---

## Simulating ESP32 Data (no hardware needed)

Install the Mosquitto client tools (`winget install mosquitto` on Windows), then:

```bash
# Normal reading
mosquitto_pub -h localhost -p 1883 -t "toren/sensors" \
  -m '{"device_id":"toren_01","ph":7.2,"turbidity":3.5,"tds":180.0,"temperature":28.1,"water_level":85.0}'

# Bad reading — triggers anomaly detection and auto-closes valves
mosquitto_pub -h localhost -p 1883 -t "toren/sensors" \
  -m '{"device_id":"toren_01","ph":4.1,"turbidity":28.0,"tds":950.0,"temperature":28.5,"water_level":84.0}'
```

---

## Running Tests

```powershell
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

No database or Docker needed for the tests.

---

## Stopping Everything

```powershell
docker compose stop        # stop containers, keep data
docker compose down -v     # stop containers and delete all data (full reset)
```

---

## Project Structure

```
capstone-e-08-2026/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry point
│   │   ├── api/v1/              REST endpoints
│   │   ├── core/                Config, database, auth, websocket manager
│   │   ├── mqtt/                MQTT client + message handlers
│   │   ├── models/              SQLAlchemy ORM models
│   │   ├── schemas/             Pydantic request/response schemas
│   │   ├── services/            Scoring, anomaly, prediction, valve, notification
│   │   ├── tasks/               Scheduled jobs (hourly prediction, daily cleanup)
│   │   └── ml/                  Model persistence and retraining
│   ├── tests/                   Unit tests
│   ├── .env.example             Copy this to .env
│   └── requirements.txt         Python dependencies
├── frontend/                    Next.js dashboard (TODO)
├── mosquitto/config/            MQTT broker config
├── docker-compose.yml           Infrastructure (DB + Redis + MQTT)
└── esp32_reference/             Arduino firmware reference
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `No module named 'app'` | Running uvicorn from wrong folder | Run from inside `backend/` |
| `ConnectionRefusedError` port 1883 | Docker not running | `docker compose up -d` first |
| `ModuleNotFoundError` | venv not activated or packages not installed | Activate venv, then `pip install -r requirements.txt` |
| `No module named 'pydantic_settings'` | Wrong venv active (system Python) | `cd backend` then `.venv\Scripts\activate` |
