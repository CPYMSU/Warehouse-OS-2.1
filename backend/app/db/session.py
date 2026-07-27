from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


@contextmanager
def tenant_session(tenant_id: UUID) -> Generator[Session, None, None]:
    """Open one transaction whose PostgreSQL RLS scope is the authenticated tenant."""
    with get_session_factory().begin() as session:
        session.execute(
            text("SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"),
            {"tenant_id": str(tenant_id)},
        )
        yield session


@contextmanager
def system_session() -> Generator[Session, None, None]:
    """Use only for identity lookup and migration/bootstrap administration."""
    with get_session_factory().begin() as session:
        yield session


def database_capabilities() -> dict[str, object] | None:
    """Return the required PostgreSQL 18 and pgvector capabilities, if reachable."""
    try:
        with get_engine().connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT current_setting('server_version_num')::integer AS server_version_num,
                           EXISTS (
                             SELECT 1 FROM pg_extension WHERE extname = 'vector'
                           ) AS pgvector_enabled
                    """
                )
            ).mappings().one()
        return dict(row)
    except Exception:
        return None


def database_is_available() -> bool:
    capabilities = database_capabilities()
    return bool(
        capabilities
        and int(capabilities["server_version_num"]) >= 180000
        and capabilities["pgvector_enabled"]
    )
