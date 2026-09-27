from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "okDriver CCTV Monitoring Platform"
    environment: str = "development"

    database_url: str = "sqlite:///./okdriver.db"
    auto_create_tables: bool = True

    jwt_secret_key: str = "change-me-in-.env-this-is-not-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    credential_encryption_key: str = "z1O5S6f9y2m3aVYQ2pXG8qk1s3iH2n1r0k9p5q3wq8k="

    redis_url: str | None = None

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    enable_analytics_simulator: bool = True
    analytics_event_interval_seconds: float = 6.0
    enable_heartbeat_service: bool = True
    heartbeat_interval_seconds: float = 8.0

    event_dedup_window_seconds: int = 10

    rate_limit_login: str = "10/minute"
    rate_limit_ingest: str = "120/minute"

    default_admin_username: str = "admin"
    default_admin_password: str = "Admin@12345"
    default_operator_username: str = "operator"
    default_operator_password: str = "Operator@12345"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
