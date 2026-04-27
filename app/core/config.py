from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://finsight:finsight@localhost:5432/finsight"

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-flash-lite-latest"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: SecretStr = SecretStr("minioadmin")
    minio_secret_key: SecretStr = SecretStr("minioadmin")
    minio_bucket: str = "finsight-reports"
    minio_secure: bool = False

    crawl_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    crawl_request_delay_seconds: float = 1.0
    crawl_default_lookback_days: int = 365
    crawl_max_retries: int = 3
    crawl_batch_size: int = 50


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
