# ─────────────────────────────────────────────────────────────────────────────
# Toren Monitoring — Frontend (Next.js PWA)
#
# Multi-stage build:
#   deps    → npm ci (node_modules)
#   builder → next build, menghasilkan .next/standalone (output file tracing)
#   runner  → image akhir ramping: server.js + static assets
#
# Catatan penting:
#   * NEXT_PUBLIC_* di-inline Next.js saat `next build` — makanya variabelnya
#     dikirim sebagai build ARG, bukan runtime ENV. Mengubah URL API berarti
#     harus rebuild image frontend.
#   * `output: 'standalone'` di next.config.ts wajib aktif, kalau tidak
#     .next/standalone tidak terbentuk dan stage runner gagal.
#   * public/ dan .next/static TIDAK ikut otomatis ke standalone, jadi
#     di-copy manual di stage runner (sesuai dokumentasi Next.js).
# ─────────────────────────────────────────────────────────────────────────────

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# URL publik untuk API + WebSocket (di-inline ke bundle client saat build)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_DEMO_MODE=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE

RUN npm run build


FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 1001 nodejs \
 && adduser -S nextjs -u 1001

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
