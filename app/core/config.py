from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="csv-job-platform", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/csv_job_platform",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    upload_dir: str = Field(default="uploads", alias="UPLOAD_DIR")
    max_upload_size_bytes: int = Field(
        default=5_242_880,
        alias="MAX_UPLOAD_SIZE_BYTES",
    )
    redis_url: str = Field(default="redis://localhost:6380/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6380/0",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6380/1",
        alias="CELERY_RESULT_BACKEND",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
