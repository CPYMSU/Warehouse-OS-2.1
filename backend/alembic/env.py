from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import Connection, engine_from_config, pool

from alembic import context
from app.core.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    settings.migration_database_url or settings.database_url,
)
version_table = str(config.attributes.get("version_table") or "alembic_version")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="app",
        version_table=version_table,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if isinstance(supplied_connection, Connection):
        context.configure(
            connection=supplied_connection,
            version_table_schema="app",
            version_table=version_table,
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            version_table_schema="app",
            version_table=version_table,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
