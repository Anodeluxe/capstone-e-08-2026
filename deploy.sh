#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Toren Monitoring — Script deploy (stack produksi lengkap)
#
#   ./deploy.sh          → build + start semua service
#   ./deploy.sh logs     → ikuti log backend
#   ./deploy.sh status   → status container
#   ./deploy.sh down     → stop container (data tetap aman)
#   ./deploy.sh backup   → dump database ke backups/
#
# Perintah yang setara:
#   docker compose --profile app up -d --build
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose --profile app"

if [ ! -f .env ]; then
    echo "❌ File .env belum ada."
    echo "   Jalankan: cp .env.example .env   lalu edit nilainya."
    exit 1
fi

if [ ! -f backend/.env ]; then
    echo "❌ File backend/.env belum ada."
    echo "   Jalankan: cp backend/.env.example backend/.env   lalu edit nilainya."
    exit 1
fi

# Muat variabel dari .env (dipakai untuk pg_dump, dll.)
set -a
# shellcheck disable=SC1091
. ./.env
set +a

# ── Peringatan produksi ──────────────────────────────────────────────────────
if grep -q "^POSTGRES_PASSWORD=password$" .env; then
    echo "⚠️  POSTGRES_PASSWORD masih 'password'. Ganti untuk produksi!"
fi
if grep -q "^SECRET_KEY=changeme$" backend/.env; then
    echo "⚠️  SECRET_KEY masih 'changeme'. Ganti untuk produksi!"
fi

case "${1:-up}" in
    up)
        $COMPOSE up -d --build
        echo ""
        echo "✅ Stack berjalan. Cek:"
        echo "   - Backend : http://localhost:8000/health"
        echo "   - Frontend: http://localhost:3000"
        echo "   - Nginx   : http://localhost"
        ;;
    logs)
        $COMPOSE logs -f backend
        ;;
    status)
        $COMPOSE ps
        ;;
    down)
        $COMPOSE down
        echo "⚠️  Data database tetap aman di volume 'toren_db_data'."
        ;;
    backup)
        mkdir -p backups
        FILE="backups/toren-$(date +%Y%m%d-%H%M%S).sql.gz"
        $COMPOSE exec -T timescaledb pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-toren_db}" | gzip > "$FILE"
        echo "✅ Backup disimpan: $FILE"
        ;;
    *)
        echo "Usage: $0 {up|logs|status|down|backup}"
        exit 1
        ;;
esac
