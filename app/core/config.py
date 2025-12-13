from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "ERPMax Orchestrator"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = (
        "postgresql+asyncpg://erpmax:erpmax_dev_password@localhost:5432/erpmax_orchestrator"
    )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "RedisErpMax2025!"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "erpmax"
    rabbitmq_password: str = "RabbitErpMax2025!"

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_reset_token_expire_hours: int = 24

    # CORS
    allowed_origins: Union[str, list[str]] = (
        "http://localhost:3000,http://localhost:8000"
    )

    # Payment Providers (optional)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    liqpay_public_key: str | None = None
    liqpay_private_key: str | None = None

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def parse_cors(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        json_schema_extra={"env_prefix": ""},
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
