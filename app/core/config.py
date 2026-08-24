from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_SECRETS = {"", "changeme", "secret", "dev-secret-change-me-32-chars-min"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "prod"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str
    opensearch_url: str
    opensearch_index: str = "chunks"
    rabbitmq_url: str

    storage_path: Path = Path("./storage")
    max_upload_mb: int = Field(default=50, gt=0)

    jwt_secret: SecretStr
    jwt_ttl_minutes: int = Field(default=60, gt=0)

    seed_user_email: str | None = None
    seed_user_password: SecretStr | None = None

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @field_validator("database_url")
    @classmethod
    def _require_asyncpg_scheme(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL должен начинаться с postgresql+asyncpg:// — "
                "с другой схемой SQLAlchemy возьмёт синхронный драйвер "
                "и упадёт при создании async-движка"
            )
        return value


class ConfigError(RuntimeError):
    pass


def _guard_prod_secrets(settings: Settings) -> None:
    if settings.app_env != "prod":
        return

    secret = settings.jwt_secret.get_secret_value()
    if secret in WEAK_SECRETS or len(secret) < 32:
        raise ConfigError(
            "JWT_SECRET непригоден для APP_ENV=prod: пустой, "
            "демонстрационный или короче 32 символов"
        )

    password = settings.seed_user_password
    if password is not None and password.get_secret_value() in WEAK_SECRETS:
        raise ConfigError("SEED_USER_PASSWORD непригоден для APP_ENV=prod")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _guard_prod_secrets(settings)
    return settings
