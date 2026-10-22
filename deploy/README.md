# Panduan Deploy ke Server

Dokumen ini menjelaskan cara menjalankan **Toren Monitoring** di server (VPS / cloud instance)
dengan Docker Compose.

---

## 1. Persyaratan Server

| Kebutuhan | Detail |
|---|---|
| OS | Ubuntu 22.04 / Debian 12 (atau apa pun yang mendukung Docker) |
| Docker Engine | 24+ dengan Compose v2 (`docker compose`, bukan `docker-compose`) |
| RAM | Minimal 2 GB (disarankan 4 GB — image backend berisi XGBoost/scipy/pandas) |
| Disk | Minimal 10 GB (image Docker ±2 GB + database + log) |
| Domain | Disarankan (butuh untuk HTTPS → PWA bisa di-install) |

Install Docker di Ubuntu:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
```

---

## 2. Setup Awal (sekali saja)

```bash
git clone <repo-url>
cd capstone-e-08-2026

# Konfigurasi Docker Compose + URL publik untuk build frontend
cp .env.example .env

# Konfigurasi aplikasi (secret)
cp backend/.env.example backend/.env
```

Isi `.env` (root):

```bash
POSTGRES_PASSWORD=<hasil: openssl rand -hex 24>
APP_ENV=production
NEXT_PUBLIC_API_URL=https://aminu.irsad.site/api/v1
NEXT_PUBLIC_WS_URL=wss://aminu.irsad.site/ws
ALLOWED_ORIGINS=https://capstone-e-08-2026.vercel.app
```

Isi `backend/.env`:

```bash
SECRET_KEY=<hasil: openssl rand -hex 32>
API_KEY=<random>
MAIL_USERNAME=...          # opsional
MAIL_PASSWORD=...
MAIL_FROM=...
NOTIF_WHATSAPP_TARGETS=628xxxxxxxxxx
```

> `.env` dan `backend/.env` sudah masuk `.gitignore` — jangan di-commit.

---

## 3. Jalankan Stack

```bash
./deploy.sh
```

Setara dengan:

```bash
docker compose --profile app up -d --build
```

Cek status:

```bash
docker compose --profile app ps
docker compose --profile app logs -f backend
```

| URL | Keterangan |
|---|---|
| `http://<ip-server>/` | Dashboard Next.js |
| `http://<ip-server>/api/v1/...` | REST API |
| `http://<ip-server>/health` | Health check backend |
| `http://<ip-server>/docs` | Swagger (hanya jika `APP_ENV=development`) |

---

## 4. Firewall

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 1883/tcp    # MQTT — WAJIB, ESP32 konek ke sini
sudo ufw enable
```

Port **5432 (database)** dan **8005 (backend)** sengaja tidak dibuka —
keduanya ter-bind ke `127.0.0.1`. Backend diakses publik lewat Cloudflare
Tunnel (koneksi keluar dari server), jadi port 80/443 tidak perlu dibuka.

---

## 5. Publik via Cloudflare Tunnel (HTTPS)

Backend keluar di **https://aminu.irsad.site** lewat tunnel `cloudflared`
yang sudah jalan di host (systemd, config `/etc/cloudflared/config.yml`).
Cloudflare yang menangani HTTPS, dan WebSocket `/ws` ikut jalan tanpa
setting tambahan.

```bash
# 1. DNS → tunnel (sudah dilakukan, cukup sekali)
cloudflared tunnel route dns e952bc2e-7d1e-4740-9073-7f65713e68df aminu.irsad.site

# 2. Tambah ingress SEBELUM baris `- service: http_status:404`
sudo nano /etc/cloudflared/config.yml
#   - hostname: aminu.irsad.site
#     service: http://localhost:8005

# 3. Validasi & restart tunnel
sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress validate
sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress rule https://aminu.irsad.site
sudo systemctl restart cloudflared
```

Cek: `curl https://aminu.irsad.site/health` dan Swagger di
`https://aminu.irsad.site/docs` (aktif selama `ENABLE_DOCS=true`).

> MQTT (1883) **tidak** lewat Cloudflare — ESP32 konek langsung ke IP
> server, karena tunnel tidak bisa meneruskan TCP mentah ke perangkat
> tanpa `cloudflared` di sisi client.

---

## 6. Update Kode

```bash
git pull
./deploy.sh
```

> Kalau `NEXT_PUBLIC_*` berubah, image frontend **harus** di-rebuild.
> `./deploy.sh` sudah memakai `--build`, jadi aman.

---

## 7. Migrasi Database

Tabel dibuat otomatis saat backend start (`init_db()` → `create_all` + hypertable).
**Namun** `create_all` tidak bisa mengubah tabel yang sudah ada.

Kalau ada perubahan skema di masa depan:

```bash
docker compose --profile app exec backend alembic upgrade head
```

---

## 8. Backup

Manual:

```bash
./deploy.sh backup
```

Otomatis (cron harian jam 03:15):

```bash
15 3 * * cd /path/ke/capstone-e-08-2026 && ./deploy.sh backup
```

Backup juga bisa dibungkus:

```bash
docker compose --profile app exec -T timescaledb \
  pg_dump -U postgres toren_db | gzip > backups/toren-$(date +%F).sql.gz
```

Restore:

```bash
gunzip -c backups/toren-20260101-031500.sql.gz | \
  docker compose --profile app exec -T timescaledb psql -U postgres toren_db
```

---

## 9. Troubleshooting

| Gejala | Penyebab & Solusi |
|---|---|
| Frontend "Failed to fetch" | `NEXT_PUBLIC_API_URL` salah, atau image frontend belum di-rebuild |
| WebSocket disconnect terus | `NEXT_PUBLIC_WS_URL` salah; pastikan `wss://` kalau sudah HTTPS |
| Backend crash saat start | `docker compose --profile app logs backend` — cek koneksi DB & MQTT |
| `relation "sensor_readings" does not exist` | Tabel belum dibuat — tunggu backend selesai start, atau `alembic upgrade head` |
| ESP32 tidak terkonek | Port 1883 belum dibuka di firewall / security group cloud provider |
| Notifikasi WAHA tidak jalan | `WAHA_BASE_URL` dari dalam container = `http://host.docker.internal:3000` |
| Prediksi/notification jalan 2× | Jangan pernah pakai `--workers > 1` (APScheduler in-process) |

---

## 10. Catatan Arsitektur

```
Internet
   │
   ├── :1883 ──────────────► toren_mqtt (Mosquitto) ◄──── ESP32 (publisher)
   │
   └── https://aminu.irsad.site ─► Cloudflare Tunnel (cloudflared di host)
                                        └─► 127.0.0.1:8005 ─► toren_backend (FastAPI :8000)
                                                   │         /api/v1, /ws, /docs
                                                   ├──► toren_db (TimescaleDB) — jaringan internal
                                                   └──► toren_mqtt
```

Semua container berada di jaringan bridge `toren`. Database **tidak** punya
port publik — hanya reachable dari dalam jaringan Docker.
