"""
Notification Service
─────────────────────
Sends email and WhatsApp notifications for three trigger types:
  1. valve_closed      — valve auto-closed due to poor water quality
  2. sudden_change     — sudden parameter drop/spike detected
  3. early_warning     — water predicted to be unfit within N days (EWS)

Supported Channels:
  - Email:     fastapi-mail (SMTP / Gmail)
  - WhatsApp:  WAHA (WhatsApp HTTP API - primary) with Fonnte fallback
"""

import logging
import re
from typing import Any
import httpx
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import get_settings

logger = logging.getLogger("NotificationService")
settings = get_settings()

# Built lazily in _get_fast_mail() so the app starts even when email is unconfigured.
_fast_mail: FastMail | None = None


def _get_fast_mail() -> FastMail:
    """Return (and cache) a FastMail instance. Only called when credentials exist."""
    global _fast_mail
    if _fast_mail is None:
        config = ConnectionConfig(
            MAIL_USERNAME=settings.mail_username,
            MAIL_PASSWORD=settings.mail_password,
            MAIL_FROM=settings.mail_from,
            MAIL_PORT=settings.mail_port,
            MAIL_SERVER=settings.mail_server,
            MAIL_STARTTLS=settings.mail_starttls,
            MAIL_SSL_TLS=settings.mail_ssl_tls,
            USE_CREDENTIALS=bool(settings.mail_username),
            VALIDATE_CERTS=True,
        )
        _fast_mail = FastMail(config)
    return _fast_mail


def format_waha_chat_id(target: str) -> str:
    """
    Format a phone number into WAHA chatId format (e.g. 628123456789@c.us).
    Preserves group chatIds ending in @g.us.
    """
    cleaned = target.strip()
    if "@c.us" in cleaned or "@g.us" in cleaned:
        return cleaned

    # Strip any non-digit characters
    digits = re.sub(r"[^\d]", "", cleaned)
    if not digits:
        return ""

    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif not digits.startswith("62") and len(digits) >= 8:
        digits = "62" + digits

    return f"{digits}@c.us"


# ─── Public interface ──────────────────────────────────────────────────────────

async def send_valve_closed_notification(
    valve_id: str,
    score: float,
    anomaly_param: str | None = None,
) -> dict[str, bool]:
    """Notify when a valve is automatically closed by the system."""
    subject = f"[Toren Monitor] Katup '{valve_id}' ditutup otomatis"
    body = _valve_closed_body(valve_id, score, anomaly_param)
    return await _dispatch_all(subject, body, trigger="valve_closed")


async def send_sudden_change_notification(
    parameter: str,
    current_value: float,
    previous_value: float,
    current_score: float,
) -> dict[str, bool]:
    """Notify when a sudden parameter change is detected."""
    subject = f"[Toren Monitor] ⚠️ Perubahan mendadak pada {parameter}"
    body = _sudden_change_body(parameter, current_value, previous_value, current_score)
    return await _dispatch_all(subject, body, trigger="sudden_change")


async def send_early_warning_notification(
    days_until: float,
    predicted_date: str,
    current_score: float,
    valve_id: str | None = None,
) -> dict[str, bool]:
    """Notify a few days before water quality reaches unfit threshold (EWS)."""
    subject = f"[Toren Monitor] 🕐 Peringatan dini kualitas air (EWS)"
    body = _early_warning_body(days_until, predicted_date, current_score, valve_id)
    return await _dispatch_all(subject, body, trigger="early_warning")


# ─── Internal dispatch ─────────────────────────────────────────────────────────

async def _dispatch_all(subject: str, body: str, trigger: str) -> dict[str, bool]:
    """Send to all configured channels and return success flags."""
    results: dict[str, bool] = {}

    if settings.mail_username:
        results["email"] = await _send_email(subject, body)

    if settings.whatsapp_targets:
        results["whatsapp"] = await _send_whatsapp(body)

    return results


