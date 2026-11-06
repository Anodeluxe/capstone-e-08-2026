"""Automatic valve decisions: open while the score is above the point threshold."""

from unittest.mock import AsyncMock

import pytest

from app.models.valve import ValveState
from app.mqtt import handlers
from app.services import valve_service

VALVE_IDS = ["bathroom", "kitchen", "laundry", "garden"]


def _valve(valve_id: str, is_open: bool, last_changed_by: str) -> ValveState:
    return ValveState(id=valve_id, is_open=is_open, last_changed_by=last_changed_by)


@pytest.mark.asyncio
async def test_auto_reopens_valve_that_system_closed(monkeypatch):
    valve = _valve("garden", is_open=False, last_changed_by="system")
    db = AsyncMock()

    async def fake_get_valve_state(_db, valve_id):
        return valve if valve_id == "garden" else None

    async def fake_execute(_db, valve_id, action, triggered_by, **_kwargs):
        valve.is_open = action == "open"
        valve.last_changed_by = triggered_by
        return valve

    monkeypatch.setattr(valve_service, "get_valve_state", fake_get_valve_state)
    monkeypatch.setattr(valve_service, "execute_valve_command", fake_execute)

    changed = await valve_service.process_auto_valve_decisions(
        db, valves_to_close=[], current_score=95.0
    )

    assert valve.is_open is True
    assert changed == ["garden"]


@pytest.mark.asyncio
async def test_auto_reopens_legacy_ack_valve(monkeypatch):
    """Rows written before the ack fix may still carry last_changed_by=esp32_ack."""
    valve = _valve("kitchen", is_open=False, last_changed_by="esp32_ack")
    db = AsyncMock()

    async def fake_get_valve_state(_db, valve_id):
        return valve if valve_id == "kitchen" else None

    async def fake_execute(_db, valve_id, action, triggered_by, **_kwargs):
        valve.is_open = action == "open"
        valve.last_changed_by = triggered_by
        return valve

    monkeypatch.setattr(valve_service, "get_valve_state", fake_get_valve_state)
    monkeypatch.setattr(valve_service, "execute_valve_command", fake_execute)

    changed = await valve_service.process_auto_valve_decisions(
        db, valves_to_close=[], current_score=95.0
    )

    assert valve.is_open is True
    assert changed == ["kitchen"]


@pytest.mark.asyncio
async def test_manual_close_stays_closed_when_score_recovers(monkeypatch):
    valve = _valve("bathroom", is_open=False, last_changed_by="user:operator_local")
    db = AsyncMock()

    async def fake_get_valve_state(_db, valve_id):
        return valve if valve_id == "bathroom" else None

    async def fake_execute(_db, valve_id, action, triggered_by, **_kwargs):
        valve.is_open = action == "open"
        return valve

    monkeypatch.setattr(valve_service, "get_valve_state", fake_get_valve_state)
    monkeypatch.setattr(valve_service, "execute_valve_command", fake_execute)

    changed = await valve_service.process_auto_valve_decisions(
        db, valves_to_close=[], current_score=95.0
    )

    assert valve.is_open is False
    assert changed == []


@pytest.mark.asyncio
async def test_manual_open_is_not_auto_closed(monkeypatch):
    valve = _valve("bathroom", is_open=True, last_changed_by="user:operator_local")
    db = AsyncMock()

    async def fake_get_valve_state(_db, valve_id):
        return valve if valve_id == "bathroom" else None

    async def fake_execute(_db, valve_id, action, triggered_by, **_kwargs):
        valve.is_open = action == "open"
        valve.last_changed_by = triggered_by
        return valve

    monkeypatch.setattr(valve_service, "get_valve_state", fake_get_valve_state)
    monkeypatch.setattr(valve_service, "execute_valve_command", fake_execute)

    changed = await valve_service.process_auto_valve_decisions(
        db, valves_to_close=["bathroom"], current_score=10.0
    )

    assert valve.is_open is True
    assert changed == []


@pytest.mark.asyncio
async def test_valve_ack_keeps_command_origin(monkeypatch):
    valve = _valve("garden", is_open=True, last_changed_by="system")

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def commit(self):
            pass

    async def fake_get_valve_state(_db, _valve_id):
        return valve

    monkeypatch.setattr(handlers, "AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr(handlers, "get_valve_state", fake_get_valve_state)
    monkeypatch.setattr(
        handlers.ws_manager, "broadcast_valve_status", AsyncMock()
    )

    await handlers.handle_valve_ack('{"valve_id":"garden","is_open":false}')

    assert valve.is_open is False
    assert valve.last_changed_by == "system"
