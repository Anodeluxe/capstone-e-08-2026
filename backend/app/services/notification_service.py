"""
Notification Service
─────────────────────
Sends email and WhatsApp notifications for three trigger types:
  1. valve_closed      — valve auto-closed due to poor water quality
  2. sudden_change     — sudden parameter drop detected
  3. early_warning     — water predicted to be unfit within N days

Uses:
  - Email:     fastapi-mail (SMTP / Gmail)
  - WhatsApp:  Fonnte HTTP API (Indonesian provider)
"""

import httpx
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import get_settings

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


# ─── Public interface ──────────────────────────────────────────────────────────

async def send_valve_closed_notification(
    valve_id: str,
    score: float,
    anomaly_param: str | None = None,
) -> dict[str, bool]:
    """Notify when a valve is automatically closed by the system."""
    subject = f"[Toren Monitor] Valve '{valve_id}' ditutup otomatis"
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
    """Notify a few days before water quality reaches unfit threshold."""
    subject = f"[Toren Monitor] 🕐 Peringatan dini kualitas air"
    body = _early_warning_body(days_until, predicted_date, current_score, valve_id)
    return await _dispatch_all(subject, body, trigger="early_warning")


# ─── Internal dispatch ─────────────────────────────────────────────────────────

async def _dispatch_all(subject: str, body: str, trigger: str) -> dict[str, bool]:
    """Send to all configured channels and return success flags."""
    results = {}

    if settings.mail_username:
        results["email"] = await _send_email(subject, body)

    if settings.fonnte_api_key and settings.whatsapp_targets:
        results["whatsapp"] = await _send_whatsapp(body)

    return results


async def _send_email(subject: str, body: str) -> bool:
    """Send email to all configured mail recipients."""
    # In production, pull recipient list from DB (user notification settings)
    recipients = [settings.mail_from]  # default to self; override from DB in handler

    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.plain,
        )
        await _get_fast_mail().send_message(message)
        print(f"[Notif] Email sent: {subject}")
        return True
    except Exception as e:
        print(f"[Notif] Email failed: {e}")
        return False


async def _send_whatsapp(message: str) -> bool:
    """Send WhatsApp message via Fonnte API to all configured targets."""
    targets = ",".join(settings.whatsapp_targets)
    if not targets:
        return False

    payload = {
        "target": targets,
        "message": message,
        "delay": "2",  # seconds between messages
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
            print(f"[Notif] WhatsApp sent to {targets}")
            return True
    except Exception as e:
        print(f"[Notif] WhatsApp failed: {e}")
        return False


# ─── Message templates ─────────────────────────────────────────────────────────

def _valve_closed_body(valve_id: str, score: float, anomaly_param: str | None) -> str:
    param_line = f"Parameter pemicu: {anomaly_param}\n" if anomaly_param else ""
    return (
        f"TOREN MONITORING SYSTEM — NOTIFIKASI OTOMATIS\n"
        f"{'='*50}\n\n"
        f"Valve '{valve_id.upper()}' telah ditutup otomatis karena kualitas air\n"
        f"berada di bawah batas aman untuk kebutuhan tersebut.\n\n"
        f"Skor kualitas saat ini : {score:.1f} / 100\n"
        f"{param_line}"
        f"\nSilakan periksa kondisi air toren Anda.\n"
        f"Anda dapat membuka kembali valve melalui aplikasi jika diperlukan.\n\n"
        f"— Toren Monitoring System"
    )


def _sudden_change_body(param: str, curr: float, prev: float, score: float) -> str:
    direction = "naik" if curr > prev else "turun"
    return (
        f"TOREN MONITORING SYSTEM — PERINGATAN MENDADAK\n"
        f"{'='*50}\n\n"
        f"Terdeteksi perubahan mendadak pada parameter: {param.upper()}\n\n"
        f"Nilai sebelumnya : {prev:.2f}\n"
        f"Nilai sekarang   : {curr:.2f}  ({direction} signifikan)\n"
        f"Skor kualitas    : {score:.1f} / 100\n\n"
        f"Kemungkinan penyebab: kontaminasi pada sumber air masuk (inlet).\n"
        f"Segera periksa kondisi inlet dan toren Anda.\n\n"
        f"— Toren Monitoring System"
    )


def _early_warning_body(days: float, date: str, score: float, valve_id: str | None) -> str:
    valve_line = f"Valve terdampak: {valve_id.upper()}\n" if valve_id else ""
    return (
        f"TOREN MONITORING SYSTEM — PERINGATAN DINI\n"
        f"{'='*50}\n\n"
        f"Berdasarkan tren kualitas air saat ini, sistem memprediksi\n"
        f"air toren akan mencapai batas tidak layak dalam:\n\n"
        f"  ⏳ {days:.1f} hari lagi (sekitar {date})\n\n"
        f"Skor kualitas saat ini : {score:.1f} / 100\n"
        f"{valve_line}"
        f"\nDisarankan untuk segera membersihkan atau menguras toren.\n\n"
        f"— Toren Monitoring System"
    )