async def _send_email(subject: str, body: str) -> bool:
    """Send email to all configured mail recipients."""
    recipients = [settings.mail_from]

    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.plain,
        )
        await _get_fast_mail().send_message(message)
        logger.info(f"[Notif] Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"[Notif] Email failed: {e}")
        return False


async def _send_whatsapp(message: str) -> bool:
    """Dispatch WhatsApp message according to configured provider."""
    provider = getattr(settings, "whatsapp_provider", "waha").lower()
    if provider == "waha":
        return await _send_waha(message)
    elif provider == "fonnte":
        return await _send_fonnte(message)
    else:
        logger.warning(f"[Notif] Unknown WhatsApp provider: '{provider}', defaulting to WAHA")
        return await _send_waha(message)


async def _send_waha(message: str) -> bool:
    """
    Send WhatsApp message via WAHA (WhatsApp HTTP API).
    Endpoint: POST /api/sendText
    Payload: {"session": session, "chatId": "628xxx@c.us", "text": message}
    """
    targets = settings.whatsapp_targets
    if not targets:
        logger.debug("[Notif] No WhatsApp targets configured.")
        return False

    base_url = settings.waha_base_url.rstrip("/")
    url = f"{base_url}/api/sendText"

    headers = {"Content-Type": "application/json"}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key

    session = settings.waha_session or "default"
    success_count = 0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for target in targets:
                chat_id = format_waha_chat_id(target)
                if not chat_id:
                    continue

                payload = {
                    "session": session,
                    "chatId": chat_id,
                    "text": message,
                }

                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    logger.info(f"[Notif] WAHA message sent successfully to {chat_id}")
                    success_count += 1
                except httpx.HTTPStatusError as e:
                    logger.error(
                        f"[Notif] WAHA HTTP error for {chat_id}: status={e.response.status_code} "
                        f"body={e.response.text}"
                    )
                except Exception as e:
                    logger.error(f"[Notif] WAHA send failed for {chat_id}: {e}")

        return success_count > 0

    except Exception as e:
        logger.error(f"[Notif] WAHA client error: {e}")
        return False


async def _send_fonnte(message: str) -> bool:
    """Send WhatsApp message via Fonnte API as fallback."""
    if not settings.fonnte_api_key:
        logger.warning("[Notif] Fonnte API key not configured.")
        return False

    # Strip @c.us suffix if present for Fonnte
    raw_targets = [re.sub(r"@c\.us|@g\.us", "", t).strip() for t in settings.whatsapp_targets]
    targets = ",".join(raw_targets)
    if not targets:
        return False

    payload = {
        "target": targets,
        "message": message,
        "delay": "2",
        "countryCode": "62",
    }
    headers = {"Authorization": settings.fonnte_api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.fonnte_api_url,
                data=payload,
                headers=headers,
            )
            response.raise_for_status()
            logger.info(f"[Notif] WhatsApp (Fonnte) sent to {targets}")
            return True
    except Exception as e:
        logger.error(f"[Notif] WhatsApp (Fonnte) failed: {e}")
        return False


async def check_waha_session_status() -> dict[str, Any]:
    """
    Check connection status with the WAHA instance and session.
    Useful for health-checks and administrative dashboard verification.
    """
    base_url = settings.waha_base_url.rstrip("/")
    session = settings.waha_session or "default"
    url = f"{base_url}/api/sessions/{session}"

    headers = {}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "online": True,
                    "session": session,
                    "status": data.get("status", "UNKNOWN"),
                    "details": data,
                }
            elif response.status_code == 404:
                return {
                    "online": True,
                    "session": session,
                    "status": "NOT_FOUND",
                    "message": f"Session '{session}' is not started in WAHA.",
                }
            else:
                return {
                    "online": False,
                    "session": session,
                    "status": f"HTTP_{response.status_code}",
                    "message": response.text,
                }
    except Exception as e:
        return {
            "online": False,
            "session": session,
            "status": "UNREACHABLE",
            "error": str(e),
        }


# ─── Message templates ─────────────────────────────────────────────────────────

def _valve_closed_body(valve_id: str, score: float, anomaly_param: str | None) -> str:
    param_line = f"• *Parameter Pemicu:* {anomaly_param.upper()}\n" if anomaly_param else ""
    return (
        f"🚨 *SISTEM MONITORING TOREN — NOTIFIKASI KATUP*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Katup distribusi *{valve_id.upper()}* telah *DITUTUP OTOMATIS* oleh sistem "
        f"karena kualitas air tidak memenuhi ambang batas aman.\n\n"
        f"• *Skor Kualitas:* `{score:.1f} / 100`\n"
        f"{param_line}"
        f"• *Status Interlock:* Aktif (Proteksi Pengguna)\n\n"
        f"Silakan periksa kondisi air toren melalui dashboard web. Anda dapat melakukan "
        f"*override manual* pada aplikasi jika diperlukan dalam kondisi darurat.\n\n"
        f"_— Tim Capstone DTETI UGM 2026 (E-08)_"
    )


def _sudden_change_body(param: str, curr: float, prev: float, score: float) -> str:
    direction = "LONJAKAN NAIK" if curr > prev else "PENURUNAN DRASTIS"
    return (
        f"⚠️ *PERINGATAN ANOMALI KONTAMINASI MENDADAK*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Terdeteksi perubahan mendadak pada parameter *{param.upper()}*!\n\n"
        f"• *Nilai Sebelumnya:* `{prev:.2f}`\n"
        f"• *Nilai Terkini:* `{curr:.2f}` ({direction})\n"
        f"• *Skor Kualitas Air:* `{score:.1f} / 100`\n\n"
        f"*Kemungkinan Penyebab:* Terjadi kontaminasi pada saluran masuk toren (pipa retak, banjir, atau sedimen dasar teraduk).\n"
        f"Sistem telah mengaktifkan mekanisme proteksi. Segera lakukan inspeksi fisik.\n\n"
        f"_— Tim Capstone DTETI UGM 2026 (E-08)_"
    )


def _early_warning_body(days: float, date: str, score: float, valve_id: str | None) -> str:
    valve_line = f"• *Distribusi Terdampak:* Katup {valve_id.upper()}\n" if valve_id else ""
    return (
        f"⏳ *EARLY WARNING SYSTEM (EWS) — KUALITAS AIR*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Berdasarkan analisis model prediktif (XGBoost RUL), air toren diperkirakan akan "
        f"mencapai batas tidak layak dalam:\n\n"
        f"👉 *{days:.1f} HARI LAGI* (Estimasi: {date})\n\n"
        f"• *Skor Kualitas Saat Ini:* `{score:.1f} / 100`\n"
        f"{valve_line}"
        f"\n*Rekomendasi Tindakan:*\n"
        f"Segera jadwalkan pengurasan toren atau pembersihan sedimen sebelum kualitas air melampaui batas toleransi kesehatan.\n\n"
        f"_— Tim Capstone DTETI UGM 2026 (E-08)_"
    )