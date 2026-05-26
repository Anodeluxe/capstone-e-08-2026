from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─── Valve ────────────────────────────────────────────────────────────────────

class ValveCommandRequest(BaseModel):
    """Body for POST /valves/{valve_id}/command — sent by the frontend."""

    action: Literal["open", "close"]
    reason: str | None = Field(
        default=None,
        max_length=300,
        description="Optional reason for manual override (stored in override log)",
    )


class ValveStateOut(BaseModel):
    id: str
    is_open: bool
    last_changed_at: datetime
    last_changed_by: str
    quality_score_at_close: float | None

    model_config = {"from_attributes": True}


class ValveOverrideLogOut(BaseModel):
    id: int
    valve_id: str
    action: str
    reason: str | None
    score_at_override: float | None
    overridden_at: datetime
    user_id: str | None

    model_config = {"from_attributes": True}


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationSettingsRequest(BaseModel):
    """Update notification targets."""

    email_recipients: list[str] = Field(default_factory=list)
    whatsapp_targets: list[str] = Field(default_factory=list)
    notify_on_valve_close: bool = True
    notify_on_sudden_change: bool = True
    notify_on_early_warning: bool = True
    early_warning_days: int = Field(default=3, ge=1, le=14)


class NotificationLogOut(BaseModel):
    id: int
    sent_at: datetime
    channel: str
    recipient: str
    subject: str
    trigger_type: str
    success: bool
    error_detail: str | None

    model_config = {"from_attributes": True}


# ─── Predictions ──────────────────────────────────────────────────────────────

class PredictionResultOut(BaseModel):
    id: int
    computed_at: datetime
    target_parameter: str
    valve_id: str | None
    days_until_threshold: float | None
    predicted_date: datetime | None
    confidence: float | None
    model_used: str
    notification_sent: bool

    model_config = {"from_attributes": True, "protected_namespaces": ()}