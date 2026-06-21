from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import DB_PATH


class Settings(BaseSettings):
    app_name: str = "Local Finance"
    app_version: str = "1.0.0"
    environment: str = "local"
    database_url: str = f"sqlite:///{DB_PATH.as_posix()}"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    bind_host: str = "127.0.0.1"
    demo_seed_enabled: bool = True
    parser_version: str = "universal_csv_v1"

    model_config = SettingsConfigDict(
        env_prefix="LOCAL_FINANCE_",
        env_file="../data/secrets/.env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
