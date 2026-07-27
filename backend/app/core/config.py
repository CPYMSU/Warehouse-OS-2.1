from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Warehouse OS 2.1 API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "postgresql+psycopg://warehouse_os:local-only-change-me@127.0.0.1:5432/warehouse_os"
    )
    migration_database_url: str | None = None
    jwt_secret: str = "development-only-change-before-public-exposure"
    jwt_access_token_minutes: int = 60
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WAREHOUSE_",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def require_production_secret(self) -> Settings:
        if self.environment == "production" and (
            len(self.jwt_secret) < 32 or "development-only" in self.jwt_secret
        ):
            raise ValueError("WAREHOUSE_JWT_SECRET must be a unique 32+ character secret")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
