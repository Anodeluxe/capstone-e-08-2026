from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_demo_mode_blocks_valve_controls_and_notifications():
    settings = get_settings()
    with patch.object(settings, "demo_mode", True):
        client = TestClient(app)
        assert client.post("/api/v1/valves/auto").status_code == 403
        assert client.post(
            "/api/v1/valves/bathroom/command", json={"action": "close"}
        ).status_code == 403
        assert client.post(
            "/api/v1/notifications/test", json={"channel": "all"}
        ).status_code == 403
        assert client.post(
            "/api/v1/notifications/trigger-ews", json={}
        ).status_code == 403
        assert client.post("/api/v1/drain-logs/start", json={}).status_code == 403
        assert client.post("/api/v1/drain-logs/1/end").status_code == 403


def test_demo_notification_status_does_not_probe_external_services():
    settings = get_settings()
    with patch.object(settings, "demo_mode", True), \
         patch("app.services.notification_service.check_waha_session_status") as probe:
        client = TestClient(app)
        response = client.get("/api/v1/notifications/status")

    assert response.status_code == 200
    assert response.json() == {"demo_mode": True, "notifications_enabled": False}
    probe.assert_not_called()
