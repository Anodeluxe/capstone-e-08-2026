#!/usr/bin/env bash
# ==============================================================================
# Database Environment Switcher for Capstone E-08 (Toren Monitoring)
#
# Usage:
#   ./scripts/switch_db.sh test   -> Switch backend to isolated toren_ml_test
#   ./scripts/switch_db.sh prod   -> Switch backend to production toren_db
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TARGET="$1"

update_env_file() {
    local file="$1"
    local db="$2"
    if [ -f "$file" ]; then
        if grep -q "^POSTGRES_DB=" "$file"; then
            sed -i "s/^POSTGRES_DB=.*/POSTGRES_DB=$db/" "$file"
        else
            echo "POSTGRES_DB=$db" >> "$file"
        fi
    fi
}

if [ "$TARGET" == "test" ]; then
    echo "=================================================="
    echo "  SWITCHING BACKEND TO: toren_ml_test (TEST DB)   "
    echo "=================================================="
    
    update_env_file ".env" "toren_ml_test"
    update_env_file "backend/.env" "toren_ml_test"

    echo "Restarting backend container pointing to 'toren_ml_test'..."
    POSTGRES_DB=toren_ml_test docker compose --profile app up -d --no-deps backend
    
    echo "Waiting for backend to be healthy..."
    sleep 3
    
    echo "Triggering prediction calculation on test data..."
    curl -s "http://127.0.0.1:8005/api/v1/predictions/run?hours=169&mode=auto" > /dev/null || true

    echo ""
    echo "✅ SUCCESS: Backend is now connected to 'toren_ml_test'."
    echo "👉 Open https://amin-u.vercel.app to preview the 9-day trend and XGBoost prediction live!"
    echo "👉 When finished, switch back using: ./scripts/switch_db.sh prod"

elif [ "$TARGET" == "prod" ]; then
    echo "=================================================="
    echo "  RESTORING BACKEND TO: toren_db (PRODUCTION DB)  "
    echo "=================================================="
    
    update_env_file ".env" "toren_db"
    update_env_file "backend/.env" "toren_db"

    echo "Restarting backend container pointing to 'toren_db'..."
    POSTGRES_DB=toren_db docker compose --profile app up -d --no-deps backend
    
    echo "Waiting for backend to be healthy..."
    sleep 3

    echo ""
    echo "✅ SUCCESS: Backend is now safely restored to PRODUCTION 'toren_db'."
    echo "👉 Real ESP32 live monitoring is active."

else
    echo "Usage: $0 [test|prod]"
    echo "  test : Switch backend to toren_ml_test (preview ML degradation on dashboard)"
    echo "  prod : Restore backend to toren_db (normal production mode)"
    exit 1
fi
