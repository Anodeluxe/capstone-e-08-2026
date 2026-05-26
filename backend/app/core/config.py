from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "Toren Monitoring"
    app_env: str = "development"
    secret_key: str = "changeme"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/toren_db"
    database_sync_url: str = "postgresql://postgres:password@localhost:5432/toren_db"

    # ── MQTT ─────────────────────────────────────────────────────────────────
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_client_id: str = "toren-backend"
    mqtt_topic_sensors: str = "toren/sensors"
    mqtt_topic_valve_cmd: str = "toren/valves/cmd"
    mqtt_topic_valve_status: str = "toren/valves/status"

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Email ─────────────────────────────────────────────────────────────────
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False

    # ── WhatsApp (Fonnte) ─────────────────────────────────────────────────────
    fonnte_api_key: str = ""
    fonnte_api_url: str = "https://api.fonnte.com/send"
    notif_whatsapp_targets: str = ""  # "628xxx,628yyy"

    # ── Scoring weights ───────────────────────────────────────────────────────
    weight_ph: float = 0.30
    weight_turbidity: float = 0.30
    weight_tds: float = 0.25
    weight_temperature: float = 0.15

    # ── Alert thresholds ──────────────────────────────────────────────────────
    sudden_change_threshold: float = 20.0  # score-point drop = sudden anomaly
    early_warning_days: int = 3            # days before unfit = send warning

    # ── Auth ──────────────────────────────────────────────────────────────────
    api_key: str = ""  # Empty = auth disabled (dev mode); set in production

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000"

    @property
    def whatsapp_targets(self) -> list[str]:
        return [t.strip() for t in self.notif_whatsapp_targets.split(",") if t.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()