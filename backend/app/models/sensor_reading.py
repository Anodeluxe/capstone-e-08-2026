from datetime import datetime

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SensorReading(Base):
    """
    Time-series table for all sensor readings from the ESP32.
    Converted to a TimescaleDB hypertable partitioned by `timestamp`.

    One row = one full reading snapshot from all 5 sensors.
    """

    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(index=True, nullable=False)

    # ── Raw sensor values ─────────────────────────────────────────────────────
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    turbidity: Mapped[float] = mapped_column(Float, nullable=False)   # NTU
    tds: Mapped[float] = mapped_column(Float, nullable=False)         # ppm
    temperature: Mapped[float] = mapped_column(Float, nullable=False) # °C
    water_level: Mapped[float] = mapped_column(Float, nullable=False) # cm or %

    # ── Computed quality scores (0–100) per use point ─────────────────────────
    score_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_bathroom: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_kitchen: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_laundry: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_garden: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Anomaly flags ──────────────────────────────────────────────────────────
    is_sudden_change: Mapped[bool] = mapped_column(default=False)
    anomaly_parameter: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        # Compound index for fast time-range queries per parameter
        Index("ix_sensor_readings_timestamp_desc", timestamp.desc()),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "ph": self.ph,
            "turbidity": self.turbidity,
            "tds": self.tds,
            "temperature": self.temperature,
            "water_level": self.water_level,
            "score_overall": self.score_overall,
            "score_bathroom": self.score_bathroom,
            "score_kitchen": self.score_kitchen,
            "score_laundry": self.score_laundry,
            "score_garden": self.score_garden,
            "is_sudden_change": self.is_sudden_change,
            "anomaly_parameter": self.anomaly_parameter,
        }