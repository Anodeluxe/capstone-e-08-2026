"""
Notification API Endpoints
──────────────────────────
Provides endpoints to check notification status, test WAHA/Email channels,
and manually trigger test alerts for demo and evaluation purposes.
"""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.security import get_current_user_optional
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])
settings = get_settings()


class TestNotificationRequest(BaseModel):
    channel: Literal["whatsapp", "email", "all"] = Field(
        default="whatsapp",
        description="Notification channel to test",
    )
    custom_target: str | None = Field(
        default=None,
        description="Optional custom phone number (e.g. 08123456789) or email address",
    )
    message: str | None = Field(
        default=None,
        description="Optional custom text message for the test",
    )


class ManualEwsRequest(BaseModel):
    days_until: float = Field(default=3.5, description="Days remaining until unfit threshold")
    target_valve: str | None = Field(default="bathroom", description="Valve ID affected or null")
    current_score: float = Field(default=52.0, description="Current quality score")


@router.get("/status")
async def get_notification_status(current_user: dict | None = Depends(get_current_user_optional)):
    """
    Check the operational status of notification channels,
    including WAHA (WhatsApp HTTP API) session connectivity.
    """
    waha_info = await notification_service.check_waha_session_status()

    return {
        "email": {
            "configured": bool(settings.mail_username and settings.mail_server),
            "server": settings.mail_server,
            "sender": settings.mail_from,
        },
        "whatsapp": {
            "provider": settings.whatsapp_provider,
            "target_count": len(settings.whatsapp_targets),
            "targets": settings.whatsapp_targets,
            "waha": {
                "base_url": settings.waha_base_url,
                "session": settings.waha_session,
                "api_key_set": bool(settings.waha_api_key),
                "connection": waha_info,
            },
            "fonnte_configured": bool(settings.fonnte_api_key),
        },
    }


@router.post("/test")
async def send_test_notification(
    req: TestNotificationRequest,
    current_user: dict | None = Depends(get_current_user_optional),
):
    """
    Dispatch a test alert via WAHA (WhatsApp) or Email.
    """
    operator = current_user.get("sub", "operator_test") if current_user else "operator_local"
    text = req.message or (
        f"🔔 *UJI COBA NOTIFIKASI CAPSTONE E-08*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Pesan uji coba pengiriman notifikasi dari Sistem Monitoring Toren DTETI UGM.\n"
        f"• *Kanal:* {req.channel.upper()}\n"
        f"• *Operator:* `{operator}`\n"
        f"• *Status:* Berhasil Terhubung!\n"
        f"_— Tim Capstone DTETI UGM 2026_"
    )

    results: dict[str, bool] = {}

    if req.channel in ("whatsapp", "all"):
        if req.custom_target:
            # Send to specific custom target
            chat_id = notification_service.format_waha_chat_id(req.custom_target)
            import httpx
            base_url = settings.waha_base_url.rstrip("/")
            url = f"{base_url}/api/sendText"
            headers = {"Content-Type": "application/json"}
            if settings.waha_api_key:
                headers["X-Api-Key"] = settings.waha_api_key
            payload = {
                "session": settings.waha_session,
                "chatId": chat_id,
                "text": text,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    results["whatsapp"] = True
            except Exception as e:
                results["whatsapp"] = False
                results["whatsapp_error"] = str(e)
        else:
            results["whatsapp"] = await notification_service._send_whatsapp(text)

    if req.channel in ("email", "all"):
        results["email"] = await notification_service._send_email(
            subject="[Toren Monitor] Test Notifikasi Sistem",
            body=text,
        )

    return {
        "status": "completed",
        "results": results,
    }


@router.post("/trigger-ews")
async def trigger_ews_notification(
    req: ManualEwsRequest,
    current_user: dict | None = Depends(get_current_user_optional),
):
    """
    Manually trigger an Early Warning System (EWS) notification alert.
    Useful for demonstration during sidang/evaluation.
    """
    from datetime import datetime, timedelta, timezone

    predicted_date = (datetime.now(timezone.utc) + timedelta(days=req.days_until)).strftime("%d %b %Y")

    results = await notification_service.send_early_warning_notification(
        days_until=req.days_until,
        predicted_date=predicted_date,
        current_score=req.current_score,
        valve_id=req.target_valve,
    )

    return {
        "status": "dispatched",
        "days_until": req.days_until,
        "predicted_date": predicted_date,
        "results": results,
    }
