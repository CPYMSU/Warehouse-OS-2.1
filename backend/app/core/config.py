from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Warehouse OS 2.1 API"
    environment: Literal["development", "test", "production"] = "development"
    public_origin: str = ""
    pages_root_domain: str = "apps.bonfirework.org"
    # The runtime frame uses a one-label-per-site origin so Cloudflare's
    # universal ``*.bonfirework.org`` certificate is sufficient while browser
    # storage and database Origin policy remain isolated between sites.
    pages_runtime_root_domain: str = "bonfirework.org"
    pages_scheme: Literal["http", "https"] = "https"
    database_url: str = (
        "postgresql+psycopg://warehouse_os:local-only-change-me@127.0.0.1:5432/warehouse_os"
    )
    migration_database_url: str | None = None
    jwt_secret: str = "development-only-change-before-public-exposure"
    integration_secret: str = "development-only-integration-secret-change-before-public-exposure"
    # Hosted data and the default code tier.  Production binds this root to
    # the mounted HDD; the application never reserves the logical quota here.
    asset_storage_root: Path = Path("var/digital-assets")
    # Explicit opt-in performance tier for core source/build artifacts only.
    asset_code_ssd_root: Path = Path("var/digital-assets-code-ssd")
    # Reserved HDD-backed root for runtime providers' persistent volumes.
    hosted_runtime_data_root: Path = Path("var/hosted-runtime-data")
    # Runtime Controller sees the same directory through the container mount,
    # while Docker Engine needs the corresponding host bind source.
    runtime_host_data_root: Path = Path("var/hosted-runtime-data")
    runtime_docker_socket: Path = Path("/var/run/docker.sock")
    runtime_docker_network: str = "warehouse-os_default"
    runtime_controller_enabled: bool = False
    runtime_controller_poll_seconds: float = 2.0
    runtime_controller_lease_seconds: int = 120
    runtime_controller_stale_seconds: int = 30
    runtime_health_timeout_seconds: int = 90
    # Dynamic hosted applications keep their container and SSD-backed data but
    # release RAM after an idle window. The public gateway requests an in-place
    # restart and waits for the controller's health gate before proxying traffic.
    runtime_idle_suspend_enabled: bool = True
    runtime_idle_timeout_seconds: int = 30 * 60
    runtime_activity_touch_seconds: int = 15
    runtime_lifecycle_scan_seconds: float = 1.0
    runtime_wake_timeout_seconds: float = 30.0
    runtime_wake_health_timeout_seconds: int = 25
    # Observable host path for the independent PostgreSQL data plane whose
    # PGDATA lives on HDD.  The API never opens files below this path directly.
    hosted_database_root: Path = Path("var/hosted-databases")
    # Internal administrator connection used only to provision isolated
    # workspace databases and roles.  It is never returned by an API.
    hosted_database_admin_url: SecretStr = SecretStr("")
    hosted_database_pool_size: int = 2
    hosted_database_connect_timeout_seconds: int = 5
    # Customer-owned PostgreSQL bindings are public-network and TLS-only by
    # default. Private-address access requires an explicitly governed network
    # connector instead of turning a database credential into an SSRF tunnel.
    external_database_allow_private_hosts: bool = False
    external_database_require_tls: bool = True
    # Read-only compatibility mount used while an older local volume is being
    # migrated to the HDD.  New writes never target this path.
    asset_legacy_storage_root: Path | None = None
    # Resumable Source uploads are streamed in fixed-size parts and may use the
    # workspace's full logical quota. Keep the legacy multipart body limit
    # separate so increasing Source capacity cannot create a multi-GiB request.
    source_max_upload_bytes: int = 3 * 1024 * 1024 * 1024
    asset_max_upload_bytes: int = 100 * 1024 * 1024
    research_repository_root: Path = Path("var/research-repositories")
    research_max_upload_bytes: int = 250 * 1024 * 1024
    research_execution_root: Path = Path("var/research-executions")
    research_execution_timeout_seconds: int = 300
    research_execution_max_output_bytes: int = 100 * 1024 * 1024
    workflow_attachment_max_upload_bytes: int = 15 * 1024 * 1024
    shield_agent_socket: Path = Path("/run/warehouse-shield/agent.sock")
    shield_agent_host: str = ""
    shield_agent_port: int = 0
    shield_agent_token: SecretStr = SecretStr("")
    shield_agent_timeout_seconds: float = 8.0
    shield_agent_max_response_bytes: int = 2 * 1024 * 1024
    shield_repair_apply: bool = False
    browser_runtime_enabled: bool = False
    browser_runtime_root: Path = Path("var/browser-runtime")
    browser_worker_token: SecretStr = SecretStr("")
    browser_allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:8080"]
    browser_resource_origins: Annotated[list[str], NoDecode] = [
        "https://static.cloudflareinsights.com",
        "https://cloudflareinsights.com",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "https://unpkg.com",
    ]
    browser_step_timeout_seconds: int = 15
    browser_run_timeout_seconds: int = 120
    jwt_access_token_minutes: int = 60
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Warehouse OS"
    webauthn_origins: Annotated[list[str], NoDecode] = ["http://localhost:8080"]
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

    @field_validator("webauthn_origins", mode="before")
    @classmethod
    def split_webauthn_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("browser_allowed_origins", "browser_resource_origins", mode="before")
    @classmethod
    def split_browser_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]
        return value

    @field_validator("public_origin", mode="before")
    @classmethod
    def normalize_public_origin(cls, value: object) -> object:
        return str(value or "").strip().rstrip("/")

    @field_validator("pages_root_domain", "pages_runtime_root_domain", mode="before")
    @classmethod
    def normalize_pages_domains(cls, value: object) -> object:
        domain = str(value or "").strip().lower().rstrip(".")
        if "://" in domain or "/" in domain or ":" in domain:
            raise ValueError("Warehouse Pages domains must be bare DNS names")
        labels = domain.split(".")
        if len(labels) < 2 or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("Warehouse Pages domains must be valid DNS names")
        return domain

    @model_validator(mode="after")
    def require_production_secret(self) -> Settings:
        if not self.public_origin:
            self.public_origin = (
                str(self.webauthn_origins[0]).rstrip("/")
                if self.webauthn_origins
                else "http://localhost:8080"
            )
        if self.environment == "production" and (
            len(self.jwt_secret) < 32 or "development-only" in self.jwt_secret
        ):
            raise ValueError("WAREHOUSE_JWT_SECRET must be a unique 32+ character secret")
        if self.environment == "production" and (
            len(self.integration_secret) < 32 or "development-only" in self.integration_secret
        ):
            raise ValueError("WAREHOUSE_INTEGRATION_SECRET must be a unique 32+ character secret")
        if self.environment == "production":
            if self.pages_scheme != "https":
                raise ValueError("WAREHOUSE_PAGES_SCHEME must be https in production")
            if not self.public_origin.startswith("https://"):
                raise ValueError("WAREHOUSE_PUBLIC_ORIGIN must be an HTTPS origin")
            if self.webauthn_rp_id in {"localhost", "127.0.0.1"}:
                raise ValueError("WAREHOUSE_WEBAUTHN_RP_ID must be the production domain")
            if not self.webauthn_origins or any(
                not origin.startswith("https://") for origin in self.webauthn_origins
            ):
                raise ValueError("WAREHOUSE_WEBAUTHN_ORIGINS must contain only HTTPS origins")
            if (
                self.browser_runtime_enabled
                and len(self.browser_worker_token.get_secret_value()) < 32
            ):
                raise ValueError(
                    "WAREHOUSE_BROWSER_WORKER_TOKEN must be a unique 32+ character secret"
                )
            if self.browser_runtime_enabled and (
                not self.browser_allowed_origins
                or any(not origin.startswith("https://") for origin in self.browser_allowed_origins)
            ):
                raise ValueError(
                    "WAREHOUSE_BROWSER_ALLOWED_ORIGINS must contain only HTTPS origins"
                )
            if self.browser_runtime_enabled and any(
                not origin.startswith("https://") for origin in self.browser_resource_origins
            ):
                raise ValueError(
                    "WAREHOUSE_BROWSER_RESOURCE_ORIGINS must contain only HTTPS origins"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
