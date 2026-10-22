#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Toren Monitoring — Setup Cloudflare Tunnel untuk backend (sekali jalan)
#
#   sudo ./deploy/setup-cloudflare.sh
#
# Yang dilakukan (aman dijalankan berulang):
#   1. Route DNS HOSTNAME → tunnel (CNAME di Cloudflare)
#   2. Tambah ingress HOSTNAME → http://localhost:BACKEND_PORT ke config
#      cloudflared, tepat sebelum rule fallback `http_status:404`
#   3. Validasi config (rollback otomatis kalau gagal), restart cloudflared
#   4. Cek /health lewat domain publik
#
# Override lewat env, contoh:
#   sudo HOSTNAME_PUBLIC=api.contoh.com BACKEND_PORT=8005 ./deploy/setup-cloudflare.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

HOSTNAME_PUBLIC="${HOSTNAME_PUBLIC:-aminu.irsad.site}"
BACKEND_PORT="${BACKEND_PORT:-8005}"
CONFIG="${CONFIG:-/etc/cloudflared/config.yml}"
SERVICE="${SERVICE:-cloudflared}"
NO_RESTART="${NO_RESTART:-0}"   # 1 = hanya edit config (untuk testing)

SERVICE_URL="http://localhost:${BACKEND_PORT}"

if [ "$NO_RESTART" != "1" ] && [ "$(id -u)" -ne 0 ]; then
    echo "❌ Jalankan dengan sudo: sudo $0"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "❌ Config cloudflared tidak ditemukan: $CONFIG"
    exit 1
fi

TUNNEL_ID="$(awk '/^tunnel:/ {print $2; exit}' "$CONFIG")"
if [ -z "$TUNNEL_ID" ]; then
    echo "❌ Field 'tunnel:' tidak ada di $CONFIG"
    exit 1
fi
echo "▶ Tunnel  : $TUNNEL_ID"
echo "▶ Hostname: $HOSTNAME_PUBLIC → $SERVICE_URL"

# ── 1. DNS ───────────────────────────────────────────────────────────────────
# cert.pem ada di home user asli, bukan /root, karena script dijalankan via sudo.
USER_HOME="$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)"
ORIGIN_CERT="${ORIGIN_CERT:-$USER_HOME/.cloudflared/cert.pem}"
if [ -f "$ORIGIN_CERT" ]; then
    if cloudflared --origincert "$ORIGIN_CERT" tunnel route dns "$TUNNEL_ID" "$HOSTNAME_PUBLIC" 2>&1 | tail -1; then
        echo "✅ DNS beres"
    else
        echo "⚠️  Route DNS gagal (mungkin sudah ada record lain) — lanjut"
    fi
else
    echo "⚠️  $ORIGIN_CERT tidak ada — lewati route DNS"
fi

# ── 2. Ingress ───────────────────────────────────────────────────────────────
if grep -qE "^[[:space:]]*-[[:space:]]*hostname:[[:space:]]*${HOSTNAME_PUBLIC//./\\.}[[:space:]]*$" "$CONFIG"; then
    echo "✅ Ingress $HOSTNAME_PUBLIC sudah ada — tidak diubah"
    CHANGED=0
else
    if ! grep -qE "^[[:space:]]*-[[:space:]]*service:[[:space:]]*http_status:404" "$CONFIG"; then
        echo "❌ Rule fallback 'http_status:404' tidak ditemukan di $CONFIG"
        exit 1
    fi
    BACKUP="${CONFIG}.bak-$(date +%Y%m%d%H%M%S)"
    cp -p "$CONFIG" "$BACKUP"
    echo "▶ Backup  : $BACKUP"

    awk -v host="$HOSTNAME_PUBLIC" -v svc="$SERVICE_URL" '
        !done && /^[[:space:]]*-[[:space:]]*service:[[:space:]]*http_status:404/ {
            match($0, /^[[:space:]]*/)
            indent = substr($0, 1, RLENGTH)
            print indent "- hostname: " host
            print indent "  service: " svc
            done = 1
        }
        { print }
    ' "$BACKUP" > "$CONFIG"
    CHANGED=1
    echo "✅ Ingress ditambahkan"
fi

# ── 3. Validasi + restart ────────────────────────────────────────────────────
if ! cloudflared --config "$CONFIG" tunnel ingress validate >/dev/null 2>&1; then
    echo "❌ Config tidak valid:"
    cloudflared --config "$CONFIG" tunnel ingress validate || true
    if [ "$CHANGED" = "1" ]; then
        cp -p "$BACKUP" "$CONFIG"
        echo "↩️  Config dikembalikan dari backup"
    fi
    exit 1
fi
echo "✅ Config valid"
cloudflared --config "$CONFIG" tunnel ingress rule "https://${HOSTNAME_PUBLIC}" | tail -2

if [ "$NO_RESTART" = "1" ]; then
    echo "ℹ️  NO_RESTART=1 — $SERVICE tidak di-restart"
    exit 0
fi

if [ "$CHANGED" = "1" ] || ! systemctl is-active --quiet "$SERVICE"; then
    systemctl restart "$SERVICE"
    sleep 3
fi
systemctl is-active --quiet "$SERVICE" && echo "✅ $SERVICE aktif" || {
    echo "❌ $SERVICE gagal jalan — cek: journalctl -u $SERVICE -n 50"
    exit 1
}

# ── 4. Cek ───────────────────────────────────────────────────────────────────
if curl -fsS --max-time 5 "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    echo "✅ Backend lokal OK"
    sleep 2
    if curl -fsS --max-time 15 "https://${HOSTNAME_PUBLIC}/health"; then
        echo ""
        echo "✅ Publik OK: https://${HOSTNAME_PUBLIC}  (Swagger: /docs)"
    else
        echo "⚠️  Publik belum respon — DNS bisa butuh 1-2 menit, coba lagi:"
        echo "   curl https://${HOSTNAME_PUBLIC}/health"
    fi
else
    echo "⚠️  Backend belum jalan di 127.0.0.1:${BACKEND_PORT} — jalankan ./deploy.sh dulu"
fi
