"""Incoming sensor timestamps must never land in the future."""

from datetime import datetime, timedelta, timezone

from app.mqtt.handlers import _resolve_reading_timestamp


def _epoch(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def test_missing_timestamp_uses_server_time():
    before = datetime.utcnow()
    result = _resolve_reading_timestamp(None)
    after = datetime.utcnow()
    assert before <= result <= after


def test_zero_timestamp_uses_server_time():
    before = datetime.utcnow()
    result = _resolve_reading_timestamp(0)
    after = datetime.utcnow()
    assert before <= result <= after


def test_future_timestamp_is_clamped():
    before = datetime.utcnow()
    result = _resolve_reading_timestamp(
        _epoch(datetime.utcnow() + timedelta(hours=9))
    )
    assert result <= datetime.utcnow()
    assert result >= before


def test_stale_timestamp_is_clamped():
    before = datetime.utcnow()
    result = _resolve_reading_timestamp(
        _epoch(datetime.utcnow() - timedelta(days=2))
    )
    assert result >= before


def test_reasonable_timestamp_is_kept():
    device_time = (datetime.utcnow() - timedelta(minutes=2)).replace(microsecond=0)
    assert _resolve_reading_timestamp(_epoch(device_time)) == device_time
