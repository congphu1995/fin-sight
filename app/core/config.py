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

    # --- Background refresh (Tier 1) ---
    # The in-process scheduler runs the reports pipeline every N hours so the DB
    # stays fresh on its own. 0 disables it (e.g. when an external cron drives it).
    refresh_interval_hours: float = 6.0
    refresh_on_startup: bool = False
    refresh_timeout_seconds: float = 1800.0

    # --- MCP server ---
    # Mira authenticates to /mcp with this static bearer token. Empty = no auth
    # (acceptable only on a private tailnet); set a random value in prod.
    mcp_auth_token: SecretStr = SecretStr("")
    mcp_path: str = "/mcp"

    # --- SSI FastConnect Data (Tier 2, market data) — https://fc-data.ssi.com.vn ---
    ssi_data_consumer_id: SecretStr = SecretStr("")
    ssi_data_consumer_secret: SecretStr = SecretStr("")
    ssi_data_url: str = "https://fc-data.ssi.com.vn/"

    # --- SSI FastConnect Trading (Tier 2, personal account, READ-ONLY) ---
    # https://fc-tradeapi.ssi.com.vn — PIN 2FA (twoFactorType=0) for headless login.
    ssi_trading_consumer_id: SecretStr = SecretStr("")
    ssi_trading_consumer_secret: SecretStr = SecretStr("")
    # Multi-line RSA PEM lives in a mounted file, not inline in env.
    ssi_trading_private_key_path: str = "secrets/ssi_private_key.pem"
    ssi_trading_pin: SecretStr = SecretStr("")
    ssi_trading_account_id: str = ""
    ssi_trading_url: str = "https://fc-tradeapi.ssi.com.vn/"

    # Short-TTL cache for live SSI responses (cuts per-key rate-limit pressure).
    ssi_cache_ttl_seconds: float = 60.0

    @property
    def ssi_data_enabled(self) -> bool:
        return bool(
            self.ssi_data_consumer_id.get_secret_value()
            and self.ssi_data_consumer_secret.get_secret_value()
        )

    @property
    def ssi_trading_enabled(self) -> bool:
        return bool(
            self.ssi_trading_consumer_id.get_secret_value()
            and self.ssi_trading_consumer_secret.get_secret_value()
            and self.ssi_trading_pin.get_secret_value()
            and self.ssi_trading_account_id
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
