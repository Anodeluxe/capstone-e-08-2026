# ─────────────────────────────────────────────────────────────────────────────
# Toren Monitoring — Backend (FastAPI)
#
# Multi-stage build:
#   builder  → install dependencies ke /opt/venv (lengkap dengan toolchain)
#   runtime  → image akhir ramping, hanya berisi venv + source code
#
# Catatan penting:
#   *.uvicorn memakai --workers 1. APScheduler berjalan in-process; kalau
#     workers > 1, job prediksi akan jalan N kali dan notifikasi WhatsApp/
#     email terkirim berulang.
#   * .env TIDAK di-COPY ke image. Secret dikirim lewat `env_file` di
#     docker-compose.yml supaya tidak ikut ter-bake di dalam image.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential hanya dibutuhkan builder (fallback kalau ada paket tanpa wheel)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Source aplikasi (termasuk bundle model ML di app/ml/models/)
COPY --chown=appuser:appuser app ./app

# Alembic — supaya `alembic upgrade head` bisa dijalankan dari dalam container
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
