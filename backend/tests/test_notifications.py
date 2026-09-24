"""
Unit and integration tests for Notification Service and WAHA (WhatsApp HTTP API).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services import notification_service
from app.services.notification_service import (
    format_waha_chat_id,
    send_valve_closed_notification,
    send_sudden_change_notification,
    send_early_warning_notification,
)


def test_format_waha_chat_id():
    # Indonesian 08xx number
    assert format_waha_chat_id("08123456789") == "628123456789@c.us"
    # Number with symbols
    assert format_waha_chat_id("+62 812-3456-7890") == "6281234567890@c.us"
    # Already with 62
    assert format_waha_chat_id("628123456789") == "628123456789@c.us"
    # Already formatted with @c.us
    assert format_waha_chat_id("628123456789@c.us") == "628123456789@c.us"
    # Group chat ID
    assert format_waha_chat_id("120363023456789@g.us") == "120363023456789@g.us"
    # Empty string
    assert format_waha_chat_id("") == ""


@pytest.mark.asyncio
async def test_send_waha_success():
    settings = get_settings()
    with patch.object(settings, "notif_whatsapp_targets", "08123456789"), \
         patch.object(settings, "waha_base_url", "http://localhost:3000"), \
         patch.object(settings, "waha_session", "default"), \
         patch.object(settings, "waha_api_key", "secret-key"):

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await notification_service._send_waha("Test Alert Message")

            assert result is True
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0] == "http://localhost:3000/api/sendText"
            assert call_kwargs["json"] == {
                "session": "default",
                "chatId": "628123456789@c.us",
                "text": "Test Alert Message",
            }
            assert call_kwargs["headers"]["X-Api-Key"] == "secret-key"


@pytest.mark.asyncio
async def test_send_waha_error_handling():
    settings = get_settings()
    with patch.object(settings, "notif_whatsapp_targets", "08123456789"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            result = await notification_service._send_waha("Test Message")
            assert result is False


@pytest.mark.asyncio
async def test_check_waha_session_status():
    settings = get_settings()
    with patch.object(settings, "waha_base_url", "http://localhost:3000"), \
         patch.object(settings, "waha_session", "default"):

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"name": "default", "status": "WORKING"}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            status = await notification_service.check_waha_session_status()
            assert status["online"] is True
            assert status["status"] == "WORKING"
            assert status["session"] == "default"


@pytest.mark.asyncio
async def test_notification_triggers_call_dispatch():
    with patch("app.services.notification_service._dispatch_all", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {"whatsapp": True}

        # 1. Valve closed
        res1 = await send_valve_closed_notification("bathroom", 45.0, "turbidity")
        assert res1 == {"whatsapp": True}
        assert mock_dispatch.call_count == 1
        args, kwargs = mock_dispatch.call_args
        assert "BATHROOM" in args[1]
        assert "45.0" in args[1]
        assert kwargs["trigger"] == "valve_closed"

        # 2. Sudden change
        res2 = await send_sudden_change_notification("ph", 4.5, 7.2, 38.0)
        assert res2 == {"whatsapp": True}
        assert mock_dispatch.call_count == 2
        args, kwargs = mock_dispatch.call_args
        assert "PH" in args[1]
        assert "4.50" in args[1]
        assert kwargs["trigger"] == "sudden_change"

        # 3. Early warning
        res3 = await send_early_warning_notification(4.2, "28 Sep 2026", 62.0, "kitchen")
        assert res3 == {"whatsapp": True}
        assert mock_dispatch.call_count == 3
        args, kwargs = mock_dispatch.call_args
        assert "4.2 HARI LAGI" in args[1]
        assert "28 Sep 2026" in args[1]
        assert kwargs["trigger"] == "early_warning"


def test_api_notification_status():
    client = TestClient(app)
    with patch("app.services.notification_service.check_waha_session_status", new_callable=AsyncMock) as mock_waha:
        mock_waha.return_value = {"online": True, "status": "WORKING"}

        response = client.get("/api/v1/notifications/status")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "whatsapp" in data
        assert data["whatsapp"]["provider"] in ("waha", "fonnte")
        assert "waha" in data["whatsapp"]


def test_api_notification_test_dispatch():
    client = TestClient(app)
    with patch("app.services.notification_service._send_whatsapp", new_callable=AsyncMock) as mock_wa:
        mock_wa.return_value = True

        response = client.post(
            "/api/v1/notifications/test",
            json={"channel": "whatsapp", "message": "Halo dari automated pytest"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["results"]["whatsapp"] is True
        mock_wa.assert_called_once()


def test_api_trigger_ews():
    client = TestClient(app)
    with patch("app.services.notification_service.send_early_warning_notification", new_callable=AsyncMock) as mock_ews:
        mock_ews.return_value = {"whatsapp": True}

        response = client.post(
            "/api/v1/notifications/trigger-ews",
            json={"days_until": 2.5, "target_valve": "laundry", "current_score": 48.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dispatched"
        assert data["days_until"] == 2.5
        mock_ews.assert_called_once()
