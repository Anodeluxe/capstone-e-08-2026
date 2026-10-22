from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time_utils import utc_to_iso


class DrainLog(Base):
    """
    Log of water tank drain cycles. Used to compute the elapsed fraction
    of the current drain cycle for ML RUL prediction.

    The ML model was trained with `elapsed_hours` as a normalized fraction
    (0.0 = just drained, 1.0 = end of expected cycle). This table tracks
    the start/end of each drain cycle to compute the current fraction.
    """

    __tablename__ = "drain_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # When the drain cycle started (valve opened / tank drained)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # When the drain cycle ended (tank refilled / valve closed)
    # NULL = cycle still in progress
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # First quality-threshold event observed during this cycle.
    threshold_crossed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    event_observed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    event_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Estimated total cycle length in hours (default ~2400h based on training data)
    # Used as denominator for elapsed_fraction = elapsed_hours / cycle_estimate_hours
    cycle_estimate_hours: Mapped[float] = mapped_column(Float, default=2400.0)

    # Who/what triggered this drain log
    # "system" | "user:<id>" | "esp32" | "admin:<id>"
    created_by: Mapped[str] = mapped_column(String(50), default="system")

    # Optional notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "started_at": utc_to_iso(self.started_at),
            "ended_at": utc_to_iso(self.ended_at),
            "threshold_crossed_at": utc_to_iso(self.threshold_crossed_at),
            "event_observed": self.event_observed,
            "event_reason": self.event_reason,
            "cycle_estimate_hours": self.cycle_estimate_hours,
            "created_by": self.created_by,
            "notes": self.notes,
            "created_at": utc_to_iso(self.created_at),
            "updated_at": utc_to_iso(self.updated_at),
            "is_active": self.ended_at is None,
            "elapsed_hours": (
                (datetime.utcnow() - self.started_at).total_seconds() / 3600.0
                if self.started_at and not self.ended_at
                else None
            ),
        }
