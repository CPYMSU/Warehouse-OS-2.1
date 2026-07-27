"""Database intent types retained by the imported command catalogue.

The command catalogue may describe a logical data access intent, but it never
accepts a connection string, database engine, schema, or tenant selector from
a human or an AI caller.  Concrete command adapters own those decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

DATABASE_EXEC_CAPABILITY = "tenant.raw_sql.write.v1"
DATABASE_QUERY_CAPABILITY = "tenant.raw_sql.read.v1"
DATABASE_SCHEMA_CAPABILITY = "tenant.schema.read.v1"
SCRIPT_RUN_CAPABILITY = "tenant.script.execute.v1"


def generic_sql_capability(logical_store: str, access: str) -> str:
    """Return a fixed capability name for a server-owned logical store."""
    allowed = {
        ("tenant.core", "read"): "tenant.generic_sql.read.v1",
        ("tenant.core", "write"): "tenant.generic_sql.write.v1",
        ("platform.control", "read"): "platform.generic_sql.read.v1",
        ("platform.control", "write"): "platform.generic_sql.write.v1",
    }
    try:
        return allowed[(logical_store, access)]
    except KeyError as exc:
        raise ValueError("unsupported logical-store access") from exc


@dataclass(frozen=True)
class DataAccessIntent:
    """An immutable, non-secret description of one command's data access."""

    logical_store: str
    tenant: str | None
    operation: str
    access: str
    capability: str
    origin: str
    execution_id: str | None = None
