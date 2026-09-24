from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "AARK Kernel Ops"
    APP_VERSION: str = "2.2.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API
    API_SECRET_KEY: str = Field(..., min_length=32)
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50

    # Ollama
    LOCAL_OLLAMA_HOST: str = "http://127.0.0.1:11434"
    DEFAULT_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: int = 60

    # Nobitex
    NOBITEX_API_BASE: str = "https://api.nobitex.ir"
    NOBITEX_TIMEOUT: int = 10

    # Risk Engine
    MAX_PORTFOLIO_ALLOCATION_IRT: float = 10_000_000.0
    MAX_SINGLE_TRADE_PCT: float = 0.20
    MAX_DAILY_LOSS_PCT: float = 0.015

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str | None = None

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()