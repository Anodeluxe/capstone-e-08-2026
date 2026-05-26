from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ─── Inbound (from ESP32 via MQTT) ────────────────────────────────────────────

class ESP32SensorPayload(BaseModel):
    """
    JSON payload published by the ESP32 to `toren/sensors`.

    ESP32 firmware should publish:
    {
      "device_id": "toren_01",
      "timestamp": 1710000000,      // Unix epoch (UTC)
      "ph": 7.2,
      "turbidity": 3.5,
      "tds": 180.0,
      "temperature": 28.1,
      "water_level": 85.0
    }
    """

    device_id: str = Field(default="toren_01")
    timestamp: int | None = Field(
        default=None,
        description="Unix epoch from ESP32 RTC. If None, server time is used.",
    )
    ph: float = Field(..., ge=0.0, le=14.0, description="pH (0–14)")
    turbidity: float = Field(..., ge=0.0, description="Turbidity in NTU")
    tds: float = Field(..., ge=0.0, description="Total Dissolved Solids in ppm")
    temperature: float = Field(..., ge=0.0, le=100.0, description="Water temperature in °C")
    water_level: float = Field(..., ge=0.0, le=100.0, description="Water level in %")

    @field_validator("ph")
    @classmethod
    def validate_ph(cls, v: float) -> float:
        if not (0.0 <= v <= 14.0):
            raise ValueError("pH must be between 0 and 14")
        return round(v, 2)

    @field_validator("turbidity", "tds", "temperature", "water_level")
    @classmethod
    def round_floats(cls, v: float) -> float:
        return round(v, 2)


class ESP32ValveAck(BaseModel):
    """
    Acknowledgment payload published by ESP32 to `toren/valves/status`
    after executing a valve command.
    """

    valve_id: str
    is_open: bool
    timestamp: int | None = None


# ─── Outbound (responses to frontend) ─────────────────────────────────────────

class SensorReadingOut(BaseModel):
    id: int
    timestamp: datetime
    ph: float
    turbidity: float
    tds: float
    temperature: float
    water_level: float
    score_overall: float | None
    score_bathroom: float | None
    score_kitchen: float | None
    score_laundry: float | None
    score_garden: float | None
    is_sudden_change: bool
    anomaly_parameter: str | None

    model_config = {"from_attributes": True}


class SensorHistoryParams(BaseModel):
    """Query params for /sensors/history endpoint."""

    hours: int = Field(default=24, ge=1, le=720, description="Look-back window in hours")
    parameter: str | None = Field(
        default=None,
        description="Filter by parameter: ph | turbidity | tds | temperature | water_level",
    )