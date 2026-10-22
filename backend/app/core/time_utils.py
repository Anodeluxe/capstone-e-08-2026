"""
UTC timestamp helpers
─────────────────────
All datetimes in the database are stored as naive UTC (datetime.utcnow()).
Before sending them to the frontend they must be marked as UTC in the
ISO-8601 string (`+00:00` / `Z`), so the browser can render the correct
local time (WIB) instead of showing the raw UTC clock (WIB − 7 jam).
"""

from datetime import datetime, timezone

from pydantic import field_serializer


def ensure_utc(dt: datetime | None) -> datetime | None:
    """
    Attach UTC tzinfo to a naive datetime. Naive values are UTC by
    project convention (see datetime.utcnow usage across the backend).
    Aware datetimes are returned unchanged.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def utc_to_iso(dt: datetime | None) -> str | None:
    """Serialize a naive-UTC datetime as ISO-8601 with an explicit +00:00 offset."""
    aware = ensure_utc(dt)
    return aware.isoformat() if aware else None


def serialize_utc(value: datetime | None) -> datetime | None:
    """
    Field serializer for Pydantic `Out` models: marks naive datetimes as
    UTC so the JSON response carries an explicit offset.

    Usage:
        @field_serializer("timestamp")
        def serialize_timestamp(self, v: datetime) -> datetime:
            return serialize_utc(v)
    """
    return ensure_utc(value)


# Re-export so models can import both helpers from one place.
__all__ = ["ensure_utc", "utc_to_iso", "serialize_utc", "field_serializer"]
