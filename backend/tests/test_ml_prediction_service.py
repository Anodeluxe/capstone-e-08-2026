import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import ml_prediction_service as service


@pytest.fixture
def ml_ready(monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(
        ml_enabled=True, ml_active_model="xgboost", ml_lookback_hours=73,
    ))
    monkeypatch.setattr(service, "get_active_drain_log", AsyncMock(return_value=None))


def test_insufficient_history_does_not_predict(ml_ready, monkeypatch):
    model = SimpleNamespace(predict=lambda _: pytest.fail("Model must not run"))
    monkeypatch.setattr(service, "load_xgb_bundle", lambda: {"model": model})
    monkeypatch.setattr(service, "get_latest_features_async", AsyncMock(return_value=None))
    result = asyncio.run(service.predict_hybrid(None, [], [], elapsed_fraction=0))
    assert result["status"] == "insufficient_history"
    assert result["message"].startswith("Data historis belum cukup")
    assert result["rul_hours"] is None
    assert result["days_until_threshold"] is None


def test_missing_model_has_distinct_status(ml_ready, monkeypatch):
    monkeypatch.setattr(service, "load_xgb_bundle", lambda: None)
    result = asyncio.run(service.predict_hybrid(None, [], [], elapsed_fraction=0))
    assert result["status"] == "model_unavailable"


def test_ready_model_returns_rul(ml_ready, monkeypatch):
    monkeypatch.setattr(service, "predict_rul_ml", AsyncMock(return_value={
        "rul_hours": 48.0, "within_30d_window": True, "confidence": 0.9,
    }))
    result = asyncio.run(service.predict_hybrid(None, [], [], elapsed_fraction=0))
    assert result["rul_hours"] == 48.0
    assert result["days_until_threshold"] == 2.0
    assert "status" not in result


def test_linear_mode_is_rejected(ml_ready):
    with pytest.raises(ValueError):
        asyncio.run(service.predict_hybrid(None, [], [], elapsed_fraction=0, mode="linear"))


@pytest.mark.parametrize("status", ["insufficient_history", "model_unavailable"])
def test_api_does_not_save_unavailable_prediction(monkeypatch, status):
    from unittest.mock import Mock
    from app.api.v1 import predictions

    result = service._not_ready_result(status, "Belum siap")
    monkeypatch.setattr(predictions, "predict_hybrid", AsyncMock(return_value=result))
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [])),
        add=Mock(), commit=AsyncMock(),
    )
    response = asyncio.run(predictions.run_prediction_now(hours=73, mode="auto", db=db))
    assert response["prediction"]["status"] == status
    assert response["data_points"] == 0
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("rows, ready", [(0, False), (12, False), (72, False), (73, True)])
def test_hourly_history_requirement(rows, ready):
    import pandas as pd
    from app.ml.features import build_feature_matrix

    hourly = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=rows, freq="h"),
        "ph": [7.0] * rows, "tds": [150.0] * rows,
        "turbidity": [1.0] * rows, "temperature": [27.0] * rows,
        "score_overall": [95.0] * rows,
    })
    assert (build_feature_matrix(hourly) is not None) is ready


def test_scheduler_skips_save_and_notification(monkeypatch):
    from unittest.mock import Mock
    from app.tasks import scheduler

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [(None, 95.0)] * 12)
    db.add = Mock()
    session = AsyncMock()
    session.__aenter__.return_value = db
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(scheduler, "predict_hybrid", AsyncMock(return_value=
        service._not_ready_result("insufficient_history", "Data historis belum cukup")
    ))
    notify = AsyncMock()
    monkeypatch.setattr(scheduler, "send_early_warning_notification", notify)
    asyncio.run(scheduler.run_prediction_job())
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
    notify.assert_not_awaited()
