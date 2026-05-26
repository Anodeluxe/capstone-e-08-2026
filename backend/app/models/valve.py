from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ValveID(str, PyEnum):
    BATHROOM = "bathroom"
    KITCHEN = "kitchen"
    LAUNDRY = "laundry"
    GARDEN = "garden"


class ValveState(Base):
    """Current state of each of the 4 solenoid valves."""

    __tablename__ = "valve_states"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "bathroom"
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_changed_by: Mapped[str] = mapped_column(String(20), default="system")  # "system" | "user:<id>" | "esp32"
    quality_score_at_close: Mapped[float | None] = mapped_column(Float, nullable=True)

    overrides: Mapped[list["ValveOverrideLog"]] = relationship(back_populates="valve")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "is_open": self.is_open,
            "last_changed_at": self.last_changed_at.isoformat(),
            "last_changed_by": self.last_changed_by,
            "quality_score_at_close": self.quality_score_at_close,
        }


class ValveOverrideLog(Base):
    """
    Log of every manual override action. Used to evaluate
    how often users override automatic decisions (feedback loop).
    """

    __tablename__ = "valve_override_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    valve_id: Mapped[str] = mapped_column(String(20), ForeignKey("valve_states.id"))
    action: Mapped[str] = mapped_column(String(10))        # "open" | "close"
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_at_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    overridden_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    valve: Mapped["ValveState"] = relationship(back_populates="overrides")


class NotificationLog(Base):
    """Records every notification sent (email / WhatsApp)."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    channel: Mapped[str] = mapped_column(String(20))       # "email" | "whatsapp"
    recipient: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(String(50))  # "sudden_change" | "early_warning" | "valve_closed"
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class PredictionResult(Base):
    """Stores the latest early-warning prediction per run."""

    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    target_parameter: Mapped[str] = mapped_column(String(50))   # "score_overall" | "ph" | ...
    valve_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    days_until_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)  # None = already below
    predicted_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0
    model_used: Mapped[str] = mapped_column(String(50), default="linear_regression")
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "computed_at": self.computed_at.isoformat(),
            "target_parameter": self.target_parameter,
            "valve_id": self.valve_id,
            "days_until_threshold": self.days_until_threshold,
            "predicted_date": self.predicted_date.isoformat() if self.predicted_date else None,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "notification_sent": self.notification_sent,
        }